import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class TenantBillingProfile(Base):
    __tablename__ = "tenant_billing_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    setup_fee = Column(Numeric(12, 2), default=0.00, nullable=False)
    setup_fee_status = Column(String(50), default="pending", nullable=False)  # 'paid', 'pending', 'waived'
    setup_fee_paid_at = Column(DateTime, nullable=True)
    setup_fee_payment_mode = Column(String(50), default="manual", nullable=True)  # 'manual', 'gateway'
    setup_fee_recorded_by = Column(String(255), nullable=True)
    monthly_maintenance_fee = Column(Numeric(12, 2), default=0.00, nullable=False)
    maintenance_currency = Column(String(10), default="INR", nullable=False)
    billing_cycle_day = Column(Integer, default=1, nullable=False)
    next_due_date = Column(DateTime, nullable=True)
    last_payment_date = Column(DateTime, nullable=True)
    payment_gateway_customer_id = Column(String(100), nullable=True)
    payment_gateway_subscription_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class BillingFeeHistory(Base):
    __tablename__ = "billing_fee_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_amount = Column(Numeric(12, 2), nullable=False)
    new_amount = Column(Numeric(12, 2), nullable=False)
    effective_from = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    recorded_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class BillingPaymentRecord(Base):
    __tablename__ = "billing_payment_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle_month = Column(String(20), nullable=False, index=True)  # e.g., '2026-09'
    charge_type = Column(String(50), default="monthly_maintenance", nullable=False)  # 'setup_fee', 'monthly_maintenance', 'feature_addon'
    amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # 'paid', 'waived', 'pending', 'overdue'
    payment_mode = Column(String(50), default="manual", nullable=False)  # 'manual', 'gateway'
    payment_reference = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    recorded_by = Column(String(255), nullable=True)
    line_items = Column(JSONB, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    # GST Invoicing Fields
    invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(DateTime, nullable=True)
    taxable_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    gst_rate = Column(Numeric(5, 2), default=18.00, nullable=True)
    cgst_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    sgst_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    igst_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    total_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    sac_code = Column(String(20), default="998313", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

# ═════════════════════════════════════════════════════════════════════════════════════
# EXPLICIT BILLING DATA MODEL (Setup Fee, Rate Plan History, Monthly Maintenance Cycles)
# ═════════════════════════════════════════════════════════════════════════════════════

VALID_PAYMENT_MODES = ["Cash", "Bank Transfer", "UPI", "Other", "Gateway"]

class OrgSetupFee(Base):
    __tablename__ = "org_setup_fee"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    status = Column(String(50), default="Pending", nullable=False, index=True)  # 'Pending', 'Paid'
    date_paid = Column(DateTime, nullable=True)
    payment_mode = Column(String(50), nullable=True)  # 'Cash', 'Bank Transfer', 'UPI', 'Other', 'Gateway'
    recorded_by = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    gst_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(100), nullable=True, index=True)
    gateway_transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OrgMaintenancePlan(Base):
    __tablename__ = "org_maintenance_plan"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    current_rate = Column(Numeric(12, 2), default=0.00, nullable=False)
    effective_from = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    changed_by = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OrgMaintenanceCycle(Base):
    __tablename__ = "org_maintenance_cycle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle_month = Column(String(20), nullable=False, index=True)  # e.g. '2026-10'
    amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    status = Column(String(50), default="Pending", nullable=False, index=True)  # 'Pending', 'Paid', 'Waived'
    date_paid = Column(DateTime, nullable=True)
    payment_mode = Column(String(50), nullable=True)  # 'Cash', 'Bank Transfer', 'UPI', 'Other', 'Gateway'
    recorded_by = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    gst_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(100), nullable=True, index=True)
    gateway_transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

