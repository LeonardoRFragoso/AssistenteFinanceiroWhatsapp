import pytest
from decimal import Decimal
from app.providers.fake_provider import FakePaymentProvider


@pytest.mark.asyncio
async def test_fake_provider_create_charge():
    provider = FakePaymentProvider()
    result = await provider.create_charge(
        amount=Decimal("150.00"),
        description="Serviço de site",
        customer_name="João Silva",
        customer_phone="+5511999999999",
        external_reference="payflow_user_1"
    )

    assert result["provider_charge_id"].startswith("fake_")
    assert result["payment_link"].startswith("http")
    assert result["qr_code"].startswith("fake-pix-code")
    assert result["status"] == "pending"
    assert result["raw_response"]["amount"] == 150.0


def test_fake_provider_parse_payment_event():
    provider = FakePaymentProvider()
    payload = provider.build_payment_simulation_payload(
        provider_charge_id="fake_abc123",
        amount=Decimal("99.90")
    )
    event = provider.parse_webhook_event(payload)

    assert event is not None
    assert event["event_type"] == "payment.approved"
    assert event["provider_charge_id"] == "fake_abc123"
    assert event["status"] == "paid"
    assert event["amount"] == Decimal("99.90")


def test_fake_provider_parse_invalid_event():
    provider = FakePaymentProvider()
    event = provider.parse_webhook_event({"event_type": "unknown"})
    assert event is None
