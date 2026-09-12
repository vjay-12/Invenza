import uuid
import secrets
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete

from app.core.database import get_db
from app.api.deps import require_super_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.location import Location
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.security_request import SecurityApprovalRequest
from app.models.audit_log import AuditLog
from app.services.email_service import EmailService
from app.schemas.security_request import (
    SecurityApprovalRequestResponse,
    SecurityApprovalRequestCreate,
    SecurityApprovalDecision,
)
from app.schemas.audit_log import AuditLogResponse

router = APIRouter()

@router.get("/queue", response_model=List[SecurityApprovalRequestResponse])
async def list_security_requests(
    status_filter: Optional[str] = Query("all", alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: List dual-authorization requests in the Security Safeguards queue.
    """
    query = select(SecurityApprovalRequest).order_by(SecurityApprovalRequest.created_at.desc())
    if status_filter and status_filter != "all":
        query = query.where(SecurityApprovalRequest.status == status_filter.lower())

    res = await db.execute(query)
    return res.scalars().all()

@router.post("/queue", response_model=SecurityApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_security_request(
    req: SecurityApprovalRequestCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    """
    Create a new dual-authorization request requiring Super Admin approval.
    """
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == req.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Target organization not found")

    new_req = SecurityApprovalRequest(
        tenant_id=req.tenant_id,
        tenant_name=tenant.name,
        requester_id=actor.id,
        requester_name=actor.full_name or "Administrator",
        requester_email=actor.email,
        action_type=req.action_type,
        target_id=req.target_id,
        target_name=req.target_name,
        reason=req.reason,
        details=req.details,
        status="pending",
    )
    db.add(new_req)

    # Log request submission to AuditLog
    db.add(AuditLog(
        actor_id=actor.id,
        actor_name=actor.full_name or "Administrator",
        actor_email=actor.email,
        tenant_id=req.tenant_id,
        tenant_name=tenant.name,
        action_type=f"safeguard_request_submitted",
        target_type="security_queue",
        target_id=str(new_req.id),
        description=f"Initiated dual-authorization request for: {req.action_type.replace('_', ' ').title()}",
        after_values={"action_type": req.action_type, "reason": req.reason},
    ))

    await db.commit()
    await db.refresh(new_req)

    # Dispatch Compliance Safeguard alert to Super Admin
    try:
        await EmailService.send_security_safeguard_alert(
            action_type=req.action_type,
            tenant_name=tenant.name,
            requester_name=actor.full_name or "Administrator",
            requester_email=actor.email,
            affected_scope=f"Target: {req.target_name or str(req.target_id)}",
            reason=req.reason,
            request_id=str(new_req.id),
        )
    except Exception as e:
        print(f"[Safeguard Alert Dispatch Error]: {e}")

    return new_req

@router.post("/queue/{request_id}/approve", response_model=SecurityApprovalRequestResponse)
async def approve_security_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Execute approval for a dual-authorization request.
    Executes destructive or high-impact operations upon sign-off.
    """
    res = await db.execute(select(SecurityApprovalRequest).where(SecurityApprovalRequest.id == request_id))
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Security request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "approved"
    req.reviewed_by = admin.id
    req.reviewer_name = admin.full_name or admin.email
    req.reviewed_at = datetime.utcnow()

    # Execute action if specific handler applies
    if req.action_type == "ledger_purge":
        # Execute ledger purge for tenant
        await db.execute(delete(StockMovement).where(StockMovement.tenant_id == req.tenant_id))

        # Add root audit record documenting authorized purge
        loc_res = await db.execute(
            select(Location).where(and_(Location.tenant_id == req.tenant_id, Location.is_active == True)).limit(1)
        )
        loc = loc_res.scalar_one_or_none()
        prod_res = await db.execute(select(Product).where(Product.tenant_id == req.tenant_id).limit(1))
        prod = prod_res.scalar_one_or_none()

        if loc and prod:
            root_audit_entry = StockMovement(
                id=secrets.token_hex(16),
                tenant_id=req.tenant_id,
                product_id=prod.id,
                location_id=loc.id,
                movement_type=MovementTypeEnum.ADJUST,
                quantity=0.0,
                unit_cost=0.0,
                reference_type="AUDIT_PURGE",
                reference_id=req.target_id or str(req.id),
                reason_code="ledger purged with super admin approval",
                performed_by=(
                    f"Requested by: {req.requester_name} ({req.requester_email}) [MFA Verified] | "
                    f"Approved & Executed by: {admin.full_name or admin.email}"
                ),
                timestamp=datetime.utcnow(),
            )
            db.add(root_audit_entry)

    elif req.action_type == "deactivate_tenant":
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == req.tenant_id))
        tenant = tenant_res.scalar_one_or_none()
        if tenant:
            tenant.is_active = False
            tenant.is_archived = True

    # Audit Log
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=req.tenant_id,
        tenant_name=req.tenant_name,
        action_type=f"safeguard_approved_{req.action_type}",
        target_type="security_queue",
        target_id=str(req.id),
        description=f"Approved and executed: {req.action_type.replace('_', ' ').title()} for {req.tenant_name}",
        after_values={"status": "approved", "reviewed_by": admin.email},
    ))

    await db.commit()
    await db.refresh(req)

    # Dispatch notification to requester
    try:
        if req.requester_email:
            await EmailService.send_email_async(
                recipient=req.requester_email,
                subject=f"APPROVED: Dual-Authorization Request - {req.action_type.replace('_', ' ').title()}",
                body_text=f"Your request for {req.action_type.replace('_', ' ').title()} has been approved and executed by Super Administrator ({admin.full_name or admin.email}).",
                body_html=f"<p>Hello {req.requester_name},</p><p>Your dual-authorization request for <strong>{req.action_type.replace('_', ' ').title()}</strong> on organization <strong>{req.tenant_name}</strong> has been approved and executed by the Super Administrator.</p>",
                metadata={"action": req.action_type, "status": "approved", "request_id": str(req.id)},
            )
    except Exception as e:
        print(f"[Safeguard Approval Email Notice Error]: {e}")

    return req

