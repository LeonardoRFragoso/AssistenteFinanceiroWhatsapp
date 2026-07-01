from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timezone
from app.models.pending_action import PendingAction, PendingActionStatus


class PendingActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        action_type: str,
        payload: dict,
        expires_at: datetime
    ) -> PendingAction:
        action = PendingAction(
            user_id=user_id,
            action_type=action_type,
            payload=payload,
            expires_at=expires_at,
            status=PendingActionStatus.PENDING
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def get_by_id(self, action_id: int, user_id: Optional[int] = None) -> Optional[PendingAction]:
        query = select(PendingAction).where(PendingAction.id == action_id)
        if user_id is not None:
            query = query.where(PendingAction.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_pending_by_user(self, user_id: int, action_type: Optional[str] = None) -> Optional[PendingAction]:
        query = select(PendingAction).where(
            PendingAction.user_id == user_id,
            PendingAction.status == PendingActionStatus.PENDING
        )
        if action_type:
            query = query.where(PendingAction.action_type == action_type)
        query = query.order_by(desc(PendingAction.created_at)).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, limit: int = 50) -> List[PendingAction]:
        result = await self.db.execute(
            select(PendingAction)
            .where(PendingAction.user_id == user_id)
            .order_by(desc(PendingAction.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def confirm(self, action_id: int) -> Optional[PendingAction]:
        action = await self.get_by_id(action_id)
        if not action or action.status != PendingActionStatus.PENDING:
            return None
        action.status = PendingActionStatus.CONFIRMED
        action.confirmed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def cancel(self, action_id: int) -> Optional[PendingAction]:
        action = await self.get_by_id(action_id)
        if not action or action.status != PendingActionStatus.PENDING:
            return None
        action.status = PendingActionStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def mark_executed(self, action_id: int) -> Optional[PendingAction]:
        action = await self.get_by_id(action_id)
        if not action:
            return None
        action.status = PendingActionStatus.EXECUTED
        action.executed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def mark_failed(self, action_id: int) -> Optional[PendingAction]:
        action = await self.get_by_id(action_id)
        if not action:
            return None
        action.status = PendingActionStatus.FAILED
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def expire_old_actions(self, before: datetime) -> int:
        result = await self.db.execute(
            select(PendingAction).where(
                PendingAction.status == PendingActionStatus.PENDING,
                PendingAction.expires_at < before
            )
        )
        expired = list(result.scalars().all())
        for action in expired:
            action.status = PendingActionStatus.EXPIRED
        await self.db.commit()
        return len(expired)
