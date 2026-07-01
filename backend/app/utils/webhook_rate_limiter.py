"""
Rate limiter for webhook endpoints (Twilio, Mercado Pago, fake).
Uses IP-based limiting with per-provider keys.
"""
from fastapi import HTTPException, status, Request
from typing import Dict, List
import time
from collections import defaultdict
from app.core.logging import logger
from app.core.config import settings


class WebhookRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._memory: Dict[str, List[float]] = defaultdict(list)

    async def check(self, request: Request, provider: str = "generic"):
        if settings.ENVIRONMENT in ("testing", "test"):
            return

        client_ip = request.client.host if request.client else "unknown"
        key = f"webhook_rl:{provider}:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds
        self._memory[key] = [t for t in self._memory[key] if t > window_start]

        if len(self._memory[key]) >= self.limit:
            logger.warning(f"Webhook rate limit exceeded provider={provider} ip={client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Webhook rate limit exceeded."
            )

        self._memory[key].append(now)


webhook_rate_limiter = WebhookRateLimiter(
    limit=settings.WEBHOOK_RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)
