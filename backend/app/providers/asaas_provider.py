"""
Asaas payment provider — Sprint 15.

Implements the PaymentProvider interface for Asaas sandbox.
Creates customers, payments (PIX/BOLETO/UNDEFINED), retrieves QR codes,
and parses webhook events.

Security:
- Never logs API key.
- Sanitizes raw responses before logging.
- Returns only normalized data to ChargeService.
"""
import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from app.providers.base import PaymentProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

_ASAAS_STATUS_MAP = {
    "PENDING": "pending",
    "RECEIVED": "paid",
    "CONFIRMED": "paid",
    "OVERDUE": "expired",
    "DELETED": "cancelled",
    "REFUNDED": "cancelled",
    "RECEIVED_IN_CASH_UNDONE": "pending",
    "RESTORED": "pending",
}

_ASAAS_EVENT_MAP = {
    "PAYMENT_CREATED": "payment.created",
    "PAYMENT_CONFIRMED": "payment.confirmed",
    "PAYMENT_RECEIVED": "payment.received",
    "PAYMENT_OVERDUE": "payment.overdue",
    "PAYMENT_DELETED": "payment.deleted",
    "PAYMENT_RESTORED": "payment.restored",
    "PAYMENT_REFUNDED": "payment.refunded",
    "PAYMENT_UPDATED": "payment.updated",
}

_BILLING_TYPE_MAP = {
    "pix": "PIX",
    "boleto": "BOLETO",
    "undefined": "UNDEFINED",
    "credit_card": "CREDIT_CARD",
}


def _generate_sandbox_cpf() -> str:
    """Generate a valid-format CPF for sandbox testing only."""
    digits = [random.randint(0, 9) for _ in range(9)]
    s1 = sum(d * (10 - i) for i, d in enumerate(digits)) % 11
    s1 = 0 if s1 < 2 else 11 - s1
    digits.append(s1)
    s2 = sum(d * (11 - i) for i, d in enumerate(digits)) % 11
    s2 = 0 if s2 < 2 else 11 - s2
    digits.append(s2)
    return "".join(str(d) for d in digits)


