"""
Redis client singletons.

Sync client  — for use inside synchronous code or thread-pool callbacks
               (fly_service.py, error_resolver.py).
Async client — for use in async FastAPI handlers, WebSocket loops,
               and Inngest functions.

Both clients connect to REDIS_URL (default: redis://localhost:6379).
If Redis is unavailable, operations degrade gracefully rather than crashing.
"""
import os
import redis
import redis.asyncio as aioredis

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

_sync_client: redis.Redis | None = None
_async_client: aioredis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    return _sync_client


def get_async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    return _async_client
