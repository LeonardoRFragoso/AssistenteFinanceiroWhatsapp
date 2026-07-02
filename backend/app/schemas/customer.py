from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    operational_status: Optional[str] = None
    total_charges_count: Optional[int] = None
    total_paid_amount: Optional[float] = None
    total_pending_amount: Optional[float] = None
    total_overdue_amount: Optional[float] = None
    last_charge_at: Optional[datetime] = None
    last_payment_at: Optional[datetime] = None
    has_overdue: Optional[bool] = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CustomerSummaryResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    notes: Optional[str]
    operational_status: str
    total_charges_count: int
    total_paid_amount: float
    total_pending_amount: float
    total_overdue_amount: float
    last_charge_at: Optional[datetime]
    last_payment_at: Optional[datetime]
    has_overdue: bool
    avg_delay_days: Optional[float]
    paid_count: int
    overdue_count: int


class CustomerDetailResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    operational_status: str
    total_charges_count: int
    total_paid_amount: float
    total_pending_amount: float
    total_overdue_amount: float
    last_charge_at: Optional[datetime]
    last_payment_at: Optional[datetime]
    has_overdue: bool
    avg_delay_days: Optional[float]
    paid_count: int
    overdue_count: int
    charges: List[Any]


class CustomerNotesUpdate(BaseModel):
    notes: str = Field(..., max_length=2000)
