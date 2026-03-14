"""
Shared mutable state backed by Redis — safe across multiple Gunicorn worker processes.

Three categories:
  1. Cancelled mockup IDs      (design_api — async)
  2. Auto-fix loop state       (error_resolver — sync)
  3. Fly sandbox metadata      (fly_service — sync, Inngest — async)
  4. Project/sandbox pub-sub   (WebSocket fanout — async)

Sync helpers use get_sync_redis() and are safe to call from threads.
Async helpers use get_async_redis() and must be awaited.
"""
from __future__ import annotations

import json
from redis_client import get_sync_redis, get_async_redis

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Cancelled mockup IDs (used in async design_api functions)
# ─────────────────────────────────────────────────────────────────────────────
_KEY_CANCELLED = "kith:cancelled_mockups"


async def add_cancelled_mockup(mockup_id: str, ttl: int = 3600) -> None:
    r = get_async_redis()
    await r.sadd(_KEY_CANCELLED, mockup_id)
    await r.expire(_KEY_CANCELLED, ttl)


async def is_mockup_cancelled(mockup_id: str) -> bool:
    r = get_async_redis()
    return bool(await r.sismember(_KEY_CANCELLED, mockup_id))


async def discard_cancelled_mockup(mockup_id: str) -> None:
    r = get_async_redis()
    await r.srem(_KEY_CANCELLED, mockup_id)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Auto-fix loop state (used in sync error_resolver)
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_FIX_STATE = {
    "attempt_count": 0,
    "last_attempt_at": 0.0,
    "last_error_hash": None,
    "cycle_start": 0.0,
}


def _fix_key(project_id: str) -> str:
    return f"kith:fix:{project_id}"


def get_fix_state(project_id: str) -> dict:
    r = get_sync_redis()
    raw = r.get(_fix_key(project_id))
    return json.loads(raw) if raw else dict(_DEFAULT_FIX_STATE)


def save_fix_state(project_id: str, state: dict) -> None:
    r = get_sync_redis()
    r.set(_fix_key(project_id), json.dumps(state), ex=86400)


def delete_fix_state(project_id: str) -> None:
    r = get_sync_redis()
    r.delete(_fix_key(project_id))


# ─────────────────────────────────────────────────────────────────────────────
# 3a.  Sandbox metadata — sync (fly_service)
# ─────────────────────────────────────────────────────────────────────────────
def _sandbox_key(project_id: str) -> str:
    return f"kith:sandbox:{project_id}"


def get_sandbox_meta_sync(project_id: str) -> dict | None:
    r = get_sync_redis()
    raw = r.get(_sandbox_key(project_id))
    return json.loads(raw) if raw else None


def set_sandbox_meta_sync(project_id: str, meta: dict, ttl: int = 86400) -> None:
    r = get_sync_redis()
    r.set(_sandbox_key(project_id), json.dumps(meta), ex=ttl)


def delete_sandbox_meta_sync(project_id: str) -> None:
    r = get_sync_redis()
    r.delete(_sandbox_key(project_id))


def list_sandbox_app_names_sync() -> set[str]:
    """Return app_names of all sandboxes tracked in Redis."""
    r = get_sync_redis()
    keys = r.keys("kith:sandbox:*")
    if not keys:
        return set()
    names: set[str] = set()
    for raw in r.mget(*keys):
        if raw:
            meta = json.loads(raw)
            if meta.get("app_name"):
                names.add(meta["app_name"])
    return names


# ─────────────────────────────────────────────────────────────────────────────
# 3b.  Sandbox metadata — async (Inngest functions, main.py)
# ─────────────────────────────────────────────────────────────────────────────
async def get_sandbox_meta_async(project_id: str) -> dict | None:
    r = get_async_redis()
    raw = await r.get(_sandbox_key(project_id))
    return json.loads(raw) if raw else None


async def set_sandbox_meta_async(project_id: str, meta: dict, ttl: int = 86400) -> None:
    r = get_async_redis()
    await r.set(_sandbox_key(project_id), json.dumps(meta), ex=ttl)


async def delete_sandbox_meta_async(project_id: str) -> None:
    r = get_async_redis()
    await r.delete(_sandbox_key(project_id))


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Pub/sub channels (async WebSocket fanout)
# ─────────────────────────────────────────────────────────────────────────────
def project_channel(project_id: str) -> str:
    return f"kith:project:{project_id}:updates"


def sandbox_events_channel(project_id: str) -> str:
    return f"kith:sandbox:{project_id}:events"


async def publish_project_update(project_id: str, payload: dict) -> None:
    r = get_async_redis()
    await r.publish(project_channel(project_id), json.dumps(payload))


async def publish_sandbox_event(project_id: str, payload: dict) -> None:
    r = get_async_redis()
    await r.publish(sandbox_events_channel(project_id), json.dumps(payload))


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Generic cache helpers  (async)
# ─────────────────────────────────────────────────────────────────────────────

