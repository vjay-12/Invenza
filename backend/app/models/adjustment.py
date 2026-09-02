import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base

class AdjustmentReason(str, enum.Enum):
    DAMAGE = "damage"
    LOSS = "loss"
    MISCOUNT = "miscount"
    RETURN = "return"
    AUDIT = "audit"

class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    adjustment_number = Column(String(50), nullable=False, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    previous_stock = Column(Numeric(12, 4), nullable=False)
    new_stock = Column(Numeric(12, 4), nullable=False)
    delta = Column(Numeric(12, 4), nullable=False)
    reason_code = Column(SQLEnum(AdjustmentReason), nullable=False)
    notes = Column(Text, nullable=True)
    author = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
