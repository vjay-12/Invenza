import uuid
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.api.deps import require_super_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.billing import (
    TenantBillingProfile,
    BillingFeeHistory,
    BillingPaymentRecord,
    OrgSetupFee,
    OrgMaintenancePlan,
    OrgMaintenanceCycle,
    VALID_PAYMENT_MODES,
)
from app.models.audit_log import AuditLog
from app.models.invoice import TenantSettings, TenantInvoiceSequence, Invoice, InvoiceItem, InvoiceStatus
from app.services.gst_service import GSTService, amount_to_indian_words
from app.services.invoice_pdf_generator import InvoicePdfGenerator
from app.services.email_service import EmailService
from app.services.tax_service import (
    TaxService,
    TAX_LABELS,
    get_org_tax_context,
    currency_symbol,
    amount_to_words,
    resolve_org_state,
    region_display,
)
from app.schemas.billing import (
    BillingOverviewResponse,
    BillingOrgSummary,
    MarkPaidRequest,
    MarkWaivedRequest,
    UpdateMaintenanceRateRequest,
    GenerateCyclesRequest,
    OrgSetupFeeResponse,
    OrgMaintenancePlanResponse,
    OrgMaintenanceCycleResponse,
    BillingTransactionItem,
    UpdateSetupFeeRequest,
    UpdateMaintenanceFeeRequest,
    RecordPaymentRequest,
)

router = APIRouter()

MASTER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


# ═════════════════════════════════════════════════════════════════════════════════════
# GST INVOICE SEQUENCING & TAX ENGINE
# ═════════════════════════════════════════════════════════════════════════════════════

async def get_or_create_next_invoice_number(db: AsyncSession) -> str:
    """
    Strict unbroken sequential invoice number generator for Invenza platform billing.
    Uses TenantInvoiceSequence with tenant_id = MASTER_TENANT_ID and row-level locking.
    Format: INV-TEN/YYYY-YY/XXXXX
    """
    seq_res = await db.execute(
        select(TenantInvoiceSequence)
        .where(TenantInvoiceSequence.tenant_id == MASTER_TENANT_ID)
        .with_for_update()
    )
    seq = seq_res.scalar_one_or_none()
    if not seq:
        seq = TenantInvoiceSequence(tenant_id=MASTER_TENANT_ID, fiscal_year="2026-27", current_number=1)
        db.add(seq)
        await db.flush()
    else:
        seq.current_number += 1
        seq.updated_at = datetime.utcnow()
        await db.flush()

    return f"INV-TEN/{seq.fiscal_year}/{seq.current_number:05d}"


async def compute_tenant_billing_tax(
    db: AsyncSession,
    tenant_id: UUID,
    amount: float,
    charge_type: str,
    cycle_or_desc: str,
    is_waived: bool = False,
) -> dict:
    """
    Computes the tax breakdown for platform billing (setup fee / monthly maintenance)
    via the centralized TaxService. India keeps CGST+SGST vs IGST; EU orgs get a
    single VAT line; US orgs get a single Sales Tax line (0% states render 0%).
    Currency/symbol always come from the org's locked country configuration.
    """
    # 0. Org tax identity (country, resolved state, derived currency, TaxReference row)
    context = await get_org_tax_context(db, tenant_id)
    country = context["country_code"]
    currency = context["currency"]
    sym = currency_symbol(currency)
    tax_type = context["tax_ref"].tax_type if context["tax_ref"] else "GST"
    tax_label = {"GST": "GST", "VAT": "VAT", "SALES_TAX": "Sales Tax"}.get(tax_type, tax_type)
    region = region_display(context)

    # 1. Fetch Invenza seller profile (Karnataka - 29)
    invenza_sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == MASTER_TENANT_ID))
    invenza_sett = invenza_sett_res.scalar_one_or_none()

    seller_name = invenza_sett.legal_business_name if invenza_sett else "Invenza Enterprise Ltd"
    seller_gstin = invenza_sett.gstin if invenza_sett else "29AABCI1234F1Z5"
    seller_pan = invenza_sett.pan if invenza_sett else "AABCI1234F"
    seller_state = invenza_sett.state if invenza_sett else "Karnataka"
    seller_state_code = invenza_sett.state_code if invenza_sett else "29"
    seller_address = (
        invenza_sett.registered_address
        if invenza_sett
        else "Plot 42, Tech Park Central, Outer Ring Road, Bengaluru, Karnataka 560103"
    )

    # 2. Fetch Tenant buyer profile
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_name = tenant.name if tenant else "Tenant Organization"

    tenant_sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    tenant_sett = tenant_sett_res.scalar_one_or_none()

    buyer_name = (tenant_sett.legal_business_name if tenant_sett and tenant_sett.legal_business_name else tenant_name)
    raw_gstin = (tenant_sett.gstin if tenant_sett and tenant_sett.gstin else ("URP" if country == "IN" else ""))
    buyer_gstin = raw_gstin.strip()[:15] if raw_gstin else ""

    if country == "IN":
        buyer_raw_state = (
            (tenant_sett.state if tenant_sett and tenant_sett.state else None)
            or (tenant.state if tenant and tenant.state else None)
            or (tenant.location if tenant else "Karnataka")
        )
        buyer_code, buyer_state = GSTService.normalize_state_code(buyer_raw_state)
        if not buyer_code:
            buyer_code, buyer_state = "29", "Karnataka"
    else:
        buyer_code = context.get("state_code") or country
        buyer_state = context.get("state_name") or region

    buyer_address = (
        tenant_sett.registered_address
        if tenant_sett and tenant_sett.registered_address
        else (
            f"{tenant.location}, {buyer_state} - {tenant.pincode}"
            if tenant and tenant.pincode and tenant.location
            else (f"{tenant.location}, {buyer_state}" if tenant else "Registered Business Address")
        )
    )

    # 3. Line items (SAC 998313 is India-specific; EU/US invoices carry no SAC/HSN)
    sac_code = "998313" if country == "IN" else ""
    amt_val = float(amount or 0.0)

    base_info = {
        "seller_name": seller_name,
        "seller_gstin": seller_gstin,
        "seller_pan": seller_pan,
        "seller_state": seller_state,
        "seller_state_code": seller_state_code,
        "seller_address": seller_address,
        "buyer_name": buyer_name,
        "buyer_gstin": buyer_gstin,
        "buyer_state": buyer_state,
        "buyer_state_code": buyer_code,
        "buyer_address": buyer_address,
        "sac_code": sac_code,
        "tax_type": tax_type,
        "tax_label": tax_label,
        "currency_code": currency,
        "currency_symbol": sym,
        "region_display": region,
        "sourcing_rule": context["tax_ref"].sourcing_rule if context["tax_ref"] else None,
        "is_inter_state": (seller_state_code != buyer_code) if country == "IN" else False,
        "place_of_supply": f"{buyer_code} - {buyer_state}" if country == "IN" else region,
    }

    if is_waived or amt_val == 0.0:
        return {
            **base_info,
            "gst_rate": 0.0,
            "tax_rate": 0.0,
            "taxable_amount": 0.0,
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "igst_amount": 0.0,
            "single_tax_amount": 0.0,
            "total_amount": 0.0,
            "item_description": f"{cycle_or_desc} (Waived - {sym}0 Promotional)",
            "calc": None,
        }

    line_items = [{
        "item_description": f"{cycle_or_desc} (SAC: {sac_code})" if sac_code else cycle_or_desc,
        "hsn_code": sac_code,
        "quantity": 1,
        "unit_price": amt_val,
        "discount": 0.0,
        "gst_rate": 18.0 if country == "IN" else 0.0,  # EU/US rate comes from TaxReference
    }]

    calc = await TaxService.calculate(
        db,
        tenant_id=tenant_id,
        line_items=line_items,
        seller_state_code=seller_state_code,
        place_of_supply_state_code=buyer_code,
        is_waived=False,
    )

    return {
        **base_info,
        "gst_rate": 18.0 if country == "IN" else calc["tax_rate"],
        "tax_rate": calc["tax_rate"],
        "taxable_amount": calc["total_taxable_value"],
        "cgst_amount": calc["total_cgst"],
        "sgst_amount": calc["total_sgst"],
        "igst_amount": calc["total_igst"],
        "single_tax_amount": calc["total_single_tax"],
        "total_amount": calc["grand_total"],
        "item_description": line_items[0]["item_description"],
        "calc": calc,
    }


