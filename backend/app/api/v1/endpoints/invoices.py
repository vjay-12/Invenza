import io
import os
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_tenant_id, get_current_user
from app.models.tenant import Tenant
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, TenantSettings, TenantInvoiceSequence
from app.models.order import SalesOrder, SalesOrderItem
from app.models.user import User, UserRole
from app.schemas.invoice import (
    InvoiceResponse,
    InvoicePaymentRequest,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.invoice_pdf_generator import InvoicePdfGenerator
from app.services.storage import StorageService
from app.services.tax_service import currency_symbol, get_org_tax_context

router = APIRouter()

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    List all issued/void invoices for the current tenant with optional filtering.
    """
    stmt = select(Invoice).options(selectinload(Invoice.items)).where(Invoice.tenant_id == tenant_id)
    if status_filter and status_filter.lower() != "all":
        stmt = stmt.where(Invoice.status == status_filter.lower())
    if search:
        s = f"%{search}%"
        stmt = stmt.where(or_(Invoice.invoice_number.ilike(s), Invoice.customer_name.ilike(s)))

    stmt = stmt.order_by(desc(Invoice.invoice_date))
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/settings/company", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the legal invoicing profile and bank settings for the tenant.
    """
    org_ctx = await get_org_tax_context(db, tenant_id)
    country_code = org_ctx.get("country_code", "IN")
    is_india = country_code == "IN"
    tax_type = org_ctx.get("tax_type", "GST")
    currency = org_ctx.get("currency_code", "INR")

    res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    sett = res.scalar_one_or_none()
    if not sett:
        # Create default tenant settings per org context
        if is_india:
            sett = TenantSettings(
                tenant_id=tenant_id,
                legal_business_name=org_ctx.get("company_name") or "Invenza Enterprise Ltd",
                gstin="29AABCI1234F1Z5",
                pan="AABCI1234F",
                registered_address="Outer Ring Road, Bengaluru, Karnataka 560103",
                state="Karnataka",
                state_code="29",
                authorized_signatory_name="Vijay B",
                bank_name="HDFC Bank",
                bank_account_number="50200012345678",
                bank_ifsc_code="HDFC0001234",
                bank_branch="Koramangala 5th Block, Bengaluru",
                account_holder_name="Invenza Enterprise Ltd",
                invoice_prefix="INV",
                auto_email_invoice=False,
            )
        else:
            sett = TenantSettings(
                tenant_id=tenant_id,
                legal_business_name=org_ctx.get("company_name") or "Enterprise Ltd",
                gstin="",
                pan="",
                registered_address=org_ctx.get("country_name", "Corporate Office"),
                state=org_ctx.get("state") or org_ctx.get("country_name", ""),
                state_code=org_ctx.get("state_code") or country_code,
                authorized_signatory_name="Authorized Signatory",
                bank_name="",
                bank_account_number="",
                bank_ifsc_code="",
                bank_branch="",
                account_holder_name=org_ctx.get("company_name") or "Enterprise Ltd",
                invoice_prefix="INV",
                auto_email_invoice=False,
            )
        db.add(sett)
        await db.commit()
        await db.refresh(sett)
    else:
        # Auto-heal legacy dummy seed if present on non-Indian org
        needs_commit = False
        if not is_india and sett.pan == "AABCI1234F":
            sett.pan = ""
            needs_commit = True
        if not is_india and sett.state_code == "29":
            sett.state_code = org_ctx.get("state_code") or country_code
            sett.state = org_ctx.get("state") or org_ctx.get("country_name", "")
            needs_commit = True
        if needs_commit:
            await db.commit()
            await db.refresh(sett)

    resp = TenantSettingsResponse.model_validate(sett)
    resp.tax_type = tax_type
    resp.country_code = country_code
    resp.currency_code = currency
    resp.tax_id = sett.gstin
    resp.vat_id = sett.gstin
    resp.tax_reg_number = sett.gstin
    resp.national_tax_id = sett.pan
    resp.bank_routing_code = sett.bank_ifsc_code
    return resp

@router.put("/settings/company", response_model=TenantSettingsResponse)
async def update_tenant_settings(
    payload: TenantSettingsUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Update tenant's legal invoicing profile, GSTIN/VAT/Tax ID, and bank remittance details.
    """
    org_ctx = await get_org_tax_context(db, tenant_id)
    res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    sett = res.scalar_one_or_none()
    if not sett:
        sett = TenantSettings(tenant_id=tenant_id)
        db.add(sett)

    update_data = payload.dict(exclude_unset=True)
    virtual_fields = {"tax_id", "vat_id", "tax_reg_number", "national_tax_id", "bank_routing_code", "ein", "steuernummer"}
    for k, v in update_data.items():
        if k not in virtual_fields and v is not None:
            setattr(sett, k, v)

    sett.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(sett)

    resp = TenantSettingsResponse.model_validate(sett)
    resp.tax_type = org_ctx.get("tax_type", "GST")
    resp.country_code = org_ctx.get("country_code", "IN")
    resp.currency_code = org_ctx.get("currency_code", "INR")
    resp.tax_id = sett.gstin
    resp.vat_id = sett.gstin
    resp.tax_reg_number = sett.gstin
    resp.national_tax_id = sett.pan
    resp.bank_routing_code = sett.bank_ifsc_code
    return resp

@router.post("/settings/upload-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload company logo to object storage.
    """
    content = await file.read()
    ext = os.path.splitext(file.filename)[1] or ".png"
    object_name = f"logos/{tenant_id}/logo{ext}"

    try:
        StorageService.upload_file(content, object_name, content_type=file.content_type)
        url = f"/api/v1/storage/files/{object_name}"
    except Exception:
        url = f"/uploads/logos/{tenant_id}_logo{ext}"

    res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    sett = res.scalar_one_or_none()
    if sett:
        sett.logo_url = url
        await db.commit()

    return {"logo_url": url}

@router.post("/settings/upload-signature")
async def upload_authorized_signature(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload authorized signatory image to object storage.
    """
    content = await file.read()
    ext = os.path.splitext(file.filename)[1] or ".png"
    object_name = f"signatures/{tenant_id}/sign{ext}"

    try:
        StorageService.upload_file(content, object_name, content_type=file.content_type)
        url = f"/api/v1/storage/files/{object_name}"
    except Exception:
        url = f"/uploads/signatures/{tenant_id}_sign{ext}"

    res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    sett = res.scalar_one_or_none()
    if sett:
        sett.signature_url = url
        await db.commit()

    return {"signature_url": url}

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv

@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: UUID,
    token: Optional[str] = Query(None),
    download: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream or download the generated GST Tax Invoice PDF.
    Retrieves from MinIO under {company_code}/sales/invoices/{invoice_number}.pdf
    """
    # 1. Fetch invoice by ID
    res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # 2. Authentication verification (Bearer header or Query token)
    token_to_verify = None
    if authorization and authorization.startswith("Bearer "):
        token_to_verify = authorization.split(" ")[1]
    elif token:
        token_to_verify = token

    if token_to_verify:
        try:
            payload = jwt.decode(token_to_verify, settings.SECRET_KEY, algorithms=["HS256"])
            user_id_str = payload.get("sub")
            if user_id_str:
                u_res = await db.execute(select(User).where(User.id == UUID(user_id_str)))
                current_user = u_res.scalar_one_or_none()
                if current_user and current_user.role not in [UserRole.SUPER_ADMIN.value, "super_admin"]:
                    if current_user.tenant_id != inv.tenant_id:
                        raise HTTPException(status_code=403, detail="Unauthorized access to this invoice")
        except HTTPException:
            raise
        except Exception:
            pass

    # 3. Resolve Tenant company unique_code
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == inv.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    comp_code = (tenant.unique_code or tenant.company_code or "DEFAULT").upper()

    safe_num = inv.invoice_number.replace("/", "_")
    expected_storage_key = f"{comp_code}/sales/data/{safe_num}.pdf"
    alt_storage_key = f"{comp_code}/sales/invoices/{safe_num}.pdf"
    storage_key = inv.pdf_storage_key or expected_storage_key

    # 4. Try fetching from MinIO
    pdf_bytes = StorageService.get_file_bytes(storage_key)
    if not pdf_bytes and storage_key != expected_storage_key:
        pdf_bytes = StorageService.get_file_bytes(expected_storage_key)
    if not pdf_bytes and storage_key != alt_storage_key:
        pdf_bytes = StorageService.get_file_bytes(alt_storage_key)

    # 5. If not in MinIO or needs regeneration, render dynamically & save to MinIO
    if not pdf_bytes:
        items_res = await db.execute(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id))
        items = items_res.scalars().all()

        sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == inv.tenant_id))
        sett = sett_res.scalar_one_or_none()

        so_number = "N/A"
        if inv.sales_order_id:
            so_res = await db.execute(select(SalesOrder.so_number).where(SalesOrder.id == inv.sales_order_id))
            so_row = so_res.first()
            if so_row:
                so_number = so_row[0]

        invoice_dict = {
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat(),
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "place_of_supply": inv.place_of_supply,
            "status": inv.status.value,
            "seller_legal_name": inv.seller_legal_name,
            "seller_gstin": inv.seller_gstin,
            "seller_pan": inv.seller_pan,
            "seller_address": inv.seller_address,
            "seller_state": inv.seller_state,
            "seller_state_code": inv.seller_state_code,
            "customer_name": inv.customer_name,
            "customer_gstin": inv.customer_gstin,
            "customer_billing_address": inv.customer_billing_address,
            "customer_shipping_address": inv.customer_shipping_address,
            "customer_state": inv.customer_state,
            "customer_state_code": inv.customer_state_code,
            "is_inter_state": inv.is_inter_state,
            "tax_type": inv.tax_type or "GST",
            "currency_code": inv.currency_code or "INR",
            "currency_symbol": currency_symbol(inv.currency_code),
            "total_single_tax": float(inv.total_single_tax),
            "payment_terms": inv.payment_terms,
            "total_taxable_value": float(inv.total_taxable_value),
            "total_cgst": float(inv.total_cgst),
            "total_sgst": float(inv.total_sgst),
            "total_igst": float(inv.total_igst),
            "round_off": float(inv.round_off),
            "grand_total": float(inv.grand_total),
            "grand_total_words": inv.grand_total_words,
            "so_number": so_number,
            "bank_name": sett.bank_name if sett and sett.bank_name else ("HDFC Bank" if inv.tax_type == "GST" else ""),
            "bank_account_number": sett.bank_account_number if sett and sett.bank_account_number else ("50200012345678" if inv.tax_type == "GST" else ""),
            "bank_ifsc_code": sett.bank_ifsc_code if sett and sett.bank_ifsc_code else ("HDFC0001234" if inv.tax_type == "GST" else ""),
            "bank_branch": sett.bank_branch if sett and sett.bank_branch else ("Koramangala 5th Block, Bengaluru" if inv.tax_type == "GST" else ""),
            "account_holder_name": sett.account_holder_name if sett else inv.seller_legal_name,
            "authorized_signatory_name": sett.authorized_signatory_name if sett else "Authorized Signatory",
            "items": [
                {
                    "item_description": it.item_description,
                    "hsn_code": it.hsn_code,
                    "quantity": float(it.quantity),
                    "unit_of_measure": it.unit_of_measure,
                    "unit_price": float(it.unit_price),
                    "discount": float(it.discount),
                    "taxable_value": float(it.taxable_value),
                    "gst_rate": float(it.gst_rate),
                    "cgst_rate": float(it.cgst_rate),
                    "cgst_amount": float(it.cgst_amount),
                    "sgst_rate": float(it.sgst_rate),
                    "sgst_amount": float(it.sgst_amount),
                    "igst_rate": float(it.igst_rate),
                    "igst_amount": float(it.igst_amount),
                    "total": float(it.total),
                }
                for it in items
            ],
        }

        pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(invoice_dict)
        try:
            StorageService.upload_file(pdf_bytes, expected_storage_key, content_type="application/pdf")
            inv.pdf_storage_key = expected_storage_key
            await db.commit()
        except Exception as e:
            print(f"[MinIO Storage Upload Notice]: {e}")

    disposition = "attachment" if download else "inline"
    safe_filename = f"Tax_Invoice_{inv.invoice_number.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
            "Content-Type": "application/pdf",
        },
    )

@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Void an invoice. The invoice number is permanently preserved and never reused.
    The PDF will automatically display the 'VOID INVOICE' watermark.
    """
    res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv.status = InvoiceStatus.VOID
    inv.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(inv)
    return inv

@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: UUID,
    payload: Optional[InvoicePaymentRequest] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an issued invoice as Paid once customer payment is recorded/confirmed.
    Voided invoices cannot be marked as paid.
    """
    res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if inv.status == InvoiceStatus.VOID:
        raise HTTPException(status_code=400, detail="Cannot record payment on a voided invoice")

    inv.status = InvoiceStatus.PAID
    inv.paid_at = (payload.paid_at if payload and payload.paid_at else None) or datetime.utcnow()
    inv.payment_method = (payload.payment_method if payload and payload.payment_method else None) or "Bank Transfer"
    if payload and payload.payment_reference:
        inv.payment_reference = payload.payment_reference
    inv.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(inv)
    return inv

