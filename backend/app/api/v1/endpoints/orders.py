import uuid
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from jose import jwt

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.user import User, UserRole
from app.models.order import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from app.models.product import Product
from app.models.location import Location
from app.models.ledger import MovementTypeEnum
from app.models.tenant import Tenant
from app.models.invoice import TenantSettings, TenantInvoiceSequence, Invoice, InvoiceItem, InvoiceStatus
from app.schemas.order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    SalesOrderCreate,
    SalesOrderResponse,
    ReceiveGoodsRequest,
    FulfillOrderRequest,
)
from app.services.ledger_service import LedgerService
from app.services.gst_service import GSTService
from app.services.invoice_pdf_generator import InvoicePdfGenerator
from app.services.storage import StorageService

router = APIRouter()

# --- Purchase Orders & GRN ---

@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == tenant_id)
        .order_by(desc(PurchaseOrder.order_date))
    )
    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = []
    for o in orders:
        loc_res = await db.execute(select(Location.name).where(Location.id == o.target_location_id))
        loc_name = loc_res.scalar_one_or_none() or "Main Hub"

        items_res = await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == o.id))
        items = items_res.scalars().all()

        item_responses = []
        for it in items:
            p_res = await db.execute(select(Product.name, Product.sku).where(Product.id == it.product_id))
            p_row = p_res.first()
            item_responses.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": p_row[0] if p_row else "Unknown",
                "sku": p_row[1] if p_row else "SKU",
                "ordered_qty": float(it.ordered_qty),
                "received_qty": float(it.received_qty),
                "unit_cost": float(it.unit_cost),
            })

        output.append(
            PurchaseOrderResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                po_number=o.po_number,
                supplier_name=o.supplier_name,
                status=o.status,
                target_location_id=o.target_location_id,
                target_location_name=loc_name,
                total_amount=float(o.total_amount),
                notes=o.notes,
                order_date=o.order_date,
                received_date=o.received_date,
                items=item_responses,
            )
        )
    return output

@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_in: PurchaseOrderCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    count_res = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id))
    count = len(count_res.scalars().all()) + 1
    po_number = f"PO-2026-{count:03d}"

    total_amount = sum(it.ordered_qty * it.unit_cost for it in po_in.items)

    po = PurchaseOrder(
        tenant_id=tenant_id,
        po_number=po_number,
        supplier_name=po_in.supplier_name,
        target_location_id=po_in.target_location_id,
        total_amount=total_amount,
        notes=po_in.notes,
        order_date=po_in.order_date or datetime.utcnow(),
    )
    db.add(po)
    await db.flush()

    items_out = []
    for it in po_in.items:
        line = PurchaseOrderItem(
            order_id=po.id,
            product_id=it.product_id,
            ordered_qty=it.ordered_qty,
            received_qty=0.0,
            unit_cost=it.unit_cost,
        )
        db.add(line)
        await db.flush()
        items_out.append({
            "id": line.id,
            "product_id": line.product_id,
            "ordered_qty": float(line.ordered_qty),
            "received_qty": 0.0,
            "unit_cost": float(line.unit_cost),
        })

    await db.commit()
    await db.refresh(po)

    return PurchaseOrderResponse(
        id=po.id,
        tenant_id=po.tenant_id,
        po_number=po.po_number,
        supplier_name=po.supplier_name,
        status=po.status,
        target_location_id=po.target_location_id,
        total_amount=float(po.total_amount),
        notes=po.notes,
        order_date=po.order_date,
        items=items_out,
    )

@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_goods_grn(
    po_id: UUID,
    payload: ReceiveGoodsRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(PurchaseOrder).where(and_(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id)))
    po = res.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if po.status == OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="PO already received")

    items_res = await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == po.id))
    items = items_res.scalars().all()

    for it in items:
        it.received_qty = it.ordered_qty
        await LedgerService.record_movement(
            db=db,
            tenant_id=po.tenant_id,
            product_id=it.product_id,
            location_id=po.target_location_id,
            movement_type=MovementTypeEnum.IN,
            quantity=float(it.ordered_qty),
            unit_cost=float(it.unit_cost),
            reference_type="PO",
            reference_id=po.po_number,
            performed_by=payload.received_by or "Admin",
        )

    po.status = OrderStatus.COMPLETED
    po.received_date = datetime.utcnow()
    if payload.notes:
        po.notes = f"{po.notes or ''} [GRN: {payload.notes}]"

    await db.commit()
    await db.refresh(po)
    return await list_purchase_orders(tenant_id, db)

