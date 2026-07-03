"""
Transaction authorization service — Sprint 14.

Creates 6-digit challenge codes, stores hash only.
In testing/demo, returns the code for validation.
In production, code is never returned.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.provider_foundation import (
    TransactionAuthorization, AuthorizationStatus, ChallengeType,
)
from app.services.organization_audit_service import OrganizationAuditService

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
EXPIRY_MINUTES = 5


class TransactionAuthorizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_code() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    async def create_authorization(
        self,
        organization_id: int,
        user_id: int,
        action_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        amount: Decimal | None = None,
        metadata: dict | None = None,
    ) -> tuple[TransactionAuthorization, str | None]:
        """Create authorization. Returns (authorization, code_or_none).
        Code is only returned in testing/demo/development."""
        code = self._generate_code()
        code_hash = self._hash_code(code)
        now = datetime.now(timezone.utc)

        auth = TransactionAuthorization(
            organization_id=organization_id,
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            amount=amount,
            status=AuthorizationStatus.PENDING,
            challenge_type=ChallengeType.PASSWORD_6,
            code_hash=code_hash,
            expires_at=now + timedelta(minutes=EXPIRY_MINUTES),
            extra_data=metadata,
        )
        self.db.add(auth)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="transaction_auth_created",
            actor_user_id=user_id,
            resource_type="transaction_authorization",
            resource_id=str(auth.id),
            metadata={"action_type": action_type, "amount": str(amount) if amount else None},
        )

        await self.db.commit()
        await self.db.refresh(auth)

        return_code = None
        if settings.ENVIRONMENT in ("testing", "development") or settings.ENABLE_DEMO_MODE:
            return_code = code

        return auth, return_code

    async def confirm_authorization(
        self, organization_id: int, authorization_id: int, user_id: int, code: str
    ) -> TransactionAuthorization:
        result = await self.db.execute(
            select(TransactionAuthorization).where(
                TransactionAuthorization.id == authorization_id,
                TransactionAuthorization.organization_id == organization_id,
            )
        )
        auth = result.scalar_one_or_none()
        if not auth:
            raise ValueError("Authorization not found")

        if auth.status != AuthorizationStatus.PENDING:
            raise ValueError(f"Authorization is not pending (status: {auth.status.value})")

        now = datetime.now(timezone.utc)
        expires_at = auth.expires_at
        if expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        if now > expires_at:
            auth.status = AuthorizationStatus.EXPIRED
            await self.db.commit()
            await self.db.refresh(auth)

            await self.audit.log_event(
                organization_id=organization_id,
                action="transaction_auth_expired",
                actor_user_id=user_id,
                resource_type="transaction_authorization",
                resource_id=str(auth.id),
            )
            raise ValueError("Authorization has expired")

        if auth.failed_attempts >= MAX_ATTEMPTS:
            auth.status = AuthorizationStatus.FAILED
            await self.db.commit()
            await self.db.refresh(auth)

            await self.audit.log_event(
                organization_id=organization_id,
                action="transaction_auth_failed",
                actor_user_id=user_id,
                resource_type="transaction_authorization",
                resource_id=str(auth.id),
                metadata={"reason": "max_attempts_exceeded"},
            )
            raise ValueError("Maximum attempts exceeded")

        provided_hash = self._hash_code(code)
        if provided_hash != auth.code_hash:
            auth.failed_attempts += 1
            await self.db.commit()
            await self.db.refresh(auth)
            raise ValueError("Invalid authorization code")

        auth.status = AuthorizationStatus.CONFIRMED
        auth.confirmed_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="transaction_auth_confirmed",
            actor_user_id=user_id,
            resource_type="transaction_authorization",
            resource_id=str(auth.id),
            metadata={"action_type": auth.action_type},
        )

        await self.db.commit()
        await self.db.refresh(auth)
        return auth

    async def cancel_authorization(
        self, organization_id: int, authorization_id: int, user_id: int
    ) -> Optional[TransactionAuthorization]:
        result = await self.db.execute(
            select(TransactionAuthorization).where(
                TransactionAuthorization.id == authorization_id,
                TransactionAuthorization.organization_id == organization_id,
            )
        )
        auth = result.scalar_one_or_none()
        if not auth:
            return None

        auth.status = AuthorizationStatus.CANCELLED
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="transaction_auth_cancelled",
            actor_user_id=user_id,
            resource_type="transaction_authorization",
            resource_id=str(auth.id),
        )

        await self.db.commit()
        await self.db.refresh(auth)
        return auth

    async def expire_old_authorizations(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(TransactionAuthorization)
            .where(
                TransactionAuthorization.status == AuthorizationStatus.PENDING,
                TransactionAuthorization.expires_at < now,
            )
            .values(status=AuthorizationStatus.EXPIRED)
        )
        await self.db.commit()
        return result.rowcount
