import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CollectionMessageStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class CollectionMessageLog(Base):
    __tablename__ = "collection_message_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    template_id = Column(Integer, ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(50), nullable=False, default="whatsapp")
    message_preview = Column(Text, nullable=True)
    status = Column(
        Enum(CollectionMessageStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CollectionMessageStatus.DRAFT,
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
