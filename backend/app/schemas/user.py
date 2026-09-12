from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.user import UserRole

class UserBase(BaseModel):
    email: str
    full_name: str
    role: str = UserRole.STAFF.value
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    tenant_name: Optional[str] = "Default Org"

class CompanyUserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: str = Field(default="staff")
    permissions: List[str] = Field(
        default_factory=lambda: ["inventory:read", "inventory:write"]
    )
    send_email: bool = True

class CompanyUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_role: str
    tenant_id: str
    full_name: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    enabled_modules: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    currency_code: str = "INR"  # tenant-derived, locked
    country_code: str = "IN"    # tenant-derived, locked
    state: Optional[str] = None
    tax_type: str = "GST"
    tax_rate: Optional[float] = None
    tax_label: str = "GST"

class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

class VerifyResetOtpRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    otp: str = Field(..., min_length=6, max_length=6)

class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)

