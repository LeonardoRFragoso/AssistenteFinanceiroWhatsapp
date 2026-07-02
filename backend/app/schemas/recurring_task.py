from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from app.models.recurring_task import RecurrenceType


class RecurringTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    recurrence_type: RecurrenceType
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)

    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v, values):
        if values.data.get('recurrence_type') == RecurrenceType.WEEKLY and v is None:
            raise ValueError('day_of_week is required for weekly recurrence')
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v, values):
        if values.data.get('recurrence_type') == RecurrenceType.MONTHLY and v is None:
            raise ValueError('day_of_month is required for monthly recurrence')
        return v


class RecurringTaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    recurrence_type: RecurrenceType
    day_of_week: Optional[int]
    day_of_month: Optional[int]
    next_run_at: datetime
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecurringTaskListResponse(BaseModel):
    items: List[RecurringTaskResponse]
    total: int
