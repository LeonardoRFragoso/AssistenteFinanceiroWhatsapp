from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseBillingProvider(ABC):
    """Abstract base for billing providers.

    This is SEPARATE from the payment provider that handles charges.
    Billing providers handle platform subscriptions only.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_subscription(
        self, plan_code: str, organization_id: int
    ) -> Dict[str, Any]:
        """Create a subscription in the billing provider."""
        ...

    @abstractmethod
    async def cancel_subscription(
        self, provider_subscription_id: str
    ) -> Dict[str, Any]:
        """Cancel a subscription in the billing provider."""
        ...

    @abstractmethod
    async def change_plan(
        self, provider_subscription_id: str, new_plan_code: str
    ) -> Dict[str, Any]:
        """Change the plan of an existing subscription."""
        ...

    @abstractmethod
    async def reactivate_subscription(
        self, provider_subscription_id: str
    ) -> Dict[str, Any]:
        """Reactivate a cancelled subscription."""
        ...
