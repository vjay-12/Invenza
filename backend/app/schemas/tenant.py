from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    company_code: Optional[str] = Field(None, max_length=50)
    unique_code: Optional[str] = Field(None, max_length=50)
    industry: str = Field("General Merchandise", min_length=2, max_length=100)
    location: str = Field("Headquarters", min_length=2, max_length=255)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    currency_code: str = Field("INR", min_length=3, max_length=10)
    tier: Optional[str] = Field("Growth Suite", max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list)
    lead_id: Optional[UUID] = None
    setup_fee: float = Field(..., ge=0.0, description="Required one-time Setup Fee in INR")
    monthly_maintenance_fee: float = Field(..., ge=0.0, description="Required initial Monthly Maintenance rate in INR (can be 0)")
    quoted_setup_fee: Optional[float] = None
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
    company_code: Optional[str] = None
    unique_code: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    currency_code: Optional[str] = None
    tier: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled_modules: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None

class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    company_code: Optional[str] = None
    unique_code: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    currency_code: str
    tier: Optional[str] = "Growth Suite"
    tags: Optional[List[str]] = []
    enabled_modules: List[str]
    is_active: bool
    is_archived: bool = False
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
