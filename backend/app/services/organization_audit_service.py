"""
Organization audit service — Sprint 14.

Logs sensitive actions with sanitized metadata and hashed IP/user-agent.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_foundation import OrganizationAuditLog

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "apikey",
    "access_token", "refresh_token", "client_secret",
    "code", "authorization", "credential",
}


class OrganizationAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def sanitize_metadata(metadata: dict | None) -> dict | None:
        if not metadata:
            return metadata
        sanitized = {}
        for key, value in metadata.items():
            key_lower = key.lower()
            if any(s in key_lower for s in _SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def hash_value(value: str | None) -> str | None:
        if not value:
            return None
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    async def log_event(
        self,
        organization_id: int,
        action: str,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        provider_type: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> OrganizationAuditLog:
        log = OrganizationAuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            provider_type=provider_type,
            ip_hash=self.hash_value(ip_address),
            user_agent_hash=self.hash_value(user_agent),
            extra_data=self.sanitize_metadata(metadata),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_logs(
        self,
        organization_id: int,
        action: str | None = None,
        resource_type: str | None = None,
        provider_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrganizationAuditLog], int]:
        query = select(OrganizationAuditLog).where(
            OrganizationAuditLog.organization_id == organization_id
        )
        count_query = select(func.count()).select_from(OrganizationAuditLog).where(
            OrganizationAuditLog.organization_id == organization_id
        )

        if action:
            query = query.where(OrganizationAuditLog.action == action)
            count_query = count_query.where(OrganizationAuditLog.action == action)
        if resource_type:
            query = query.where(OrganizationAuditLog.resource_type == resource_type)
            count_query = count_query.where(OrganizationAuditLog.resource_type == resource_type)
        if provider_type:
            query = query.where(OrganizationAuditLog.provider_type == provider_type)
            count_query = count_query.where(OrganizationAuditLog.provider_type == provider_type)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(OrganizationAuditLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total
