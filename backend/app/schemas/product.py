from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

VALID_GST_RATES: List[float] = [0.0, 5.0, 18.0, 40.0]

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    category: str = Field("General", max_length=100)
    unit_of_measure: str = Field("pcs", max_length=50)
    cost_price: float = Field(0.0, ge=0.0)
    sell_price: float = Field(0.0, ge=0.0)
    barcode: Optional[str] = None
    reorder_point: float = Field(10.0, ge=0.0)
    max_stock: Optional[float] = Field(None, ge=0.0)
    hsn_code: str = Field("8471", min_length=2, max_length=20, description="HSN classification code")
    gst_rate: float = Field(18.0, description="Default GST percentage (0%, 5%, 18%, 40%)")
    variant_attributes: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("hsn_code")
    @classmethod
    def validate_hsn_code(cls, v: str) -> str:
        clean = (v or "").strip()
        if not clean:
            raise ValueError("HSN code cannot be empty")
        return clean

    @field_validator("gst_rate")
    @classmethod
    def validate_gst_rate(cls, v: float) -> float:
        val = float(v)
        if val not in VALID_GST_RATES:
            raise ValueError(f"Invalid GST rate: {val}%. Allowed GST 2.0 slab rates are 0%, 5%, 18%, and 40%.")
        return val

class ProductCreate(ProductBase):
    initial_stock: Optional[float] = Field(0.0, ge=0.0)

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    barcode: Optional[str] = None
    reorder_point: Optional[float] = None
    max_stock: Optional[float] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    variant_attributes: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator("hsn_code")
    @classmethod
    def validate_hsn_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("HSN code cannot be empty")
            return clean
        return v

    @field_validator("gst_rate")
    @classmethod
    def validate_gst_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            val = float(v)
            if val not in VALID_GST_RATES:
                raise ValueError(f"Invalid GST rate: {val}%. Allowed GST 2.0 slab rates are 0%, 5%, 18%, and 40%.")
            return val
        return v

class ProductResponse(ProductBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    current_stock: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
