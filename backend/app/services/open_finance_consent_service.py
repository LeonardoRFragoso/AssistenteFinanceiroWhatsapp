"""
Open Finance consent service — Sprint 14.

Creates fake consents only. Real consent requires feature flag + real provider.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.provider_foundation import (
    OpenFinanceConsent, ConsentStatus,
)
from app.services.organization_audit_service import OrganizationAuditService

logger = logging.getLogger(__name__)


class OpenFinanceConsentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)

    async def create_fake_consent(
        self,
        organization_id: int,
        user_id: int,
        scopes: list[str] | None = None,
        institution_name: str = "Fake Bank",
        institution_code: str | None = None,
    ) -> OpenFinanceConsent:
        if not settings.ENABLE_DEMO_MODE and settings.ENVIRONMENT == "production":
            if not settings.ENABLE_OPEN_FINANCE:
                raise ValueError(
                    "Open Finance consent requires ENABLE_OPEN_FINANCE=true or demo mode"
                )

        consent_id = f"fake_consent_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        consent = OpenFinanceConsent(
            organization_id=organization_id,
            user_id=user_id,
            provider_name="fake",
            external_consent_id=consent_id,
            status=ConsentStatus.AUTHORIZED,
            scopes=scopes or ["accounts", "transactions"],
            institution_name=institution_name,
            institution_code=institution_code,
            authorization_url=f"https://fake.openfinance.payflow.ai/authorize/{consent_id}",
            expires_at=now + timedelta(days=365),
        )
        self.db.add(consent)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="consent_created",
            actor_user_id=user_id,
            resource_type="open_finance_consent",
            resource_id=str(consent.id),
            provider_type="open_finance",
            metadata={
                "institution_name": institution_name,
                "provider_name": "fake",
                "scopes": scopes or ["accounts", "transactions"],
            },
        )

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def list_consents(self, organization_id: int) -> list[OpenFinanceConsent]:
        result = await self.db.execute(
            select(OpenFinanceConsent).where(
                OpenFinanceConsent.organization_id == organization_id
            ).order_by(OpenFinanceConsent.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_consent(
        self, organization_id: int, consent_id: int, user_id: int
    ) -> Optional[OpenFinanceConsent]:
        result = await self.db.execute(
            select(OpenFinanceConsent).where(
                OpenFinanceConsent.id == consent_id,
                OpenFinanceConsent.organization_id == organization_id,
            )
        )
        consent = result.scalar_one_or_none()
        if not consent:
            return None

        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="consent_revoked",
            actor_user_id=user_id,
            resource_type="open_finance_consent",
            resource_id=str(consent.id),
            provider_type="open_finance",
            metadata={"institution_name": consent.institution_name},
        )

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def expire_old_consents(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(OpenFinanceConsent)
            .where(
                OpenFinanceConsent.status == ConsentStatus.AUTHORIZED,
                OpenFinanceConsent.expires_at < now,
            )
            .values(status=ConsentStatus.EXPIRED)
        )
        await self.db.commit()
        return result.rowcount
