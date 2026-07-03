"""
Bill payment intent service — Sprint 17.

Manages fake payment intents for bills. This does NOT execute any payment.
It is only a sandbox/fake intention. All data is org-scoped.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bills import (
    DetectedBill, BillPaymentIntent, BillEventLog,
    PaymentIntentStatus, PaymentIntentType, BillEventAction,
)
from app.models.provider_foundation import (
    TransactionAuthorization, AuthorizationStatus, ChallengeType,
)

logger = logging.getLogger(__name__)


class BillPaymentIntentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_fake_payment_intent(
        self,
        organization_id: int,
        bill_id: int,
        user_id: int,
        intent_type: PaymentIntentType = PaymentIntentType.FAKE_BOLETO,
    ) -> Optional[BillPaymentIntent]:
        """Create a fake payment intent for a bill. Does NOT execute payment."""
        bill_result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.id == bill_id,
                )
            )
        )
        bill = bill_result.scalar_one_or_none()
        if not bill:
            return None

        intent = BillPaymentIntent(
            organization_id=organization_id,
            detected_bill_id=bill_id,
            user_id=user_id,
            provider_name="fake",
            amount=bill.amount,
            currency=bill.currency,
            status=PaymentIntentStatus.DRAFT,
            intent_type=intent_type,
            fake_payment_reference=f"FAKE-{uuid.uuid4().hex[:12].upper()}",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            metadata_sanitized={
                "demo": True,
                "note": "This is a fake payment intent. No real payment will be executed.",
                "bill_title": bill.title,
                "bill_beneficiary": bill.beneficiary_name,
            },
        )
        self.db.add(intent)
        await self.db.flush()

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=bill_id,
            actor_user_id=user_id,
            action=BillEventAction.PAYMENT_INTENT_CREATED,
            metadata_sanitized={"intent_id": str(intent.id), "is_fake": True},
        )
        self.db.add(event)
        await self.db.commit()
        return intent

    async def authorize_fake_intent(
        self,
        organization_id: int,
        intent_id: int,
        user_id: int,
        authorization_code: Optional[str] = None,
    ) -> Optional[BillPaymentIntent]:
        """Authorize a fake payment intent. Does NOT execute payment."""
        intent_result = await self.db.execute(
            select(BillPaymentIntent).where(
                and_(
                    BillPaymentIntent.organization_id == organization_id,
                    BillPaymentIntent.id == intent_id,
                )
            )
        )
        intent = intent_result.scalar_one_or_none()
        if not intent:
            return None

        if intent.status not in (PaymentIntentStatus.DRAFT, PaymentIntentStatus.PENDING_AUTHORIZATION):
            return None

        tx_auth = None
        if authorization_code:
            tx_auth = TransactionAuthorization(
                organization_id=organization_id,
                user_id=user_id,
                action_type="fake_bill_payment",
                resource_type="bill_payment_intent",
                resource_id=str(intent.id),
                amount=intent.amount,
                currency=intent.currency,
                status=AuthorizationStatus.CONFIRMED,
                challenge_type=ChallengeType.PASSWORD_6,
                code_hash=f"fake_hash_{uuid.uuid4().hex[:16]}",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                confirmed_at=datetime.now(timezone.utc),
                extra_data={"is_fake": True, "intent_id": str(intent.id)},
            )
            self.db.add(tx_auth)
            await self.db.flush()
            intent.transaction_authorization_id = tx_auth.id

        intent.status = PaymentIntentStatus.AUTHORIZED_FAKE
        intent.confirmed_at = datetime.now(timezone.utc)

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=intent.detected_bill_id,
            actor_user_id=user_id,
            action=BillEventAction.PAYMENT_INTENT_AUTHORIZED_FAKE,
            metadata_sanitized={
                "intent_id": str(intent.id),
                "tx_auth_id": str(tx_auth.id) if tx_auth else None,
                "is_fake": True,
                "note": "Fake authorization. No real payment executed.",
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(intent)
        return intent

    async def cancel_intent(
        self,
        organization_id: int,
        intent_id: int,
        user_id: int,
    ) -> Optional[BillPaymentIntent]:
        """Cancel a payment intent."""
        intent_result = await self.db.execute(
            select(BillPaymentIntent).where(
                and_(
                    BillPaymentIntent.organization_id == organization_id,
                    BillPaymentIntent.id == intent_id,
                )
            )
        )
        intent = intent_result.scalar_one_or_none()
        if not intent:
            return None

        intent.status = PaymentIntentStatus.CANCELLED
        intent.cancelled_at = datetime.now(timezone.utc)

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=intent.detected_bill_id,
            actor_user_id=user_id,
            action=BillEventAction.PAYMENT_INTENT_CANCELLED,
            metadata_sanitized={"intent_id": str(intent.id)},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(intent)
        return intent

    async def expire_old_intents(self) -> int:
        """Expire intents that have passed their expiry date."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(BillPaymentIntent)
            .where(
                and_(
                    BillPaymentIntent.expires_at < now,
                    BillPaymentIntent.status.in_([
                        PaymentIntentStatus.DRAFT,
                        PaymentIntentStatus.PENDING_AUTHORIZATION,
                    ]),
                )
            )
            .values(status=PaymentIntentStatus.EXPIRED)
        )
        count = result.rowcount
        if count > 0:
            await self.db.commit()
        return count