# --- Sales Orders & Fulfillment ---

@router.get("/sales-orders", response_model=List[SalesOrderResponse])
async def list_sales_orders(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SalesOrder)
        .where(SalesOrder.tenant_id == tenant_id)
        .order_by(desc(SalesOrder.order_date))
    )
    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = []
    for o in orders:
        loc_res = await db.execute(select(Location.name).where(Location.id == o.source_location_id))
        loc_name = loc_res.scalar_one_or_none() or "Main Hub"

        items_res = await db.execute(select(SalesOrderItem).where(SalesOrderItem.order_id == o.id))
        items = items_res.scalars().all()

        item_responses = []
        for it in items:
            p_res = await db.execute(select(Product.name, Product.sku).where(Product.id == it.product_id))
            p_row = p_res.first()
            item_responses.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": p_row[0] if p_row else "Unknown",
                "sku": p_row[1] if p_row else "SKU",
                "ordered_qty": float(it.ordered_qty),
                "fulfilled_qty": float(it.fulfilled_qty),
                "unit_price": float(it.unit_price),
            })

        output.append(
            SalesOrderResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                so_number=o.so_number,
                customer_name=o.customer_name,
                customer_gstin=o.customer_gstin,
                billing_address=o.billing_address,
                shipping_address=o.shipping_address,
                state=o.state,
                state_code=o.state_code,
                billing_state=o.billing_state,
                billing_state_code=o.billing_state_code,
                shipping_state=o.shipping_state,
                shipping_state_code=o.shipping_state_code,
                invoice_id=o.invoice_id,
                status=o.status,
                source_location_id=o.source_location_id,
                source_location_name=loc_name,
                total_amount=float(o.total_amount),
                notes=o.notes,
                order_date=o.order_date,
                fulfilled_date=o.fulfilled_date,
                items=item_responses,
            )
        )
    return output

