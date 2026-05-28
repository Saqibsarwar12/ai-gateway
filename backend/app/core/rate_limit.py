"""Rate limiting using Redis sliding window."""
import time
from app.db.session import get_redis


async def check_rate_limit(user_id: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    Sliding window rate limit using Redis ZSET.
    """
    redis = await get_redis()
    key = f"rl:{user_id}"
    now = time.time()
    window_start = now - window

    # Remove old entries
    await redis.zremrangebyscore(key, 0, window_start)

    # Count current
    count = await redis.zcard(key)

    if count >= limit:
        ttl = await redis.ttl(key)
        return False, 0

    # Add this request
    await redis.zadd(key, {str(now): now})
    await redis.expire(key, window)

    remaining = limit - count - 1
    return True, remaining
