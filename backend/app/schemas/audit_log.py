from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: Optional[UUID] = None
    actor_name: str
    actor_email: str
    tenant_id: Optional[UUID] = None
    tenant_name: Optional[str] = None
    action_type: str
    target_type: str
    target_id: Optional[str] = None
    description: str
    before_values: Optional[Dict[str, Any]] = None
    after_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    tenant_id: Optional[UUID] = None
    action_type: Optional[str] = None
    actor_email: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
