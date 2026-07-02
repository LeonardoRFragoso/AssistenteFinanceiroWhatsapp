from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.collection_rule import TriggerType


class CollectionRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    days_offset: int = Field(0, ge=0, le=365)
    trigger_type: TriggerType
    template_id: Optional[int] = None


class CollectionRuleResponse(BaseModel):
    id: int
    user_id: int
    name: str
    days_offset: int
    trigger_type: TriggerType
    template_id: Optional[int]
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionRuleListResponse(BaseModel):
    items: List[CollectionRuleResponse]
    total: int


class CollectionMessageLogResponse(BaseModel):
    id: int
    user_id: int
    charge_id: int
    customer_id: Optional[int]
    template_id: Optional[int]
    channel: str
    message_preview: Optional[str]
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionMessageLogListResponse(BaseModel):
    items: List[CollectionMessageLogResponse]
    total: int


class FollowupPreviewItem(BaseModel):
    charge_id: int
    customer_name: str
    amount: float
    due_date: Optional[str]
    days_overdue: int
    rendered_message: str
    template_name: Optional[str]


class FollowupPreviewResponse(BaseModel):
    items: List[FollowupPreviewItem]
    total: int
    message: str
