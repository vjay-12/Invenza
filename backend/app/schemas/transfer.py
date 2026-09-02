from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class TransferItemCreate(BaseModel):
    product_id: UUID
    quantity: float = Field(..., gt=0)

class TransferItemResponse(TransferItemCreate):
    id: UUID
    sku: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

class StockTransferCreate(BaseModel):
    source_location_id: UUID
    target_location_id: UUID
    notes: Optional[str] = None
    items: List[TransferItemCreate]

class StockTransferResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    transfer_number: str
    source_location_id: UUID
    source_location_name: Optional[str] = None
    target_location_id: UUID
    target_location_name: Optional[str] = None
    status: str
    transfer_date: datetime
    notes: Optional[str] = None
    items: List[TransferItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
