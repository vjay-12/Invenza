import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_name = Column(String(255), nullable=False, default="System Administrator")
    actor_email = Column(String(255), nullable=False, default="superadmin@invenza.internal")
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_name = Column(String(255), nullable=True)
    action_type = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    before_values = Column(JSONB, nullable=True)
    after_values = Column(JSONB, nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
