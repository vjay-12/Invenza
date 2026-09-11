from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.invoice import InvoiceStatus

class InvoiceItemResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    item_description: str
    hsn_code: str
    quantity: float
    unit_of_measure: str
    unit_price: float
    discount: float
    taxable_value: float
    gst_rate: float
    cgst_rate: float
    cgst_amount: float
    sgst_rate: float
    sgst_amount: float
    igst_rate: float
    igst_amount: float
    total: float

    class Config:
        from_attributes = True

class InvoiceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    invoice_number: str
    sales_order_id: Optional[UUID] = None
    invoice_date: datetime
    due_date: Optional[datetime] = None
    place_of_supply: str
    status: InvoiceStatus
    seller_legal_name: str
    seller_gstin: str
    seller_pan: str
    seller_address: str
    seller_state: str
    seller_state_code: str
    customer_name: str
    customer_gstin: Optional[str] = None
    customer_billing_address: str
    customer_shipping_address: str
    customer_state: str
    customer_state_code: str
    is_inter_state: bool
    total_taxable_value: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    round_off: float
    grand_total: float
    grand_total_words: str
    pdf_url: Optional[str] = None
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True

class TenantSettingsResponse(BaseModel):
    tenant_id: UUID
    legal_business_name: str
    gstin: str
    pan: str
    registered_address: str
    state: str
    state_code: str
    logo_url: Optional[str] = None
    authorized_signatory_name: str
    signature_url: Optional[str] = None
    bank_name: str
    bank_account_number: str
    bank_ifsc_code: str
    bank_branch: str
    account_holder_name: str
    invoice_prefix: str
    auto_email_invoice: bool

    class Config:
        from_attributes = True

class TenantSettingsUpdate(BaseModel):
    legal_business_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    registered_address: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    logo_url: Optional[str] = None
    authorized_signatory_name: Optional[str] = None
    signature_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_branch: Optional[str] = None
    account_holder_name: Optional[str] = None
    invoice_prefix: Optional[str] = None
    auto_email_invoice: Optional[bool] = None

class CustomerCreate(BaseModel):
    legal_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    billing_address: str
    shipping_address: Optional[str] = None
    state: Optional[str] = "Karnataka"
    state_code: Optional[str] = "29"

class CustomerResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    legal_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    billing_address: str
    shipping_address: str
    state: str
    state_code: str

    class Config:
        from_attributes = True
