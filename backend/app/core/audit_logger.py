"""
Structured audit logger for critical events.
Logs safe metadata without exposing tokens, full payloads, or sensitive user data.
"""
from app.core.logging import logger
from typing import Optional


def log_charge_created(user_id: int, charge_id: int, provider: str, amount: Optional[str] = None):
    logger.info(
        f"AUDIT charge_created user_id={user_id} charge_id={charge_id} provider={provider}"
        + (f" amount={amount}" if amount else "")
    )


def log_pending_action_confirmed(user_id: int, pending_action_id: int, action_type: str):
    logger.info(
        f"AUDIT pending_action_confirmed user_id={user_id} pending_action_id={pending_action_id} action_type={action_type}"
    )


def log_webhook_received(provider: str, event_type: str, external_id: Optional[str] = None):
    logger.info(
        f"AUDIT webhook_received provider={provider} event_type={event_type}"
        + (f" external_id={external_id}" if external_id else "")
    )


def log_payment_confirmed(user_id: int, charge_id: int, provider: str):
    logger.info(
        f"AUDIT payment_confirmed user_id={user_id} charge_id={charge_id} provider={provider}"
    )


def log_provider_failure(provider: str, charge_id: Optional[int], error: str):
    logger.error(
        f"AUDIT provider_failure provider={provider}"
        + (f" charge_id={charge_id}" if charge_id else "")
        + f" error={error}"
    )


def log_export(user_id: int, format: str, status_filter: Optional[str] = None, count: Optional[int] = None):
    logger.info(
        f"AUDIT export user_id={user_id} format={format}"
        + (f" status={status_filter}" if status_filter else "")
        + (f" count={count}" if count is not None else "")
    )


def log_demo_login(user_id: int, email: str):
    logger.info(f"AUDIT demo_login user_id={user_id} email={email}")


def log_demo_reset(user_id: int, charges_created: int, transactions_created: int):
    logger.info(
        f"AUDIT demo_reset user_id={user_id} charges_created={charges_created} transactions_created={transactions_created}"
    )


def log_reminder_job(run_count: int, reminders_sent: int):
    logger.info(f"AUDIT reminder_job run_count={run_count} reminders_sent={reminders_sent}")


def log_rate_limit_hit(user_id: Optional[int], endpoint: str, limit: int):
    logger.warning(
        f"AUDIT rate_limit_hit endpoint={endpoint} limit={limit}"
        + (f" user_id={user_id}" if user_id else "")
    )
