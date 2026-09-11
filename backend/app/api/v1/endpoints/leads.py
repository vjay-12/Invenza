import os
import urllib.parse
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.lead import LeadInquiry
from app.schemas.lead import LeadInquiryCreate, LeadInquiryResponse
from app.services.email_service import EmailService

router = APIRouter()

def normalize_whatsapp_phone(raw_phone: str) -> str:
    if not raw_phone:
        return ""
    clean = "".join(filter(str.isdigit, str(raw_phone)))
    # If 10-digit Indian mobile number, prefix with India country code 91
    if len(clean) == 10 and clean[0] in "6789":
        return f"91{clean}"
    return clean

def build_whatsapp_url(lead: LeadInquiry) -> str:
    admin_wa = os.getenv("SUPERADMIN_WHATSAPP_NUMBER", "919876543210")
    clean_phone = normalize_whatsapp_phone(admin_wa)
    modules_str = ", ".join([m.capitalize() for m in (lead.selected_modules or [])])
    
    text_content = (
        f"Hello Invenza Team! We are requesting an enterprise access quotation:\n\n"
        f"• Company: {lead.company_name} ({lead.industry})\n"
        f"• Contact: {lead.contact_name} | {lead.email} | {lead.phone}\n"
        f"• Location: {lead.location}\n"
        f"• Scale: {lead.estimated_warehouses} Hubs | {lead.estimated_skus} SKUs | {lead.estimated_monthly_orders} orders/mo\n"
        f"• Estimated Tier: {lead.tier_estimate}\n"
        f"• Modules: {modules_str}\n"
    )
    if lead.notes:
        text_content += f"• Requirements: {lead.notes}\n"

    encoded_text = urllib.parse.quote(text_content)
    return f"https://wa.me/{clean_phone}?text={encoded_text}"

@router.post("/inquiry", response_model=LeadInquiryResponse, status_code=status.HTTP_201_CREATED)
async def submit_lead_inquiry(
    inquiry_in: LeadInquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Public Lead Capture & Quotation Inquiry endpoint.
    Saves prospective customer inquiry, dispatches Super Admin email, and generates WhatsApp chat link.
    """
    new_lead = LeadInquiry(
        company_name=inquiry_in.company_name.strip(),
        company_code=inquiry_in.company_code.strip() if inquiry_in.company_code else None,
        industry=inquiry_in.industry.strip(),
        location=inquiry_in.location.strip(),
        contact_name=inquiry_in.contact_name.strip(),
        email=inquiry_in.email.strip().lower(),
        phone=inquiry_in.phone.strip(),
        whatsapp_number=inquiry_in.whatsapp_number.strip() if inquiry_in.whatsapp_number else inquiry_in.phone.strip(),
        estimated_warehouses=inquiry_in.estimated_warehouses,
        estimated_skus=inquiry_in.estimated_skus,
        estimated_monthly_orders=inquiry_in.estimated_monthly_orders,
        selected_modules=inquiry_in.selected_modules,
        tier_estimate=inquiry_in.tier_estimate,
        notes=inquiry_in.notes.strip() if inquiry_in.notes else None,
        status="pending",
    )

    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)

    # 1. Asynchronously dispatch Email to Super Admin
    lead_dict = {
        "id": str(new_lead.id),
        "company_name": new_lead.company_name,
        "company_code": new_lead.company_code,
        "industry": new_lead.industry,
        "location": new_lead.location,
        "contact_name": new_lead.contact_name,
        "email": new_lead.email,
        "phone": new_lead.phone,
        "whatsapp_number": new_lead.whatsapp_number,
        "estimated_warehouses": new_lead.estimated_warehouses,
        "estimated_skus": new_lead.estimated_skus,
        "estimated_monthly_orders": new_lead.estimated_monthly_orders,
        "selected_modules": new_lead.selected_modules,
        "tier_estimate": new_lead.tier_estimate,
        "notes": new_lead.notes,
    }
    
    try:
        await EmailService.send_lead_inquiry_notification(lead_dict)
    except Exception as e:
        print(f"[Lead Inquiry Notification Error]: {e}")

    # 2. Build WhatsApp Click-to-Chat URL
    wa_url = build_whatsapp_url(new_lead)

    response_data = LeadInquiryResponse.from_orm(new_lead) if hasattr(LeadInquiryResponse, "from_orm") else LeadInquiryResponse.model_validate(new_lead)
    response_data.whatsapp_url = wa_url
    return response_data
