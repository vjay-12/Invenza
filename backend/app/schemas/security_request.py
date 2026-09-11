from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class SecurityApprovalRequestCreate(BaseModel):
    tenant_id: UUID
    action_type: str  # 'ledger_purge', 'remove_last_admin', 'waive_maintenance_fee', 'deactivate_tenant'
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    reason: str
    details: Optional[Dict[str, Any]] = None

class SecurityApprovalDecision(BaseModel):
    decision: str  # 'approve' or 'reject'
    rejection_reason: Optional[str] = None

class SecurityApprovalRequestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: str
    requester_id: Optional[UUID] = None
    requester_name: str
    requester_email: str
    action_type: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    reason: str
    details: Optional[Dict[str, Any]] = None
    status: str
    reviewed_by: Optional[UUID] = None
    reviewer_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
