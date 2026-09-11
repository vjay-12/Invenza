from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    amount: float
    type: Optional[str] = "charge"

class TenantBillingProfileResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: Optional[str] = None
    setup_fee: float
    setup_fee_status: str
    setup_fee_paid_at: Optional[datetime] = None
    setup_fee_payment_mode: Optional[str] = "manual"
    setup_fee_recorded_by: Optional[str] = None
    monthly_maintenance_fee: float
    maintenance_currency: str = "INR"
    billing_cycle_day: int = 1
    next_due_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    payment_gateway_customer_id: Optional[str] = None
    payment_gateway_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BillingFeeHistoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    previous_amount: float
    new_amount: float
    effective_from: datetime
    reason: Optional[str] = None
    recorded_by: str
    created_at: datetime

    class Config:
        from_attributes = True

class BillingPaymentRecordResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    cycle_month: str
    charge_type: str
    amount: float
    status: str
    payment_mode: str
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    recorded_by: Optional[str] = None
    line_items: List[Dict[str, Any]] = []
    notes: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    taxable_amount: Optional[float] = 0.0
    gst_rate: Optional[float] = 18.0
    cgst_amount: Optional[float] = 0.0
    sgst_amount: Optional[float] = 0.0
    igst_amount: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    sac_code: Optional[str] = "998313"
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateSetupFeeRequest(BaseModel):
    amount: Optional[float] = None
    setup_fee: Optional[float] = None
    status: Optional[str] = None
    setup_fee_status: Optional[str] = None
    payment_mode: Optional[str] = "manual"
    payment_reference: Optional[str] = None
    notes: Optional[str] = None

    def get_amount(self) -> Optional[float]:
        return self.setup_fee if self.setup_fee is not None else self.amount

    def get_status(self) -> str:
        return self.setup_fee_status or self.status or "paid"

class UpdateMaintenanceFeeRequest(BaseModel):
    new_amount: Optional[float] = None
    new_monthly_fee: Optional[float] = None
    effective_from: Optional[datetime] = None  # None for immediate, or future date
    reason: Optional[str] = None

    def get_new_amount(self) -> float:
        if self.new_monthly_fee is not None:
            return self.new_monthly_fee
        return self.new_amount or 0.0

class RecordPaymentRequest(BaseModel):
    cycle_month: str  # e.g., '2026-09'
    charge_type: str = "monthly_maintenance"  # 'monthly_maintenance', 'setup_fee', 'feature_addon'
    amount: float
    status: str = "paid"  # 'paid', 'waived', 'pending', 'overdue'
    payment_mode: str = "manual"  # 'manual', 'gateway'
    payment_reference: Optional[str] = None
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None

    def get_reference(self) -> Optional[str]:
        return self.payment_reference or self.transaction_reference

class BillingOrgSummary(BaseModel):
    id: Optional[UUID] = None
    tenant_id: UUID
    tenant_name: str
    company_code: Optional[str] = None
    industry: Optional[str] = None
    tier: Optional[str] = "Growth Suite"
    setup_fee_amount: float = 0.0
    setup_fee_status: str = "Pending"  # 'Pending', 'Paid'
    setup_fee: float = 0.0  # backward compat
    current_monthly_rate: float = 0.0
    monthly_maintenance_fee: float = 0.0  # backward compat
    last_payment_date: Optional[datetime] = None
    next_due_date: Optional[datetime] = None
    this_month_status: str = "Pending"  # 'Paid', 'Pending', 'Overdue', 'Waived'
    payment_status: str = "Pending"  # backward compat


class BillingOverviewResponse(BaseModel):
    total_revenue_collected: float
    pending_setup_fees: float  # amount
    pending_setup_fees_amount: float
    pending_setup_fees_count: int
    active_monthly_recurring: float
    active_mrr_sum: float  # backward compat
    zero_maintenance_orgs_count: int
    zero_maintenance_orgs: Optional[int] = None  # backward compat
    overdue_count: int
    organizations: List[BillingOrgSummary]
    tenants: Optional[List[BillingOrgSummary]] = None


# ═════════════════════════════════════════════════════════════════════════════════════
# EXPLICIT BILLING REQUEST & RESPONSE SCHEMAS
# ═════════════════════════════════════════════════════════════════════════════════════

class MarkPaidRequest(BaseModel):
    confirmed_amount: Optional[float] = Field(None, ge=0.0, description="Confirmed payment amount in INR")
    amount: Optional[float] = Field(None, ge=0.0, description="Confirmed payment amount in INR (alias)")
    date_received: Optional[datetime] = None
    payment_date: Optional[Any] = None
    payment_mode: str = Field("Bank Transfer", description="Cash, Bank Transfer, UPI, Other, Gateway")
    note: Optional[str] = None


class MarkWaivedRequest(BaseModel):
    reason_note: Optional[str] = Field(None, description="Required justification note for waiving cycle")
    reason: Optional[str] = Field(None, description="Required justification note for waiving cycle (alias)")


class UpdateMaintenanceRateRequest(BaseModel):
    new_rate: float = Field(..., ge=0.0, description="New agreed monthly maintenance rate in INR")
    effective_from: Optional[datetime] = None
    reason: Optional[str] = None


class GenerateCyclesRequest(BaseModel):
    cycle_month: Optional[str] = None  # e.g., '2026-10' for testing/simulation


class OrgSetupFeeResponse(BaseModel):
    id: UUID
    org_id: UUID
    amount: float
    status: str
    date_paid: Optional[datetime] = None
    payment_mode: Optional[str] = None
    recorded_by: Optional[str] = None
    note: Optional[str] = None
    gst_invoice_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgMaintenancePlanResponse(BaseModel):
    id: UUID
    org_id: UUID
    current_rate: float
    effective_from: datetime
    changed_by: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrgMaintenanceCycleResponse(BaseModel):
    id: UUID
    org_id: UUID
    cycle_month: str
    amount: float
    status: str
    date_paid: Optional[datetime] = None
    payment_mode: Optional[str] = None
    recorded_by: Optional[str] = None
    note: Optional[str] = None
    gst_invoice_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillingTransactionItem(BaseModel):
    item_type: str  # 'setup_fee' | 'monthly_cycle'
    id: UUID
    cycle_month: str  # 'One-Time Setup' or '2026-09'
    amount: float
    status: str  # 'Pending', 'Paid', 'Waived'
    date_paid: Optional[datetime] = None
    date_recorded: datetime
    payment_mode: Optional[str] = None
    recorded_by: Optional[str] = None
    note: Optional[str] = None
    invoice_number: Optional[str] = None
    gst_invoice_id: Optional[UUID] = None
    can_mark_paid: bool = False
    can_mark_waived: bool = False


class OrgBillingDetailResponse(BaseModel):
    org: Dict[str, Any]
    setup_fee: OrgSetupFeeResponse
    current_plan: OrgMaintenancePlanResponse
    rate_history: List[OrgMaintenancePlanResponse]
    cycles: List[OrgMaintenanceCycleResponse]
    transactions: List[BillingTransactionItem]