async def create_gst_invoice_for_billing(
    db: AsyncSession,
    tenant_id: UUID,
    amount: float,
    charge_type: str,
    description: str,
    payment_date: datetime,
) -> tuple[Invoice, str]:
    """
    Allocates sequential invoice number, computes GST taxes,
    and inserts an Invoice and InvoiceItem into the database.
    """
    inv_num = await get_or_create_next_invoice_number(db)
    tax_info = await compute_tenant_billing_tax(
        db=db,
        tenant_id=tenant_id,
        amount=amount,
        charge_type=charge_type,
        cycle_or_desc=description,
        is_waived=False,
    )

    inv = Invoice(
        tenant_id=tenant_id,
        invoice_number=inv_num,
        invoice_date=payment_date or datetime.utcnow(),
        due_date=payment_date or datetime.utcnow(),
        place_of_supply=tax_info["place_of_supply"],
        status=InvoiceStatus.PAID,
        seller_legal_name=tax_info["seller_name"],
        seller_gstin=tax_info["seller_gstin"],
        seller_pan=tax_info["seller_pan"],
        seller_address=tax_info["seller_address"],
        seller_state=tax_info["seller_state"],
        seller_state_code=tax_info["seller_state_code"],
        customer_name=tax_info["buyer_name"],
        customer_gstin=tax_info["buyer_gstin"],
        customer_billing_address=tax_info["buyer_address"],
        customer_shipping_address=tax_info["buyer_address"],
        customer_state=tax_info["buyer_state"],
        customer_state_code=tax_info["buyer_state_code"],
        is_inter_state=tax_info["is_inter_state"],
        tax_type=tax_info["tax_type"],
        currency_code=tax_info["currency_code"],
        payment_terms="Advance SaaS Service Agreement",
        total_taxable_value=tax_info["taxable_amount"],
        total_cgst=tax_info["cgst_amount"],
        total_sgst=tax_info["sgst_amount"],
        total_igst=tax_info["igst_amount"],
        total_single_tax=tax_info["single_tax_amount"],
        round_off=0.00,
        grand_total=tax_info["total_amount"],
        grand_total_words=amount_to_words(tax_info["total_amount"], tax_info["currency_code"]),
    )
    db.add(inv)
    await db.flush()

    # Rate labels come from the computed line (never hardcoded 9/9/18 literals):
    # GST intra -> cgst=sgst=rate/2, inter -> igst=rate; EU/US -> single_tax only.
    calc_item = (tax_info.get("calc") or {}).get("items", [{}])[0]
    item = InvoiceItem(
        invoice_id=inv.id,
        item_description=tax_info["item_description"],
        hsn_code=tax_info["sac_code"],
        quantity=1,
        unit_of_measure="service",
        unit_price=tax_info["taxable_amount"],
        discount=0.0,
        taxable_value=tax_info["taxable_amount"],
        gst_rate=tax_info["gst_rate"],
        cgst_rate=calc_item.get("cgst_rate", 0.0),
        cgst_amount=tax_info["cgst_amount"],
        sgst_rate=calc_item.get("sgst_rate", 0.0),
        sgst_amount=tax_info["sgst_amount"],
        igst_rate=calc_item.get("igst_rate", 0.0),
        igst_amount=tax_info["igst_amount"],
        single_tax_rate=calc_item.get("single_tax_rate", 0.0),
        single_tax_amount=tax_info["single_tax_amount"],
        total=tax_info["total_amount"],
    )
    db.add(item)
    await db.flush()

    return inv, inv_num


async def build_pdf_invoice_dict_from_tax(
    db: AsyncSession,
    tenant_id: UUID,
    amount: float,
    charge_type: str,
    desc: str,
    invoice_number: str,
    payment_date: Optional[datetime] = None,
    is_waived: bool = False,
) -> dict:
    """
    Constructs the standard invoice_data dictionary for ReportLab InvoicePdfGenerator.
    """
    tax_info = await compute_tenant_billing_tax(
        db=db,
        tenant_id=tenant_id,
        amount=amount,
        charge_type=charge_type,
        cycle_or_desc=desc,
        is_waived=is_waived,
    )

    is_inter = tax_info["is_inter_state"]

    # Invenza bank remittance details
    invenza_sett_res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == MASTER_TENANT_ID))
    invenza_sett = invenza_sett_res.scalar_one_or_none()

    calc_item = (tax_info.get("calc") or {}).get("items", [{}])[0]
    item_row = {
        "item_description": tax_info["item_description"],
        "hsn_code": tax_info["sac_code"],
        "quantity": 1,
        "unit_price": tax_info["taxable_amount"],
        "taxable_value": tax_info["taxable_amount"],
        "gst_rate": tax_info["gst_rate"],
        "cgst_rate": calc_item.get("cgst_rate", 0.0),
        "cgst_amount": tax_info["cgst_amount"],
        "sgst_rate": calc_item.get("sgst_rate", 0.0),
        "sgst_amount": tax_info["sgst_amount"],
        "igst_rate": calc_item.get("igst_rate", 0.0),
        "igst_amount": tax_info["igst_amount"],
        "single_tax_rate": calc_item.get("single_tax_rate", 0.0),
        "single_tax_amount": tax_info["single_tax_amount"],
        "total": tax_info["total_amount"],
    }

    words = amount_to_words(tax_info["total_amount"], tax_info["currency_code"])
    inv_date_str = (payment_date or datetime.utcnow()).strftime("%Y-%m-%d")

    return {
        "seller_legal_name": tax_info["seller_name"],
        "seller_address": tax_info["seller_address"],
        "seller_gstin": tax_info["seller_gstin"],
        "seller_pan": tax_info["seller_pan"],
        "seller_state": tax_info["seller_state"],
        "seller_state_code": tax_info["seller_state_code"],
        "tax_type": tax_info["tax_type"],
        "tax_label": tax_info["tax_label"],
        "tax_rate": tax_info.get("tax_rate"),
        "currency_code": tax_info["currency_code"],
        "currency_symbol": tax_info["currency_symbol"],
        "region_display": tax_info["region_display"],
        "sourcing_rule": tax_info.get("sourcing_rule"),
        "document_title": "TAX INVOICE" if not is_waived else "BILL OF SUPPLY / WAIVED RECORD",
        "invoice_number": invoice_number,
        "invoice_date": inv_date_str,
        "due_date": inv_date_str,
        "customer_name": tax_info["buyer_name"],
        "customer_billing_address": tax_info["buyer_address"],
        "customer_shipping_address": tax_info["buyer_address"],
        "customer_gstin": tax_info["buyer_gstin"],
        "customer_state": tax_info["buyer_state"],
        "customer_state_code": tax_info["buyer_state_code"],
        "place_of_supply": tax_info["place_of_supply"],
        "is_inter_state": is_inter,
        "items": [item_row],
        "total_taxable_value": tax_info["taxable_amount"],
        "total_cgst": tax_info["cgst_amount"],
        "total_sgst": tax_info["sgst_amount"],
        "total_igst": tax_info["igst_amount"],
        "total_single_tax": tax_info["single_tax_amount"],
        "round_off": 0.0,
        "grand_total": tax_info["total_amount"],
        "grand_total_words": words,
        "bank_name": invenza_sett.bank_name if invenza_sett else "HDFC Bank",
        "bank_account_number": invenza_sett.bank_account_number if invenza_sett else "50200012345678",
        "bank_ifsc_code": invenza_sett.bank_ifsc_code if invenza_sett else "HDFC0001234",
        "bank_branch": invenza_sett.bank_branch if invenza_sett else "Koramangala 5th Block, Bengaluru",
        "account_holder_name": invenza_sett.account_holder_name if invenza_sett else "Invenza Enterprise Ltd",
        "authorized_signatory_name": invenza_sett.authorized_signatory_name if invenza_sett else "Invenza Commercial Operations",
        "payment_terms": "Advance SaaS Service Agreement",
        "so_number": f"AGR-{invoice_number.split('/')[-1]}",
    }


