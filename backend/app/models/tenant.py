import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    company_code = Column(String(50), unique=True, index=True, nullable=True)
    unique_code = Column(String(50), unique=True, index=True, nullable=True)
    industry = Column(String(100), nullable=True, default="General Merchandise")
    location = Column(String(255), nullable=True, default="Headquarters")
    currency_code = Column(String(10), default="INR", nullable=False)
    tier = Column(String(100), default="Growth Suite", nullable=False)
    tags = Column(JSONB, default=list, nullable=False)
    enabled_modules = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