@router.post("/sales-orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    so_in: SalesOrderCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    count_res = await db.execute(select(SalesOrder).where(SalesOrder.tenant_id == tenant_id))
    count = len(count_res.scalars().all()) + 1
    so_number = f"SO-2026-{count:03d}"

    total_amount = sum(
        float(it.ordered_qty) * (float(it.unit_price) * (1.0 - (float(getattr(it, "discount_percent", 0.0) or 0.0) / 100.0)))
        for it in so_in.items
    )

    b_state = so_in.billing_state or so_in.state or "Karnataka"
    b_code = so_in.billing_state_code or so_in.state_code or "29"
    norm_b_code, norm_b_state = GSTService.normalize_state_code(b_code or b_state)

    s_state = so_in.shipping_state
    s_code = so_in.shipping_state_code
    if s_state or s_code:
        norm_s_code, norm_s_state = GSTService.normalize_state_code(s_code or s_state)
    else:
        norm_s_code, norm_s_state = None, None

    so = SalesOrder(
        tenant_id=tenant_id,
        so_number=so_number,
        customer_name=so_in.customer_name,
        customer_gstin=so_in.customer_gstin,
        billing_address=so_in.billing_address,
        shipping_address=so_in.shipping_address,
        state=norm_b_state or b_state,
        state_code=norm_b_code or b_code,
        billing_state=norm_b_state or b_state,
        billing_state_code=norm_b_code or b_code,
        shipping_state=norm_s_state or s_state,
        shipping_state_code=norm_s_code or s_code,
        source_location_id=so_in.source_location_id,
        total_amount=total_amount,
        notes=so_in.notes,
        order_date=so_in.order_date or datetime.utcnow(),
    )
    db.add(so)
    await db.flush()

    items_out = []
    for it in so_in.items:
        line = SalesOrderItem(
            order_id=so.id,
            product_id=it.product_id,
            ordered_qty=it.ordered_qty,
            fulfilled_qty=0.0,
            unit_price=it.unit_price,
        )
        db.add(line)
        await db.flush()
        items_out.append({
            "id": line.id,
            "product_id": line.product_id,
            "ordered_qty": float(line.ordered_qty),
            "fulfilled_qty": 0.0,
            "unit_price": float(line.unit_price),
        })

    await db.commit()
    await db.refresh(so)

    loc_res = await db.execute(select(Location.name).where(Location.id == so.source_location_id))
    loc_name = loc_res.scalar_one_or_none() or "Main Hub"

    return SalesOrderResponse(
        id=so.id,
        tenant_id=so.tenant_id,
        so_number=so.so_number,
        customer_name=so.customer_name,
        customer_gstin=so.customer_gstin,
        billing_address=so.billing_address,
        shipping_address=so.shipping_address,
        state=so.state,
        state_code=so.state_code,
        billing_state=so.billing_state,
        billing_state_code=so.billing_state_code,
        shipping_state=so.shipping_state,
        shipping_state_code=so.shipping_state_code,
        invoice_id=so.invoice_id,
        status=so.status,
        source_location_id=so.source_location_id,
        source_location_name=loc_name,
        total_amount=float(so.total_amount),
        notes=so.notes,
        order_date=so.order_date,
        items=items_out,
    )

@router.post("/sales-orders/{so_id}/fulfill")
async def fulfill_sales_order(
    so_id: UUID,
    payload: FulfillOrderRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(SalesOrder).where(and_(SalesOrder.id == so_id, SalesOrder.tenant_id == tenant_id)))
    so = res.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status == OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Sales order already fulfilled")

    # 1. Pre-validation: Check Tenant Invoicing Settings & Registered Business State
    sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    sett = sett_res.scalar_one_or_none()
    if not sett or not sett.gstin or not sett.registered_address or not sett.bank_account_number:
        raise HTTPException(
            status_code=400,
            detail="Incomplete company invoicing settings. Please configure legal business name, GSTIN, registered address, and bank details in Settings before fulfilling orders.",
        )
    if not sett.state or not str(sett.state).strip():
        raise HTTPException(
            status_code=400,
            detail="Cannot generate invoice: Tenant registered business state is missing in company settings. Please configure supplier state in Settings.",
        )

    # 2. Pre-validation: Check Customer Address & Resolve Place of Supply
    if not so.billing_address and not so.shipping_address:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate invoice: Customer address (billing or shipping) is required before an invoice can be generated.",
        )

    pos_code, pos_name = GSTService.resolve_place_of_supply(
        billing_state=so.billing_state,
        billing_state_code=so.billing_state_code,
        billing_address=so.billing_address,
        shipping_state=so.shipping_state,
        shipping_state_code=so.shipping_state_code,
        shipping_address=so.shipping_address,
        customer_gstin=so.customer_gstin,
        legacy_state=so.state,
        legacy_state_code=so.state_code,
    )
    if not pos_code or not pos_name:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate invoice: Customer Place of Supply state could not be resolved. Please specify a valid billing or shipping state.",
        )

    # 3. Pre-validation: Check Products Tax Data & Stock
    items_res = await db.execute(select(SalesOrderItem).where(SalesOrderItem.order_id == so.id))
    items = items_res.scalars().all()

    products_map = {}
    for it in items:
        p_res = await db.execute(select(Product).where(Product.id == it.product_id))
        p = p_res.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=400, detail="Product for line item not found")
        if not p.hsn_code or not str(p.hsn_code).strip() or p.gst_rate is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot fulfill order: SKU '{p.sku}' ({p.name}) is missing required HSN/SAC code or GST rate. Please update product tax data before generating an invoice.",
            )
        products_map[it.product_id] = p

        avail = await LedgerService.get_current_stock(db, so.tenant_id, it.product_id, so.source_location_id)
        if avail < float(it.ordered_qty):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{p.name}'. Available: {avail}, Ordered: {it.ordered_qty}",
            )

    # 4. Write stock deduction to ledger
    for it in items:
        it.fulfilled_qty = it.ordered_qty
        await LedgerService.record_movement(
            db=db,
            tenant_id=so.tenant_id,
            product_id=it.product_id,
            location_id=so.source_location_id,
            movement_type=MovementTypeEnum.OUT,
            quantity=float(it.ordered_qty),
            unit_cost=0.0,
            reference_type="SO",
            reference_id=so.so_number,
            performed_by=payload.dispatched_by or "Dispatch Lead",
        )

    so.status = OrderStatus.COMPLETED
    so.fulfilled_date = datetime.utcnow()

    # 5. Strict Unbroken Sequential Invoice Numbering with Row-Level Locking
    seq_res = await db.execute(
        select(TenantInvoiceSequence)
        .where(TenantInvoiceSequence.tenant_id == tenant_id)
        .with_for_update()
    )
    seq = seq_res.scalar_one_or_none()
    if not seq:
        seq = TenantInvoiceSequence(tenant_id=tenant_id, fiscal_year="2026-27", current_number=1)
        db.add(seq)
    else:
        seq.current_number += 1
        seq.updated_at = datetime.utcnow()

    prefix = sett.invoice_prefix or "INV"
    inv_number = f"{prefix}/{seq.fiscal_year}/{seq.current_number:05d}"

    # 6. Compute GST Tax Split based on Place of Supply
    calc_items = []
    for it in items:
        prod = products_map[it.product_id]
        calc_items.append({
            "product_id": it.product_id,
            "item_description": prod.name,
            "hsn_code": prod.hsn_code,
            "quantity": float(it.ordered_qty),
            "unit_of_measure": prod.unit_of_measure or "pcs",
            "unit_price": float(it.unit_price),
            "discount": 0.0,
            "gst_rate": float(prod.gst_rate),
        })

    seller_code = sett.state_code or sett.state or "29"
    tax_calc = GSTService.calculate_invoice_taxes(seller_code, pos_code, calc_items)

    # Resolve company unique_code for MinIO object path
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    comp_code = (tenant.unique_code or tenant.company_code or "DEFAULT").upper()
    safe_inv_num = inv_number.replace('/', '_')
    pdf_key = f"{comp_code}/sales/data/{safe_inv_num}.pdf"

    # 7. Create Invoice Record with Snapshot of GST Rates and Breakdowns
    invoice_id = uuid.uuid4()
    invoice = Invoice(
        id=invoice_id,
        tenant_id=tenant_id,
        invoice_number=inv_number,
        sales_order_id=so.id,
        invoice_date=datetime.utcnow(),
        due_date=datetime.utcnow(),
        place_of_supply=tax_calc["place_of_supply"],
        status=InvoiceStatus.ISSUED,
        seller_legal_name=sett.legal_business_name,
        seller_gstin=sett.gstin,
        seller_pan=sett.pan,
        seller_address=sett.registered_address,
        seller_state=sett.state,
        seller_state_code=sett.state_code,
        customer_name=so.customer_name,
        customer_gstin=so.customer_gstin,
        customer_billing_address=so.billing_address or so.shipping_address or sett.registered_address,
        customer_shipping_address=so.shipping_address or so.billing_address or sett.registered_address,
        customer_state=tax_calc["customer_state"],
        customer_state_code=tax_calc["customer_state_code"],
        is_inter_state=tax_calc["is_inter_state"],
        total_taxable_value=tax_calc["total_taxable_value"],
        total_cgst=tax_calc["total_cgst"],
        total_sgst=tax_calc["total_sgst"],
        total_igst=tax_calc["total_igst"],
        round_off=tax_calc["round_off"],
        grand_total=tax_calc["grand_total"],
        grand_total_words=tax_calc["grand_total_words"],
        pdf_storage_key=pdf_key,
        pdf_url=f"/api/v1/invoices/{invoice_id}/pdf",
    )
    db.add(invoice)
    await db.flush()

    for cit in tax_calc["items"]:
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            product_id=cit["product_id"],
            item_description=cit["item_description"],
            hsn_code=cit["hsn_code"],
            quantity=cit["quantity"],
            unit_of_measure=cit["unit_of_measure"],
            unit_price=cit["unit_price"],
            discount=cit["discount"],
            taxable_value=cit["taxable_value"],
            gst_rate=cit["gst_rate"],
            cgst_rate=cit["cgst_rate"],
            cgst_amount=cit["cgst_amount"],
            sgst_rate=cit["sgst_rate"],
            sgst_amount=cit["sgst_amount"],
            igst_rate=cit["igst_rate"],
            igst_amount=cit["igst_amount"],
            total=cit["total"],
        ))

    so.invoice_id = invoice.id
    await db.commit()

    # 7. Generate & Store Vector PDF in MinIO / Object Storage
    pdf_payload = {
        "invoice_number": inv_number,
        "invoice_date": invoice.invoice_date.isoformat(),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "place_of_supply": invoice.place_of_supply,
        "status": "issued",
        "seller_legal_name": invoice.seller_legal_name,
        "seller_gstin": invoice.seller_gstin,
        "seller_pan": invoice.seller_pan,
        "seller_address": invoice.seller_address,
        "seller_state": invoice.seller_state,
        "seller_state_code": invoice.seller_state_code,
        "customer_name": invoice.customer_name,
        "customer_gstin": invoice.customer_gstin,
        "customer_billing_address": invoice.customer_billing_address,
        "customer_shipping_address": invoice.customer_shipping_address,
        "customer_state": invoice.customer_state,
        "customer_state_code": invoice.customer_state_code,
        "is_inter_state": invoice.is_inter_state,
        "payment_terms": invoice.payment_terms,
        "so_number": so.so_number,
        "bank_name": sett.bank_name,
        "bank_account_number": sett.bank_account_number,
        "bank_ifsc_code": sett.bank_ifsc_code,
        "bank_branch": sett.bank_branch,
        "account_holder_name": sett.account_holder_name,
        "authorized_signatory_name": sett.authorized_signatory_name,
        **tax_calc,
    }

    try:
        pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(pdf_payload)
        StorageService.upload_file(pdf_bytes, pdf_key, content_type="application/pdf")
    except Exception as e:
        print(f"[Invoice PDF Storage Notice]: {e}")

    return {
        "message": f"Sales Order {so.so_number} fulfilled, stock deducted, and GST Tax Invoice {inv_number} issued.",
        "invoice_id": str(invoice.id),
        "invoice_number": inv_number,
        "pdf_url": f"/api/v1/invoices/{invoice.id}/pdf",
    }