# ═════════════════════════════════════════════════════════════════════════════════════
# AUTO-GENERATION OF MONTHLY CYCLE RECORDS (BACKGROUND JOB & API)
# ═════════════════════════════════════════════════════════════════════════════════════

async def generate_monthly_maintenance_cycles(db: AsyncSession, target_month: Optional[str] = None) -> dict:
    """
    Scheduled background job on the 1st of every month (and startup check) that,
    for every active, non-archived org, creates a new org_maintenance_cycle row using
    that org's current maintenance plan rate, with status = Pending.
    If an org is archived/deactivated, stops generating new cycle rows for it.
    """
    now = datetime.utcnow()
    month_str = target_month or now.strftime("%Y-%m")

    # Fetch all active, non-archived tenants (excluding Master platform tenant)
    tenants_res = await db.execute(
        select(Tenant).where(
            and_(
                Tenant.id != MASTER_TENANT_ID,
                Tenant.is_active == True,
                or_(Tenant.is_archived == False, Tenant.is_archived.is_(None)),
            )
        )
    )
    active_tenants = tenants_res.scalars().all()
    created_count = 0
    skipped_count = 0

    for t in active_tenants:
        # Check if cycle already exists for this org and target month
        existing_res = await db.execute(
            select(OrgMaintenanceCycle).where(
                and_(
                    OrgMaintenanceCycle.org_id == t.id,
                    OrgMaintenanceCycle.cycle_month == month_str,
                )
            )
        )
        if existing_res.scalar_one_or_none():
            skipped_count += 1
            continue

        # Fetch latest agreed rate from OrgMaintenancePlan
        plan_res = await db.execute(
            select(OrgMaintenancePlan)
            .where(OrgMaintenancePlan.org_id == t.id)
            .order_by(OrgMaintenancePlan.effective_from.desc(), OrgMaintenancePlan.created_at.desc())
        )
        latest_plan = plan_res.scalars().first()
        rate = float(latest_plan.current_rate) if latest_plan else 0.0

        new_cycle = OrgMaintenanceCycle(
            org_id=t.id,
            cycle_month=month_str,
            amount=rate,
            status="Pending",
            payment_mode=None,
            date_paid=None,
            recorded_by="System Auto-Billing",
            note=f"Automatic monthly maintenance cycle for {month_str}",
        )
        db.add(new_cycle)
        created_count += 1

    await db.commit()
    return {
        "cycle_month": month_str,
        "created_count": created_count,
        "skipped_count": skipped_count,
        "active_tenants_count": len(active_tenants),
    }