class AsaasPaymentProvider(PaymentProvider):
    """Asaas sandbox charge provider.

    Supports PIX, BOLETO, and UNDEFINED (link) billing types.
    All operations are receive-only (no Pix Out, no withdrawals).
    """

    name = "asaas"

    def __init__(self):
        from app.integrations.asaas_client import AsaasClient, AsaasApiError

        if not settings.ENABLE_ASAAS_CHARGE_PROVIDER:
            raise RuntimeError(
                "Asaas charge provider is not enabled. "
                "Set ENABLE_ASAAS_CHARGE_PROVIDER=true to use it."
            )
        if settings.ENABLE_DEMO_MODE:
            raise RuntimeError(
                "Demo mode is active. Asaas provider cannot be used in demo mode. "
                "Set ENABLE_DEMO_MODE=false or use provider=fake."
            )
        if not settings.ASAAS_API_KEY:
            raise RuntimeError(
                "ENABLE_ASAAS_CHARGE_PROVIDER=true but ASAAS_API_KEY is not set. "
                "Configure ASAAS_API_KEY or set ENABLE_ASAAS_CHARGE_PROVIDER=false."
            )

        self._client = AsaasClient()
        self._environment = settings.ASAAS_ENVIRONMENT

    async def create_charge(
        self,
        amount: Decimal,
        description: str,
        customer_name: str,
        customer_phone: Optional[str] = None,
        external_reference: Optional[str] = None,
        due_date: Optional[str] = None,
        payer_email: Optional[str] = None,
        billing_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.integrations.asaas_client import AsaasApiError

        asaas_billing = _BILLING_TYPE_MAP.get(
            (billing_type or "pix").lower(), "PIX"
        )

        if not due_date:
            from datetime import date, timedelta
            due_date = (date.today() + timedelta(days=7)).isoformat()

        try:
            customer = await self._client.create_customer(
                name=customer_name,
                cpf_cnpj=_generate_sandbox_cpf() if self._environment == "sandbox" else None,
                email=payer_email,
                mobile_phone=customer_phone,
                external_reference=external_reference,
            )
            customer_id = customer["id"]

            payment = await self._client.create_payment(
                customer_id=customer_id,
                billing_type=asaas_billing,
                value=float(amount),
                due_date=due_date,
                description=description,
                external_reference=external_reference,
            )

            payment_id = payment["id"]
            invoice_url = payment.get("invoiceUrl")
            bank_slip_url = payment.get("bankSlipUrl")
            provider_status = payment.get("status", "PENDING")

            qr_code = None
            qr_code_base64 = None
            if asaas_billing == "PIX":
                try:
                    pix_data = await self._client.get_pix_qr_code(payment_id)
                    qr_code = pix_data.get("payload")
                    qr_code_base64 = pix_data.get("encodedImage")
                except AsaasApiError as e:
                    logger.warning(
                        f"Failed to retrieve Pix QR code for payment {payment_id}: {e}"
                    )

            return {
                "provider_charge_id": payment_id,
                "payment_link": invoice_url,
                "qr_code": qr_code,
                "qr_code_base64": qr_code_base64,
                "provider_bank_slip_url": bank_slip_url,
                "provider_status": provider_status,
                "status": _ASAAS_STATUS_MAP.get(provider_status, "pending"),
                "amount": float(amount),
                "raw_response": {
                    "payment_id": payment_id,
                    "billing_type": asaas_billing,
                    "status": provider_status,
                    "invoice_url": invoice_url,
                    "bank_slip_url": bank_slip_url,
                    "environment": self._environment,
                },
            }

        except AsaasApiError as e:
            logger.error(f"Asaas create_charge failed: {e.status_code} — {e}")
            raise RuntimeError(f"Asaas API error: {e}") from e

    async def get_charge(self, provider_charge_id: str) -> Optional[Dict[str, Any]]:
        from app.integrations.asaas_client import AsaasApiError

        try:
            payment = await self._client.get_payment(provider_charge_id)
            provider_status = payment.get("status", "PENDING")
            return {
                "provider_charge_id": payment["id"],
                "status": _ASAAS_STATUS_MAP.get(provider_status, "pending"),
                "provider_status": provider_status,
                "amount": payment.get("value"),
                "raw_response": {
                    "id": payment["id"],
                    "status": provider_status,
                    "value": payment.get("value"),
                },
            }
        except AsaasApiError as e:
            if e.status_code == 404:
                return None
            logger.error(f"Asaas get_charge failed: {e}")
            raise RuntimeError(f"Asaas API error: {e}") from e

    async def cancel_charge(self, provider_charge_id: str) -> bool:
        from app.integrations.asaas_client import AsaasApiError

        try:
            await self._client.cancel_payment(provider_charge_id)
            return True
        except AsaasApiError as e:
            logger.error(f"Asaas cancel_charge failed: {e}")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_name = payload.get("event", "")
        payment_obj = payload.get("payment", {})

        if isinstance(payment_obj, dict):
            payment_id = payment_obj.get("id")
        else:
            payment_id = None

        if not payment_id:
            logger.warning(f"Asaas webhook without payment id: event={event_name}")
            return None

        event_type = _ASAAS_EVENT_MAP.get(event_name, f"payment.{event_name.lower()}")

        status: Optional[str] = None
        if event_name in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
            status = "paid"
        elif event_name == "PAYMENT_OVERDUE":
            status = "expired"
        elif event_name in ("PAYMENT_DELETED", "PAYMENT_REFUNDED"):
            status = "cancelled"
        elif event_name == "PAYMENT_RESTORED":
            status = "pending"

        paid_at = None
        if status == "paid":
            paid_at = datetime.now(timezone.utc).isoformat()

        return {
            "event_type": event_type,
            "provider_charge_id": payment_id,
            "external_reference": payment_obj.get("externalReference") if isinstance(payment_obj, dict) else None,
            "amount": Decimal(str(payment_obj["value"])) if isinstance(payment_obj, dict) and payment_obj.get("value") else None,
            "status": status,
            "paid_at": paid_at,
            "raw_data": payload,
        }

    def validate_webhook(self, headers: Dict[str, str], payload: Dict[str, Any]) -> bool:
        token = headers.get("asaas-access-token") or headers.get("Asaas-Access-Token")
        if not token:
            logger.warning("Asaas webhook without asaas-access-token header")
            return False
        if not settings.ASAAS_WEBHOOK_TOKEN:
            logger.warning("ASAAS_WEBHOOK_TOKEN not configured — rejecting webhook")
            return False
        return token == settings.ASAAS_WEBHOOK_TOKEN
