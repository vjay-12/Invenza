from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class LeadInquiryCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    company_code: Optional[str] = Field(None, max_length=50)
    industry: str = Field("General Merchandise", max_length=100)
    location: str = Field("Headquarters", max_length=255)
    contact_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=5, max_length=50)
    whatsapp_number: Optional[str] = Field(None, max_length=50)
    estimated_warehouses: Optional[str] = Field("1-2", max_length=50)
    estimated_skus: Optional[str] = Field("< 500", max_length=50)
    estimated_monthly_orders: Optional[str] = Field("< 1,000", max_length=50)
    selected_modules: List[str] = Field(
        default_factory=lambda: [
            "products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"
        ]
    )
    tier_estimate: Optional[str] = Field("Growth Suite", max_length=100)
    quoted_amount: Optional[float] = 0.0
    notes: Optional[str] = None

class LeadInquiryStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)  # 'new', 'in_discussion', 'quoted', 'converted', 'rejected_lost'
    quoted_amount: Optional[float] = None
    notes: Optional[str] = None

class LeadInquiryResponse(BaseModel):
    id: UUID
    company_name: str
    company_code: Optional[str] = None
    industry: str
    location: str
    contact_name: str
    email: str
    phone: str
    whatsapp_number: Optional[str] = None
    estimated_warehouses: Optional[str] = None
    estimated_skus: Optional[str] = None
    estimated_monthly_orders: Optional[str] = None
    selected_modules: List[str]
    tier_estimate: Optional[str] = None
    quoted_amount: Optional[float] = 0.0
    converted_tenant_id: Optional[UUID] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    whatsapp_url: Optional[str] = None

    class Config:
        from_attributes = True