@router.get("/sales-orders/{so_id}/pdf")
async def download_sales_order_pdf(
    so_id: UUID,
    token: Optional[str] = Query(None),
    download: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream or download a Sales Order / Tax Invoice PDF from MinIO.
    Stored under: {company_unique_code}/sales/data/{invoice_or_so_number}.pdf
    """
    res = await db.execute(select(SalesOrder).where(SalesOrder.id == so_id))
    so = res.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")

    # Verify authorization if provided
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
                    if current_user.tenant_id != so.tenant_id:
                        raise HTTPException(status_code=403, detail="Unauthorized access to this sales order")
        except HTTPException:
            raise
        except Exception:
            pass

    # Resolve company unique_code
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == so.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    comp_code = (tenant.unique_code or tenant.company_code or "DEFAULT").upper()

    sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == so.tenant_id))
    sett = sett_res.scalar_one_or_none()

    # Case A: If order has an invoice associated, fetch invoice PDF
    if so.invoice_id:
        inv_res = await db.execute(select(Invoice).where(Invoice.id == so.invoice_id))
        inv = inv_res.scalar_one_or_none()
        if inv:
            safe_inv = inv.invoice_number.replace("/", "_")
            primary_key = inv.pdf_storage_key or f"{comp_code}/sales/data/{safe_inv}.pdf"
            alt_key = f"{comp_code}/sales/invoices/{safe_inv}.pdf"

            pdf_bytes = StorageService.get_file_bytes(primary_key)
            if not pdf_bytes:
                pdf_bytes = StorageService.get_file_bytes(f"{comp_code}/sales/data/{safe_inv}.pdf")
            if not pdf_bytes:
                pdf_bytes = StorageService.get_file_bytes(alt_key)

            if pdf_bytes:
                disposition = "attachment" if download else "inline"
                safe_filename = f"Tax_Invoice_{safe_inv}.pdf"
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
                        "Content-Type": "application/pdf",
                    },
                )

    # Case B: Pending Sales Order (or invoice not yet generated) -> Generate Sales Order Confirmation PDF
    safe_so_num = so.so_number.replace("/", "_")
    storage_key = f"{comp_code}/sales/data/{safe_so_num}.pdf"

    pdf_bytes = StorageService.get_file_bytes(storage_key)
    if not pdf_bytes:
        items_res = await db.execute(select(SalesOrderItem).where(SalesOrderItem.order_id == so.id))
        items = items_res.scalars().all()

        calc_items = []
        subtotal = 0.0
        for it in items:
            p_res = await db.execute(select(Product).where(Product.id == it.product_id))
            prod = p_res.scalar_one_or_none()
            p_name = prod.name if prod else "Item"
            hsn = prod.hsn_code if prod and prod.hsn_code else "8471"
            qty = float(it.ordered_qty)
            price = float(it.unit_price)
            item_tot = qty * price
            subtotal += item_tot
            calc_items.append({
                "item_description": p_name,
                "hsn_code": hsn,
                "quantity": qty,
                "unit_of_measure": prod.unit_of_measure if prod else "pcs",
                "unit_price": price,
                "discount": 0.0,
                "taxable_value": item_tot,
                "gst_rate": float(prod.gst_rate) if prod and prod.gst_rate else 18.0,
                "cgst_rate": 9.0,
                "cgst_amount": item_tot * 0.09,
                "sgst_rate": 9.0,
                "sgst_amount": item_tot * 0.09,
                "igst_rate": 0.0,
                "igst_amount": 0.0,
                "total": item_tot * 1.18,
            })

        order_dict = {
            "document_title": "SALES ORDER CONFIRMATION",
            "number_label": "SO Number",
            "date_label": "Order Date",
            "invoice_number": so.so_number,
            "invoice_date": so.order_date.isoformat() if so.order_date else datetime.utcnow().isoformat(),
            "due_date": so.order_date.isoformat() if so.order_date else datetime.utcnow().isoformat(),
            "place_of_supply": f"{so.state_code or '29'}-{so.state or 'Karnataka'}",
            "status": so.status.value if hasattr(so.status, "value") else str(so.status),
            "seller_legal_name": sett.legal_business_name if sett else (tenant.name if tenant else "Invenza"),
            "seller_gstin": sett.gstin if sett and sett.gstin else "29AABCI1234F1Z5",
            "seller_pan": sett.pan if sett and sett.pan else "AABCI1234F",
            "seller_address": sett.registered_address if sett and sett.registered_address else "Outer Ring Road, Bengaluru, Karnataka 560103",
            "seller_state": sett.state if sett and sett.state else "Karnataka",
            "seller_state_code": sett.state_code if sett and sett.state_code else "29",
            "customer_name": so.customer_name,
            "customer_gstin": so.customer_gstin or "B2C / Unregistered",
            "customer_billing_address": so.billing_address or "Customer Address",
            "customer_shipping_address": so.shipping_address or so.billing_address or "Delivery Address",
            "customer_state": so.state or "Karnataka",
            "customer_state_code": so.state_code or "29",
            "is_inter_state": False,
            "payment_terms": "Standard Net 30",
            "total_taxable_value": subtotal,
            "total_cgst": subtotal * 0.09,
            "total_sgst": subtotal * 0.09,
            "total_igst": 0.0,
            "round_off": 0.0,
            "grand_total": subtotal * 1.18,
            "grand_total_words": "Sales Order Confirmation Slip",
            "so_number": so.so_number,
            "bank_name": sett.bank_name if sett else "HDFC Bank",
            "bank_account_number": sett.bank_account_number if sett else "50200012345678",
            "bank_ifsc_code": sett.bank_ifsc_code if sett else "HDFC0001234",
            "bank_branch": sett.bank_branch if sett else "Koramangala 5th Block, Bengaluru",
            "account_holder_name": sett.account_holder_name if sett else (tenant.name if tenant else "Invenza"),
            "authorized_signatory_name": sett.authorized_signatory_name if sett else "Authorized Signatory",
            "items": calc_items,
        }

        pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(order_dict)
        try:
            StorageService.upload_file(pdf_bytes, storage_key, content_type="application/pdf")
        except Exception as e:
            print(f"[MinIO Storage Upload Notice for SO]: {e}")

    disposition = "attachment" if download else "inline"
    safe_filename = f"Sales_Order_{safe_so_num}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
            "Content-Type": "application/pdf",
        },
    )