async def cache_get(key: str) -> str | None:
    """Return cached string value or None if missing/expired."""
    r = get_async_redis()
    raw = await r.get(key)
    return raw.decode() if isinstance(raw, bytes) else raw


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    """Store a string value with TTL (seconds). Default 5 min."""
    r = get_async_redis()
    await r.set(key, value, ex=ttl)


async def cache_get_json(key: str) -> dict | list | None:
    """Return a deserialized JSON value or None."""
    raw = await cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def cache_set_json(key: str, value: dict | list, ttl: int = 300) -> None:
    """Serialize *value* as JSON and store with TTL."""
    await cache_set(key, json.dumps(value), ttl=ttl)


async def cache_invalidate(key: str) -> None:
    """Delete a single cache key."""
    r = get_async_redis()
    await r.delete(key)


async def cache_invalidate_prefix(prefix: str) -> None:
    """Delete all keys matching *prefix* + '*'. Use sparingly (SCAN, not KEYS)."""
    r = get_async_redis()
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor, match=f"{prefix}*", count=100)
        if keys:
            await r.delete(*keys)
        if cursor == 0:
            break


# ─────────────────────────────────────────────────────────────────────────────
# Typed domain helpers
# ─────────────────────────────────────────────────────────────────────────────

def _project_context_key(project_id: str) -> str:
    return f"kith:cache:project_ctx:{project_id}"


def _billing_tier_key(user_id: str) -> str:
    return f"kith:cache:billing_tier:{user_id}"


async def get_cached_project_context(project_id: str) -> dict | None:
    return await cache_get_json(_project_context_key(project_id))


async def set_cached_project_context(project_id: str, ctx: dict, ttl: int = 300) -> None:
    await cache_set_json(_project_context_key(project_id), ctx, ttl=ttl)


async def invalidate_project_context(project_id: str) -> None:
    await cache_invalidate(_project_context_key(project_id))


async def get_cached_billing_tier(user_id: str) -> str | None:
    return await cache_get(_billing_tier_key(user_id))


async def set_cached_billing_tier(user_id: str, tier: str, ttl: int = 300) -> None:
    await cache_set(_billing_tier_key(user_id), tier, ttl=ttl)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  WebSocket fire-and-forget job channels
# ─────────────────────────────────────────────────────────────────────────────

def ws_job_channel(job_id: str) -> str:
    """Ephemeral Redis pub/sub channel for one LLM generation job."""
    return f"kith:ws:job:{job_id}"


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Improvement plan cache  (csuite /improve async offload)
# ─────────────────────────────────────────────────────────────────────────────

async def store_improve_plan(job_id: str, plan: dict, ttl: int = 300) -> None:
    r = get_async_redis()
    await r.set(f"kith:improve_plan:{job_id}", json.dumps(plan), ex=ttl)


async def get_improve_plan(job_id: str) -> dict | None:
    r = get_async_redis()
    raw = await r.get(f"kith:improve_plan:{job_id}")
    return json.loads(raw) if raw else None


# ─────────────────────────────────────────────────────────────────────────────
# 6.  WebSocket fire-and-forget job channels
# ─────────────────────────────────────────────────────────────────────────────

def ws_job_channel(job_id: str) -> str:
    """Ephemeral Redis pub/sub channel for one LLM generation job."""
    return f"kith:ws:job:{job_id}"


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Improvement plan cache  (csuite /improve async offload)
# ─────────────────────────────────────────────────────────────────────────────

async def store_improve_plan(job_id: str, plan: dict, ttl: int = 300) -> None:
    r = get_async_redis()
    await r.set(f"kith:improve_plan:{job_id}", json.dumps(plan), ex=ttl)


async def get_improve_plan(job_id: str) -> dict | None:
    r = get_async_redis()
    raw = await r.get(f"kith:improve_plan:{job_id}")
    return json.loads(raw) if raw else None


async def invalidate_billing_tier(user_id: str) -> None:
    await cache_invalidate(_billing_tier_key(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# Sync cache helpers  (for sync code paths like billing_api)
# ─────────────────────────────────────────────────────────────────────────────

def cache_get_sync(key: str) -> str | None:
    r = get_sync_redis()
    raw = r.get(key)
    return raw.decode() if isinstance(raw, bytes) else raw


def cache_set_sync(key: str, value: str, ttl: int = 300) -> None:
    r = get_sync_redis()
    r.set(key, value, ex=ttl)


def cache_invalidate_sync(key: str) -> None:
    r = get_sync_redis()
    r.delete(key)


def get_cached_billing_tier_sync(user_id: str) -> str | None:
    return cache_get_sync(_billing_tier_key(user_id))


def set_cached_billing_tier_sync(user_id: str, tier: str, ttl: int = 300) -> None:
    cache_set_sync(_billing_tier_key(user_id), tier, ttl=ttl)


def invalidate_billing_tier_sync(user_id: str) -> None:
    cache_invalidate_sync(_billing_tier_key(user_id))
