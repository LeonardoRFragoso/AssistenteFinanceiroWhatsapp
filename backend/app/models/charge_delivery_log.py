from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
import enum


class DeliveryStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    SIMULATED = "simulated"


class DeliveryChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


class ChargeDeliveryLog(Base):
    __tablename__ = "charge_delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_phone = Column(String(20), nullable=True)
    channel = Column(SQLEnum(DeliveryChannel), nullable=False, default=DeliveryChannel.WHATSAPP)
    status = Column(SQLEnum(DeliveryStatus), nullable=False, default=DeliveryStatus.SENT)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    charge = relationship("Charge", backref="delivery_logs")