@router.post("/cycles/generate")
async def trigger_cycle_generation(
    cycle_month: Optional[str] = Query(None),
    req: Optional[GenerateCyclesRequest] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin / Cron: Trigger or simulate monthly maintenance cycle generation.
    Pass cycle_month (e.g. '2026-10') to simulate month rollovers.
    """
    target = (req.cycle_month if req and req.cycle_month else None) or cycle_month
    result = await generate_monthly_maintenance_cycles(db, target_month=target)
    return {"success": True, **result}


# ═════════════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL BILLING OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════════════

@router.get("/overview", response_model=BillingOverviewResponse)
async def get_billing_overview(
    status_filter: Optional[str] = Query(None, alias="status"),
    industry_filter: Optional[str] = Query(None, alias="industry"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Retrieve top-level aggregate billing telemetry and all organization billing summaries.
    100% computed dynamically from org_setup_fee, org_maintenance_plan, and org_maintenance_cycle.
    """
    current_month_str = datetime.utcnow().strftime("%Y-%m")

    # 1. Fetch all tenants (excluding master platform)
    tenant_query = select(Tenant).where(
        and_(
            Tenant.id != MASTER_TENANT_ID,
            Tenant.is_active == True,
            or_(Tenant.is_archived == False, Tenant.is_archived.is_(None)),
        )
    ).order_by(Tenant.name.asc())

    if search:
        s = f"%{search.strip()}%"
        tenant_query = tenant_query.where(or_(Tenant.name.ilike(s), Tenant.company_code.ilike(s), Tenant.unique_code.ilike(s)))
    if industry_filter and industry_filter.lower() != "all":
        tenant_query = tenant_query.where(Tenant.industry == industry_filter)

    tenants_res = await db.execute(tenant_query)
    all_tenants = tenants_res.scalars().all()

    org_summaries: List[BillingOrgSummary] = []
    active_mrr_sum = 0.0
    zero_maintenance_count = 0
    pending_setup_count = 0
    pending_setup_sum = 0.0
    overdue_count = 0
    # Per-currency subtotals — amounts across currencies must never be summed together
    revenue_by_currency: Dict[str, float] = {}
    mrr_by_currency: Dict[str, float] = {}

    for t in all_tenants:
        # Fetch or initialize OrgSetupFee
        sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.org_id == t.id))
        sf = sf_res.scalar_one_or_none()
        if not sf:
            # Fallback to TenantBillingProfile or default
            bp_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
            bp = bp_res.scalar_one_or_none()
            sf = OrgSetupFee(
                org_id=t.id,
                amount=float(bp.setup_fee) if bp else 25000.0,
                status="Paid" if (bp and bp.setup_fee_status == "paid") else "Pending",
                date_paid=bp.setup_fee_paid_at if (bp and bp.setup_fee_status == "paid") else None,
                payment_mode=bp.setup_fee_payment_mode if (bp and bp.setup_fee_status == "paid") else None,
                recorded_by=bp.setup_fee_recorded_by if bp else "Super Admin",
            )
            db.add(sf)
            await db.flush()

        # Fetch latest OrgMaintenancePlan
        plan_res = await db.execute(
            select(OrgMaintenancePlan)
            .where(OrgMaintenancePlan.org_id == t.id)
            .order_by(OrgMaintenancePlan.effective_from.desc(), OrgMaintenancePlan.created_at.desc())
        )
        latest_plan = plan_res.scalars().first()
        if not latest_plan:
            bp_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
            bp = bp_res.scalar_one_or_none()
            rate_val = float(bp.monthly_maintenance_fee) if bp else 4500.0
            latest_plan = OrgMaintenancePlan(
                org_id=t.id,
                current_rate=rate_val,
                effective_from=t.created_at or datetime.utcnow(),
                changed_by="Super Admin",
                reason="Initial agreed maintenance rate",
            )
            db.add(latest_plan)
            await db.flush()

        current_rate = float(latest_plan.current_rate or 0.0)
        setup_fee_amt = float(sf.amount or 0.0)

        active_mrr_sum += current_rate
        if current_rate == 0.0:
            zero_maintenance_count += 1
        if sf.status == "Pending":
            pending_setup_count += 1
            pending_setup_sum += setup_fee_amt

        # Fetch current month's cycle
        cur_cycle_res = await db.execute(
            select(OrgMaintenanceCycle).where(
                and_(OrgMaintenanceCycle.org_id == t.id, OrgMaintenanceCycle.cycle_month == current_month_str)
            )
        )
        cur_cycle = cur_cycle_res.scalar_one_or_none()
        if not cur_cycle:
            # Auto-create if missing for current month
            cur_cycle = OrgMaintenanceCycle(
                org_id=t.id,
                cycle_month=current_month_str,
                amount=current_rate,
                status="Pending",
                recorded_by="System Auto-Billing",
                note=f"Automatic monthly maintenance cycle for {current_month_str}",
            )
            db.add(cur_cycle)
            await db.flush()

        # Check last payment date (latest date_paid across setup fee and cycles)
        last_pay_res = await db.execute(
            select(func.max(OrgMaintenanceCycle.date_paid)).where(
                and_(OrgMaintenanceCycle.org_id == t.id, OrgMaintenanceCycle.status == "Paid")
            )
        )
        last_cycle_paid = last_pay_res.scalar_one_or_none()
        last_payment_dt = sf.date_paid
        if last_cycle_paid and (not last_payment_dt or last_cycle_paid > last_payment_dt):
            last_payment_dt = last_cycle_paid

        # Determine this month's status
        this_month_st = cur_cycle.status if cur_cycle else "Pending"

        # Check if overdue (pending cycle from an earlier month)
        overdue_res = await db.execute(
            select(OrgMaintenanceCycle).where(
                and_(
                    OrgMaintenanceCycle.org_id == t.id,
                    OrgMaintenanceCycle.status == "Pending",
                    OrgMaintenanceCycle.cycle_month < current_month_str,
                )
            )
        )
        has_overdue = overdue_res.scalars().first() is not None
        if has_overdue:
            overdue_count += 1
            if this_month_st == "Pending":
                this_month_st = "Overdue"

        # Filtering logic
        if status_filter and status_filter.lower() != "all":
            flt = status_filter.lower()
            if flt == "paid" and (this_month_st != "Paid" or sf.status != "Paid"):
                continue
            elif flt == "pending" and (this_month_st != "Pending" and sf.status != "Pending"):
                continue
            elif flt == "overdue" and (not has_overdue and this_month_st != "Overdue"):
                continue
            elif flt == "waived" and (this_month_st != "Waived" and current_rate > 0):
                continue

        # Per-currency aggregates (append-only; totals across currencies are never mixed)
        org_currency = (t.currency_code or "INR").upper()
        mrr_by_currency[org_currency] = round(mrr_by_currency.get(org_currency, 0.0) + current_rate, 2)
        if sf.status == "Paid":
            revenue_by_currency[org_currency] = round(revenue_by_currency.get(org_currency, 0.0) + setup_fee_amt, 2)
        paid_cyc_res = await db.execute(
            select(func.coalesce(func.sum(OrgMaintenanceCycle.amount), 0.0)).where(
                and_(OrgMaintenanceCycle.org_id == t.id, OrgMaintenanceCycle.status == "Paid")
            )
        )
        paid_cyc_amt = float(paid_cyc_res.scalar_one() or 0.0)
        if paid_cyc_amt:
            revenue_by_currency[org_currency] = round(revenue_by_currency.get(org_currency, 0.0) + paid_cyc_amt, 2)

        org_summaries.append(
            BillingOrgSummary(
                id=t.id,
                tenant_id=t.id,
                tenant_name=t.name,
                company_code=t.company_code or t.unique_code,
                industry=t.industry or "General Merchandise",
                tier=getattr(t, "tier", "Growth Suite") or "Growth Suite",
                country_code=(t.country_code or "IN").upper(),
                currency_code=(t.currency_code or "INR").upper(),
                setup_fee_amount=setup_fee_amt,
                setup_fee_status=sf.status,
                setup_fee=setup_fee_amt,
                current_monthly_rate=current_rate,
                monthly_maintenance_fee=current_rate,
                last_payment_date=last_payment_dt,
                next_due_date=datetime(datetime.utcnow().year, datetime.utcnow().month, 1),
                this_month_status=this_month_st,
                payment_status=this_month_st.lower(),
            )
        )

    # Calculate total revenue collected (paid setup fees + paid cycles)
    paid_sf_res = await db.execute(
        select(func.coalesce(func.sum(OrgSetupFee.amount), 0.0)).where(OrgSetupFee.status == "Paid")
    )
    total_sf_rev = float(paid_sf_res.scalar_one() or 0.0)

    paid_cycles_res = await db.execute(
        select(func.coalesce(func.sum(OrgMaintenanceCycle.amount), 0.0)).where(OrgMaintenanceCycle.status == "Paid")
    )
    total_cycle_rev = float(paid_cycles_res.scalar_one() or 0.0)
    total_revenue_collected = total_sf_rev + total_cycle_rev

    await db.commit()

    return BillingOverviewResponse(
        total_revenue_collected=round(total_revenue_collected, 2),
        pending_setup_fees=round(pending_setup_sum, 2),
        pending_setup_fees_amount=round(pending_setup_sum, 2),
        pending_setup_fees_count=pending_setup_count,
        active_monthly_recurring=round(active_mrr_sum, 2),
        active_mrr_sum=round(active_mrr_sum, 2),
        zero_maintenance_orgs_count=zero_maintenance_count,
        zero_maintenance_orgs=zero_maintenance_count,
        overdue_count=overdue_count,
        revenue_by_currency=revenue_by_currency,
        mrr_by_currency=mrr_by_currency,
        organizations=org_summaries,
        tenants=org_summaries,
    )


# ═════════════════════════════════════════════════════════════════════════════════════
# ORG-LEVEL BILLING DRILL-DOWN
# ═════════════════════════════════════════════════════════════════════════════════════

