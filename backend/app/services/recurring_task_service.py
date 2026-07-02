from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.models.recurring_task import RecurringTask, RecurringTaskLog, RecurrenceType
from app.schemas.recurring_task import RecurringTaskCreate
from app.core.logging import logger


class RecurringTaskService:
    """Service for managing recurring non-transactional tasks.

    These tasks only send reminders/messages. They NEVER execute payments
    or bank operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, user_id: int, data: RecurringTaskCreate, organization_id: Optional[int] = None) -> RecurringTask:
        next_run = self._calculate_next_run(
            data.recurrence_type,
            data.day_of_week,
            data.day_of_month,
        )

        task = RecurringTask(
            user_id=user_id,
            organization_id=organization_id,
            title=data.title,
            description=data.description,
            recurrence_type=data.recurrence_type,
            day_of_week=data.day_of_week,
            day_of_month=data.day_of_month,
            next_run_at=next_run,
            active=True,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        logger.info(f"Recurring task {task.id} created for user {user_id}")
        return task

    async def get_user_tasks(self, user_id: int, organization_id: Optional[int] = None) -> List[RecurringTask]:
        query = select(RecurringTask).where(RecurringTask.user_id == user_id)
        if organization_id is not None:
            query = query.where(RecurringTask.organization_id == organization_id)
        result = await self.db.execute(
            query.order_by(RecurringTask.next_run_at)
        )
        return list(result.scalars().all())

    async def cancel_task(self, task_id: int, user_id: int, organization_id: Optional[int] = None) -> Optional[RecurringTask]:
        query = select(RecurringTask).where(
            and_(
                RecurringTask.id == task_id,
                RecurringTask.user_id == user_id,
            )
        )
        if organization_id is not None:
            query = query.where(RecurringTask.organization_id == organization_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            return None
        task.active = False
        await self.db.commit()
        await self.db.refresh(task)
        logger.info(f"Recurring task {task_id} cancelled by user {user_id}")
        return task

    async def get_due_tasks(self) -> List[RecurringTask]:
        """Get all active tasks that are due (next_run_at <= now)."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RecurringTask).where(
                and_(
                    RecurringTask.active == True,
                    RecurringTask.next_run_at <= now,
                )
            )
        )
        return list(result.scalars().all())

    async def execute_task(self, task: RecurringTask) -> RecurringTaskLog:
        """Execute a recurring task by sending a reminder and updating next_run_at.

        This only sends a message/reminder. It NEVER executes payments.
        """
        now = datetime.now(timezone.utc)

        message_sent = None
        success = True
        error = None

        try:
            from app.repositories.user_repository import UserRepository
            from app.integrations.twilio_whatsapp import TwilioWhatsAppService

            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(task.user_id)

            if user and user.phone_number:
                twilio = TwilioWhatsAppService()
                message = f"🔔 *Lembrete recorrente:*\n\n{task.title}"
                if task.description:
                    message += f"\n{task.description}"
                await twilio.send_message(user.phone_number, message)
                message_sent = message
            else:
                message_sent = f"[No phone number] {task.title}"
                logger.warning(f"User {task.user_id} has no phone number for recurring task {task.id}")
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Error executing recurring task {task.id}: {str(e)}")

        # Update next_run_at
        task.next_run_at = self._calculate_next_run(
            task.recurrence_type,
            task.day_of_week,
            task.day_of_month,
            from_date=now,
        )
        await self.db.commit()
        await self.db.refresh(task)

        # Log execution
        log = RecurringTaskLog(
            task_id=task.id,
            executed_at=now,
            success=success,
            message_sent=message_sent,
            error=error,
        )
        self.db.add(log)
        await self.db.commit()

        logger.info(f"Recurring task {task.id} executed, next_run_at={task.next_run_at}")
        return log

    def _calculate_next_run(
        self,
        recurrence_type: RecurrenceType,
        day_of_week: Optional[int],
        day_of_month: Optional[int],
        from_date: Optional[datetime] = None,
    ) -> datetime:
        """Calculate the next run time based on recurrence type."""
        now = from_date or datetime.now(timezone.utc)

        if recurrence_type == RecurrenceType.DAILY:
            return now + timedelta(days=1)

        elif recurrence_type == RecurrenceType.WEEKLY:
            target_day = day_of_week if day_of_week is not None else 0
            days_ahead = (target_day - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return now + timedelta(days=days_ahead)

        elif recurrence_type == RecurrenceType.MONTHLY:
            target_day = day_of_month if day_of_month is not None else 1
            # Calculate next month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=min(target_day, 28))
            else:
                next_month = now.replace(month=now.month + 1, day=min(target_day, 28))
            return next_month

        return now + timedelta(days=1)
