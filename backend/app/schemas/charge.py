from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from app.models.charge import ChargeStatus


class ChargeCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=20)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    description: Optional[str] = Field(None, max_length=1000)
    provider: Optional[str] = Field(None, max_length=50)
    due_date: Optional[date] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)


class ChargeResponse(BaseModel):
    id: int
    user_id: int
    customer_name: str
    customer_phone: Optional[str]
    amount: Decimal
    description: Optional[str]
    provider: str
    provider_charge_id: Optional[str]
    payment_link: Optional[str]
    qr_code: Optional[str]
    qr_code_base64: Optional[str]
    status: ChargeStatus
    due_date: Optional[date]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChargeListResponse(BaseModel):
    items: List[ChargeResponse]
    total: int
