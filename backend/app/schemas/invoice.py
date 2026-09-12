from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any, Dict
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
    single_tax_rate: float = 0.0    # VAT / Sales Tax rate (0 for GST invoices)
    single_tax_amount: float = 0.0  # VAT / Sales Tax amount (0 for GST invoices)
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
    tax_type: str = "GST"        # GST / VAT / SALES_TAX
    currency_code: str = "INR"   # display currency locked at provisioning
    total_taxable_value: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_single_tax: float = 0.0
    round_off: float
    grand_total: float
    grand_total_words: str
    pdf_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True

class InvoicePaymentRequest(BaseModel):
    payment_method: Optional[str] = "Bank Transfer"
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None

class TenantSettingsResponse(BaseModel):
    tenant_id: UUID
    legal_business_name: str
    gstin: str
    pan: str
    registered_address: str
    state: str
    state_code: str
    pincode: Optional[str] = None
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
    tax_id: Optional[str] = None
    vat_id: Optional[str] = None
    tax_reg_number: Optional[str] = None
    national_tax_id: Optional[str] = None
    bank_routing_code: Optional[str] = None
    tax_type: Optional[str] = "GST"
    country_code: Optional[str] = "IN"
    currency_code: Optional[str] = "INR"

    class Config:
        from_attributes = True

class TenantSettingsUpdate(BaseModel):
    legal_business_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    registered_address: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None
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
    tax_id: Optional[str] = None
    vat_id: Optional[str] = None
    tax_reg_number: Optional[str] = None
    national_tax_id: Optional[str] = None
    bank_routing_code: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Resolve primary tax id (gstin / vat_id / tax_id / tax_reg_number)
            tid = data.get("tax_id") or data.get("vat_id") or data.get("tax_reg_number")
            if tid is not None and "gstin" not in data:
                data["gstin"] = str(tid).strip()
            # Resolve secondary tax id (pan / national_tax_id / ein / steuernummer)
            nid = data.get("national_tax_id") or data.get("ein") or data.get("steuernummer")
            if nid is not None and "pan" not in data:
                data["pan"] = str(nid).strip()
            # Resolve bank routing code (bank_routing_code / bank_ifsc_code)
            brc = data.get("bank_routing_code")
            if brc is not None and "bank_ifsc_code" not in data:
                data["bank_ifsc_code"] = str(brc).strip()
        return data

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
