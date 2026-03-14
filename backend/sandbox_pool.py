"""
Pre-warm sandbox pool — keeps a small set of ready Fly sandboxes so new
project sessions start instantly instead of waiting ~30–60s for VM bootstrap.

Redis keys:
  kith:sandbox:pool:warm     — List of JSON metadata dicts (warm, idle sandboxes)
  kith:sandbox:pool:creating — String counter (# currently being provisioned)

Usage (from inngest_functions.py cron):
    from sandbox_pool import fill_pool
    await fill_pool(target=3)

Usage (from fly_service.get_or_create_worker):
    from sandbox_pool import lease_machine
    meta = lease_machine()
    if meta:
        # reassign to this project and use immediately
"""
from __future__ import annotations

import json
import threading

from redis_client import get_sync_redis

_POOL_KEY = "kith:sandbox:pool:warm"
_CREATING_KEY = "kith:sandbox:pool:creating"
_POOL_MAX = 5          # never store more than this many warm machines
_POOL_TARGET = 3       # default fill target
_FILL_LOCK = threading.Lock()  # one fill_pool() at a time per process


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def pool_size() -> int:
    """Return the number of warm sandboxes currently in the pool."""
    try:
        r = get_sync_redis()
        return r.llen(_POOL_KEY)
    except Exception:
        return 0


def lease_machine() -> dict | None:
    """
    Atomically pop one warm sandbox from the pool.
    Returns the metadata dict (suitable for FlySandboxWorker.from_metadata),
    or None if the pool is empty.
    """
    try:
        r = get_sync_redis()
        raw = r.rpop(_POOL_KEY)
        if raw is None:
            return None
        return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception as e:
        print(f"[sandbox_pool] lease_machine error: {e}")
        return None


def return_machine(meta: dict) -> bool:
    """
    Return an *unused* warm sandbox back to the pool.
    Pushes to the front of the list so it will be leased again first.
    Returns True if returned, False if pool is full (caller should destroy).
    """
    try:
        r = get_sync_redis()
        if r.llen(_POOL_KEY) >= _POOL_MAX:
            return False
        r.lpush(_POOL_KEY, json.dumps(meta))
        return True
    except Exception as e:
        print(f"[sandbox_pool] return_machine error: {e}")
        return False


def fill_pool(target: int = _POOL_TARGET) -> int:
    """
    Synchronously create warm sandboxes until the pool reaches *target*.
    Returns the number of sandboxes successfully added.

    This function is intentionally synchronous (called from Inngest thread).
    Uses a per-process lock so parallel Inngest invocations don't double-fill.
    """
    with _FILL_LOCK:
        try:
            r = get_sync_redis()
            current = r.llen(_POOL_KEY)
            creating_raw = r.get(_CREATING_KEY)
            creating = int(creating_raw) if creating_raw else 0
        except Exception as e:
            print(f"[sandbox_pool] fill_pool redis error: {e}")
            return 0

        needed = max(0, target - current - creating)
        if needed == 0:
            print(f"[sandbox_pool] Pool already has {current}+{creating} machines (target={target}) — skipping fill")
            return 0

        print(f"[sandbox_pool] Filling pool: current={current}, creating={creating}, target={target}, needed={needed}")
        added = 0
        for _ in range(needed):
            try:
                _increment_creating(1)
                meta = _create_warm_sandbox()
                if meta:
                    try:
                        r.lpush(_POOL_KEY, json.dumps(meta))
                        added += 1
                        print(f"[sandbox_pool] Warm sandbox {meta.get('app_name')} added to pool ({pool_size()} total)")
                    finally:
                        _increment_creating(-1)
                else:
                    _increment_creating(-1)
            except Exception as e:
                _increment_creating(-1)
                print(f"[sandbox_pool] fill_pool create error: {e}")

        return added


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _increment_creating(delta: int) -> None:
    try:
        r = get_sync_redis()
        if delta > 0:
            r.incrby(_CREATING_KEY, delta)
            r.expire(_CREATING_KEY, 300)  # safety TTL — clear stale counter after 5 min
        else:
            val = r.get(_CREATING_KEY)
            current = int(val) if val else 0
            new_val = max(0, current + delta)
            r.set(_CREATING_KEY, new_val, ex=300)
    except Exception:
        pass


def _create_warm_sandbox() -> dict | None:
    """Create a new sandbox, wait for it to come up, return its metadata."""
    try:
        from fly_service import FlySandboxWorker
        worker = FlySandboxWorker(project_id="pool")
        worker.create()  # blocks ~30-60s until bridge is healthy
        meta = worker.to_metadata()
        meta["pool"] = True  # tag so we know it came from the pool
        return meta
    except Exception as e:
        print(f"[sandbox_pool] _create_warm_sandbox failed: {e}")
        return None