@router.post("/queue/{request_id}/reject", response_model=SecurityApprovalRequestResponse)
async def reject_security_request(
    request_id: UUID,
    decision: SecurityApprovalDecision,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Reject a dual-authorization request with reason.
    """
    res = await db.execute(select(SecurityApprovalRequest).where(SecurityApprovalRequest.id == request_id))
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Security request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "rejected"
    req.reviewed_by = admin.id
    req.reviewer_name = admin.full_name or admin.email
    req.rejection_reason = decision.rejection_reason or "Rejected by Super Administrator"
    req.reviewed_at = datetime.utcnow()

    # Audit Log
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=req.tenant_id,
        tenant_name=req.tenant_name,
        action_type=f"safeguard_rejected_{req.action_type}",
        target_type="security_queue",
        target_id=str(req.id),
        description=f"Rejected: {req.action_type.replace('_', ' ').title()} for {req.tenant_name}. Reason: {req.rejection_reason}",
        after_values={"status": "rejected", "rejection_reason": req.rejection_reason},
    ))

    await db.commit()
    await db.refresh(req)

    # Dispatch notification to requester
    try:
        if req.requester_email:
            await EmailService.send_email_async(
                recipient=req.requester_email,
                subject=f"REJECTED: Dual-Authorization Request - {req.action_type.replace('_', ' ').title()}",
                body_text=f"Your request for {req.action_type.replace('_', ' ').title()} has been rejected by Super Administrator. Reason: {req.rejection_reason}",
                body_html=f"<p>Hello {req.requester_name},</p><p>Your dual-authorization request for <strong>{req.action_type.replace('_', ' ').title()}</strong> on organization <strong>{req.tenant_name}</strong> was rejected by the Super Administrator.</p><p><strong>Reason:</strong> {req.rejection_reason}</p>",
                metadata={"action": req.action_type, "status": "rejected", "request_id": str(req.id)},
            )
    except Exception as e:
        print(f"[Safeguard Rejection Email Notice Error]: {e}")

    return req

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    tenant_id: Optional[UUID] = None,
    action_type: Optional[str] = None,
    actor_email: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Retrieve audit trail across privileged platform events.
    Filterable by tenant, action type, actor, and text query. Retained for 12+ months.
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
    if action_type and action_type != "all":
        query = query.where(AuditLog.action_type == action_type)
    if actor_email:
        query = query.where(AuditLog.actor_email.ilike(f"%{actor_email.strip()}%"))
    if search:
        s = f"%{search.strip()}%"
        query = query.where(or_(
            AuditLog.description.ilike(s),
            AuditLog.tenant_name.ilike(s),
            AuditLog.actor_name.ilike(s),
            AuditLog.action_type.ilike(s),
        ))

    res = await db.execute(query)
    return res.scalars().all()
