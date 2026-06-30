import pytest
from decimal import Decimal
from app.services.pending_action_service import PendingActionService
from app.models.pending_action import PendingActionStatus


@pytest.mark.asyncio
async def test_create_charge_action(db_session, sample_user):
    service = PendingActionService(db_session)
    action = await service.create_charge_action(
        user_id=sample_user.id,
        amount=150.0,
        customer_name="João Cliente",
        description="Serviço do site",
        customer_phone="11999999999"
    )

    assert action.id is not None
    assert action.user_id == sample_user.id
    assert action.action_type == "create_charge"
    assert action.status == PendingActionStatus.PENDING
    assert action.payload["amount"] == 150.0
    assert action.payload["customer_name"] == "João Cliente"


@pytest.mark.asyncio
async def test_confirm_and_execute_charge_action(db_session, sample_user):
    service = PendingActionService(db_session)
    action = await service.create_charge_action(
        user_id=sample_user.id,
        amount=199.90,
        customer_name="Ana Cliente",
        description="Design"
    )

    charge = await service.confirm_and_execute(action.id, sample_user.id)

    assert charge is not None
    assert charge.user_id == sample_user.id
    assert charge.customer_name == "Ana Cliente"
    assert charge.amount == Decimal("199.90")
    assert charge.status.value == "pending"

    await db_session.refresh(action)
    assert action.status == PendingActionStatus.EXECUTED


@pytest.mark.asyncio
async def test_cancel_latest_pending(db_session, sample_user):
    service = PendingActionService(db_session)
    await service.create_charge_action(
        user_id=sample_user.id,
        amount=100.0,
        customer_name="Carlos"
    )

    cancelled = await service.cancel_latest_pending(sample_user.id)
    assert cancelled is not None
    assert cancelled.status == PendingActionStatus.CANCELLED


@pytest.mark.asyncio
async def test_format_charge_summary(db_session, sample_user):
    service = PendingActionService(db_session)
    action = await service.create_charge_action(
        user_id=sample_user.id,
        amount=250.0,
        customer_name="Pedro",
        description="Projeto"
    )

    summary = service.format_charge_summary(action)
    assert "R$ 250.00" in summary
    assert "Pedro" in summary
    assert "Projeto" in summary
    assert "confirmar" in summary.lower()