@router.get("/tenants/{tenant_id}")
async def get_tenant_billing_detail(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Drill down into an organization's complete commercial profile.
    Returns Setup Fee card, Current Rate + Rate Change History, and unified Transaction Table.
    """
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    current_month_str = datetime.utcnow().strftime("%Y-%m")

    # 1. Fetch or initialize OrgSetupFee
    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.org_id == tenant_id))
    sf = sf_res.scalar_one_or_none()
    if not sf:
        bp_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == tenant_id))
        bp = bp_res.scalar_one_or_none()
        sf = OrgSetupFee(
            org_id=tenant_id,
            amount=float(bp.setup_fee) if bp else 25000.0,
            status="Paid" if (bp and bp.setup_fee_status == "paid") else "Pending",
            date_paid=bp.setup_fee_paid_at if (bp and bp.setup_fee_status == "paid") else None,
            payment_mode=bp.setup_fee_payment_mode if (bp and bp.setup_fee_status == "paid") else None,
            recorded_by=bp.setup_fee_recorded_by if bp else "Super Admin",
        )
        db.add(sf)
        await db.flush()

    # 2. Fetch Rate History and Current Plan
    plans_res = await db.execute(
        select(OrgMaintenancePlan)
        .where(OrgMaintenancePlan.org_id == tenant_id)
        .order_by(OrgMaintenancePlan.effective_from.desc(), OrgMaintenancePlan.created_at.desc())
    )
    rate_history = plans_res.scalars().all()
    if not rate_history:
        bp_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == tenant_id))
        bp = bp_res.scalar_one_or_none()
        rate_val = float(bp.monthly_maintenance_fee) if bp else 4500.0
        initial_plan = OrgMaintenancePlan(
            org_id=tenant_id,
            current_rate=rate_val,
            effective_from=tenant.created_at or datetime.utcnow(),
            changed_by="Super Admin",
            reason="Initial agreed maintenance rate",
        )
        db.add(initial_plan)
        await db.flush()
        rate_history = [initial_plan]

    current_plan = rate_history[0]

    # 3. Fetch all Monthly Cycles
    cycles_res = await db.execute(
        select(OrgMaintenanceCycle)
        .where(OrgMaintenanceCycle.org_id == tenant_id)
        .order_by(OrgMaintenanceCycle.cycle_month.desc(), OrgMaintenanceCycle.created_at.desc())
    )
    cycles = cycles_res.scalars().all()
    if not cycles:
        # Create cycle for current month
        cur_cycle = OrgMaintenanceCycle(
            org_id=tenant_id,
            cycle_month=current_month_str,
            amount=float(current_plan.current_rate),
            status="Pending",
            recorded_by="System Auto-Billing",
            note=f"Automatic monthly maintenance cycle for {current_month_str}",
        )
        db.add(cur_cycle)
        await db.flush()
        cycles = [cur_cycle]

    await db.commit()

    # 4. Construct unified Chronological Transaction Table
    transactions: List[BillingTransactionItem] = []

    # Setup Fee transaction row
    transactions.append(
        BillingTransactionItem(
            item_type="setup_fee",
            id=sf.id,
            cycle_month="One-Time Setup Fee",
            amount=float(sf.amount),
            status=sf.status,
            date_paid=sf.date_paid,
            date_recorded=sf.created_at,
            payment_mode=sf.payment_mode,
            recorded_by=sf.recorded_by,
            note=sf.note,
            invoice_number=sf.invoice_number,
            gst_invoice_id=sf.gst_invoice_id,
            can_mark_paid=(sf.status == "Pending"),
            can_mark_waived=False,  # Setup fee cannot be waived per prompt
        )
    )

    # Monthly Cycle transaction rows
    for c in cycles:
        transactions.append(
            BillingTransactionItem(
                item_type="monthly_cycle",
                id=c.id,
                cycle_month=f"Maintenance ({c.cycle_month})",
                amount=float(c.amount),
                status=c.status,
                date_paid=c.date_paid,
                date_recorded=c.created_at,
                payment_mode=c.payment_mode,
                recorded_by=c.recorded_by,
                note=c.note,
                invoice_number=c.invoice_number,
                gst_invoice_id=c.gst_invoice_id,
                can_mark_paid=(c.status == "Pending"),
                can_mark_waived=(c.status == "Pending"),
            )
        )

    # Sort unified transactions by date (date_paid or date_recorded descending)
    transactions.sort(key=lambda x: x.date_paid or x.date_recorded, reverse=True)

    org_context = {
        "id": tenant.id,
        "name": tenant.name,
        "tenant_name": tenant.name,
        "unique_code": tenant.unique_code or tenant.company_code or "N/A",
        "company_code": tenant.company_code or tenant.unique_code or "N/A",
        "industry": tenant.industry or "General Merchandise",
        "location": tenant.location or "Headquarters",
        "tier": getattr(tenant, "tier", "Growth Suite") or "Growth Suite",
        "country_code": (tenant.country_code or "IN").upper(),
        "currency_code": (tenant.currency_code or "INR").upper(),
        "is_active": tenant.is_active,
        "is_archived": getattr(tenant, "is_archived", False),
        "status": "Active" if (tenant.is_active and not getattr(tenant, "is_archived", False)) else "Deactivated",
    }

    # Backward-compatible response payload supporting both new structured contracts and legacy callers
    profile_dict = {
        "id": sf.id,
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "setup_fee": float(sf.amount),
        "setup_fee_status": sf.status.lower(),
        "setup_fee_paid_at": sf.date_paid,
        "setup_fee_payment_mode": sf.payment_mode or "manual",
        "setup_fee_recorded_by": sf.recorded_by,
        "monthly_maintenance_fee": float(current_plan.current_rate),
        "maintenance_currency": (tenant.currency_code or "INR").upper(),
        "billing_cycle_day": 1,
        "created_at": sf.created_at,
        "updated_at": sf.updated_at,
    }

    return {
        # Backward compatibility properties
        **profile_dict,
        "country_code": (tenant.country_code or "IN").upper(),
        "currency_code": (tenant.currency_code or "INR").upper(),
        "profile": profile_dict,
        "fee_history": rate_history,
        "payments": transactions,
        "payment_records": transactions,
        # Structured models (precedence)
        "org": org_context,
        "tenant": org_context,
        "setup_fee": sf,
        "current_plan": current_plan,
        "current_maintenance_plan": current_plan,
        "rate_history": rate_history,
        "cycles": cycles,
        "transactions": transactions,
    }


# ═════════════════════════════════════════════════════════════════════════════════════
# MARKING PAYMENTS (MANUAL FLOW)
# ═════════════════════════════════════════════════════════════════════════════════════

@router.post("/setup-fee/{setup_fee_id}/mark-paid")
async def mark_setup_fee_paid(
    setup_fee_id: UUID,
    req: MarkPaidRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Mark Setup Fee as Paid.
    Captures confirmed amount, date received, payment mode, and note.
    Auto-generates sequential GST-compliant tax invoice and logs to audit log.
    Guardrail: Prevents marking as Paid twice.
    """
    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.id == setup_fee_id))
    setup_fee = sf_res.scalar_one_or_none()
    if not setup_fee:
        raise HTTPException(status_code=404, detail="Setup fee record not found")

    if setup_fee.status == "Paid":
        raise HTTPException(status_code=400, detail="Setup fee has already been finalized as Paid.")

    amount_to_pay = req.confirmed_amount if req.confirmed_amount is not None else (req.amount if req.amount is not None else float(setup_fee.amount))
    if amount_to_pay < 0:
        raise HTTPException(status_code=400, detail="Confirmed amount cannot be negative.")

    if req.payment_mode not in VALID_PAYMENT_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid payment mode. Must be one of {VALID_PAYMENT_MODES}")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == setup_fee.org_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_name = tenant.name if tenant else "Organization"

    before_vals = {"status": setup_fee.status, "amount": float(setup_fee.amount)}

    payment_date = req.date_received
    if not payment_date and req.payment_date:
        try:
            if isinstance(req.payment_date, str):
                payment_date = datetime.strptime(req.payment_date, "%Y-%m-%d")
        except Exception:
            payment_date = datetime.utcnow()
    if not payment_date:
        payment_date = datetime.utcnow()

    inv, inv_num = await create_gst_invoice_for_billing(
        db=db,
        tenant_id=setup_fee.org_id,
        amount=amount_to_pay,
        charge_type="setup_fee",
        description="Invenza Dedicated Platform Setup & Architecture Deployment",
        payment_date=payment_date,
    )

    setup_fee.amount = amount_to_pay
    setup_fee.status = "Paid"
    setup_fee.date_paid = payment_date
    setup_fee.payment_mode = req.payment_mode
    setup_fee.recorded_by = admin.full_name or admin.email
    setup_fee.note = req.note
    setup_fee.gst_invoice_id = inv.id
    setup_fee.invoice_number = inv_num

    # Update legacy profile
    prof_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == setup_fee.org_id))
    prof = prof_res.scalar_one_or_none()
    if prof:
        prof.setup_fee = amount_to_pay
        prof.setup_fee_status = "paid"
        prof.setup_fee_paid_at = payment_date
        prof.setup_fee_payment_mode = req.payment_mode
        prof.setup_fee_recorded_by = setup_fee.recorded_by

    after_vals = {
        "status": "Paid",
        "amount": amount_to_pay,
        "payment_mode": req.payment_mode,
        "date_paid": payment_date.isoformat(),
        "invoice_number": inv_num,
    }

    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=setup_fee.org_id,
        tenant_name=tenant_name,
        action_type="setup_fee_marked_paid",
        target_type="billing",
        target_id=str(setup_fee.id),
        description=f"Marked setup fee as Paid ({currency_symbol((tenant.currency_code or 'INR') if tenant else 'INR')}{amount_to_pay:,.2f}) via {req.payment_mode} for {tenant_name} (Invoice: {inv_num})",
        before_values=before_vals,
        after_values=after_vals,
    ))

    await db.commit()
    await db.refresh(setup_fee)

    # Dispatch official GST Tax Invoice & payment receipt email
    try:
        admin_user_res = await db.execute(
            select(User).where(and_(User.tenant_id == setup_fee.org_id, User.role.in_(["admin", "super_admin"])))
        )
        admin_user = admin_user_res.scalars().first()
        rcpt_email = admin_user.email if admin_user else admin.email
        rcpt_name = admin_user.full_name if admin_user else tenant_name

        await EmailService.send_billing_receipt_email(
            recipient_email=rcpt_email,
            recipient_name=rcpt_name,
            company_name=tenant_name,
            invoice_number=inv_num,
            payment_mode=req.payment_mode,
            taxable_value=float(inv.total_taxable_value or 0.0),
            cgst=float(inv.total_cgst or 0.0),
            sgst=float(inv.total_sgst or 0.0),
            igst=float(inv.total_igst or 0.0),
            single_tax=float(inv.total_single_tax or 0.0),
            tax_type=inv.tax_type or "GST",
            tax_label=TAX_LABELS.get(inv.tax_type or "GST", "GST"),
            currency_code=inv.currency_code or "INR",
            currency_symbol=currency_symbol(inv.currency_code),
            grand_total=float(inv.grand_total or 0.0),
            place_of_supply=inv.place_of_supply or "India",
            invoice_id=str(setup_fee.id),
        )
    except Exception as e:
        print(f"[Billing Email Warning]: Failed to dispatch setup fee invoice receipt: {e}")

    return {
        "success": True,
        "message": f"Setup fee marked as Paid. Invoice {inv_num} generated.",
        "invoice_number": inv_num,
        "setup_fee": setup_fee,
        "tax_summary": {
            "subtotal": float(inv.total_taxable_value or 0.0),
            "cgst": float(inv.total_cgst or 0.0),
            "sgst": float(inv.total_sgst or 0.0),
            "igst": float(inv.total_igst or 0.0),
            "total": float(inv.grand_total or 0.0),
            "is_inter_state": bool(inv.is_inter_state),
            "place_of_supply": inv.place_of_supply,
        },
    }


