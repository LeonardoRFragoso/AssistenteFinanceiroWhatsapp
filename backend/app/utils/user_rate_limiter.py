"""
User-based rate limiter for authenticated endpoints.
Uses Redis when available, falls back to in-memory in development/test.
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, List
import time
from collections import defaultdict
from app.core.logging import logger
from app.core.config import settings
from app.core.redis import get_redis


class UserRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60, key_prefix: str = "user_rl"):
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._memory: Dict[str, List[float]] = defaultdict(list)

    async def check(self, user_id: int, endpoint: str = ""):
        if not settings.USER_RATE_LIMIT_ENABLED:
            return

        if settings.ENVIRONMENT in ("development", "testing", "dev", "test") and not settings.REDIS_URL:
            self._check_memory(user_id, endpoint)
            return

        await self._check_redis(user_id, endpoint)

    def _check_memory(self, user_id: int, endpoint: str):
        key = f"{self.key_prefix}:{user_id}:{endpoint}"
        now = time.time()
        window_start = now - self.window_seconds
        self._memory[key] = [t for t in self._memory[key] if t > window_start]

        if len(self._memory[key]) >= self.limit:
            logger.warning(f"Rate limit exceeded for user_id={user_id} endpoint={endpoint} limit={self.limit}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.limit} requests per {self.window_seconds}s."
            )

        self._memory[key].append(now)

    async def _check_redis(self, user_id: int, endpoint: str):
        redis = await get_redis()
        if redis is None:
            self._check_memory(user_id, endpoint)
            return

        key = f"{self.key_prefix}:{user_id}:{endpoint}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self.window_seconds)

            if count > self.limit:
                logger.warning(f"Rate limit exceeded for user_id={user_id} endpoint={endpoint} limit={self.limit}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.limit} requests per {self.window_seconds}s."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Redis rate limit error: {e} — falling back to memory")
            self._check_memory(user_id, endpoint)


# Pre-configured limiters
charges_limiter = UserRateLimiter(
    limit=settings.USER_RATE_LIMIT_CHARGES_PER_MINUTE,
    window_seconds=60,
    key_prefix="user_rl_charges",
)

exports_limiter = UserRateLimiter(
    limit=settings.USER_RATE_LIMIT_EXPORTS_PER_MINUTE,
    window_seconds=60,
    key_prefix="user_rl_exports",
)

demo_reset_limiter = UserRateLimiter(
    limit=settings.USER_RATE_LIMIT_DEMO_RESET_PER_HOUR,
    window_seconds=3600,
    key_prefix="user_rl_demo_reset",
)
