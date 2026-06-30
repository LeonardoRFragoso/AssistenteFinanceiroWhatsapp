from decimal import Decimal
from typing import Dict, Any, Optional
from app.providers.base import PaymentProvider
from app.integrations.mercado_pago import MercadoPagoService
from app.core.logging import logger


class MercadoPagoPaymentProvider(PaymentProvider):
    """Mercado Pago provider for creating payment links and preferences.

    This provider reuses the existing MercadoPagoService for subscription billing
    while adding one-off charge/preference creation. It does NOT perform real
    Pix Out or balance movement.
    """

    name = "mercado_pago"

    def __init__(self):
        self.mp_service = MercadoPagoService()

    async def create_charge(
        self,
        amount: Decimal,
        description: str,
        customer_name: str,
        customer_phone: Optional[str] = None,
        external_reference: Optional[str] = None,
        due_date: Optional[str] = None,
        payer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # Mercado Pago preference does not accept a phone in the item, so we
            # enrich the description with customer info for reconciliation.
            enriched_description = f"{description} - {customer_name}"
            if customer_phone:
                enriched_description += f" ({customer_phone})"

            result = self.mp_service.create_payment_preference(
                title=enriched_description[:250],
                quantity=1,
                unit_price=float(amount),
                payer_email=payer_email or "payer@example.com",
                external_reference=external_reference or "payflow_charge"
            )

            if not result.get("success"):
                logger.error(f"Mercado Pago preference creation failed: {result}")
                raise RuntimeError("Failed to create Mercado Pago preference")

            return {
                "provider_charge_id": result["preference_id"],
                "payment_link": result.get("init_point", result.get("sandbox_init_point", "")),
                "qr_code": None,
                "qr_code_base64": None,
                "status": "pending",
                "raw_response": result
            }
        except Exception as e:
            logger.error(f"Error creating Mercado Pago charge: {str(e)}")
            raise

    async def get_charge(self, provider_charge_id: str) -> Optional[Dict[str, Any]]:
        # Mercado Pago SDK does not expose a direct preference GET in the same
        # shape as payments. We treat this as a no-op for now; the webhook flow
        # is the source of truth for status updates.
        return {
            "provider_charge_id": provider_charge_id,
            "status": "pending",
            "amount": None,
            "raw_response": {"provider": self.name}
        }

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Mercado Pago webhook events for payment preferences.

        Mercado Pago sends notification payloads with type and data.id. The
        preference id (external_reference) maps to our Charge record via the
        provider_charge_id column.
        """
        try:
            processed = self.mp_service.process_webhook_notification(payload)
            notification_type = processed.get("type")
            data = processed.get("data") or {}

            if notification_type == "payment":
                preference_id = data.get("preference_id")
                if not preference_id:
                    return None

                status = data.get("status")
                return {
                    "event_type": "payment.approved" if status == "approved" else f"payment.{status}",
                    "provider_charge_id": preference_id,
                    "external_reference": data.get("external_reference"),
                    "amount": Decimal(str(data.get("transaction_amount", 0))) if data.get("transaction_amount") else None,
                    "status": "paid" if status == "approved" else status,
                    "paid_at": data.get("date_approved") or data.get("date_created"),
                    "raw_data": data
                }

            return None
        except Exception as e:
            logger.error(f"Error parsing Mercado Pago webhook event: {str(e)}")
            return None
