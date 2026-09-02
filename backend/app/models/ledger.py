import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base

class MovementTypeEnum(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"
    TRANSFER = "TRANSFER"

class StockMovement(Base):
    """
    Immutable ledger for all inventory movements.
    Records should NEVER be mutated or deleted.
    Current stock is always computed by aggregating movements.
    """
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True)
    
    movement_type = Column(SQLEnum(MovementTypeEnum), nullable=False, index=True)
    quantity = Column(Numeric(12, 4), nullable=False)  # positive or signed delta
    unit_cost = Column(Numeric(12, 4), nullable=False, default=0.00)
    
    reference_type = Column(String(50), nullable=False)  # 'PO', 'SO', 'ADJUST', 'TRANSFER', 'INITIAL'
    reference_id = Column(String(100), nullable=False, index=True)
    
    reason_code = Column(String(50), nullable=True)      # e.g., 'damage', 'loss', 'miscount'
    performed_by = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_movements_tenant_product_loc", "tenant_id", "product_id", "location_id"),
        Index("ix_movements_timestamp_desc", "timestamp"),
    )
