"""
Tests for AsaasClient hardening — Sprint 15.1.
Covers: timeout, 400, 401, 500, invalid JSON, production base URL validation.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.integrations.asaas_client import AsaasClient, AsaasApiError, _sanitize_for_log


@pytest.mark.asyncio
async def test_client_400_does_not_retry():
    """4xx errors should not be retried."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"errors": [{"description": "Bad request"}]}'
    mock_response.json.return_value = {"errors": [{"description": "Bad request"}]}

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
        assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_client_401_raises_error():
    """401 should raise AsaasApiError with status_code=401."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.side_effect = Exception("no json")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.get_payment("pay_001")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_client_500_retries_then_fails():
    """500 should retry up to MAX_RETRIES times then raise."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient") as mock_client_class, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.create_customer(name="Test")
        assert exc_info.value.status_code == 500
        assert mock_client.request.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_client_timeout_retries_then_fails():
    """Timeout should retry then raise AsaasApiError with 408."""
    import httpx
    with patch("httpx.AsyncClient") as mock_client_class, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.create_customer(name="Test")
        assert exc_info.value.status_code == 408
        assert mock_client.request.call_count == 3


@pytest.mark.asyncio
async def test_client_invalid_json_raises_error():
    """Invalid JSON in success response should raise AsaasApiError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("not JSON")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.create_customer(name="Test")
        assert "invalid json" in str(exc_info.value).lower()


def test_client_production_rejects_sandbox_url():
    """AsaasClient should reject sandbox URL in production environment."""
    from app.core.config import settings
    old_env = settings.ENVIRONMENT
    old_url = settings.ASAAS_API_BASE_URL
    try:
        settings.ENVIRONMENT = "production"
        settings.ASAAS_API_BASE_URL = "https://sandbox.asaas.com/api/v3"
        with pytest.raises(AsaasApiError, match="sandbox URL detected in production"):
            AsaasClient(api_key="test-key")
    finally:
        settings.ENVIRONMENT = old_env
        settings.ASAAS_API_BASE_URL = old_url


def test_sanitize_nested_sensitive_keys():
    """_sanitize_for_log should redact deeply nested sensitive keys."""
    data = {
        "access_token": "secret",
        "nested": {
            "deep": {
                "api_key": "deep-secret",
                "safe": "ok"
            }
        },
        "list_item": [{"token": "list-secret", "id": 1}],
    }
    result = _sanitize_for_log(data)
    assert result["access_token"] == "[REDACTED]"
    assert result["nested"]["deep"]["api_key"] == "[REDACTED]"
    assert result["nested"]["deep"]["safe"] == "ok"
    assert result["list_item"][0]["token"] == "[REDACTED]"
    assert result["list_item"][0]["id"] == 1


@pytest.mark.asyncio
async def test_client_request_error_retries():
    """RequestError (non-timeout) should retry then raise."""
    import httpx
    with patch("httpx.AsyncClient") as mock_client_class, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        client = AsaasClient(api_key="test-key")
        with pytest.raises(AsaasApiError) as exc_info:
            await client.get_payment("pay_001")
        assert exc_info.value.status_code == 0
        assert mock_client.request.call_count == 3
