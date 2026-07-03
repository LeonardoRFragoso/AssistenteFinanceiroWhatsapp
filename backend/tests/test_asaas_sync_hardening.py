"""
Tests for sync provider status hardening — Sprint 15.1.
Covers: RBAC, org isolation, provider errors, paid stays paid, unknown provider.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.models.charge import Charge, ChargeStatus


@pytest.mark.asyncio
async def test_sync_already_paid_stays_paid(db_session, sample_user, sample_organization):
    """Sync should not change a paid charge."""
    from app.services.charge_service import ChargeService

    original_paid_at = datetime.now(timezone.utc)
    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_paid001",
        status=ChargeStatus.PAID,
        paid_at=original_paid_at,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
    assert result.status == ChargeStatus.PAID
    assert result.paid_at.replace(tzinfo=None) == original_paid_at.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_sync_no_provider_charge_id_returns_charge(db_session, sample_user, sample_organization):
    """Sync without provider_charge_id should return charge unchanged."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="fake",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
    assert result.status == ChargeStatus.PENDING


@pytest.mark.asyncio
async def test_sync_wrong_org_returns_none(db_session, sample_user, sample_organization, second_organization):
    """Sync should not find charge from another organization."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_org001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=second_organization.id)
    assert result is None


@pytest.mark.asyncio
async def test_sync_provider_error_does_not_change_status(db_session, sample_user, sample_organization):
    """If provider raises error, charge status should not change."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_err001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    with patch("app.providers.provider_factory.get_payment_provider") as mock_factory:
        mock_provider = MagicMock()
        mock_provider.get_charge = AsyncMock(side_effect=RuntimeError("Asaas API error 500"))
        mock_factory.return_value = mock_provider

        service = ChargeService(db_session)
        result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
        assert result.status == ChargeStatus.PENDING


@pytest.mark.asyncio
async def test_sync_updates_to_paid(db_session, sample_user, sample_organization):
    """Sync should update pending to paid when provider returns paid."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_sync001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    with patch("app.providers.provider_factory.get_payment_provider") as mock_factory:
        mock_provider = MagicMock()
        mock_provider.get_charge = AsyncMock(return_value={
            "provider_charge_id": "pay_sync001",
            "status": "paid",
            "provider_status": "RECEIVED",
            "amount": 100.0,
        })
        mock_factory.return_value = mock_provider

        service = ChargeService(db_session)
        result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
        assert result.status == ChargeStatus.PAID
        assert result.paid_at is not None
        assert result.provider_status == "RECEIVED"


@pytest.mark.asyncio
async def test_sync_expired_does_not_revert_to_pending(db_session, sample_user, sample_organization):
    """Sync should not revert expired back to pending."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_exp001",
        status=ChargeStatus.EXPIRED,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    with patch("app.providers.provider_factory.get_payment_provider") as mock_factory:
        mock_provider = MagicMock()
        mock_provider.get_charge = AsyncMock(return_value={
            "provider_charge_id": "pay_exp001",
            "status": "pending",
            "provider_status": "PENDING",
            "amount": 100.0,
        })
        mock_factory.return_value = mock_provider

        service = ChargeService(db_session)
        result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
        assert result.status == ChargeStatus.EXPIRED


@pytest.mark.asyncio
async def test_sync_fake_provider_returns_safely(db_session, sample_user, sample_organization):
    """Sync with fake provider should work without errors."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="fake",
        provider_charge_id="fake_test123",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
    assert result is not None
    assert result.status == ChargeStatus.PENDING


@pytest.mark.asyncio
async def test_sync_does_not_increment_usage(db_session, sample_user, sample_organization):
    """Sync should not increment billing usage counters."""
    from app.services.charge_service import ChargeService
    from app.services.saas_billing_service import SaaSBillingService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="fake",
        provider_charge_id="fake_usage_test",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    billing = SaaSBillingService(db_session)
    before = await billing.get_usage(sample_organization.id)
    before_count = before.charges_created if before else 0

    service = ChargeService(db_session)
    await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)

    after = await billing.get_usage(sample_organization.id)
    after_count = after.charges_created if after else 0
    assert after_count == before_count
