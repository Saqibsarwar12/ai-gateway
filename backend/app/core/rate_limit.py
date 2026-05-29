"""Rate limiting using Redis sliding window."""
import time


async def check_rate_limit(key: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """Returns (allowed, remaining)."""
    from app.db.session import redis_client
    r = redis_client
    now = time.time()
    window_key = f"rl:{key}:{int(now / window)}"

    pipe = r.pipeline()
    pipe.zadd(window_key, {str(now): now})
    pipe.zremrangebyscore(window_key, 0, now - window)
    pipe.zcard(window_key)
    pipe.expire(window_key, window + 1)
    results = await pipe.execute()
    count = results[2]

    if count > limit:
        return False, 0
    return True, max(0, limit - count)
