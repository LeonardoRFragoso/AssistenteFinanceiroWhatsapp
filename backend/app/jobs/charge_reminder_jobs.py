"""
Background job for charge reminders.

Can be enqueued via RQ or called directly from CLI / scheduler.
"""
from app.core.logging import logger


def run_charge_reminders_job() -> dict:
    """Synchronous wrapper for ChargeReminderService.run_reminders().

    Designed to be called by RQ worker or CLI. Creates its own async
    database session, runs reminders, and returns a summary dict.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.services.charge_reminder_service import ChargeReminderService

    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            service = ChargeReminderService(db)
            result = await service.run_reminders()
            await db.commit()
            return result

    try:
        logger.info("Starting charge reminders job")
        result = asyncio.run(_run())
        logger.info(f"Charge reminders job completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Charge reminders job failed: {str(e)}", exc_info=True)
        return {
            "sent_due_soon": 0,
            "sent_overdue": 0,
            "skipped": 0,
            "errors": 1,
            "total_processed": 1,
            "error": str(e)
        }
