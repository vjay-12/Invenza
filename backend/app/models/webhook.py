import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.core.database import Base

class OutboundWebhook(Base):
    __tablename__ = "outbound_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    target_url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(ARRAY(String), nullable=False)  # ['stock.low', 'stock.movement', 'po.received']
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
