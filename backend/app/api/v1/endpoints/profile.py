import uuid
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash
from app.api.deps import get_current_user, require_admin
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.email_change import EmailChangeRequest
from app.api.v1.endpoints.auth import validate_password_strength

router = APIRouter()

# --- Request / Response Schemas ---

class UpdateUserNameRequest(BaseModel):
    full_name: str

class UpdateCompanyDetailsRequest(BaseModel):
    name: str
    industry: Optional[str] = None
    location: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class RequestEmailChangePayload(BaseModel):
    requested_email: EmailStr
    reason: Optional[str] = None

# --- Endpoints ---

@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch comprehensive profile data for the active user session,
    including personal details, company/tenant details, permissions,
    and any pending email modification requests.
    """
    # 1. Fetch Company details
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    # 2. Check for active pending email change request
    pending_res = await db.execute(
        select(EmailChangeRequest)
        .where(
            and_(
                EmailChangeRequest.user_id == current_user.id,
                EmailChangeRequest.status == "pending",
            )
        )
        .order_by(EmailChangeRequest.created_at.desc())
    )
    pending_req = pending_res.scalar_one_or_none()

    is_admin = current_user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "admin", "super_admin"]

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "company": {
            "id": str(tenant.id) if tenant else None,
            "name": tenant.name if tenant else "Invenza Workspace",
            "company_code": tenant.company_code or tenant.unique_code if tenant else None,
            "industry": tenant.industry or "General Merchandise" if tenant else "General",
            "location": tenant.location or "Headquarters" if tenant else "Headquarters",
            "currency_code": tenant.currency_code if tenant else "INR",
        },
        "is_admin": is_admin,
        "pending_email_request": {
            "id": str(pending_req.id),
            "current_email": pending_req.current_email,
            "requested_email": pending_req.requested_email,
            "status": pending_req.status,
            "reason": pending_req.reason,
            "created_at": pending_req.created_at.isoformat(),
        } if pending_req else None,
    }

@router.put("/user")
async def update_my_user_name(
    payload: UpdateUserNameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Allow any user to directly edit and update their own full name.
    """
    name_clean = payload.full_name.strip()
    if not name_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name cannot be blank.",
        )

    current_user.full_name = name_clean
    await db.commit()
    await db.refresh(current_user)

    return {
        "success": True,
        "full_name": current_user.full_name,
        "message": "User profile name updated successfully.",
    }

@router.put("/company")
async def update_company_details(
    payload: UpdateCompanyDetailsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update company organizational details.
    RESTRICTED: Only Organization Administrators or Super Administrators are authorized.
    """
    is_admin = current_user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "admin", "super_admin"]
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission Denied: Editing company details is restricted to Organization Administrators only.",
        )

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Company organization record not found.")

    name_clean = payload.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be blank.")

    tenant.name = name_clean
    if payload.industry is not None:
        tenant.industry = payload.industry.strip()
    if payload.location is not None:
        tenant.location = payload.location.strip()

    await db.commit()
    await db.refresh(tenant)

    return {
        "success": True,
        "company": {
            "id": str(tenant.id),
            "name": tenant.name,
            "industry": tenant.industry,
            "location": tenant.location,
            "company_code": tenant.company_code or tenant.unique_code,
        },
        "message": "Company details updated successfully.",
    }

@router.post("/reset-password")
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change and reset the authenticated user's password directly from the Profile page.
    Requires current password verification and strict password complexity rules.
    """
    # 1. Verify current password against stored bcrypt hash
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current account password does not match our records. Please try again.",
        )

    # 2. Check that new password is not identical to current
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )

    # 3. Validate new password strength
    validate_password_strength(payload.new_password)

    # 4. Hash new password securely with bcrypt and save
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()

    return {
        "success": True,
        "message": "Your account password has been successfully updated.",
    }

@router.post("/request-email-change")
async def request_email_change(
    payload: RequestEmailChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits an email change request.
    The change is NOT applied immediately — it is held in 'pending' status
    until reviewed and approved by an Administrator.
    """
    requested_clean = payload.requested_email.strip().lower()

    if requested_clean == current_user.email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested email address is already your current registered email.",
        )

    # Ensure no other user globally is already using this email
    existing = await db.execute(select(User).where(User.email == requested_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The email address '{requested_clean}' is already registered to another account.",
        )

    # Remove or supersede any previous pending requests by this user
    await db.execute(
        delete(EmailChangeRequest).where(
            and_(
                EmailChangeRequest.user_id == current_user.id,
                EmailChangeRequest.status == "pending",
            )
        )
    )

    new_request = EmailChangeRequest(
        id=uuid.uuid4(),
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        current_email=current_user.email,
        requested_email=requested_clean,
        status="pending",
        reason=payload.reason.strip() if payload.reason else None,
        created_at=datetime.utcnow(),
    )
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)

    return {
        "success": True,
        "status": "pending",
        "requested_email": requested_clean,
        "created_at": new_request.created_at.isoformat(),
        "message": f"Your request to change your email to '{requested_clean}' has been submitted and is held pending administrator approval.",
    }

@router.get("/email-change-requests")
async def list_pending_email_change_requests(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrator: View all pending email change requests within this company organization.
    """
    res = await db.execute(
        select(EmailChangeRequest, User.full_name)
        .outerjoin(User, EmailChangeRequest.user_id == User.id)
        .where(
            and_(
                EmailChangeRequest.tenant_id == current_admin.tenant_id,
                EmailChangeRequest.status == "pending",
            )
        )
        .order_by(EmailChangeRequest.created_at.desc())
    )
    rows = res.all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "user_name": full_name or r.current_email,
            "current_email": r.current_email,
            "requested_email": r.requested_email,
            "status": r.status,
            "reason": r.reason,
            "created_at": r.created_at.isoformat(),
        }
        for r, full_name in rows
    ]

@router.post("/email-change-requests/{request_id}/approve")
async def approve_email_change_request(
    request_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrator: Approve a pending email change request.
    Applies the new email to the user's account immediately.
    """
    res = await db.execute(
        select(EmailChangeRequest)
        .where(
            and_(
                EmailChangeRequest.id == request_id,
                EmailChangeRequest.tenant_id == current_admin.tenant_id,
            )
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Email change request not found.")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}.")

    # Fetch user
    user_res = await db.execute(select(User).where(User.id == req.user_id))
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User account associated with this request not found.")

    # Check that requested email is still available
    existing = await db.execute(select(User).where(and_(User.email == req.requested_email, User.id != target_user.id)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="The requested email address is already in use by another user.")

    # Apply change
    target_user.email = req.requested_email
    req.status = "approved"
    req.reviewed_by = current_admin.email
    req.reviewed_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "status": "approved",
        "user_email": target_user.email,
        "message": f"Email change approved. User's account email is now '{target_user.email}'.",
    }

@router.post("/email-change-requests/{request_id}/reject")
async def reject_email_change_request(
    request_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrator: Reject a pending email change request.
    """
    res = await db.execute(
        select(EmailChangeRequest)
        .where(
            and_(
                EmailChangeRequest.id == request_id,
                EmailChangeRequest.tenant_id == current_admin.tenant_id,
            )
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Email change request not found.")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}.")

    req.status = "rejected"
    req.reviewed_by = current_admin.email
    req.reviewed_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "status": "rejected",
        "message": "Email change request has been rejected.",
    }
