"""
Billing API — Stripe integration, subscription management, usage enforcement.

Tier limits (from kith_foundry_scale_pricing_analysis):
  free       — 1 project, 3 C-Suite/mo, 5 design screens/mo, BYOK only
  indie $39  — 5 projects, 20 C-Suite/mo, 30 design screens/mo, 3 artifact sets/mo
  pro   $89  — unlimited projects, 100 C-Suite/mo, 150 design screens/mo, unlimited artifacts
  team  $249 — same as pro × seat_count (3–10 seats)
  enterprise — custom (unlimited by default, managed via support)

Add-on packs (one-time purchases):
  csuite_runs   — 25 extra runs for $9
  design_screens — 50 extra screens for $9

BYOK discount  — 20% off any paid plan (applied at checkout via coupon)
Annual discount — 20% off monthly price when billing annually
"""
from __future__ import annotations

import os
import math
from datetime import datetime, timezone
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import (
    get_db,
    Subscription, SubscriptionTier, SubscriptionStatus,
    UsageRecord, UsagePack,
    ProviderKey,
)
from auth import get_current_user
from models import User

# ── Stripe bootstrap ──────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

# ── Tier configuration ────────────────────────────────────────────────────────
# None = unlimited
TIER_LIMITS: dict[str, dict] = {
    "free": {
        "projects": 1,
        "csuite_runs_mo": 3,
        "design_screens_mo": 5,
        "artifact_sets_mo": 0,        # BYOK only → no hosted LLM artifacts
        "byok_required": True,
        "price_monthly_cents": 0,
        "price_annual_cents": 0,
        "stripe_price_monthly": None,
        "stripe_price_annual": None,
    },
    "indie": {
        "projects": 5,
        "csuite_runs_mo": 20,
        "design_screens_mo": 30,
        "artifact_sets_mo": 3,
        "byok_required": False,
        "price_monthly_cents": 3900,
        "price_annual_cents": 37440,  # $3120/yr = $39 * 0.8 * 12
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_INDIE_MONTHLY", ""),
        "stripe_price_annual": os.getenv("STRIPE_PRICE_INDIE_ANNUAL", ""),
    },
    "pro": {
        "projects": None,
        "csuite_runs_mo": 100,
        "design_screens_mo": 150,
        "artifact_sets_mo": None,
        "byok_required": False,
        "price_monthly_cents": 8900,
        "price_annual_cents": 85440,  # $89 * 0.8 * 12
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
        "stripe_price_annual": os.getenv("STRIPE_PRICE_PRO_ANNUAL", ""),
    },
    "team": {
        "projects": None,
        "csuite_runs_mo": 100,        # per seat
        "design_screens_mo": 150,     # per seat
        "artifact_sets_mo": None,
        "byok_required": False,
        "price_monthly_cents": 24900,
        "price_annual_cents": 239040,
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_TEAM_MONTHLY", ""),
        "stripe_price_annual": os.getenv("STRIPE_PRICE_TEAM_ANNUAL", ""),
    },
    "enterprise": {
        "projects": None,
        "csuite_runs_mo": None,
        "design_screens_mo": None,
        "artifact_sets_mo": None,
        "byok_required": False,
        "price_monthly_cents": 99900,
        "price_annual_cents": 959040,
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", ""),
        "stripe_price_annual": os.getenv("STRIPE_PRICE_ENTERPRISE_ANNUAL", ""),
    },
}

ADD_ON_PRICES = {
    "csuite_runs": {
        "pack_size": 25,
        "cents": 900,
        "stripe_price": os.getenv("STRIPE_PRICE_PACK_CSUITE", ""),
    },
    "design_screens": {
        "pack_size": 50,
        "cents": 900,
        "stripe_price": os.getenv("STRIPE_PRICE_PACK_DESIGN", ""),
    },
}

BYOK_COUPON = os.getenv("STRIPE_COUPON_BYOK_20PCT", "")   # 20% off, applied at checkout
ANNUAL_COUPON = os.getenv("STRIPE_COUPON_ANNUAL_20PCT", "") # 20% off for annual billing

# ── Helpers ───────────────────────────────────────────────────────────────────

