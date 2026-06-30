from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.pending_action import PendingActionStatus


class PendingActionCreate(BaseModel):
    action_type: str = Field(..., min_length=1, max_length=50)
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class PendingActionResponse(BaseModel):
    id: int
    user_id: int
    action_type: str
    payload: Dict[str, Any]
    status: PendingActionStatus
    expires_at: datetime
    confirmed_at: Optional[datetime]
    executed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
