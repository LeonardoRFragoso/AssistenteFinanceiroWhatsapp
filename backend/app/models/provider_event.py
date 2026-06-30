from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class ProviderEvent(Base):
    __tablename__ = "provider_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
