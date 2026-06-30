from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class PaymentProvider(ABC):
    """Abstract base class for payment providers.

    Implementations must support creating a charge, retrieving its status,
    and parsing webhook events.
    """

    name: str = "base"

    @abstractmethod
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
        """Create a charge and return provider-specific data.

        Expected return keys:
        - provider_charge_id: str
        - payment_link: str
        - qr_code: Optional[str]
        - qr_code_base64: Optional[str]
        - status: str (provider-specific)
        - raw_response: dict
        """
        raise NotImplementedError

    @abstractmethod
    async def get_charge(self, provider_charge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve charge data from the provider."""
        raise NotImplementedError

    @abstractmethod
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a provider webhook payload into a normalized event.

        Normalized event shape:
        - event_type: str (e.g., "payment.approved", "charge.paid")
        - provider_charge_id: str
        - external_reference: Optional[str]
        - amount: Optional[Decimal]
        - status: Optional[str]
        - paid_at: Optional[str]
        - raw_data: dict
        """
        raise NotImplementedError
