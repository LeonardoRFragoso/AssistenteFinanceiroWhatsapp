import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class RecurrenceType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RecurringTask(Base):
    __tablename__ = "recurring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    recurrence_type = Column(
        Enum(RecurrenceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RecurrenceType.DAILY,
    )
    day_of_week = Column(Integer, nullable=True)  # 0=Sunday, 1=Monday, ..., 6=Saturday
    day_of_month = Column(Integer, nullable=True)  # 1-31
    next_run_at = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="recurring_tasks")


class RecurringTaskLog(Base):
    __tablename__ = "recurring_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("recurring_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    message_sent = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
