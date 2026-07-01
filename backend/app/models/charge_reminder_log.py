import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ReminderType(str, enum.Enum):
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


class ChargeReminderLog(Base):
    __tablename__ = "charge_reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_type = Column(Enum(ReminderType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    charge = relationship("Charge")
    user = relationship("User")
