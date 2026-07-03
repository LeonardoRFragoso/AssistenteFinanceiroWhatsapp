"""
Bill management schemas — Sprint 17.

Pydantic schemas for all bill management endpoints.
All responses include is_demo_data flag for transparency.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class BillStatusResponse(BaseModel):
    dda_enabled: bool
    bill_payment_enabled: bool
    provider: str
    real_dda_access: bool
    real_bill_payment_allowed: bool
    demo_mode: bool
    message: str


class DetectedBillResponse(BaseModel):
    id: int
    organization_id: int
    provider_name: str
    provider_bill_id: Optional[str] = None
    source: str
    title: str
    beneficiary_name: str
    beneficiary_document_masked: Optional[str] = None
    payer_name: Optional[str] = None
    amount: Decimal
    currency: str
    due_date: date
    issue_date: Optional[date] = None
    barcode: Optional[str] = None
    digitable_line: Optional[str] = None
    bill_type: str
    category: Optional[str] = None
    status: str
    risk_level: str
    is_demo_data: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    ignored_at: Optional[datetime] = None
    manually_marked_paid_at: Optional[datetime] = None

    @field_validator("amount", mode="before")
    @classmethod
    def convert_amount(cls, v):
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    class Config:
        from_attributes = True


class BillFilters(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class BillSummaryResponse(BaseModel):
    overdue_total: str
    due_today_total: str
    upcoming_7_days_total: str
    upcoming_30_days_total: str
    open_total: str
    overdue_count: int
    due_today_count: int
    upcoming_7_days_count: int
    upcoming_30_days_count: int
    open_count: int
    top_categories: List[dict]
    top_beneficiaries: List[dict]
    largest_bill: Optional[dict] = None
    is_demo_data: bool


class BillReminderCreate(BaseModel):
    reminder_date: date
    channel: str = "whatsapp"


class BillReminderResponse(BaseModel):
    id: int
    organization_id: int
    detected_bill_id: int
    reminder_date: date
    channel: str
    status: str
    message_preview: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BillPaymentIntentResponse(BaseModel):
    id: int
    organization_id: int
    detected_bill_id: int
    user_id: Optional[int] = None
    transaction_authorization_id: Optional[int] = None
    provider_name: str
    amount: Decimal
    currency: str
    status: str
    intent_type: str
    fake_payment_reference: Optional[str] = None
    expires_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("amount", mode="before")
    @classmethod
    def convert_amount(cls, v):
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    class Config:
        from_attributes = True


class BillPaymentIntentAuthorize(BaseModel):
    authorization_code: Optional[str] = None


class BillMarkPaidManualRequest(BaseModel):
    pass


class BillIgnoreRequest(BaseModel):
    pass


class BillEventLogResponse(BaseModel):
    id: int
    organization_id: int
    detected_bill_id: int
    actor_user_id: Optional[int] = None
    action: str
    metadata_sanitized: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncFakeBillsResponse(BaseModel):
    created: int
    skipped: int
    total: int
    is_demo_data: bool = True
