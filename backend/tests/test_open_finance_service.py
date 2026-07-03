"""
Tests for Open Finance service — Sprint 16.

Tests consent creation, account sync, transaction sync, categories,
sync logs, and audit logging. All data is fake/demo.
"""
import pytest
from datetime import datetime, timezone, date
from decimal import Decimal

from app.services.open_finance_service import OpenFinanceService
from app.services.bank_transaction_service import BankTransactionService
from app.services.financial_summary_service import FinancialSummaryService
from app.models.open_finance import (
    ConnectedAccount, BankTransaction, FinancialCategory, OpenFinanceSyncLog,
    ConnectedAccountStatus, TransactionType, TransactionStatus,
    SyncType, SyncStatus,
)
from app.models.provider_foundation import OpenFinanceConsent, ConsentStatus
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_fake_consent(db_session, sample_organization, sample_user):
    """Test creating a fake Open Finance consent."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(
        sample_organization.id, sample_user.id, "fake_bank"
    )

    assert consent.id is not None
    assert consent.organization_id == sample_organization.id
    assert consent.status == ConsentStatus.AUTHORIZED
    assert consent.provider_name == "fake"
    assert consent.external_consent_id is not None


@pytest.mark.asyncio
async def test_list_consents(db_session, sample_organization, sample_user):
    """Test listing consents for an organization."""
    service = OpenFinanceService(db_session)
    await service.create_fake_consent(sample_organization.id, sample_user.id)
    consents = await service.list_consents(sample_organization.id)

    assert len(consents) == 1
    assert consents[0].organization_id == sample_organization.id


@pytest.mark.asyncio
async def test_revoke_consent(db_session, sample_organization, sample_user):
    """Test revoking a consent."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)

    revoked = await service.revoke_consent(sample_organization.id, consent.id, sample_user.id)
    assert revoked is not None
    assert revoked.status == ConsentStatus.REVOKED
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_nonexistent_consent(db_session, sample_organization, sample_user):
    """Test revoking a consent that doesn't exist."""
    service = OpenFinanceService(db_session)
    result = await service.revoke_consent(sample_organization.id, 99999, sample_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_sync_fake_accounts(db_session, sample_organization, sample_user):
    """Test syncing fake connected accounts."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)

    accounts = await service.sync_fake_accounts(
        sample_organization.id, sample_user.id, consent.id
    )

    assert len(accounts) == 2  # Fake provider generates 2 accounts
    for acc in accounts:
        assert acc.organization_id == sample_organization.id
        assert acc.is_demo_data is True
        assert acc.provider_name == "fake"
        assert acc.status == ConnectedAccountStatus.ACTIVE


@pytest.mark.asyncio
async def test_sync_fake_transactions(db_session, sample_organization, sample_user):
    """Test syncing fake bank transactions."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)

    transactions = await service.sync_fake_transactions(
        sample_organization.id, sample_user.id
    )

    assert len(transactions) > 0
    for tx in transactions:
        assert tx.organization_id == sample_organization.id
        assert tx.is_demo_data is True
        assert tx.provider_name == "fake"


@pytest.mark.asyncio
async def test_sync_transactions_without_accounts(db_session, sample_organization, sample_user):
    """Test syncing transactions without any connected accounts raises error."""
    service = OpenFinanceService(db_session)
    with pytest.raises(ValueError, match="No active connected accounts"):
        await service.sync_fake_transactions(sample_organization.id, sample_user.id)


@pytest.mark.asyncio
async def test_sync_logs_created(db_session, sample_organization, sample_user):
    """Test that sync logs are created after sync operations."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    logs = await service.get_sync_logs(sample_organization.id)
    assert len(logs) >= 2

    account_log = [l for l in logs if l.sync_type == SyncType.ACCOUNTS]
    assert len(account_log) == 1
    assert account_log[0].status == SyncStatus.SUCCESS

    tx_log = [l for l in logs if l.sync_type == SyncType.TRANSACTIONS]
    assert len(tx_log) == 1
    assert tx_log[0].status == SyncStatus.SUCCESS


@pytest.mark.asyncio
async def test_seed_default_categories(db_session, sample_organization):
    """Test seeding default financial categories."""
    service = OpenFinanceService(db_session)
    categories = await service.seed_default_categories(sample_organization.id)

    assert len(categories) > 0
    for cat in categories:
        assert cat.organization_id == sample_organization.id
        assert cat.is_system is True


@pytest.mark.asyncio
async def test_seed_categories_idempotent(db_session, sample_organization):
    """Test that seeding categories twice doesn't create duplicates."""
    service = OpenFinanceService(db_session)
    await service.seed_default_categories(sample_organization.id)
    second_run = await service.seed_default_categories(sample_organization.id)
    assert len(second_run) == 0


@pytest.mark.asyncio
async def test_bank_transaction_service_list(db_session, sample_organization, sample_user):
    """Test listing transactions with BankTransactionService."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    tx_service = BankTransactionService(db_session)
    transactions = await tx_service.list_transactions(sample_organization.id, limit=5)

    assert len(transactions) <= 5
    for tx in transactions:
        assert tx.organization_id == sample_organization.id


@pytest.mark.asyncio
async def test_bank_transaction_service_category_filter(db_session, sample_organization, sample_user):
    """Test filtering transactions by category."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    tx_service = BankTransactionService(db_session)
    all_txs = await tx_service.list_transactions(sample_organization.id, limit=100)
    if all_txs:
        category = all_txs[0].category
        if category:
            filtered = await tx_service.list_transactions(
                sample_organization.id, category=category, limit=100
            )
            for tx in filtered:
                assert tx.category == category


@pytest.mark.asyncio
async def test_financial_summary_service(db_session, sample_organization, sample_user):
    """Test FinancialSummaryService monthly summary."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    summary_service = FinancialSummaryService(db_session)
    now = date.today()
    summary = await summary_service.get_monthly_summary(
        sample_organization.id, now.year, now.month
    )

    assert "income_total" in summary
    assert "expense_total" in summary
    assert "net_flow" in summary
    assert "top_categories" in summary
    assert "insight" in summary
    assert summary["is_demo_data"] is True
    assert "Dados de demonstração" in summary["insight"] or "saídas" in summary["insight"]


@pytest.mark.asyncio
async def test_financial_summary_balance(db_session, sample_organization, sample_user):
    """Test FinancialSummaryService balance summary."""
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)

    summary_service = FinancialSummaryService(db_session)
    balance = await summary_service.get_balance_summary(sample_organization.id)

    assert balance["accounts_count"] == 2
    assert balance["is_demo_data"] is True
    assert float(balance["total_balance_available"]) > 0


@pytest.mark.asyncio
async def test_audit_log_created_on_consent(db_session, sample_organization, sample_user):
    """Test that audit logs are created when a consent is created."""
    from app.models.provider_foundation import OrganizationAuditLog

    service = OpenFinanceService(db_session)
    await service.create_fake_consent(sample_organization.id, sample_user.id)

    result = await db_session.execute(
        select(OrganizationAuditLog).where(
            OrganizationAuditLog.organization_id == sample_organization.id,
            OrganizationAuditLog.action == "of_consent_created",
        )
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].provider_type == "open_finance"
