from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.adjustment import AdjustmentReason

class StockAdjustmentCreate(BaseModel):
    location_id: UUID
    product_id: UUID
    new_stock: float = Field(..., ge=0)
    reason_code: AdjustmentReason
    notes: str = Field(..., min_length=3, description="Mandatory audit justification notes")
    author: Optional[str] = "Sarah Connor (Admin)"

class StockAdjustmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    adjustment_number: str
    location_id: UUID
    location_name: Optional[str] = None
    product_id: UUID
    sku: Optional[str] = None
    product_name: Optional[str] = None
    previous_stock: float
    new_stock: float
    delta: float
    reason_code: AdjustmentReason
    notes: str
    author: str
    created_at: datetime

    class Config:
        from_attributes = True

class BulkAdjustmentItem(BaseModel):
    product_id: UUID
    location_id: UUID
    delta: float
    reason_code: AdjustmentReason
    notes: str

class BulkAdjustmentRequest(BaseModel):
    adjustments: List[BulkAdjustmentItem]
    author: Optional[str] = "Admin"
