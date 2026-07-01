#!/usr/bin/env python
"""
Simple scheduler for charge reminders in development.

Controlled by environment variables:
  ENABLE_CHARGE_REMINDER_WORKER=true   — enable the scheduler
  CHARGE_REMINDER_INTERVAL_MINUTES=60  — interval between runs

Usage:
  python -m app.jobs.reminder_scheduler

Or run as a background process alongside the API server.
"""
import time
import asyncio
import threading

from app.core.config import settings
from app.core.logging import logger


class ReminderScheduler:
    """Lightweight loop that periodically enqueues the charge reminders job."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self):
        if not settings.ENABLE_CHARGE_REMINDER_WORKER:
            logger.info("Charge reminder worker is disabled (ENABLE_CHARGE_REMINDER_WORKER=false)")
            return

        self._thread = threading.Thread(target=self._loop, daemon=True, name="reminder-scheduler")
        self._thread.start()
        logger.info(
            f"Reminder scheduler started (interval={settings.CHARGE_REMINDER_INTERVAL_MINUTES}min)"
        )

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Reminder scheduler stopped")

    def _loop(self):
        interval = max(settings.CHARGE_REMINDER_INTERVAL_MINUTES * 60, 60)
        while not self._stop_event.is_set():
            try:
                from app.core.queue import enqueue_charge_reminders
                enqueue_charge_reminders()
            except Exception as e:
                logger.error(f"Reminder scheduler error: {str(e)}")
            self._stop_event.wait(timeout=interval)


scheduler = ReminderScheduler()


if __name__ == "__main__":
    import signal
    import sys

    if not settings.ENABLE_CHARGE_REMINDER_WORKER:
        logger.info("ENABLE_CHARGE_REMINDER_WORKER is not set — enabling for CLI run")
        settings.ENABLE_CHARGE_REMINDER_WORKER = True

    scheduler.start()

    def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM, stopping scheduler...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    logger.info(
        f"Reminder scheduler running in foreground "
        f"(interval={settings.CHARGE_REMINDER_INTERVAL_MINUTES}min). "
        f"Press Ctrl+C to stop."
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
