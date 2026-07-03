"""
Provider connection service — Sprint 14.

Manages provider connections with feature flag validation.
All providers default to fake/sandbox. Real providers are blocked.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.provider_foundation import (
    ProviderConnection, ProviderConnectionStatus,
)
from app.services.organization_audit_service import OrganizationAuditService

logger = logging.getLogger(__name__)

_VALID_PROVIDER_TYPES = {
    "open_finance", "banking", "bill_payment", "pix",
    "kyc", "fraud", "dda", "receipt", "consent",
}

_FLAG_MAP = {
    "open_finance": "ENABLE_OPEN_FINANCE",
    "banking": "ENABLE_REAL_BANKING",
    "bill_payment": "ENABLE_BILL_PAYMENT",
    "pix": "ENABLE_PIX_OUT",
    "kyc": "ENABLE_KYC",
    "dda": "ENABLE_DDA",
}

_NAME_MAP = {
    "open_finance": "OPEN_FINANCE_PROVIDER",
    "banking": "BANKING_PROVIDER_NAME",
    "bill_payment": "BILL_PAYMENT_PROVIDER_NAME",
    "pix": "PIX_PROVIDER_NAME",
    "kyc": "KYC_PROVIDER_NAME",
    "fraud": "FRAUD_PROVIDER_NAME",
    "dda": "DDA_PROVIDER_NAME",
    "receipt": "RECEIPT_PROVIDER_NAME",
    "consent": "CONSENT_PROVIDER_NAME",
}


class ProviderConnectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)

    def validate_provider_activation(self, provider_type: str, provider_name: str) -> None:
        """Validate that a provider can be activated. Raises ValueError if not allowed."""
        if provider_type not in _VALID_PROVIDER_TYPES:
            raise ValueError(f"Invalid provider type: {provider_type}")

        if settings.ENABLE_DEMO_MODE:
            if provider_name != "fake":
                raise ValueError("Demo mode forces fake providers only")
            return

        if provider_name == "fake":
            return

        flag_name = _FLAG_MAP.get(provider_type)
        if flag_name:
            flag_enabled = getattr(settings, flag_name, False)
            if not flag_enabled:
                raise ValueError(
                    f"Provider '{provider_name}' for '{provider_type}' requires "
                    f"feature flag '{flag_name}' to be enabled"
                )

        if settings.ENVIRONMENT == "production":
            raise ValueError(
                f"Real {provider_type} provider '{provider_name}' is not yet implemented. "
                f"Use fake provider or implement the integration first."
            )

    async def list_connections(self, organization_id: int) -> list[ProviderConnection]:
        result = await self.db.execute(
            select(ProviderConnection).where(
                ProviderConnection.organization_id == organization_id
            ).order_by(ProviderConnection.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_connection(
        self,
        organization_id: int,
        user_id: int,
        provider_type: str,
        provider_name: str = "fake",
        display_name: str | None = None,
        institution_name: str | None = None,
        institution_code: str | None = None,
        scopes: list | None = None,
        metadata: dict | None = None,
    ) -> ProviderConnection:
        self.validate_provider_activation(provider_type, provider_name)

        connection = ProviderConnection(
            organization_id=organization_id,
            provider_type=provider_type,
            provider_name=provider_name,
            status=ProviderConnectionStatus.ACTIVE,
            environment="sandbox" if provider_name == "fake" else "production",
            display_name=display_name,
            institution_name=institution_name,
            institution_code=institution_code,
            scopes=scopes,
            extra_data=metadata,
            created_by_user_id=user_id,
            active=True,
        )
        self.db.add(connection)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="provider_connection_created",
            actor_user_id=user_id,
            resource_type="provider_connection",
            resource_id=str(connection.id),
            provider_type=provider_type,
            metadata={"provider_name": provider_name, "environment": connection.environment},
        )

        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def get_connection(self, organization_id: int, connection_id: int) -> Optional[ProviderConnection]:
        result = await self.db.execute(
            select(ProviderConnection).where(
                ProviderConnection.id == connection_id,
                ProviderConnection.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_connection(self, organization_id: int, provider_type: str) -> Optional[ProviderConnection]:
        result = await self.db.execute(
            select(ProviderConnection).where(
                ProviderConnection.organization_id == organization_id,
                ProviderConnection.provider_type == provider_type,
                ProviderConnection.active == True,
                ProviderConnection.status == ProviderConnectionStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def deactivate_connection(
        self, organization_id: int, connection_id: int, user_id: int
    ) -> Optional[ProviderConnection]:
        conn = await self.get_connection(organization_id, connection_id)
        if not conn:
            return None

        conn.active = False
        conn.status = ProviderConnectionStatus.INACTIVE
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="provider_connection_deactivated",
            actor_user_id=user_id,
            resource_type="provider_connection",
            resource_id=str(conn.id),
            provider_type=conn.provider_type,
            metadata={"provider_name": conn.provider_name},
        )

        await self.db.commit()
        await self.db.refresh(conn)
        return conn