@router.post("/cycles/{cycle_id}/mark-paid")
async def mark_cycle_paid(
    cycle_id: UUID,
    req: MarkPaidRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Mark a Monthly Maintenance Cycle row as Paid.
    Captures confirmed amount, date received, payment mode, and note.
    Auto-generates sequential GST-compliant tax invoice and logs to audit log.
    Guardrail: Prevents marking as Paid or Waived twice.
    """
    c_res = await db.execute(select(OrgMaintenanceCycle).where(OrgMaintenanceCycle.id == cycle_id))
    cycle = c_res.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Maintenance cycle record not found")

    if cycle.status in ["Paid", "Waived"]:
        raise HTTPException(status_code=400, detail=f"Monthly cycle has already been finalized as {cycle.status}.")

    amount_to_pay = req.confirmed_amount if req.confirmed_amount is not None else (req.amount if req.amount is not None else float(cycle.amount))
    if amount_to_pay < 0:
        raise HTTPException(status_code=400, detail="Confirmed amount cannot be negative.")

    if req.payment_mode not in VALID_PAYMENT_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid payment mode. Must be one of {VALID_PAYMENT_MODES}")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == cycle.org_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_name = tenant.name if tenant else "Organization"

    before_vals = {"status": cycle.status, "amount": float(cycle.amount)}

    payment_date = req.date_received
    if not payment_date and req.payment_date:
        try:
            if isinstance(req.payment_date, str):
                payment_date = datetime.strptime(req.payment_date, "%Y-%m-%d")
        except Exception:
            payment_date = datetime.utcnow()
    if not payment_date:
        payment_date = datetime.utcnow()

    inv, inv_num = await create_gst_invoice_for_billing(
        db=db,
        tenant_id=cycle.org_id,
        amount=amount_to_pay,
        charge_type="monthly_maintenance",
        description=f"Invenza SaaS Cloud Maintenance & Technical Support ({cycle.cycle_month})",
        payment_date=payment_date,
    )

    cycle.amount = amount_to_pay
    cycle.status = "Paid"
    cycle.date_paid = payment_date
    cycle.payment_mode = req.payment_mode
    cycle.recorded_by = admin.full_name or admin.email
    cycle.note = req.note
    cycle.gst_invoice_id = inv.id
    cycle.invoice_number = inv_num

    # Update legacy profile last payment date
    prof_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == cycle.org_id))
    prof = prof_res.scalar_one_or_none()
    if prof:
        prof.last_payment_date = payment_date

    after_vals = {
        "status": "Paid",
        "amount": amount_to_pay,
        "payment_mode": req.payment_mode,
        "date_paid": payment_date.isoformat(),
        "invoice_number": inv_num,
    }

    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=cycle.org_id,
        tenant_name=tenant_name,
        action_type="cycle_marked_paid",
        target_type="billing",
        target_id=str(cycle.id),
        description=f"Marked cycle {cycle.cycle_month} as Paid ({currency_symbol((tenant.currency_code or 'INR') if tenant else 'INR')}{amount_to_pay:,.2f}) via {req.payment_mode} for {tenant_name} (Invoice: {inv_num})",
        before_values=before_vals,
        after_values=after_vals,
    ))

    await db.commit()
    await db.refresh(cycle)

    # Dispatch official GST Tax Invoice & payment receipt email
    try:
        admin_user_res = await db.execute(
            select(User).where(and_(User.tenant_id == cycle.org_id, User.role.in_(["admin", "super_admin"])))
        )
        admin_user = admin_user_res.scalars().first()
        rcpt_email = admin_user.email if admin_user else admin.email
        rcpt_name = admin_user.full_name if admin_user else tenant_name

        await EmailService.send_billing_receipt_email(
            recipient_email=rcpt_email,
            recipient_name=rcpt_name,
            company_name=tenant_name,
            invoice_number=inv_num,
            payment_mode=req.payment_mode,
            taxable_value=float(inv.total_taxable_value or 0.0),
            cgst=float(inv.total_cgst or 0.0),
            sgst=float(inv.total_sgst or 0.0),
            igst=float(inv.total_igst or 0.0),
            single_tax=float(inv.total_single_tax or 0.0),
            tax_type=inv.tax_type or "GST",
            tax_label=TAX_LABELS.get(inv.tax_type or "GST", "GST"),
            currency_code=inv.currency_code or "INR",
            currency_symbol=currency_symbol(inv.currency_code),
            grand_total=float(inv.grand_total or 0.0),
            place_of_supply=inv.place_of_supply or "India",
            invoice_id=str(cycle.id),
        )
    except Exception as e:
        print(f"[Billing Email Warning]: Failed to dispatch cycle invoice receipt: {e}")

    return {
        "success": True,
        "message": f"Cycle {cycle.cycle_month} marked as Paid. Invoice {inv_num} generated.",
        "invoice_number": inv_num,
        "cycle": cycle,
        "tax_summary": {
            "subtotal": float(inv.total_taxable_value or 0.0),
            "cgst": float(inv.total_cgst or 0.0),
            "sgst": float(inv.total_sgst or 0.0),
            "igst": float(inv.total_igst or 0.0),
            "total": float(inv.grand_total or 0.0),
            "is_inter_state": bool(inv.is_inter_state),
            "place_of_supply": inv.place_of_supply,
        },
    }


@router.post("/cycles/{cycle_id}/mark-waived")
async def mark_cycle_waived(
    cycle_id: UUID,
    req: MarkWaivedRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Mark a Monthly Maintenance Cycle row as Waived (Monthly Cycle only, not Setup Fee).
    Requires a reason note. Generates NO invoice. Logs action to audit log.
    Guardrail: Prevents marking as Paid or Waived twice.
    """
    c_res = await db.execute(select(OrgMaintenanceCycle).where(OrgMaintenanceCycle.id == cycle_id))
    cycle = c_res.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Maintenance cycle record not found")

    if cycle.status in ["Paid", "Waived"]:
        raise HTTPException(status_code=400, detail=f"Monthly cycle has already been finalized as {cycle.status}.")

    reason = (req.reason_note or req.reason or "").strip()
    if not reason or len(reason) < 2:
        raise HTTPException(status_code=400, detail="A valid reason note is required to waive a monthly maintenance cycle.")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == cycle.org_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_name = tenant.name if tenant else "Organization"

    before_vals = {"status": cycle.status, "amount": float(cycle.amount)}

    cycle.status = "Waived"
    cycle.note = reason
    cycle.recorded_by = admin.full_name or admin.email
    cycle.date_paid = datetime.utcnow()
    # Statutory requirement: No invoice is generated for waived/₹0 cycles
    cycle.gst_invoice_id = None
    cycle.invoice_number = None

    after_vals = {
        "status": "Waived",
        "reason_note": reason,
        "date_waived": cycle.date_paid.isoformat(),
    }

    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=cycle.org_id,
        tenant_name=tenant_name,
        action_type="cycle_marked_waived",
        target_type="billing",
        target_id=str(cycle.id),
        description=f"Marked cycle {cycle.cycle_month} as Waived for {tenant_name}. Reason: {reason}",
        before_values=before_vals,
        after_values=after_vals,
    ))

    await db.commit()
    await db.refresh(cycle)
    return {
        "success": True,
        "message": f"Cycle {cycle.cycle_month} marked as Waived. No invoice generated.",
        "status": "Waived",
        "gst_invoice_id": None,
        "invoice_number": None,
        "cycle": cycle,
    }


