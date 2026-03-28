"""Cloudflare integration: Turnstile verification, rate-limit rules, WAF, and zone management."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

CF_API = "https://api.cloudflare.com/client/v4"
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


# ── Config helpers ────────────────────────────────────────────────────────────

def _cf_api_token() -> str:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is not set")
    return token


def _zone_id() -> str:
    zid = os.getenv("CLOUDFLARE_ZONE_ID", "")
    if not zid:
        raise RuntimeError("CLOUDFLARE_ZONE_ID is not set")
    return zid


def _account_id() -> str:
    aid = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    if not aid:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID is not set")
    return aid


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_cf_api_token()}",
        "Content-Type": "application/json",
    }


def _zone_url(path: str = "") -> str:
    return f"{CF_API}/zones/{_zone_id()}{path}"


def _account_url(path: str = "") -> str:
    return f"{CF_API}/accounts/{_account_id()}{path}"


# ── Turnstile ─────────────────────────────────────────────────────────────────

async def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """Verify a Turnstile CAPTCHA token server-side. Returns True if valid."""
    secret = os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "")
    if not secret:
        logger.warning("Turnstile secret key not configured — skipping verification (fail-open in dev)")
        return True  # fail-open: never block auth in dev when key is absent

    payload: dict[str, str] = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(TURNSTILE_VERIFY_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    success = data.get("success", False)
    if not success:
        codes = data.get("error-codes", [])
        logger.warning("Turnstile verification failed: %s", codes)
    return success


# ── Rate Limiting ─────────────────────────────────────────────────────────────

async def setup_rate_limit_rules() -> list[dict]:
    """Create rate-limit rules for the Cloudflare zone. Returns list of created/existing rules."""
    # Free plan: 1 rule max, period=10s only, mitigation_timeout=10 only.
    # Only rate-limit auth/security endpoints — NOT editor/project API paths
    # which have legitimate high-frequency polling.
    rules = [
        {
            "description": "Auth rate limit — 10 req/10s per IP",
            "expression": (
                '(http.request.uri.path contains "/api/turnstile" or '
                'http.request.uri.path contains "/api/auth" or '
                'http.request.uri.path eq "/login")'
            ),
            "action": "block",
            "ratelimit": {
                "characteristics": ["cf.colo.id", "ip.src"],
                "period": 10,
                "requests_per_period": 10,
                "mitigation_timeout": 10,
            },
        },
    ]
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            _zone_url("/rulesets/phases/http_ratelimit/entrypoint"),
            headers=_headers(),
            json={
                "rules": [
                    {
                        "description": r["description"],
                        "expression": r["expression"],
                        "action": r["action"],
                        "ratelimit": r["ratelimit"],
                    }
                    for r in rules
                ],
            },
        )
        if resp.status_code == 403:
            logger.warning("API token lacks Zone WAF permission — cannot configure rate limits")
            return [{"error": "Token needs 'Zone WAF Edit' permission"}]
        if not resp.is_success:
            logger.error("Rate limit API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        results = resp.json().get("result", {}).get("rules", [])
        logger.info("Rate limit rules configured: %d rules", len(results))
    return results


# ── WAF Custom Rules ──────────────────────────────────────────────────────────

async def setup_waf_rules() -> list[dict]:
    """Deploy custom WAF rules for the Cloudflare zone."""
    rules = [
        {
            "description": "Block empty or missing user agents",
            "expression": '(http.user_agent eq "")',
            "action": "managed_challenge",
        },
        {
            "description": "Block suspicious user agents (scanners)",
            "expression": (
                '(http.user_agent contains "sqlmap" or '
                'http.user_agent contains "nikto" or '
                'http.user_agent contains "nmap" or '
                'http.user_agent contains "masscan" or '
                'http.user_agent contains "dirbuster")'
            ),
            "action": "block",
        },
        {
            "description": "Challenge non-browser API requests without valid origin",
            "expression": (
                '(http.request.uri.path contains "/api/" and '
                'http.request.method ne "OPTIONS" and '
                'not any(http.request.headers["referer"][*] contains "forgeoperator.com") and '
                'not any(http.request.headers["origin"][*] contains "forgeoperator.com") and '
                'not any(http.request.headers["referer"][*] contains "localhost") and '
                'not any(http.request.headers["origin"][*] contains "localhost"))'
            ),
            "action": "managed_challenge",
        },
        {
            "description": "Block access to sensitive paths",
            "expression": (
                '(http.request.uri.path contains "/.env" or '
                'http.request.uri.path contains "/.git" or '
                'http.request.uri.path contains "/wp-admin" or '
                'http.request.uri.path contains "/phpmyadmin")'
            ),
            "action": "block",
        },
    ]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            _zone_url("/rulesets/phases/http_request_firewall_custom/entrypoint"),
            headers=_headers(),
            json={"rules": rules},
        )
        if resp.status_code == 403:
            logger.warning("API token lacks Zone WAF permission — cannot configure WAF rules")
            return [{"error": "Token needs 'Zone WAF Edit' permission"}]
        if not resp.is_success:
            logger.error("WAF API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        results = resp.json().get("result", {}).get("rules", [])
        logger.info("WAF custom rules configured: %d rules", len(results))
    return results


# ── Zone Info + Analytics ─────────────────────────────────────────────────────

async def get_zone_info() -> dict:
    """Fetch zone details."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_zone_url(), headers=_headers())
        resp.raise_for_status()
        return resp.json().get("result", {})


async def get_zone_analytics(since_minutes: int = 1440) -> dict:
    """Fetch zone analytics for the last N minutes (default 24h)."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=since_minutes)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            _zone_url("/analytics/dashboard"),
            headers=_headers(),
            params={
                "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        resp.raise_for_status()
        return resp.json().get("result", {})
