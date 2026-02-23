import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import logger
from typing import Optional

redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    return redis_client


async def init_redis():
    global redis_client
    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not configured. Redis features will be disabled.")
        return
    
    try:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Redis features will be disabled.")
        redis_client = None


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
