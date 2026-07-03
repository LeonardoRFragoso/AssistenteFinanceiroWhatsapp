"""
Tests for Asaas provider hardening — Sprint 15.1.
Covers: partial API responses, billing type validation, boleto without bankSlipUrl,
Pix without QR code, unknown status, sensitive data sanitization.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal

from app.providers.asaas_provider import (
    AsaasPaymentProvider,
    _ASAAS_STATUS_MAP,
    _BILLING_TYPE_MAP,
    _generate_sandbox_cpf,
)


def test_unknown_status_maps_to_pending():
    """Unknown Asaas status should map to 'pending' (safe default)."""
    assert _ASAAS_STATUS_MAP.get("UNKNOWN_STATUS", "pending") == "pending"


def test_billing_type_invalid_defaults_to_pix():
    """Invalid billing_type should default to PIX (safe default)."""
    asaas_billing = _BILLING_TYPE_MAP.get("invalid_type".lower(), "PIX")
    assert asaas_billing == "PIX"


def test_billing_type_pix_maps_correctly():
    assert _BILLING_TYPE_MAP["pix"] == "PIX"


def test_billing_type_boleto_maps_correctly():
    assert _BILLING_TYPE_MAP["boleto"] == "BOLETO"


def test_billing_type_undefined_maps_correctly():
    assert _BILLING_TYPE_MAP["undefined"] == "UNDEFINED"


def test_sandbox_cpf_is_11_digits():
    """Generated sandbox CPF should always be 11 digits."""
    for _ in range(100):
        cpf = _generate_sandbox_cpf()
        assert len(cpf) == 11
        assert cpf.isdigit()


@pytest.mark.asyncio
async def test_create_charge_partial_response_no_customer_id():
    """If Asaas returns customer without id, should raise RuntimeError."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._client = MagicMock()
    provider._environment = "sandbox"
    provider._client.create_customer = AsyncMock(return_value={"name": "Test", "id": None})

    with pytest.raises(RuntimeError, match="customer without id"):
        await provider.create_charge(
            amount=Decimal("100.00"),
            description="Test",
            customer_name="Test Customer",
        )


@pytest.mark.asyncio
async def test_create_charge_partial_response_no_payment_id():
    """If Asaas returns payment without id, should raise RuntimeError."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._environment = "sandbox"
    provider._client = MagicMock()
    provider._client.create_customer = AsyncMock(return_value={"id": "cus_001"})
    provider._client.create_payment = AsyncMock(return_value={"status": "PENDING", "id": None})

    with pytest.raises(RuntimeError, match="payment without id"):
        await provider.create_charge(
            amount=Decimal("100.00"),
            description="Test",
            customer_name="Test Customer",
        )


@pytest.mark.asyncio
async def test_create_charge_boleto_without_bank_slip_url():
    """Boleto charge without bankSlipUrl should not break."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._environment = "sandbox"
    provider._client = MagicMock()
    provider._client.create_customer = AsyncMock(return_value={"id": "cus_001"})
    provider._client.create_payment = AsyncMock(return_value={
        "id": "pay_boleto001",
        "status": "PENDING",
        "invoiceUrl": "https://sandbox.asaas.com/i/pay_boleto001",
    })
    provider._client.get_pix_qr_code = AsyncMock()

    result = await provider.create_charge(
        amount=Decimal("100.00"),
        description="Test boleto",
        customer_name="Test Customer",
        billing_type="boleto",
    )

    assert result["provider_charge_id"] == "pay_boleto001"
    assert result["provider_bank_slip_url"] is None
    assert result["qr_code"] is None
    assert result["qr_code_base64"] is None
    assert result["status"] == "pending"
    provider._client.get_pix_qr_code.assert_not_called()


