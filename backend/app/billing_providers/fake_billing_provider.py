import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from app.billing_providers.base import BaseBillingProvider
from app.core.logging import logger


class FakeBillingProvider(BaseBillingProvider):
    """Fake billing provider for sandbox/demo mode.

    No real payments are processed. All operations are simulated.
    """

    @property
    def name(self) -> str:
        return "fake"

    async def create_subscription(
        self, plan_code: str, organization_id: int
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        sub_id = f"fake_sub_{uuid.uuid4().hex[:12]}"
        logger.info(f"FakeBillingProvider: created subscription {sub_id} for org {organization_id}, plan={plan_code}")
        return {
            "provider_subscription_id": sub_id,
            "status": "active",
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "trial_ends_at": None,
        }

    async def cancel_subscription(
        self, provider_subscription_id: str
    ) -> Dict[str, Any]:
        logger.info(f"FakeBillingProvider: cancelled subscription {provider_subscription_id}")
        return {
            "status": "cancelled",
            "cancel_at_period_end": True,
        }

    async def change_plan(
        self, provider_subscription_id: str, new_plan_code: str
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        logger.info(f"FakeBillingProvider: changed plan for {provider_subscription_id} to {new_plan_code}")
        return {
            "status": "active",
            "plan_code": new_plan_code,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
        }

    async def reactivate_subscription(
        self, provider_subscription_id: str
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        logger.info(f"FakeBillingProvider: reactivated subscription {provider_subscription_id}")
        return {
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
        }
