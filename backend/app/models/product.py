import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="General")
    unit_of_measure = Column(String(50), default="pcs", nullable=False)  # pcs, kg, box, etc.
    cost_price = Column(Numeric(12, 4), default=0.00, nullable=False)
    sell_price = Column(Numeric(12, 4), default=0.00, nullable=False)
    barcode = Column(String(100), nullable=True, index=True)
    reorder_point = Column(Numeric(12, 2), default=10.00, nullable=False)
    
    # Simple attribute tags (e.g. {"color": "Blue", "size": "L"})
    variant_attributes = Column(JSONB, default=dict, nullable=False)
    
    # Custom fields JSONB column for user-defined schema extensions
    custom_fields = Column(JSONB, default=dict, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_products_tenant_sku", "tenant_id", "sku", unique=True),
    )
