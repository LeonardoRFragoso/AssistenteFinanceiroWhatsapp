from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class ProviderEventCreate(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    event_type: str = Field(..., min_length=1, max_length=100)
    external_id: Optional[str] = Field(None, max_length=255)
    payload: Dict[str, Any] = Field(default_factory=dict)


class ProviderEventResponse(BaseModel):
    id: int
    provider: str
    event_type: str
    external_id: Optional[str]
    payload: Dict[str, Any]
    processed: bool
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True
