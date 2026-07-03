"""
Open Finance schemas — Sprint 16.

Pydantic schemas for Open Finance read provider endpoints.
All responses include is_demo_data flag for transparency.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class OpenFinanceStatusResponse(BaseModel):
    enabled: bool
    provider: str
    real_provider_configured: bool
    demo_mode: bool
    real_data_access: bool
    message: str


class OpenFinanceConsentCreateFake(BaseModel):
    institution_id: str = Field(default="fake_bank", description="Fake institution identifier")


class ConnectedAccountResponse(BaseModel):
    id: int
    organization_id: int
    provider_name: str
    external_account_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    account_type: Optional[str] = None
    account_subtype: Optional[str] = None
    account_number_masked: Optional[str] = None
    currency: str
    balance_available: Optional[Decimal] = None
    balance_current: Optional[Decimal] = None
    balance_updated_at: Optional[datetime] = None
    status: str
    is_demo_data: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BankTransactionResponse(BaseModel):
    id: int
    organization_id: int
    connected_account_id: int
    provider_name: str
    external_transaction_id: Optional[str] = None
    transaction_type: str
    amount: Decimal
    currency: str
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    transaction_date: Optional[date] = None
    posted_at: Optional[datetime] = None
    status: str
    is_demo_data: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinancialCategoryResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    type: str
    color: Optional[str] = None
    icon: Optional[str] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpenFinanceSyncLogResponse(BaseModel):
    id: int
    organization_id: int
    sync_type: str
    status: str
    records_found: int
    records_created: int
    records_updated: int
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category: Optional[str] = None
    connected_account_id: Optional[int] = None
    search: Optional[str] = None
    limit: int = Field(default=50, le=200)
    offset: int = Field(default=0, ge=0)


class CategoryBreakdownResponse(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage: float


class MerchantBreakdownResponse(BaseModel):
    merchant: str
    total_amount: Decimal
    transaction_count: int


class FinancialSummaryResponse(BaseModel):
    total_balance_available: Decimal
    total_balance_current: Decimal
    income_total: Decimal
    expense_total: Decimal
    net_flow: Decimal
    top_categories: List[CategoryBreakdownResponse]
    top_merchants: List[MerchantBreakdownResponse]
    largest_expense: Optional[BankTransactionResponse] = None
    transaction_count: int
    is_demo_data: bool
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    insight: str


class ConsentResponse(BaseModel):
    id: int
    organization_id: int
    provider_name: str
    external_consent_id: Optional[str] = None
    status: str
    scopes: Optional[list] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    authorization_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
