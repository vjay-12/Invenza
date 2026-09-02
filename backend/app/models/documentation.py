import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

class HelpDocument(Base):
    """
    RAG knowledge base for Invenza documentation.
    Indexed with vector embeddings for semantic search.
    """
    __tablename__ = "help_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # 'valuation', 'ledger', 'workflows', 'general'
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # Vector embedding JSON array
    token_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
