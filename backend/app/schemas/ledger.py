from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class StockMovementCreate(BaseModel):
    product_id: UUID
    location_id: UUID
    target_location_id: Optional[UUID] = None
    movement_type: str = Field(..., pattern="^(IN|OUT|ADJUST|TRANSFER)$")
    quantity: float = Field(...)
    unit_cost: float = Field(0.0, ge=0.0)
    reference_type: str = Field(..., max_length=50)
    reference_id: str = Field(..., max_length=100)
    reason_code: Optional[str] = None
    performed_by: str = Field(..., max_length=255)

class StockMovementResponse(StockMovementCreate):
    id: UUID
    tenant_id: UUID
    product_name: Optional[str] = None
    sku: Optional[str] = None
    location_name: Optional[str] = None
    target_location_name: Optional[str] = None
    running_balance: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class StockValuationSummary(BaseModel):
    total_valuation_fifo: float
    total_valuation_weighted_avg: float
    total_skus: int
    total_units: float
    low_stock_count: int
