import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ChargeStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Charge(Base):
    __tablename__ = "charges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False, default="fake")
    provider_charge_id = Column(String(255), nullable=True, index=True)
    payment_link = Column(Text, nullable=True)
    qr_code = Column(Text, nullable=True)
    qr_code_base64 = Column(Text, nullable=True)
    status = Column(Enum(ChargeStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ChargeStatus.PENDING, index=True)
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="charges")