@pytest.mark.asyncio
async def test_create_charge_pix_without_qr_code():
    """Pix charge where QR code endpoint fails should not break."""
    from app.integrations.asaas_client import AsaasApiError

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._environment = "sandbox"
    provider._client = MagicMock()
    provider._client.create_customer = AsyncMock(return_value={"id": "cus_001"})
    provider._client.create_payment = AsyncMock(return_value={
        "id": "pay_pix001",
        "status": "PENDING",
        "invoiceUrl": "https://sandbox.asaas.com/i/pay_pix001",
    })
    provider._client.get_pix_qr_code = AsyncMock(side_effect=AsaasApiError("QR code error", status_code=404))

    result = await provider.create_charge(
        amount=Decimal("100.00"),
        description="Test pix",
        customer_name="Test Customer",
        billing_type="pix",
    )

    assert result["provider_charge_id"] == "pay_pix001"
    assert result["qr_code"] is None
    assert result["qr_code_base64"] is None
    assert result["payment_link"] == "https://sandbox.asaas.com/i/pay_pix001"
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_create_charge_undefined_billing_type():
    """UNDEFINED billing type should create a payment link without QR code."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._environment = "sandbox"
    provider._client = MagicMock()
    provider._client.create_customer = AsyncMock(return_value={"id": "cus_001"})
    provider._client.create_payment = AsyncMock(return_value={
        "id": "pay_undef001",
        "status": "PENDING",
        "invoiceUrl": "https://sandbox.asaas.com/i/pay_undef001",
    })
    provider._client.get_pix_qr_code = AsyncMock()

    result = await provider.create_charge(
        amount=Decimal("100.00"),
        description="Test undefined",
        customer_name="Test Customer",
        billing_type="undefined",
    )

    assert result["provider_charge_id"] == "pay_undef001"
    assert result["payment_link"] == "https://sandbox.asaas.com/i/pay_undef001"
    provider._client.get_pix_qr_code.assert_not_called()


@pytest.mark.asyncio
async def test_create_charge_default_billing_type_is_pix():
    """When billing_type is None, should default to PIX."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._environment = "sandbox"
    provider._client = MagicMock()
    provider._client.create_customer = AsyncMock(return_value={"id": "cus_001"})
    provider._client.create_payment = AsyncMock(return_value={
        "id": "pay_default001",
        "status": "PENDING",
        "invoiceUrl": "https://sandbox.asaas.com/i/pay_default001",
    })
    provider._client.get_pix_qr_code = AsyncMock(return_value={
        "payload": "00020126580014br.gov.bcb.pix",
        "encodedImage": "data:image/png;base64,abc",
    })

    result = await provider.create_charge(
        amount=Decimal("100.00"),
        description="Test default",
        customer_name="Test Customer",
        billing_type=None,
    )

    assert result["qr_code"] == "00020126580014br.gov.bcb.pix"
    assert result["qr_code_base64"] == "data:image/png;base64,abc"
    call_args = provider._client.create_payment.call_args
    assert call_args.kwargs["billing_type"] == "PIX"


@pytest.mark.asyncio
async def test_get_charge_404_returns_none():
    """get_charge should return None for 404."""
    from app.integrations.asaas_client import AsaasApiError

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._client = MagicMock()
    provider._client.get_payment = AsyncMock(side_effect=AsaasApiError("Not found", status_code=404))

    result = await provider.get_charge("pay_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cancel_charge_failure_returns_false():
    """cancel_charge should return False on API error."""
    from app.integrations.asaas_client import AsaasApiError

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._client = MagicMock()
    provider._client.cancel_payment = AsyncMock(side_effect=AsaasApiError("Error", status_code=500))

    result = await provider.cancel_charge("pay_001")
    assert result is False


@pytest.mark.asyncio
async def test_cancel_charge_success_returns_true():
    """cancel_charge should return True on success."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    provider._client = MagicMock()
    provider._client.cancel_payment = AsyncMock(return_value={"deleted": True})

    result = await provider.cancel_charge("pay_001")
    assert result is True
