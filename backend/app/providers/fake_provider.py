import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
from app.providers.base import PaymentProvider
from app.core.config import settings


class FakePaymentProvider(PaymentProvider):
    """Sandbox provider for local development and testing.

    Generates deterministic fake links and IDs so the product flow can be
    exercised without touching real financial institutions.
    """

    name = "fake"

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
        provider_charge_id = f"fake_{uuid.uuid4().hex[:12]}"
        payment_link = f"{settings.BACKEND_URL}/provider-webhooks/fake/pay/{provider_charge_id}"
        qr_code = f"fake-pix-code:{provider_charge_id}:{amount}"
        qr_code_base64 = f"data:image/png;base64,{uuid.uuid4().hex}"

        return {
            "provider_charge_id": provider_charge_id,
            "payment_link": payment_link,
            "qr_code": qr_code,
            "qr_code_base64": qr_code_base64,
            "status": "pending",
            "raw_response": {
                "provider": self.name,
                "amount": float(amount),
                "description": description,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "external_reference": external_reference,
                "due_date": due_date,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }

    async def get_charge(self, provider_charge_id: str) -> Optional[Dict[str, Any]]:
        return {
            "provider_charge_id": provider_charge_id,
            "status": "pending",
            "amount": None,
            "raw_response": {"provider": self.name}
        }

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_type = payload.get("event_type", "")
        provider_charge_id = payload.get("provider_charge_id")
        if not provider_charge_id:
            return None

        if event_type == "payment.approved":
            return {
                "event_type": "payment.approved",
                "provider_charge_id": provider_charge_id,
                "external_reference": payload.get("external_reference"),
                "amount": Decimal(str(payload.get("amount", 0))) if payload.get("amount") else None,
                "status": "paid",
                "paid_at": payload.get("paid_at") or datetime.now(timezone.utc).isoformat(),
                "raw_data": payload
            }

        return {
            "event_type": event_type or "unknown",
            "provider_charge_id": provider_charge_id,
            "external_reference": payload.get("external_reference"),
            "amount": None,
            "status": None,
            "paid_at": None,
            "raw_data": payload
        }

    def build_payment_simulation_payload(self, provider_charge_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        return {
            "event_type": "payment.approved",
            "provider_charge_id": provider_charge_id,
            "amount": float(amount) if amount else None,
            "paid_at": datetime.now(timezone.utc).isoformat()
        }
