from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_GST_RATES: List[float] = [0.0, 5.0, 12.0, 18.0, 28.0, 40.0]

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
    hsn_code: Optional[str] = Field(None, max_length=20, description="Tax / HSN classification code")
    gst_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Tax rate percentage")
    tax_code: Optional[str] = Field(None, max_length=20, description="Generic tax code alias for hsn_code")
    tax_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Generic tax rate alias for gst_rate")
    variant_attributes: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def reconcile_tax_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Cross-populate tax_code <-> hsn_code
            tc = data.get("tax_code")
            hc = data.get("hsn_code")
            resolved_code = tc if tc is not None else hc
            if resolved_code is not None:
                resolved_code = str(resolved_code).strip()
            data["tax_code"] = resolved_code
            data["hsn_code"] = resolved_code

            # Cross-populate tax_rate <-> gst_rate
            tr = data.get("tax_rate")
            gr = data.get("gst_rate")
            resolved_rate = tr if tr is not None else gr
            if resolved_rate is not None:
                try:
                    resolved_rate = float(resolved_rate)
                except (ValueError, TypeError):
                    pass
            data["tax_rate"] = resolved_rate
            data["gst_rate"] = resolved_rate
        return data

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
    tax_code: Optional[str] = None
    tax_rate: Optional[float] = None
    variant_attributes: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_update_tax_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tc = data.get("tax_code")
            hc = data.get("hsn_code")
            if tc is not None and hc is None:
                data["hsn_code"] = str(tc).strip() if tc else ""
            elif hc is not None and tc is None:
                data["tax_code"] = str(hc).strip() if hc else ""

            tr = data.get("tax_rate")
            gr = data.get("gst_rate")
            if tr is not None and gr is None:
                try:
                    data["gst_rate"] = float(tr)
                except (ValueError, TypeError):
                    pass
            elif gr is not None and tr is None:
                try:
                    data["tax_rate"] = float(gr)
                except (ValueError, TypeError):
                    pass
        return data

class ProductResponse(ProductBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    current_stock: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
