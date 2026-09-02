from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class LocationBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    address: Optional[str] = None
    capacity: Optional[int] = Field(10000, ge=0)

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None

class LocationResponse(LocationBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    total_stored_units: float = 0.0
    active_skus_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