# ═════════════════════════════════════════════════════════════════════════════════════
# MAINTENANCE RATE UPDATE & APPEND-ONLY HISTORY
# ═════════════════════════════════════════════════════════════════════════════════════

@router.post("/tenants/{tenant_id}/maintenance-plan")
async def update_tenant_maintenance_rate(
    tenant_id: UUID,
    req: UpdateMaintenanceRateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Update current maintenance rate for an organization.
    Creates a new org_maintenance_plan row (never overwriting existing ones).
    Logs rate adjustment to platform audit log.
    """
    if req.new_rate < 0:
        raise HTTPException(status_code=400, detail="Maintenance rate cannot be negative.")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get previous plan
    plan_res = await db.execute(
        select(OrgMaintenancePlan)
        .where(OrgMaintenancePlan.org_id == tenant_id)
        .order_by(OrgMaintenancePlan.effective_from.desc(), OrgMaintenancePlan.created_at.desc())
    )
    latest_plan = plan_res.scalars().first()
    prev_rate = float(latest_plan.current_rate) if latest_plan else 0.0

    effective_dt = req.effective_from or datetime.utcnow()

    # Never overwrite — always insert a new row per Requirement 2
    new_plan = OrgMaintenancePlan(
        org_id=tenant_id,
        current_rate=req.new_rate,
        effective_from=effective_dt,
        changed_by=admin.full_name or admin.email,
        reason=req.reason or "Negotiated maintenance rate adjustment",
    )
    db.add(new_plan)

    # Keep TenantBillingProfile synchronized
    prof_res = await db.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == tenant_id))
    prof = prof_res.scalar_one_or_none()
    if prof:
        prof.monthly_maintenance_fee = req.new_rate

    # Record to AuditLog
    rate_sym = currency_symbol(tenant.currency_code or "INR")
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        action_type="maintenance_rate_changed",
        target_type="billing",
        target_id=str(tenant_id),
        description=f"Adjusted agreed maintenance rate from {rate_sym}{prev_rate:,.2f} to {rate_sym}{req.new_rate:,.2f} for {tenant.name} (Effective: {effective_dt.strftime('%Y-%m-%d')})",
        before_values={"current_rate": prev_rate},
        after_values={
            "current_rate": req.new_rate,
            "effective_from": effective_dt.isoformat(),
            "reason": req.reason,
        },
    ))

    await db.commit()
    await db.refresh(new_plan)
    return {
        "success": True,
        "message": f"Maintenance plan updated to {rate_sym}{req.new_rate:,.2f} / month.",
        "plan": new_plan,
    }


# ═════════════════════════════════════════════════════════════════════════════════════
# INVOICE PDF DOWNLOAD ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════════════

@router.get("/setup-fee/{setup_fee_id}/invoice-pdf")
async def get_setup_fee_invoice_pdf_by_id(
    setup_fee_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Download GST Tax Invoice PDF for a paid setup fee by setup_fee_id.
    """
    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.id == setup_fee_id))
    sf = sf_res.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="Setup fee record not found")

    if sf.status != "Paid":
        raise HTTPException(status_code=400, detail="GST Invoice PDF is only available for paid setup fees.")

    # Auto-generate GST invoice if invoice_number was not previously generated
    if not sf.invoice_number:
        inv, inv_num = await create_gst_invoice_for_billing(
            db=db,
            tenant_id=sf.org_id,
            amount=float(sf.amount),
            charge_type="setup_fee",
            description="Invenza Dedicated Platform Setup & Architecture Deployment",
            payment_date=sf.date_paid or sf.created_at or datetime.utcnow(),
        )
        sf.invoice_number = inv_num
        sf.gst_invoice_id = inv.id
        await db.commit()
        await db.refresh(sf)

    inv_data = await build_pdf_invoice_dict_from_tax(
        db=db,
        tenant_id=sf.org_id,
        amount=float(sf.amount),
        charge_type="setup_fee",
        desc="Invenza Dedicated Platform Setup & Architecture Deployment",
        invoice_number=sf.invoice_number,
        payment_date=sf.date_paid,
        is_waived=False,
    )

    pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(inv_data)
    safe_num = sf.invoice_number.replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Invoice_{safe_num}.pdf"'},
    )


