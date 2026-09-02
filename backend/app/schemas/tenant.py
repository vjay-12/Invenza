from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    industry: str = Field("General Merchandise", min_length=2, max_length=100)
    location: str = Field("Headquarters", min_length=2, max_length=255)
    currency_code: str = Field("USD", min_length=3, max_length=10)
    admin_full_name: str = Field(..., min_length=2, max_length=255)
    admin_email: str = Field(..., min_length=5, max_length=255)
    admin_password: str = Field(..., min_length=6)
    enabled_modules: List[str] = Field(
        default_factory=lambda: [
            "products",
            "locations",
            "orders",
            "transfers",
            "adjustments",
            "ledger",
            "reports",
            "storage",
        ]
    )
    send_email: bool = True

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    currency_code: Optional[str] = None
    enabled_modules: Optional[List[str]] = None
    is_active: Optional[bool] = None

class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    industry: Optional[str] = None
    location: Optional[str] = None
    currency_code: str
    enabled_modules: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None
    product_count: int = 0
    user_count: int = 0
    storage_count: int = 0

    class Config:
        from_attributes = True

class CompanyAnalyticsResponse(BaseModel):
    company_id: UUID
    company_name: str
    industry: Optional[str] = None
    total_products: int
    total_stock_units: float
    total_inventory_valuation: float
    total_movements: int
    total_orders: int
    total_users: int
    total_storage_files: int
    is_active: bool
