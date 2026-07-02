"""Job for executing due recurring tasks.

This job only sends reminders/messages. It NEVER executes payments
or bank operations.
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.recurring_task_service import RecurringTaskService
from app.core.logging import logger


async def run_recurring_tasks_async():
    """Find and execute all due recurring tasks."""
    async with AsyncSessionLocal() as db:
        service = RecurringTaskService(db)
        due_tasks = await service.get_due_tasks()

        if not due_tasks:
            logger.info("No due recurring tasks found")
            return 0

        logger.info(f"Found {len(due_tasks)} due recurring tasks")

        executed = 0
        for task in due_tasks:
            try:
                log = await service.execute_task(task)
                executed += 1
                logger.info(
                    f"Recurring task {task.id} executed: success={log.success}"
                )
            except Exception as e:
                logger.error(f"Error executing recurring task {task.id}: {str(e)}")

        return executed


def run_recurring_tasks():
    """Sync wrapper for the async recurring task job."""
    return asyncio.run(run_recurring_tasks_async())