def _billing_month() -> str:
    """Return current billing month as 'YYYY-MM'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_or_create_subscription(db: Session, user: User) -> Subscription:
    """Fetch or lazily create a free-tier subscription row for the user."""
    # Fast path: tier string cached in Redis (TTL 5 min)
    try:
        from redis_state import get_cached_billing_tier_sync, set_cached_billing_tier_sync
        cached_tier = get_cached_billing_tier_sync(user.id)
        if cached_tier:
            # Still need the ORM object for effective_limit(); build a lightweight stub
            sub = db.query(Subscription).filter_by(user_id=user.id).first()
            if sub is not None:
                return sub
    except Exception:
        pass

    sub = db.query(Subscription).filter_by(user_id=user.id).first()
    if sub is None:
        sub = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.free,
            status=SubscriptionStatus.active,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    # Cache the tier string so the next call checks Redis before hitting the DB
    try:
        from redis_state import set_cached_billing_tier_sync
        tier_val = sub.tier.value if hasattr(sub.tier, "value") else str(sub.tier)
        set_cached_billing_tier_sync(user.id, tier_val, ttl=300)
    except Exception:
        pass

    return sub


def get_or_create_usage(db: Session, user_id: str, month: str) -> UsageRecord:
    """Fetch or lazily create a usage record for the user/month."""
    rec = db.query(UsageRecord).filter_by(user_id=user_id, billing_month=month).first()
    if rec is None:
        rec = UsageRecord(user_id=user_id, billing_month=month)
        db.add(rec)
        db.commit()
        db.refresh(rec)
    return rec


def user_has_byok(db: Session, user_id: str) -> bool:
    """Return True if the user has at least one active provider API key (BYOK)."""
    return db.query(ProviderKey).filter_by(user_id=user_id, is_active=True).count() > 0


def pack_remaining(db: Session, user_id: str, pack_type: str) -> int:
    """Sum of remaining units in all non-expired packs for this user/type."""
    now = datetime.now(timezone.utc)
    packs = db.query(UsagePack).filter(
        UsagePack.user_id == user_id,
        UsagePack.pack_type == pack_type,
        UsagePack.remaining > 0,
    ).all()
    total = 0
    for p in packs:
        if p.expires_at is None or p.expires_at.replace(tzinfo=timezone.utc) > now:
            total += p.remaining
    return total


def consume_pack_units(db: Session, user_id: str, pack_type: str, qty: int = 1) -> int:
    """
    Deduct `qty` units from the oldest non-expired pack(s).
    Returns units consumed from packs (0 if none available).
    """
    now = datetime.now(timezone.utc)
    packs = db.query(UsagePack).filter(
        UsagePack.user_id == user_id,
        UsagePack.pack_type == pack_type,
        UsagePack.remaining > 0,
    ).order_by(UsagePack.purchased_at).all()
    consumed = 0
    remaining_to_consume = qty
    for p in packs:
        if p.expires_at and p.expires_at.replace(tzinfo=timezone.utc) <= now:
            continue
        take = min(p.remaining, remaining_to_consume)
        p.remaining -= take
        remaining_to_consume -= take
        consumed += take
        if remaining_to_consume == 0:
            break
    if consumed > 0:
        db.commit()
    return consumed


def effective_limit(sub: Subscription, limit_key: str) -> int | None:
    """
    Return the effective limit for a given resource, accounting for seat_count
    on team tier. None = unlimited.
    """
    tier = sub.tier.value if hasattr(sub.tier, "value") else sub.tier
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    base = limits.get(limit_key)
    if base is None:
        return None  # unlimited
    # Team tier scales per-seat limits by seat count
    if tier == "team" and limit_key in ("csuite_runs_mo", "design_screens_mo"):
        return base * max(sub.seat_count, 1)
    return base


# ── Usage enforcement gate ────────────────────────────────────────────────────

class LimitExceeded(HTTPException):
    def __init__(self, resource: str, limit: int, used: int, pack_type: str | None = None):
        detail = {
            "error": "usage_limit_exceeded",
            "resource": resource,
            "limit": limit,
            "used": used,
            "upgrade_url": "/billing",
        }
        if pack_type:
            detail["pack_available"] = pack_type
        super().__init__(status_code=402, detail=detail)


def enforce_csuite_limit(db: Session, user: User) -> None:
    """Raise 402 if user has exhausted C-Suite runs for this month (+ packs)."""
    if getattr(user, "is_super_admin", False):
        return  # super admins are never gate-kept
    sub = get_or_create_subscription(db, user)
    limit = effective_limit(sub, "csuite_runs_mo")
    if limit is None:
        return  # unlimited
    month = _billing_month()
    rec = get_or_create_usage(db, user.id, month)
    if rec.csuite_runs < limit:
        return  # within plan
    # Check packs
    if pack_remaining(db, user.id, "csuite_runs") > 0:
        consume_pack_units(db, user.id, "csuite_runs")
        return
    raise LimitExceeded("csuite_runs", limit, rec.csuite_runs, "csuite_runs")


def enforce_design_screen_limit(db: Session, user: User) -> None:
    """Raise 402 if user has exhausted design screens for this month (+ packs)."""
    if getattr(user, "is_super_admin", False):
        return
    sub = get_or_create_subscription(db, user)
    limit = effective_limit(sub, "design_screens_mo")
    if limit is None:
        return
    month = _billing_month()
    rec = get_or_create_usage(db, user.id, month)
    if rec.design_screens < limit:
        return
    if pack_remaining(db, user.id, "design_screens") > 0:
        consume_pack_units(db, user.id, "design_screens")
        return
    raise LimitExceeded("design_screens", limit, rec.design_screens, "design_screens")


def enforce_artifact_limit(db: Session, user: User) -> None:
    """Raise 402 if user has exhausted artifact sets for this month."""
    if getattr(user, "is_super_admin", False):
        return
    sub = get_or_create_subscription(db, user)
    limit = effective_limit(sub, "artifact_sets_mo")
    if limit is None:
        return
    if limit == 0:
        # Free tier: only BYOK users can generate artifacts with their own key
        if not user_has_byok(db, user.id):
            raise LimitExceeded("artifact_sets", 0, 0)
        return
    month = _billing_month()
    rec = get_or_create_usage(db, user.id, month)
    if rec.artifact_sets < limit:
        return
    raise LimitExceeded("artifact_sets", limit, rec.artifact_sets)


def enforce_project_limit(db: Session, user: User) -> None:
    """Raise 402 if user has hit their project cap."""
    if getattr(user, "is_super_admin", False):
        return
    sub = get_or_create_subscription(db, user)
    limit = effective_limit(sub, "projects")
    if limit is None:
        return
    month = _billing_month()
    rec = get_or_create_usage(db, user.id, month)
    if rec.project_count < limit:
        return
    raise LimitExceeded("projects", limit, rec.project_count)


# ── Usage recording helpers ───────────────────────────────────────────────────

def record_csuite_run(db: Session, user_id: str) -> None:
    rec = get_or_create_usage(db, user_id, _billing_month())
    rec.csuite_runs += 1
    db.commit()


def record_design_screen(db: Session, user_id: str, count: int = 1) -> None:
    rec = get_or_create_usage(db, user_id, _billing_month())
    rec.design_screens += count
    db.commit()


def record_artifact_set(db: Session, user_id: str) -> None:
    rec = get_or_create_usage(db, user_id, _billing_month())
    rec.artifact_sets += 1
    db.commit()


def record_project_created(db: Session, user_id: str) -> None:
    rec = get_or_create_usage(db, user_id, _billing_month())
    rec.project_count += 1
    db.commit()


# ── REST endpoints ────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    tier: Literal["indie", "pro", "team", "enterprise"]
    annual: bool = False
    seat_count: int = 1


class PackPurchaseRequest(BaseModel):
    pack_type: Literal["csuite_runs", "design_screens"]


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current subscription tier + usage for the logged-in user."""
    sub = get_or_create_subscription(db, user)
    month = _billing_month()
    rec = get_or_create_usage(db, user.id, month)
    tier_key = sub.tier.value if hasattr(sub.tier, "value") else sub.tier
    limits = TIER_LIMITS.get(tier_key, TIER_LIMITS["free"])
    packs = db.query(UsagePack).filter(
        UsagePack.user_id == user.id,
        UsagePack.remaining > 0,
    ).all()
    return {
        "tier": tier_key,
        "status": sub.status.value if hasattr(sub.status, "value") else sub.status,
        "is_annual": sub.is_annual,
        "seat_count": sub.seat_count,
        "byok_discount_applied": sub.byok_discount_applied,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "limits": {
            "projects": limits["projects"],
            "csuite_runs_mo": effective_limit(sub, "csuite_runs_mo"),
            "design_screens_mo": effective_limit(sub, "design_screens_mo"),
            "artifact_sets_mo": effective_limit(sub, "artifact_sets_mo"),
        },
        "usage": {
            "billing_month": month,
            "csuite_runs": rec.csuite_runs,
            "design_screens": rec.design_screens,
            "artifact_sets": rec.artifact_sets,
            "project_count": rec.project_count,
        },
        "packs": [
            {
                "pack_type": p.pack_type,
                "remaining": p.remaining,
                "pack_size": p.pack_size,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
            }
            for p in packs
        ],
    }


