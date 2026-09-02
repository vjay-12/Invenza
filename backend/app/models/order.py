import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    COMPLETED = "completed"  # received for PO, fulfilled for SO
    CANCELLED = "cancelled"

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    po_number = Column(String(50), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    target_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    total_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    received_date = Column(DateTime, nullable=True)
    
    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    ordered_qty = Column(Numeric(12, 4), nullable=False)
    received_qty = Column(Numeric(12, 4), default=0.00, nullable=False)
    unit_cost = Column(Numeric(12, 4), nullable=False)

    order = relationship("PurchaseOrder", back_populates="items")

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    so_number = Column(String(50), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    source_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    total_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    fulfilled_date = Column(DateTime, nullable=True)

    items = relationship("SalesOrderItem", back_populates="order", cascade="all, delete-orphan")

class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    ordered_qty = Column(Numeric(12, 4), nullable=False)
    fulfilled_qty = Column(Numeric(12, 4), default=0.00, nullable=False)
    unit_price = Column(Numeric(12, 4), nullable=False)

    order = relationship("SalesOrder", back_populates="items")
