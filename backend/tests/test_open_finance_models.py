"""
Tests for Open Finance models — Sprint 16.

Verifies model creation, table structure, enums, and org-scoped constraints.
"""
import pytest
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import select, inspect

from app.models.open_finance import (
    ConnectedAccount, BankTransaction, FinancialCategory, OpenFinanceSyncLog,
    ConnectedAccountStatus, TransactionType, TransactionStatus,
    SyncType, SyncStatus, CategoryType,
)


@pytest.mark.asyncio
async def test_connected_account_creation(db_session, sample_organization, sample_user):
    """Test creating a ConnectedAccount record."""
    account = ConnectedAccount(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        external_account_id="fake_acc_001",
        institution_name="Nubank (Fake)",
        institution_code="nubank",
        account_type="checking",
        account_subtype="personal",
        account_number_masked="****1234",
        currency="BRL",
        balance_available=Decimal("5000.00"),
        balance_current=Decimal("5200.00"),
        balance_updated_at=datetime.now(timezone.utc),
        status=ConnectedAccountStatus.ACTIVE,
        is_demo_data=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    assert account.id is not None
    assert account.organization_id == sample_organization.id
    assert account.is_demo_data is True
    assert account.status == ConnectedAccountStatus.ACTIVE
    assert account.provider_name == "fake"


@pytest.mark.asyncio
async def test_bank_transaction_creation(db_session, sample_organization, sample_user):
    """Test creating a BankTransaction record."""
    account = ConnectedAccount(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        external_account_id="fake_acc_tx_001",
        institution_name="Fake Bank",
        account_type="checking",
        account_number_masked="****5678",
        currency="BRL",
        balance_available=Decimal("1000.00"),
        balance_current=Decimal("1000.00"),
        status=ConnectedAccountStatus.ACTIVE,
        is_demo_data=True,
    )
    db_session.add(account)
    await db_session.flush()

    tx = BankTransaction(
        organization_id=sample_organization.id,
        connected_account_id=account.id,
        provider_name="fake",
        external_transaction_id="fake_tx_001",
        transaction_type=TransactionType.DEBIT,
        amount=Decimal("-50.00"),
        currency="BRL",
        description="Supermercado Fake",
        merchant_name="Extra",
        category="Alimentação",
        subcategory="expense",
        transaction_date=date.today(),
        posted_at=datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        is_demo_data=True,
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)

    assert tx.id is not None
    assert tx.organization_id == sample_organization.id
    assert tx.transaction_type == TransactionType.DEBIT
    assert tx.is_demo_data is True


@pytest.mark.asyncio
async def test_financial_category_creation(db_session, sample_organization):
    """Test creating a FinancialCategory record."""
    cat = FinancialCategory(
        organization_id=sample_organization.id,
        name="Alimentação",
        type=CategoryType.EXPENSE,
        color="#FF6B6B",
        icon="🍔",
        is_system=True,
    )
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)

    assert cat.id is not None
    assert cat.organization_id == sample_organization.id
    assert cat.type == CategoryType.EXPENSE
    assert cat.is_system is True


@pytest.mark.asyncio
async def test_sync_log_creation(db_session, sample_organization):
    """Test creating an OpenFinanceSyncLog record."""
    log = OpenFinanceSyncLog(
        organization_id=sample_organization.id,
        sync_type=SyncType.TRANSACTIONS,
        status=SyncStatus.SUCCESS,
        records_found=30,
        records_created=25,
        records_updated=5,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.organization_id == sample_organization.id
    assert log.sync_type == SyncType.TRANSACTIONS
    assert log.status == SyncStatus.SUCCESS
    assert log.records_found == 30


@pytest.mark.asyncio
async def test_bank_transaction_unique_constraint(db_session, sample_organization, sample_user):
    """Test that duplicate transactions (org + provider + external_id) are rejected."""
    account = ConnectedAccount(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        external_account_id="fake_acc_unique_001",
        institution_name="Fake Bank",
        account_type="checking",
        account_number_masked="****9999",
        currency="BRL",
        balance_available=Decimal("1000.00"),
        balance_current=Decimal("1000.00"),
        status=ConnectedAccountStatus.ACTIVE,
        is_demo_data=True,
    )
    db_session.add(account)
    await db_session.flush()

    tx1 = BankTransaction(
        organization_id=sample_organization.id,
        connected_account_id=account.id,
        provider_name="fake",
        external_transaction_id="fake_tx_dup_001",
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("100.00"),
        currency="BRL",
        description="Test 1",
        transaction_date=date.today(),
        posted_at=datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        is_demo_data=True,
    )
    db_session.add(tx1)
    await db_session.commit()

    tx2 = BankTransaction(
        organization_id=sample_organization.id,
        connected_account_id=account.id,
        provider_name="fake",
        external_transaction_id="fake_tx_dup_001",
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("200.00"),
        currency="BRL",
        description="Test 2",
        transaction_date=date.today(),
        posted_at=datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        is_demo_data=True,
    )
    db_session.add(tx2)
    with pytest.raises(Exception):
        await db_session.commit()


@pytest.mark.asyncio
async def test_transactions_org_scoped(db_session, sample_organization, second_organization, sample_user, second_user):
    """Test that transactions from different orgs don't mix."""
    acc1 = ConnectedAccount(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        external_account_id="fake_acc_org1",
        institution_name="Bank A",
        account_type="checking",
        account_number_masked="****1111",
        currency="BRL",
        balance_available=Decimal("1000.00"),
        balance_current=Decimal("1000.00"),
        status=ConnectedAccountStatus.ACTIVE,
        is_demo_data=True,
    )
    acc2 = ConnectedAccount(
        organization_id=second_organization.id,
        user_id=second_user.id,
        provider_name="fake",
        external_account_id="fake_acc_org2",
        institution_name="Bank B",
        account_type="checking",
        account_number_masked="****2222",
        currency="BRL",
        balance_available=Decimal("2000.00"),
        balance_current=Decimal("2000.00"),
        status=ConnectedAccountStatus.ACTIVE,
        is_demo_data=True,
    )
    db_session.add_all([acc1, acc2])
    await db_session.flush()

    tx1 = BankTransaction(
        organization_id=sample_organization.id,
        connected_account_id=acc1.id,
        provider_name="fake",
        external_transaction_id="fake_tx_org1",
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("500.00"),
        currency="BRL",
        description="Org 1 transaction",
        transaction_date=date.today(),
        posted_at=datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        is_demo_data=True,
    )
    tx2 = BankTransaction(
        organization_id=second_organization.id,
        connected_account_id=acc2.id,
        provider_name="fake",
        external_transaction_id="fake_tx_org2",
        transaction_type=TransactionType.DEBIT,
        amount=Decimal("-300.00"),
        currency="BRL",
        description="Org 2 transaction",
        transaction_date=date.today(),
        posted_at=datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        is_demo_data=True,
    )
    db_session.add_all([tx1, tx2])
    await db_session.commit()

    result = await db_session.execute(
        select(BankTransaction).where(
            BankTransaction.organization_id == sample_organization.id
        )
    )
    org1_txs = list(result.scalars().all())
    assert len(org1_txs) == 1
    assert org1_txs[0].description == "Org 1 transaction"

    result2 = await db_session.execute(
        select(BankTransaction).where(
            BankTransaction.organization_id == second_organization.id
        )
    )
    org2_txs = list(result2.scalars().all())
    assert len(org2_txs) == 1
    assert org2_txs[0].description == "Org 2 transaction"
