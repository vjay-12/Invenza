import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"

class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    legal_business_name = Column(String(255), nullable=False, default="Invenza Enterprise Ltd")
    gstin = Column(String(15), nullable=False, default="29AABCI1234F1Z5")
    pan = Column(String(10), nullable=False, default="AABCI1234F")
    registered_address = Column(Text, nullable=False, default="Plot 42, Tech Park Central, Outer Ring Road, Bengaluru, Karnataka 560103")
    state = Column(String(100), nullable=False, default="Karnataka")
    state_code = Column(String(2), nullable=False, default="29")
    logo_url = Column(String(500), nullable=True)
    authorized_signatory_name = Column(String(255), nullable=False, default="Vijay B")
    signature_url = Column(String(500), nullable=True)
    bank_name = Column(String(255), nullable=False, default="HDFC Bank")
    bank_account_number = Column(String(100), nullable=False, default="50200012345678")
    bank_ifsc_code = Column(String(50), nullable=False, default="HDFC0001234")
    bank_branch = Column(String(255), nullable=False, default="Koramangala 5th Block, Bengaluru")
    account_holder_name = Column(String(255), nullable=False, default="Invenza Enterprise Ltd")
    invoice_prefix = Column(String(20), nullable=False, default="INV")
    auto_email_invoice = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class TenantInvoiceSequence(Base):
    __tablename__ = "tenant_invoice_sequences"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    fiscal_year = Column(String(10), nullable=False, default="2026-27")
    current_number = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    legal_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    gstin = Column(String(15), nullable=True)  # Optional for unregistered/consumer
    billing_address = Column(Text, nullable=False)
    billing_state = Column(String(100), nullable=True, default="Karnataka")
    billing_state_code = Column(String(2), nullable=True, default="29")
    shipping_address = Column(Text, nullable=False)
    shipping_state = Column(String(100), nullable=True)
    shipping_state_code = Column(String(2), nullable=True)
    state = Column(String(100), nullable=False, default="Karnataka")
    state_code = Column(String(2), nullable=False, default="29")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=True)
    place_of_supply = Column(String(100), nullable=False, default="29-Karnataka")
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.ISSUED, nullable=False)

    # Seller Snapshot at time of generation
    seller_legal_name = Column(String(255), nullable=False)
    seller_gstin = Column(String(15), nullable=False)
    seller_pan = Column(String(10), nullable=False)
    seller_address = Column(Text, nullable=False)
    seller_state = Column(String(100), nullable=False)
    seller_state_code = Column(String(2), nullable=False)

    # Buyer / Customer Snapshot
    customer_name = Column(String(255), nullable=False)
    customer_gstin = Column(String(15), nullable=True)
    customer_billing_address = Column(Text, nullable=False)
    customer_shipping_address = Column(Text, nullable=False)
    customer_state = Column(String(100), nullable=False)
    customer_state_code = Column(String(2), nullable=False)

    # Tax regime flag
    is_inter_state = Column(Boolean, default=False, nullable=False)
    payment_terms = Column(String(100), default="Due on Receipt", nullable=False)

    # Totals
    total_taxable_value = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_cgst = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_sgst = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_igst = Column(Numeric(14, 2), default=0.00, nullable=False)
    round_off = Column(Numeric(8, 2), default=0.00, nullable=False)
    grand_total = Column(Numeric(14, 2), default=0.00, nullable=False)
    grand_total_words = Column(Text, nullable=False, default="")

    # MinIO / Object Storage references
    pdf_storage_key = Column(String(500), nullable=True)
    pdf_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_invoices_tenant_number", "tenant_id", "invoice_number", unique=True),
    )

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=False, default="8471")
    quantity = Column(Numeric(12, 4), nullable=False)
    unit_of_measure = Column(String(50), nullable=False, default="pcs")
    unit_price = Column(Numeric(12, 4), nullable=False)
    discount = Column(Numeric(12, 4), default=0.00, nullable=False)
    taxable_value = Column(Numeric(14, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False, default=18.00)
    cgst_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    cgst_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    sgst_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    sgst_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    igst_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    igst_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    total = Column(Numeric(14, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
