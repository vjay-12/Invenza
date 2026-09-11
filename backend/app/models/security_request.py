import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class SecurityApprovalRequest(Base):
    __tablename__ = "security_approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_name = Column(String(255), nullable=False)
    requester_id = Column(UUID(as_uuid=True), nullable=True)
    requester_name = Column(String(255), nullable=False, default="Administrator")
    requester_email = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False, index=True)  # 'ledger_purge', 'remove_last_admin', 'waive_maintenance_fee', 'deactivate_tenant'
    target_id = Column(String(255), nullable=True)
    target_name = Column(String(255), nullable=True)
    reason = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    reviewer_name = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=True)
