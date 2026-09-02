from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.order import OrderStatus

class POLineItemCreate(BaseModel):
    product_id: UUID
    ordered_qty: float = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)

class POLineItemResponse(POLineItemCreate):
    id: UUID
    received_qty: float
    sku: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

class PurchaseOrderCreate(BaseModel):
    supplier_name: str = Field(..., max_length=255)
    target_location_id: UUID
    order_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[POLineItemCreate]

class PurchaseOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    po_number: str
    supplier_name: str
    status: OrderStatus
    target_location_id: UUID
    target_location_name: Optional[str] = None
    total_amount: float
    notes: Optional[str] = None
    order_date: datetime
    received_date: Optional[datetime] = None
    items: List[POLineItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class ReceiveGoodsRequest(BaseModel):
    notes: Optional[str] = None
    received_by: Optional[str] = "Admin"

# Sales Orders
class SOLineItemCreate(BaseModel):
    product_id: UUID
    ordered_qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)

class SOLineItemResponse(SOLineItemCreate):
    id: UUID
    fulfilled_qty: float
    sku: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

class SalesOrderCreate(BaseModel):
    customer_name: str = Field(..., max_length=255)
    source_location_id: UUID
    order_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[SOLineItemCreate]

class SalesOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    so_number: str
    customer_name: str
    status: OrderStatus
    source_location_id: UUID
    source_location_name: Optional[str] = None
    total_amount: float
    notes: Optional[str] = None
    order_date: datetime
    fulfilled_date: Optional[datetime] = None
    items: List[SOLineItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class FulfillOrderRequest(BaseModel):
    dispatched_by: Optional[str] = "Dispatch Lead"
