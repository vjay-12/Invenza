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
    max_stock = Column(Numeric(12, 2), nullable=True, default=100.00)
    hsn_code = Column(String(20), nullable=False, default="8471")  # Harmonized System Nomenclature (e.g. 8471, 9403)
    gst_rate = Column(Numeric(5, 2), nullable=False, default=18.00)  # GST rate percentage (e.g. 5.0, 12.0, 18.0, 28.0)
    
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
