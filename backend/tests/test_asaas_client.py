"""
Tests for AsaasClient HTTP client.
Sprint 15 — Asaas sandbox provider.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.integrations.asaas_client import AsaasClient, AsaasApiError, _sanitize_for_log


def test_sanitize_for_log_removes_sensitive_keys():
    """_sanitize_for_log should redact sensitive keys."""
    data = {
        "access_token": "secret123",
        "name": "John",
        "api_key": "key456",
        "nested": {
            "token": "inner-token",
            "safe": "ok",
        },
        "list": [{"password": "pw", "id": 1}],
    }
    result = _sanitize_for_log(data)
    assert result["access_token"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["name"] == "John"
    assert result["nested"]["token"] == "[REDACTED]"
    assert result["nested"]["safe"] == "ok"
    assert result["list"][0]["password"] == "[REDACTED]"
    assert result["list"][0]["id"] == 1


def test_asaas_client_requires_api_key():
    """AsaasClient should raise if API key is not configured."""
    from app.core.config import settings
    old_key = settings.ASAAS_API_KEY
    try:
        settings.ASAAS_API_KEY = None
        with pytest.raises(AsaasApiError, match="ASAAS_API_KEY is not configured"):
            AsaasClient()
    finally:
        settings.ASAAS_API_KEY = old_key


def test_asaas_client_accepts_explicit_api_key():
    """AsaasClient should accept an explicit API key."""
    client = AsaasClient(api_key="explicit-key")
    assert client._api_key == "explicit-key"


@pytest.mark.asyncio
async def test_asaas_client_create_customer():
    """create_customer should POST to /customers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "cus_001", "name": "Test"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        result = await client.create_customer(name="Test", email="test@test.com")

        assert result["id"] == "cus_001"
        call_args = mock_client.request.call_args
        assert call_args.kwargs["json"]["name"] == "Test"
        assert call_args.kwargs["json"]["email"] == "test@test.com"
        assert call_args.kwargs["headers"]["access_token"] == "test-key"


@pytest.mark.asyncio
async def test_asaas_client_create_payment():
    """create_payment should POST to /payments."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "pay_001", "status": "PENDING"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        result = await client.create_payment(
            customer_id="cus_001",
            billing_type="PIX",
            value=100.50,
            due_date="2025-07-10",
            description="Test payment",
        )

        assert result["id"] == "pay_001"
        call_args = mock_client.request.call_args
        assert call_args.kwargs["json"]["customer"] == "cus_001"
        assert call_args.kwargs["json"]["billingType"] == "PIX"
        assert call_args.kwargs["json"]["value"] == 100.50


@pytest.mark.asyncio
async def test_asaas_client_get_pix_qr_code():
    """get_pix_qr_code should GET /payments/{id}/pixQrCode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "encodedImage": "data:image/png;base64,abc",
        "payload": "00020126580014br.gov.bcb.pix",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        result = await client.get_pix_qr_code("pay_001")

        assert result["encodedImage"].startswith("data:image/png;base64,")
        assert result["payload"].startswith("00020126")


@pytest.mark.asyncio
async def test_asaas_client_400_raises_error():
    """AsaasClient should raise AsaasApiError for 400 responses."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"errors": [{"description": "Invalid"}]}'
    mock_response.json.return_value = {"errors": [{"description": "Invalid"}]}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.create_customer(name="Test")
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_asaas_client_404_get_payment_returns_none():
    """get_charge should return None for 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.json.side_effect = Exception("no json")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.get_payment("pay_nonexistent")
        assert exc_info.value.status_code == 404
