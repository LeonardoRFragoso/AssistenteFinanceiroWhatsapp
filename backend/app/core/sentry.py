"""
Optional Sentry integration. Only initializes if SENTRY_DSN is set.
Does not send sensitive data (tokens, full webhook payloads, phone numbers, messages).
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from app.core.config import settings
from app.core.logging import logger


def init_sentry():
    """Initialize Sentry SDK if SENTRY_DSN is configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not configured — skipping Sentry initialization")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            RedisIntegration(),
        ],
        before_send=_sanitize_event,
    )
    logger.info(f"Sentry initialized (environment={settings.SENTRY_ENVIRONMENT})")


def _sanitize_event(event, hint):
    """Strip sensitive data from Sentry events before sending."""
    if not event:
        return event

    # Remove sensitive keys from extra/context
    sensitive_keys = {"token", "password", "secret", "api_key", "access_token", "auth_token"}

    if "extra" in event:
        for key in list(event["extra"].keys()):
            if any(s in key.lower() for s in sensitive_keys):
                event["extra"][key] = "***REDACTED***"

    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        for key in list(headers.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                headers[key] = "***REDACTED***"

    return event
