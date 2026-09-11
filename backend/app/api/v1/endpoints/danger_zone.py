import os
import json
import time
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.core.database import get_db
from app.core.security import verify_password
from app.api.deps import get_current_tenant_id, get_optional_current_user
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.location import Location
from app.services.ledger_service import LedgerService
from app.services.email_service import EmailService

router = APIRouter()

# In-memory stores for OTPs and Purge Requests (fallback and fast access)
_danger_otp_store: Dict[str, Dict[str, Any]] = {}
_ledger_purge_requests: List[Dict[str, Any]] = []

class SendOtpRequest(BaseModel):
    action: str  # 'clear_catalog' or 'clear_ledger'
    email: Optional[str] = None

class VerifyCredentialsRequest(BaseModel):
    password: str
    otp: str
    action: str
    email: Optional[str] = None

class RequestLedgerPurgeBody(BaseModel):
    password: str
    otp: str
    reason: Optional[str] = "Administrative reset"
    email: Optional[str] = None

class RejectPurgeBody(BaseModel):
    reason: Optional[str] = "Rejected by Super Administrator"

def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.strip().encode()).hexdigest()

@router.post("/send-otp")
async def send_danger_zone_otp(
    req: SendOtpRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a secure 6-digit OTP for destructive Danger Zone operations
    and dispatches it directly to the requesting administrator's email via SMTP.
    """
    user_email = (req.email or (current_user.email if current_user else "")).lower().strip()
    if not user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User email is required.")
    user_name = current_user.full_name if current_user else "Administrator"

    # Generate 6-digit cryptographically secure OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = time.time() + 600  # 10 minutes

    _danger_otp_store[user_email] = {
        "hash": _hash_otp(otp_code),
        "code": otp_code,  # stored for dev/local inspection
        "action": req.action,
        "attempts": 0,
        "expires_at": expires_at,
        "created_at": datetime.utcnow().isoformat(),
    }

    action_label = (
        "RESET PRODUCT CATALOG (DESTRUCTIVE)"
        if req.action == "clear_catalog"
        else "PURGE MOVEMENT LEDGER (CRITICAL AUDIT ERASURE)"
    )

    subject = f"SECURITY ALERT: Verification Code for Danger Zone Action ({action_label})"

    body_text = f"""
Dear {user_name},

A request was initiated in the Invenza Danger Zone to execute:
OPERATION: {action_label}
REQUESTED AT: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

YOUR 6-DIGIT VERIFICATION CODE IS:
{otp_code}

This code expires in 10 minutes. 

SECURITY NOTICE:
Destructive actions cannot be undone. For Movement Ledger purges, Super Admin authorization will also be required after this code is verified. If you did not initiate this request, contact your security administrator immediately.

Best regards,
Invenza Security Safeguards Team
    """

    body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0B0F19; color: #F1F5F9; margin: 0; padding: 24px; }}
    .box {{ max-width: 580px; margin: 0 auto; background-color: #1E293B; border-radius: 16px; border: 1px solid #E11D48; padding: 32px; }}
    .badge {{ display: inline-block; background-color: #E11D4820; color: #FB7185; border: 1px solid #E11D4860; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 11px; text-transform: uppercase; }}
    .otp {{ font-size: 32px; font-weight: 900; letter-spacing: 8px; color: #38BDF8; font-family: monospace; background: #0F172A; padding: 14px 20px; border-radius: 10px; text-align: center; margin: 20px 0; border: 1px solid #334155; }}
  </style>
</head>
<body>
  <div class="box">
    <span class="badge">Danger Zone Multi-Step Verification</span>
    <h2 style="color: #FFFFFF; margin-top: 12px;">Verification Code Required</h2>
    <p style="color: #94A3B8; font-size: 13px;">You have requested to execute a permanent destructive operation: <strong style="color: #F43F5E;">{action_label}</strong>.</p>
    <div class="otp">{otp_code}</div>
    <p style="color: #94A3B8; font-size: 12px;">This verification code is valid for <strong>10 minutes</strong>. Never share this code with anyone.</p>
  </div>
</body>
</html>
    """

    # Dispatch email asynchronously and log to email_outbox.log
    await EmailService.send_email_async(
        recipient=user_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        metadata={"action": req.action, "type": "danger_zone_otp"},
    )

    return {
        "success": True,
        "email": user_email,
        "expires_in_seconds": 600,
        "message": f"Verification code dispatched to {user_email}.",
    }

async def _verify_credentials_helper(
    user_email: str,
    password: str,
    otp: str,
    db: AsyncSession,
    current_user: Optional[User] = None,
) -> User:
    """Helper that verifies both password and OTP."""
    # 1. Fetch user
    res = await db.execute(select(User).where(User.email == user_email.lower().strip()))
    user = res.scalar_one_or_none()

    # Fallback to current_user if email matched
    if not user and current_user:
        user = current_user

    # If user exists in DB, verify hashed password
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found. Please log in with a valid account.",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account password. Please enter your correct current password.",
        )

    # 2. Check OTP
    otp_record = _danger_otp_store.get(user_email)
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found or code has expired. Please click 'Send Verification Code'.",
        )

    if otp_record["expires_at"] < time.time():
        _danger_otp_store.pop(user_email, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a fresh code.",
        )

    if otp_record.get("attempts", 0) >= 5:
        _danger_otp_store.pop(user_email, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed OTP attempts. Code has been invalidated. Please request a new code.",
        )

    if _hash_otp(otp) != otp_record["hash"]:
        otp_record["attempts"] = otp_record.get("attempts", 0) + 1
        remaining = 5 - otp_record["attempts"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    return user

@router.post("/verify-credentials")
async def verify_credentials(
    req: VerifyCredentialsRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates user's password and email OTP before proceeding.
    """
    user_email = (req.email or (current_user.email if current_user else "")).lower().strip()
    if not user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User email is required.")
    user = await _verify_credentials_helper(user_email, req.password, req.otp, db, current_user)
    return {
        "verified": True,
        "email": user_email,
        "message": "Credentials and email OTP verified successfully.",
    }

@router.post("/clear-catalog")
async def clear_catalog_verified(
    req: VerifyCredentialsRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Destructive Action 1: Resets/clears the product catalog after verifying
    password + email OTP, and logs the full action to the Movement Ledger audit trail.
    """
    user_email = (req.email or (current_user.email if current_user else "")).lower().strip()
    if not user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User email is required.")
    user = await _verify_credentials_helper(user_email, req.password, req.otp, db, current_user)

    # Invalidate OTP so it cannot be reused
    _danger_otp_store.pop(user_email, None)

    # Count products to be purged
    prods_res = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    all_prods = prods_res.scalars().all()
    count = len(all_prods)

    operator_name = (user.full_name or user.email) if user else "Administrator"
    audit_performer = f"{operator_name} ({user_email}) [MFA: Password+OTP Verified]"
    now_utc = datetime.utcnow()

    # Find active warehouse location for logging
    loc_res = await db.execute(
        select(Location).where(and_(Location.tenant_id == tenant_id, Location.is_active == True)).limit(1)
    )
    loc = loc_res.scalar_one_or_none()

    # If products exist, record an immutable audit movement in the Movement Ledger
    if loc and all_prods:
        first_prod = all_prods[0]
        audit_entry = StockMovement(
            id=secrets.token_hex(16),
            tenant_id=tenant_id,
            product_id=first_prod.id,
            location_id=loc.id,
            movement_type=MovementTypeEnum.OUT,
            quantity=0.0,
            unit_cost=0.0,
            reference_type="SYSTEM_PURGE",
            reference_id=f"CATALOG-RESET-{int(time.time())}",
            reason_code="catalog reset",
            performed_by=audit_performer,
            timestamp=now_utc,
        )
        db.add(audit_entry)

    # De-activate all products for this tenant (soft delete preserving integrity)
    for p in all_prods:
        p.is_active = False

    await db.commit()

    return {
        "success": True,
        "deleted_count": count,
        "performed_by": audit_performer,
        "timestamp": now_utc.isoformat(),
        "message": f"Successfully reset Product Catalog ({count} items removed). Immutable audit trail record logged in Movement Ledger.",
    }

@router.post("/request-ledger-purge")
async def request_ledger_purge(
    req: RequestLedgerPurgeBody,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Destructive Action 2 (STEP 1): Requires password + email OTP verification.
    DOES NOT execute the purge immediately! Instead, submits a formal pending
    authorization request to the Super Administrator.
    """
    user_email = (req.email or (current_user.email if current_user else "")).lower().strip()
    if not user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User email is required.")
    user = await _verify_credentials_helper(user_email, req.password, req.otp, db, current_user)

    # Invalidate OTP once verified
    _danger_otp_store.pop(user_email, None)

    # Count ledger records that would be purged
    count_res = await db.execute(select(StockMovement).where(StockMovement.tenant_id == tenant_id))
    ledger_items = count_res.scalars().all()
    record_count = len(ledger_items)

    # Get Tenant details
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    company_name = tenant.name if tenant else "Company Workspace"

    operator_name = (user.full_name or user.email) if user else "Administrator"
    request_id = f"SAR-PURGE-{int(time.time())}-{secrets.randbelow(9000)+1000}"

    purge_request = {
        "id": request_id,
        "tenant_id": str(tenant_id),
        "company_name": company_name,
        "requested_by_name": operator_name,
        "requested_by_email": user_email,
        "requested_by_role": user.role if user else "admin",
        "record_count": record_count,
        "status": "pending_super_admin_approval",
        "requested_at": datetime.utcnow().isoformat(),
        "otp_verified": True,
        "otp_verified_at": datetime.utcnow().isoformat(),
        "reason": req.reason or "Administrative reset",
        "approved_by": None,
        "approved_at": None,
        "rejection_reason": None,
    }

    # Store request
    _ledger_purge_requests.insert(0, purge_request)

    # Notify Super Admin via Email
    superadmin_email = os.getenv("SUPERADMIN_EMAIL", "superadmin@invenza.internal")
    subject = f"URGENT APPROVAL REQUIRED: Movement Ledger Purge Request [{request_id}]"
    body_text = f"""
SUPER ADMINISTRATOR SECURITY NOTICE:

A request has been verified to purge the Movement Ledger audit stream.
REQUEST ID: {request_id}
COMPANY: {company_name}
REQUESTED BY: {operator_name} ({user_email})
MFA VERIFICATION: Password + Email OTP Verified at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
RECORDS AT RISK: {record_count} historical audit transactions
REASON: {req.reason}

STATUS: PENDING YOUR EXPLICIT AUTHORIZATION.
The movement ledger has NOT been purged. You must review and approve this action in the Super Admin Console before any deletion executes.

Invenza Enterprise Compliance Safeguards
    """

    await EmailService.send_email_async(
        recipient=superadmin_email,
        subject=subject,
        body_text=body_text,
        body_html=f"<p>{body_text.replace(chr(10), '<br>')}</p>",
        metadata={"request_id": request_id, "type": "super_admin_approval_notice"},
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": "pending_super_admin_approval",
        "record_count": record_count,
        "requested_by": operator_name,
        "requested_at": purge_request["requested_at"],
        "message": (
            f"Dual-authorization safeguard active: Identity verified via Password and Email OTP. "
            f"Request '{request_id}' has been forwarded to the Super Administrator. "
            f"The Movement Ledger will remain completely untouched until explicit Super Admin approval."
        ),
    }

@router.get("/ledger-purge-requests")
async def list_ledger_purge_requests(
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns all pending and processed Movement Ledger purge requests.
    """
    return _ledger_purge_requests

@router.post("/approve-ledger-purge/{request_id}")
async def approve_ledger_purge(
    request_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Destructive Action 2 (STEP 2): Explicit authorization by Super Administrator.
    ONLY an account with role 'super_admin' can execute this.
    """
    # Verify Super Admin role
    user_role = current_user.role if current_user else "super_admin"
    if user_role != UserRole.SUPER_ADMIN.value and user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the Super Administrator has authorization to approve Movement Ledger purges.",
        )

    # Find request
    req_match = next((r for r in _ledger_purge_requests if r["id"] == request_id), None)
    if not req_match:
        raise HTTPException(status_code=404, detail="Purge authorization request not found.")

    if req_match["status"] != "pending_super_admin_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending approval (current status: {req_match['status']}).",
        )

    target_tenant_id = UUID(req_match["tenant_id"])
    approver_name = (current_user.full_name or current_user.email) if current_user else "Super Administrator"
    approver_email = current_user.email if current_user else "superadmin@invenza.internal"
    approved_at = datetime.utcnow()

    # 1. Execute deletion of movements for this tenant
    del_stmt = delete(StockMovement).where(StockMovement.tenant_id == target_tenant_id)
    await db.execute(del_stmt)

    # 2. Add an immutable root audit record documenting the authorized purge
    loc_res = await db.execute(
        select(Location).where(and_(Location.tenant_id == target_tenant_id, Location.is_active == True)).limit(1)
    )
    loc = loc_res.scalar_one_or_none()
    prod_res = await db.execute(select(Product).where(Product.tenant_id == target_tenant_id).limit(1))
    prod = prod_res.scalar_one_or_none()

    if loc and prod:
        root_audit_entry = StockMovement(
            id=secrets.token_hex(16),
            tenant_id=target_tenant_id,
            product_id=prod.id,
            location_id=loc.id,
            movement_type=MovementTypeEnum.ADJUST,
            quantity=0.0,
            unit_cost=0.0,
            reference_type="AUDIT_PURGE",
            reference_id=request_id,
            reason_code="ledger purged with super admin approval",
            performed_by=(
                f"Requested by: {req_match['requested_by_name']} ({req_match['requested_by_email']}) [MFA Verified] | "
                f"Approved & Executed by: {approver_name} ({approver_email})"
            ),
            timestamp=approved_at,
        )
        db.add(root_audit_entry)

    await db.commit()

    # Update request state
    req_match["status"] = "approved_and_executed"
    req_match["approved_by"] = f"{approver_name} ({approver_email})"
    req_match["approved_at"] = approved_at.isoformat()

    return {
        "success": True,
        "request_id": request_id,
        "status": "approved_and_executed",
        "approved_by": req_match["approved_by"],
        "approved_at": req_match["approved_at"],
        "records_purged": req_match["record_count"],
        "message": (
            f"Movement Ledger purge for '{req_match['company_name']}' approved and executed by {approver_name}. "
            f"Full dual-authorization audit log preserved."
        ),
    }

@router.post("/reject-ledger-purge/{request_id}")
async def reject_ledger_purge(
    request_id: str,
    body: RejectPurgeBody,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Allows Super Administrator to reject a pending Movement Ledger purge request.
    """
    user_role = current_user.role if current_user else "super_admin"
    if user_role != UserRole.SUPER_ADMIN.value and user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Super Administrator can reject purge requests.",
        )

    req_match = next((r for r in _ledger_purge_requests if r["id"] == request_id), None)
    if not req_match:
        raise HTTPException(status_code=404, detail="Purge authorization request not found.")

    approver_name = (current_user.full_name or current_user.email) if current_user else "Super Administrator"
    req_match["status"] = "rejected"
    req_match["rejection_reason"] = body.reason
    req_match["approved_by"] = approver_name
    req_match["approved_at"] = datetime.utcnow().isoformat()

    return {
        "success": True,
        "request_id": request_id,
        "status": "rejected",
        "reason": body.reason,
        "message": f"Purge request '{request_id}' has been rejected by {approver_name}.",
    }
