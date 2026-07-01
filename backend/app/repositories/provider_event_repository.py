from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timezone
from app.models.provider_event import ProviderEvent


class ProviderEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        provider: str,
        event_type: str,
        payload: dict,
        external_id: Optional[str] = None
    ) -> ProviderEvent:
        event = ProviderEvent(
            provider=provider,
            event_type=event_type,
            external_id=external_id,
            payload=payload,
            processed=False
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id: int) -> Optional[ProviderEvent]:
        result = await self.db.execute(
            select(ProviderEvent).where(ProviderEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str, provider: Optional[str] = None) -> List[ProviderEvent]:
        query = select(ProviderEvent).where(ProviderEvent.external_id == external_id)
        if provider:
            query = query.where(ProviderEvent.provider == provider)
        query = query.order_by(desc(ProviderEvent.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unprocessed(self, limit: int = 100) -> List[ProviderEvent]:
        result = await self.db.execute(
            select(ProviderEvent)
            .where(ProviderEvent.processed == False)
            .order_by(desc(ProviderEvent.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(self, event_id: int) -> Optional[ProviderEvent]:
        event = await self.get_by_id(event_id)
        if not event:
            return None
        event.processed = True
        event.processed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event
