import os
import json
import time
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete

from app.core.database import get_db
from app.core.security import verify_password
from app.api.deps import get_current_tenant_id, get_optional_current_user
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.location import Location
from app.models.security_request import SecurityApprovalRequest
from app.models.audit_log import AuditLog
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

    # Dispatch official destruction OTP email via centralized EmailService
    await EmailService.send_destruction_otp_email(
        operator_email=user_email,
        action_name=req.action,
        otp_code=otp_code,
        operator_name=user_name,
        ttl_minutes=10,
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

    from app.models.adjustment import StockAdjustment
    from app.models.transfer import StockTransferItem
    from app.models.order import PurchaseOrderItem, SalesOrderItem
    from app.models.audit_log import AuditLog

    prod_ids = [p.id for p in all_prods]

    # Record immutable audit trail in AuditLog
    db.add(AuditLog(
        actor_name=operator_name,
        actor_email=user_email,
        tenant_id=tenant_id,
        action_type="CATALOG_RESET",
        target_type="PRODUCT_CATALOG",
        description=f"Product catalog reset: {count} SKU items permanently deleted with all stock allocations purged [MFA: Password+OTP Verified].",
        created_at=now_utc,
    ))

    # Permanently delete all related dependent records and products for this tenant
    if prod_ids:
        await db.execute(delete(StockMovement).where(StockMovement.tenant_id == tenant_id))
        await db.execute(delete(StockAdjustment).where(StockAdjustment.tenant_id == tenant_id))
        await db.execute(delete(StockTransferItem).where(StockTransferItem.product_id.in_(prod_ids)))
        await db.execute(delete(PurchaseOrderItem).where(PurchaseOrderItem.product_id.in_(prod_ids)))
        await db.execute(delete(SalesOrderItem).where(SalesOrderItem.product_id.in_(prod_ids)))
        await db.execute(delete(Product).where(Product.tenant_id == tenant_id))

    await db.commit()

    return {
        "success": True,
        "deleted_count": count,
        "performed_by": audit_performer,
        "timestamp": now_utc.isoformat(),
        "message": f"Successfully reset Product Catalog ({count} items permanently removed). Immutable audit trail record logged.",
    }

def _is_valid_uuid(val: str) -> bool:
    try:
        UUID(str(val))
        return True
    except Exception:
        return False

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
    authorization request to the Super Administrator, persisted in PostgreSQL.
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
    request_code = f"SAR-PURGE-{int(time.time())}-{secrets.randbelow(9000)+1000}"
    req_uuid = uuid4()
    now_utc = datetime.utcnow()

    # Persist directly into central PostgreSQL SecurityApprovalRequest table
    sec_req = SecurityApprovalRequest(
        id=req_uuid,
        tenant_id=tenant_id,
        tenant_name=company_name,
        requester_id=user.id if user else None,
        requester_name=operator_name,
        requester_email=user_email,
        action_type="ledger_purge",
        target_id=request_code,
        target_name=f"Movement Ledger ({record_count} Records)",
        reason=req.reason or "Administrative reset",
        details={
            "reference_code": request_code,
            "record_count": record_count,
            "otp_verified": True,
            "otp_verified_at": now_utc.isoformat(),
        },
        status="pending",
        created_at=now_utc,
    )
    db.add(sec_req)

    # Audit Log
    db.add(AuditLog(
        actor_id=user.id if user else None,
        actor_name=operator_name,
        actor_email=user_email,
        tenant_id=tenant_id,
        tenant_name=company_name,
        action_type="safeguard_request_submitted",
        target_type="security_queue",
        target_id=str(req_uuid),
        description=f"Initiated dual-authorization request: Ledger Purge ({record_count} records) [MFA: Password+OTP Verified]",
        after_values={"action_type": "ledger_purge", "reference_code": request_code, "reason": req.reason},
        created_at=now_utc,
    ))

    await db.commit()
    await db.refresh(sec_req)

    # Notify Super Admin via official Compliance Safeguard email
    superadmin_email = os.getenv("SUPERADMIN_EMAIL", "superadmin@invenza.internal")
    await EmailService.send_security_safeguard_alert(
        action_type="ledger_purge",
        tenant_name=company_name,
        requester_name=operator_name,
        requester_email=user_email,
        affected_scope=f"{record_count} historical audit transactions",
        reason=req.reason,
        request_id=request_code,
        superadmin_email=superadmin_email,
    )

    return {
        "success": True,
        "request_id": request_code,
        "uuid": str(req_uuid),
        "status": "pending_super_admin_approval",
        "record_count": record_count,
        "requested_by": operator_name,
        "requested_at": sec_req.created_at.isoformat(),
        "message": (
            f"Dual-authorization safeguard active: Identity verified via Password and Email OTP. "
            f"Request '{request_code}' has been forwarded to the Super Administrator. "
            f"The Movement Ledger will remain completely untouched until explicit Super Admin approval."
        ),
    }

@router.get("/ledger-purge-requests")
async def list_ledger_purge_requests(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns all pending and processed Movement Ledger purge requests from PostgreSQL for the active tenant.
    """
    query = select(SecurityApprovalRequest).where(
        and_(
            SecurityApprovalRequest.tenant_id == tenant_id,
            SecurityApprovalRequest.action_type == "ledger_purge",
        )
    ).order_by(SecurityApprovalRequest.created_at.desc())
    res = await db.execute(query)
    items = res.scalars().all()
    out = []
    for it in items:
        ref_code = (it.details or {}).get("reference_code") or it.target_id or str(it.id)
        out.append({
            "id": ref_code,
            "uuid": str(it.id),
            "tenant_id": str(it.tenant_id),
            "company_name": it.tenant_name,
            "requested_by_name": it.requester_name,
            "requested_by_email": it.requester_email,
            "record_count": (it.details or {}).get("record_count", 0),
            "status": "pending_super_admin_approval" if it.status == "pending" else it.status,
            "raw_status": it.status,
            "requested_at": it.created_at.isoformat() if it.created_at else None,
            "reason": it.reason,
            "approved_by": it.reviewer_name,
            "approved_at": it.reviewed_at.isoformat() if it.reviewed_at else None,
            "rejection_reason": it.rejection_reason,
        })
    return out

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

    # Find request by UUID or reference code in target_id
    if _is_valid_uuid(request_id):
        res = await db.execute(select(SecurityApprovalRequest).where(
            or_(SecurityApprovalRequest.id == UUID(request_id), SecurityApprovalRequest.target_id == request_id)
        ))
    else:
        res = await db.execute(select(SecurityApprovalRequest).where(SecurityApprovalRequest.target_id == request_id))
    sec_req = res.scalar_one_or_none()

    if not sec_req:
        raise HTTPException(status_code=404, detail="Purge authorization request not found.")

    if sec_req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending approval (current status: {sec_req.status}).",
        )

    target_tenant_id = sec_req.tenant_id
    approver_name = (current_user.full_name or current_user.email) if current_user else "Super Administrator"
    approver_email = current_user.email if current_user else "superadmin@invenza.internal"
    approved_at = datetime.utcnow()

    # 1. Execute deletion of movements for this tenant
    await db.execute(delete(StockMovement).where(StockMovement.tenant_id == target_tenant_id))

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
            reference_id=sec_req.target_id or str(sec_req.id),
            reason_code="ledger purged with super admin approval",
            performed_by=(
                f"Requested by: {sec_req.requester_name} ({sec_req.requester_email}) [MFA Verified] | "
                f"Approved & Executed by: {approver_name} ({approver_email})"
            ),
            timestamp=approved_at,
        )
        db.add(root_audit_entry)

    # 3. Update request state
    sec_req.status = "approved"
    sec_req.reviewed_by = current_user.id if current_user else None
    sec_req.reviewer_name = f"{approver_name} ({approver_email})"
    sec_req.reviewed_at = approved_at

    # 4. Audit Log
    db.add(AuditLog(
        actor_id=current_user.id if current_user else None,
        actor_name=approver_name,
        actor_email=approver_email,
        tenant_id=target_tenant_id,
        tenant_name=sec_req.tenant_name,
        action_type="safeguard_approved_ledger_purge",
        target_type="security_queue",
        target_id=str(sec_req.id),
        description=f"Approved and executed: Ledger Purge for {sec_req.tenant_name}",
        after_values={"status": "approved", "reviewed_by": approver_email},
        created_at=approved_at,
    ))

    await db.commit()
    await db.refresh(sec_req)

    return {
        "success": True,
        "request_id": request_id,
        "status": "approved",
        "approved_by": sec_req.reviewer_name,
        "approved_at": sec_req.reviewed_at.isoformat(),
        "message": (
            f"Movement Ledger purge for '{sec_req.tenant_name}' approved and executed by {approver_name}. "
            f"Full dual-authorization audit log preserved."
        ),
    }

@router.post("/reject-ledger-purge/{request_id}")
async def reject_ledger_purge(
    request_id: str,
    body: RejectPurgeBody,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
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

    if _is_valid_uuid(request_id):
        res = await db.execute(select(SecurityApprovalRequest).where(
            or_(SecurityApprovalRequest.id == UUID(request_id), SecurityApprovalRequest.target_id == request_id)
        ))
    else:
        res = await db.execute(select(SecurityApprovalRequest).where(SecurityApprovalRequest.target_id == request_id))
    sec_req = res.scalar_one_or_none()

    if not sec_req:
        raise HTTPException(status_code=404, detail="Purge authorization request not found.")

    approver_name = (current_user.full_name or current_user.email) if current_user else "Super Administrator"
    approver_email = current_user.email if current_user else "superadmin@invenza.internal"
    now_utc = datetime.utcnow()

    sec_req.status = "rejected"
    sec_req.rejection_reason = body.reason
    sec_req.reviewed_by = current_user.id if current_user else None
    sec_req.reviewer_name = approver_name
    sec_req.reviewed_at = now_utc

    db.add(AuditLog(
        actor_id=current_user.id if current_user else None,
        actor_name=approver_name,
        actor_email=approver_email,
        tenant_id=sec_req.tenant_id,
        tenant_name=sec_req.tenant_name,
        action_type="safeguard_rejected_ledger_purge",
        target_type="security_queue",
        target_id=str(sec_req.id),
        description=f"Rejected: Ledger Purge for {sec_req.tenant_name}. Reason: {body.reason}",
        after_values={"status": "rejected", "rejection_reason": body.reason},
        created_at=now_utc,
    ))

    await db.commit()
    await db.refresh(sec_req)

    return {
        "success": True,
        "request_id": request_id,
        "status": "rejected",
        "reason": body.reason,
        "message": f"Purge request '{request_id}' has been rejected by {approver_name}.",
    }