@router.get("/cycles/{cycle_id}/invoice-pdf")
async def get_cycle_invoice_pdf_by_id(
    cycle_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Download GST Tax Invoice PDF for a paid maintenance cycle by cycle_id.
    """
    c_res = await db.execute(select(OrgMaintenanceCycle).where(OrgMaintenanceCycle.id == cycle_id))
    cycle = c_res.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Maintenance cycle record not found")

    if cycle.status != "Paid":
        raise HTTPException(status_code=400, detail="GST Invoice PDF is only available for paid maintenance cycles.")

    # Auto-generate GST invoice if invoice_number was not previously generated
    if not cycle.invoice_number:
        inv, inv_num = await create_gst_invoice_for_billing(
            db=db,
            tenant_id=cycle.org_id,
            amount=float(cycle.amount),
            charge_type="monthly_maintenance",
            description=f"Invenza SaaS Cloud Maintenance & Technical Support ({cycle.cycle_month})",
            payment_date=cycle.date_paid or cycle.created_at or datetime.utcnow(),
        )
        cycle.invoice_number = inv_num
        cycle.gst_invoice_id = inv.id
        await db.commit()
        await db.refresh(cycle)

    inv_data = await build_pdf_invoice_dict_from_tax(
        db=db,
        tenant_id=cycle.org_id,
        amount=float(cycle.amount),
        charge_type="monthly_maintenance",
        desc=f"Invenza SaaS Cloud Maintenance & Technical Support ({cycle.cycle_month})",
        invoice_number=cycle.invoice_number,
        payment_date=cycle.date_paid,
        is_waived=False,
    )

    pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(inv_data)
    safe_num = cycle.invoice_number.replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Invoice_{safe_num}.pdf"'},
    )


# Backward-compatible endpoints for old UI / test callers
@router.get("/tenants/{tenant_id}/setup-fee/invoice-pdf")
async def get_setup_fee_invoice_pdf(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.org_id == tenant_id))
    sf = sf_res.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="Setup fee record not found")
    return await get_setup_fee_invoice_pdf_by_id(setup_fee_id=sf.id, db=db, _=admin)


@router.get("/tenants/{tenant_id}/payments/{payment_id}/invoice-pdf")
async def get_payment_invoice_pdf_compat(
    tenant_id: UUID,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    # Check if payment_id maps to OrgMaintenanceCycle or OrgSetupFee
    c_res = await db.execute(select(OrgMaintenanceCycle).where(OrgMaintenanceCycle.id == payment_id))
    cycle = c_res.scalar_one_or_none()
    if cycle:
        return await get_cycle_invoice_pdf_by_id(cycle_id=cycle.id, db=db, _=admin)

    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.id == payment_id))
    sf = sf_res.scalar_one_or_none()
    if sf:
        return await get_setup_fee_invoice_pdf_by_id(setup_fee_id=sf.id, db=db, _=admin)

    raise HTTPException(status_code=404, detail="Payment record not found")


@router.post("/tenants/{tenant_id}/setup-fee")
@router.put("/tenants/{tenant_id}/setup-fee")
async def update_setup_fee_compat(
    tenant_id: UUID,
    req: UpdateSetupFeeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    sf_res = await db.execute(select(OrgSetupFee).where(OrgSetupFee.org_id == tenant_id))
    sf = sf_res.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="Setup fee record not found")

    amt = req.get_amount()
    st = req.get_status()
    if st.lower() == "paid":
        mark_req = MarkPaidRequest(
            confirmed_amount=amt if amt is not None else float(sf.amount),
            date_received=datetime.utcnow(),
            payment_mode=req.payment_mode or "Bank Transfer",
            note=req.notes,
        )
        return await mark_setup_fee_paid(setup_fee_id=sf.id, req=mark_req, db=db, admin=admin)
    else:
        if amt is not None:
            sf.amount = amt
        sf.status = "Pending"
        await db.commit()
        return {"success": True, "message": "Setup fee updated"}


@router.post("/tenants/{tenant_id}/update-fee")
async def update_monthly_fee_compat(
    tenant_id: UUID,
    req: UpdateMaintenanceFeeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    return await update_tenant_maintenance_rate(
        tenant_id=tenant_id,
        req=UpdateMaintenanceRateRequest(
            new_rate=req.get_new_amount(),
            effective_from=req.effective_from,
            reason=req.reason,
        ),
        db=db,
        admin=admin,
    )


@router.post("/tenants/{tenant_id}/payments")
async def record_payment_compat(
    tenant_id: UUID,
    req: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    # Find or create cycle for req.cycle_month
    cycle_res = await db.execute(
        select(OrgMaintenanceCycle).where(
            and_(OrgMaintenanceCycle.org_id == tenant_id, OrgMaintenanceCycle.cycle_month == req.cycle_month)
        )
    )
    cycle = cycle_res.scalar_one_or_none()
    if not cycle:
        cycle = OrgMaintenanceCycle(
            org_id=tenant_id,
            cycle_month=req.cycle_month,
            amount=req.amount,
            status="Pending",
            recorded_by=admin.full_name or admin.email,
        )
        db.add(cycle)
        await db.flush()

    if req.status == "waived" or float(req.amount or 0) == 0:
        return await mark_cycle_waived(
            cycle_id=cycle.id,
            req=MarkWaivedRequest(reason_note=req.notes or "Waived by administrator"),
            db=db,
            admin=admin,
        )
    else:
        return await mark_cycle_paid(
            cycle_id=cycle.id,
            req=MarkPaidRequest(
                confirmed_amount=req.amount,
                date_received=datetime.utcnow(),
                payment_mode=req.payment_mode if req.payment_mode in VALID_PAYMENT_MODES else "Bank Transfer",
                note=req.notes,
            ),
            db=db,
            admin=admin,
        )
