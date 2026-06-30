from decimal import Decimal
from datetime import date
from app.schemas.charge import ChargeCreate
from app.schemas.pending_action import PendingActionCreate
from app.schemas.provider_event import ProviderEventCreate


def test_charge_create_valid():
    data = ChargeCreate(
        customer_name="João Silva",
        customer_phone="+5511999999999",
        amount=Decimal("150.00"),
        description="Serviço de site",
        due_date=date(2026, 12, 31)
    )
    assert data.customer_name == "João Silva"
    assert data.amount == Decimal("150.00")


def test_charge_create_invalid_amount():
    try:
        ChargeCreate(
            customer_name="João Silva",
            amount=Decimal("-10.00")
        )
    except Exception as e:
        assert "greater than 0" in str(e)


def test_pending_action_create():
    data = PendingActionCreate(
        action_type="create_charge",
        payload={"amount": 150.0, "customer_name": "João"}
    )
    assert data.action_type == "create_charge"
    assert data.payload["amount"] == 150.0


def test_provider_event_create():
    data = ProviderEventCreate(
        provider="fake",
        event_type="payment.approved",
        external_id="fake_abc123",
        payload={"amount": 150.0}
    )
    assert data.provider == "fake"
    assert data.external_id == "fake_abc123"
