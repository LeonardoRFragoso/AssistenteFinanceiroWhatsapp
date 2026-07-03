"""
Asaas HTTP client — Sprint 15.

Handles all HTTP communication with the Asaas API.
- Never logs API key or sensitive headers.
- Timeout on all requests.
- Retry on 5xx and timeouts only (safe retries).
- Sanitizes response data before logging.
"""
import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import date

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_MAX_RETRIES = 2
_RETRY_DELAY = 1.0

_SENSITIVE_KEYS = {
    "access_token", "api_key", "apikey", "token", "secret",
    "password", "authorization", "credential", "client_secret",
}


class AsaasApiError(Exception):
    """Raised when Asaas API returns an error."""

    def __init__(self, message: str, status_code: int = 0, detail: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def _sanitize_for_log(data: Any) -> Any:
    """Remove sensitive values from data before logging."""
    if isinstance(data, dict):
        return {
            k: ("[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _sanitize_for_log(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize_for_log(item) for item in data]
    return data


class AsaasClient:
    """HTTP client for Asaas API v3 (sandbox/production)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key or settings.ASAAS_API_KEY
        self._base_url = (base_url or settings.ASAAS_API_BASE_URL).rstrip("/")
        self._environment = settings.ASAAS_ENVIRONMENT

        if not self._api_key:
            raise AsaasApiError(
                "ASAAS_API_KEY is not configured. "
                "Set ENABLE_ASAAS_CHARGE_PROVIDER=false or provide a valid API key.",
                status_code=401,
            )

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "access_token": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        json=json,
                        params=params,
                        headers=self._headers,
                    )

                    if resp.status_code >= 500:
                        body = resp.text[:500] if resp.text else ""
                        logger.warning(
                            f"Asaas API {method} {path} returned {resp.status_code}, "
                            f"attempt {attempt + 1}/{_MAX_RETRIES + 1}"
                        )
                        last_exc = AsaasApiError(
                            f"Asaas API error {resp.status_code}: {body}",
                            status_code=resp.status_code,
                        )
                        if attempt < _MAX_RETRIES:
                            await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                            continue
                        raise last_exc

                    if resp.status_code >= 400:
                        detail = None
                        try:
                            detail = resp.json()
                        except Exception:
                            pass
                        sanitized = _sanitize_for_log(detail)
                        logger.error(
                            f"Asaas API {method} {path} returned {resp.status_code}: {sanitized}"
                        )
                        raise AsaasApiError(
                            f"Asaas API error {resp.status_code}",
                            status_code=resp.status_code,
                            detail=detail,
                        )

                    return resp.json()

            except httpx.TimeoutException:
                logger.warning(
                    f"Asaas API {method} {path} timed out, "
                    f"attempt {attempt + 1}/{_MAX_RETRIES + 1}"
                )
                last_exc = AsaasApiError(
                    f"Asaas API timeout for {method} {path}",
                    status_code=408,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
                raise last_exc

            except httpx.RequestError as exc:
                logger.warning(
                    f"Asaas API {method} {path} request error: {exc}, "
                    f"attempt {attempt + 1}/{_MAX_RETRIES + 1}"
                )
                last_exc = AsaasApiError(
                    f"Asaas API request error: {exc}",
                    status_code=0,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
                raise last_exc

        raise last_exc or AsaasApiError("Unexpected error in Asaas client")

    async def create_customer(
        self,
        name: str,
        cpf_cnpj: Optional[str] = None,
        email: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        external_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": name}
        if cpf_cnpj:
            body["cpfCnpj"] = cpf_cnpj
        if email:
            body["email"] = email
        if mobile_phone:
            body["mobilePhone"] = mobile_phone
        if external_reference:
            body["externalReference"] = external_reference

        return await self._request("POST", "/customers", json=body)

    async def create_payment(
        self,
        customer_id: str,
        billing_type: str,
        value: float,
        due_date: str,
        description: Optional[str] = None,
        external_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": value,
            "dueDate": due_date,
        }
        if description:
            body["description"] = description[:500]
        if external_reference:
            body["externalReference"] = external_reference

        return await self._request("POST", "/payments", json=body)

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/payments/{payment_id}")

    async def get_pix_qr_code(self, payment_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/payments/{payment_id}/pixQrCode")

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/payments/{payment_id}")

    async def list_customers(self, name: Optional[str] = None, external_reference: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if name:
            params["name"] = name
        if external_reference:
            params["externalReference"] = external_reference
        return await self._request("GET", "/customers", params=params)