@router.post("/checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for upgrading to a paid tier."""
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    tier_config = TIER_LIMITS.get(req.tier)
    if tier_config is None:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {req.tier}")

    price_id = tier_config["stripe_price_annual"] if req.annual else tier_config["stripe_price_monthly"]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe price not configured for {req.tier} ({'annual' if req.annual else 'monthly'}). "
                   f"Set STRIPE_PRICE_{req.tier.upper()}_{'ANNUAL' if req.annual else 'MONTHLY'} in .env",
        )

    # Get or create Stripe customer
    sub = get_or_create_subscription(db, user)
    if sub.stripe_customer_id:
        customer_id = sub.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user.id},
        )
        customer_id = customer.id
        sub.stripe_customer_id = customer_id
        db.commit()

    # Determine coupons
    discounts = []
    has_byok = user_has_byok(db, user.id)
    if has_byok and BYOK_COUPON:
        discounts.append({"coupon": BYOK_COUPON})

    # Build session
    origin = os.getenv("FRONTEND_URL", "http://localhost:5173")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{
            "price": price_id,
            "quantity": req.seat_count,
        }],
        discounts=discounts if discounts else None,
        subscription_data={
            "metadata": {
                "user_id": user.id,
                "tier": req.tier,
                "annual": str(req.annual),
                "seat_count": str(req.seat_count),
            }
        },
        success_url=f"{origin}/billing?checkout=success",
        cancel_url=f"{origin}/billing?checkout=cancelled",
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/pack/checkout")
async def create_pack_checkout(
    req: PackPurchaseRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for a usage pack add-on."""
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured.")
    pack_config = ADD_ON_PRICES.get(req.pack_type)
    if not pack_config:
        raise HTTPException(status_code=400, detail=f"Unknown pack_type: {req.pack_type}")
    if not pack_config["stripe_price"]:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe price not configured for {req.pack_type} pack. "
                   f"Set STRIPE_PRICE_PACK_{req.pack_type.upper()} in .env",
        )

    sub = get_or_create_subscription(db, user)
    if sub.stripe_customer_id:
        customer_id = sub.stripe_customer_id
    else:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        customer_id = customer.id
        sub.stripe_customer_id = customer_id
        db.commit()

    origin = os.getenv("FRONTEND_URL", "http://localhost:5173")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": pack_config["stripe_price"], "quantity": 1}],
        success_url=f"{origin}/billing?pack=success&type={req.pack_type}",
        cancel_url=f"{origin}/billing?pack=cancelled",
        metadata={"user_id": user.id, "pack_type": req.pack_type},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_billing_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a Stripe Customer Portal URL for managing subscription/invoices."""
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured.")
    sub = get_or_create_subscription(db, user)
    if not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer yet. Please subscribe first.")
    origin = os.getenv("FRONTEND_URL", "http://localhost:5173")
    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{origin}/billing",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook endpoint — processes checkout.session.completed and
    customer.subscription.* events to keep local subscription state in sync.

    Configure in Stripe Dashboard → Webhooks → this URL with:
      - checkout.session.completed
      - customer.subscription.updated
      - customer.subscription.deleted
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        import json
        event = json.loads(payload)

    etype = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        mode = data.get("mode")
        user_id = data.get("metadata", {}).get("user_id")
        if not user_id:
            return {"received": True}

        if mode == "subscription":
            subscription_id = data.get("subscription")
            if subscription_id:
                stripe_sub = stripe.Subscription.retrieve(subscription_id)
                _sync_subscription_from_stripe(db, user_id, stripe_sub)

        elif mode == "payment":
            pack_type = data.get("metadata", {}).get("pack_type")
            payment_intent = data.get("payment_intent")
            if pack_type and pack_type in ADD_ON_PRICES:
                pack_config = ADD_ON_PRICES[pack_type]
                pack = UsagePack(
                    user_id=user_id,
                    pack_type=pack_type,
                    pack_size=pack_config["pack_size"],
                    remaining=pack_config["pack_size"],
                    stripe_payment_intent=payment_intent,
                )
                db.add(pack)
                db.commit()

    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        stripe_sub = data
        customer_id = stripe_sub.get("customer")
        local_sub = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()
        if local_sub:
            _sync_subscription_from_stripe(db, local_sub.user_id, stripe_sub)

    elif etype == "customer.subscription.deleted":
        customer_id = data.get("customer")
        local_sub = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()
        if local_sub:
            local_sub.tier = SubscriptionTier.free
            local_sub.status = SubscriptionStatus.canceled
            local_sub.stripe_subscription_id = None
            local_sub.stripe_price_id = None
            db.commit()
            try:
                from redis_state import invalidate_billing_tier_sync
                invalidate_billing_tier_sync(local_sub.user_id)
            except Exception:
                pass

    return {"received": True}


def _sync_subscription_from_stripe(db: Session, user_id: str, stripe_sub: dict) -> None:
    """Update local Subscription row from a Stripe subscription object."""
    # Map Stripe status to local enum
    status_map = {
        "active": SubscriptionStatus.active,
        "trialing": SubscriptionStatus.trialing,
        "past_due": SubscriptionStatus.past_due,
        "canceled": SubscriptionStatus.canceled,
        "unpaid": SubscriptionStatus.unpaid,
    }
    stripe_status = stripe_sub.get("status", "active")
    local_status = status_map.get(stripe_status, SubscriptionStatus.active)

    # Derive tier from metadata (set at checkout time)
    meta = stripe_sub.get("metadata", {})
    tier_str = meta.get("tier", "free")
    tier_map = {t: getattr(SubscriptionTier, t) for t in ("free", "indie", "pro", "team", "enterprise")}
    tier = tier_map.get(tier_str, SubscriptionTier.free)
    is_annual = meta.get("annual", "false").lower() == "true"
    seat_count = int(meta.get("seat_count", "1"))

    # Period timestamps
    period_start = period_end = None
    if stripe_sub.get("current_period_start"):
        period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
    if stripe_sub.get("current_period_end"):
        period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)

    price_id = None
    items = stripe_sub.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")

    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    if sub is None:
        sub = Subscription(user_id=user_id)
        db.add(sub)
    sub.tier = tier
    sub.status = local_status
    sub.stripe_subscription_id = stripe_sub.get("id")
    sub.stripe_price_id = price_id
    sub.current_period_start = period_start
    sub.current_period_end = period_end
    sub.is_annual = is_annual
    sub.seat_count = seat_count
    db.commit()

    # Invalidate cached tier so the next request gets the updated value
    try:
        from redis_state import invalidate_billing_tier_sync
        invalidate_billing_tier_sync(user_id)
    except Exception:
        pass


# ── Public pricing info (no auth required) ─────────────────────────────────────
@router.get("/plans", include_in_schema=True)
async def get_plans():
    """Return public pricing tiers for the landing / pricing page."""
    plans = []
    for tier_name, cfg in TIER_LIMITS.items():
        plans.append({
            "tier": tier_name,
            "price_monthly_cents": cfg["price_monthly_cents"],
            "price_annual_cents": cfg["price_annual_cents"],
            "limits": {
                "projects": cfg["projects"],
                "csuite_runs_mo": cfg["csuite_runs_mo"],
                "design_screens_mo": cfg["design_screens_mo"],
                "artifact_sets_mo": cfg["artifact_sets_mo"],
            },
            "byok_required": cfg["byok_required"],
        })
    return {
        "plans": plans,
        "addons": {
            k: {"pack_size": v["pack_size"], "cents": v["cents"]}
            for k, v in ADD_ON_PRICES.items()
        },
        "discounts": {
            "byok_percent": 20,
            "annual_percent": 20,
        },
    }
