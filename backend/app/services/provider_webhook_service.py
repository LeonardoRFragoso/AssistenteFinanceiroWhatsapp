"""
Provider webhook service — Sprint 14.

Records webhook events with sanitization and idempotency.
Never executes real operations.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_foundation import (
    ProviderWebhookEvent, WebhookEventStatus,
)
from app.services.organization_audit_service import OrganizationAuditService

logger = logging.getLogger(__name__)

_SENSITIVE_HEADER_KEYS = {
    "authorization", "token", "secret", "key", "password",
    "api_key", "apikey", "x-api-key", "x-auth-token",
}

_SENSITIVE_PAYLOAD_KEYS = {
    "password", "secret", "token", "api_key", "apikey",
    "access_token", "refresh_token", "client_secret",
    "code", "authorization", "credential",
}


class ProviderWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)

    @staticmethod
    def sanitize_payload(payload: dict | None) -> dict | None:
        if not payload:
            return payload
        sanitized = {}
        for key, value in payload.items():
            key_lower = key.lower()
            if any(s in key_lower for s in _SENSITIVE_PAYLOAD_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = ProviderWebhookService.sanitize_payload(value)
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def sanitize_headers(headers: dict | None) -> dict | None:
        if not headers:
            return headers
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(s in key_lower for s in _SENSITIVE_HEADER_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    async def is_duplicate(
        self, provider_type: str, provider_name: str, provider_event_id: str
    ) -> Optional[ProviderWebhookEvent]:
        result = await self.db.execute(
            select(ProviderWebhookEvent).where(
                ProviderWebhookEvent.provider_type == provider_type,
                ProviderWebhookEvent.provider_name == provider_name,
                ProviderWebhookEvent.provider_event_id == provider_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def record_event(
        self,
        organization_id: int,
        provider_type: str,
        provider_name: str,
        event_type: str,
        provider_event_id: str,
        payload: dict | None = None,
        headers: dict | None = None,
        idempotency_key: str | None = None,
    ) -> ProviderWebhookEvent:
        existing = await self.is_duplicate(provider_type, provider_name, provider_event_id)
        if existing:
            existing.status = WebhookEventStatus.DUPLICATE
            await self.db.commit()
            return existing

        event = ProviderWebhookEvent(
            organization_id=organization_id,
            provider_type=provider_type,
            provider_name=provider_name,
            event_type=event_type,
            provider_event_id=provider_event_id,
            idempotency_key=idempotency_key,
            status=WebhookEventStatus.RECEIVED,
            payload=self.sanitize_payload(payload),
            headers_sanitized=self.sanitize_headers(headers),
        )
        self.db.add(event)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="webhook_received",
            resource_type="provider_webhook_event",
            resource_id=str(event.id),
            provider_type=provider_type,
            metadata={"event_type": event_type, "provider_name": provider_name},
        )

        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def mark_processed(self, event_id: int) -> Optional[ProviderWebhookEvent]:
        result = await self.db.execute(
            select(ProviderWebhookEvent).where(ProviderWebhookEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return None
        event.status = WebhookEventStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def mark_failed(self, event_id: int, error_message: str) -> Optional[ProviderWebhookEvent]:
        result = await self.db.execute(
            select(ProviderWebhookEvent).where(ProviderWebhookEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return None
        event.status = WebhookEventStatus.FAILED
        event.error_message = error_message
        event.processed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event
