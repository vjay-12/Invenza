from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    category: str = Field("General", max_length=100)
    unit_of_measure: str = Field("pcs", max_length=50)
    cost_price: float = Field(0.0, ge=0.0)
    sell_price: float = Field(0.0, ge=0.0)
    barcode: Optional[str] = None
    reorder_point: float = Field(10.0, ge=0.0)
    variant_attributes: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    barcode: Optional[str] = None
    reorder_point: Optional[float] = None
    variant_attributes: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    current_stock: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
