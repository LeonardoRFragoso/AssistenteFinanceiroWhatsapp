import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TriggerType(str, enum.Enum):
    BEFORE_DUE = "before_due"
    ON_DUE = "on_due"
    AFTER_DUE = "after_due"


class CollectionRule(Base):
    __tablename__ = "collection_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    days_offset = Column(Integer, nullable=False, default=0)
    trigger_type = Column(
        Enum(TriggerType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TriggerType.ON_DUE,
    )
    template_id = Column(Integer, ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="collection_rules")
    template = relationship("MessageTemplate", backref="collection_rules")
