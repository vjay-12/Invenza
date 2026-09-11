import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class LeadInquiry(Base):
    __tablename__ = "lead_inquiries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    company_code = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=False, default="General Merchandise")
    location = Column(String(255), nullable=False, default="Headquarters")
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    whatsapp_number = Column(String(50), nullable=True)
    estimated_warehouses = Column(String(50), nullable=True, default="1-2")
    estimated_skus = Column(String(50), nullable=True, default="< 500")
    estimated_monthly_orders = Column(String(50), nullable=True, default="< 1,000")
    selected_modules = Column(JSONB, default=list, nullable=False)
    tier_estimate = Column(String(100), nullable=True, default="Growth Suite")
    quoted_amount = Column(Numeric(12, 2), nullable=True, default=0.00)
    converted_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="new", nullable=False, index=True)  # 'new', 'in_discussion', 'quoted', 'converted', 'rejected_lost'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
