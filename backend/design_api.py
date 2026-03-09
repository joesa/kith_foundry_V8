"""
Design Studio API — Generate and manage design mockups.
"""
import uuid
import json
import os
import asyncio
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

import litellm

from models import (
    get_db, User, Project, DesignMockup, CSuiteAnalysis,
    CSuiteRole, MockupStatus, MockupPriority, AgentStatus,
    Artifact, ArtifactType,
)
from auth import get_current_user
from design_fallbacks import (
    screen_variant as _screen_variant_impl,
    screen_specific_requirements as _screen_specific_requirements_impl,
    fallback_mockup_html as _fallback_mockup_html_impl,
)
from design_intelligence import (
    compose_project_context,
    build_design_brief,
    build_compiled_design_spec,
    format_design_brief,
    format_compiled_design_spec,
    extract_product_name,
)

import inngest
from inngest_client import client as inngest_client, use_inngest

litellm.drop_params = True
router = APIRouter(prefix="/api/v1/projects", tags=["design"])

# ── Cancellation registry ─────────────────────────────────────────────────────
# Mockup IDs added here will be skipped / aborted by the generation functions.
# Entries are discarded once the generation function notices them.
_cancelled_mockups: set[str] = set()


DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"

def _get_model():
    return os.getenv("DESIGN_MODEL", DEFAULT_MODEL)


def _resolve_design_model(user_id: str | None = None, db=None) -> dict:
    """Resolve model config for design task."""
    if user_id:
        from model_resolver import resolve_model_for_task
        return resolve_model_for_task(user_id, "design", db=db)
    return {"model": _get_model(), "api_key": None, "api_base": None, "provider_name": "Default"}


def _build_litellm_kwargs(model_config: dict, messages: list, **extra) -> dict:
    """Build litellm.acompletion kwargs from model config."""
    if model_config.get("error"):
        raise HTTPException(status_code=400, detail=model_config["error"])
    kwargs = {"model": model_config["model"], "messages": messages, **extra}
    if model_config.get("api_key"):
        kwargs["api_key"] = model_config["api_key"]
    if model_config.get("api_base"):
        kwargs["api_base"] = model_config["api_base"]
    return kwargs


# ── Deterministic brand palette selector ─────────────────────────────────────

_PALETTES = [
    # 0 — Ocean Teal (research / academic / science)
    {"name": "Ocean Teal", "bg": "#08111a", "surface": "#0d1f2d", "border": "#1a3a50",
     "primary": "#0ea5c9", "accent": "#34d399", "text": "#e2f4fb", "muted": "#7ab8d4"},
    # 1 — Forest Green (agriculture / sustainability / health)
    {"name": "Forest Green", "bg": "#070f09", "surface": "#0e1f12", "border": "#1a3d20",
     "primary": "#22c55e", "accent": "#86efac", "text": "#e8f5ea", "muted": "#7dba8a"},
    # 2 — Amber Gold (finance / legal / enterprise)
    {"name": "Amber Gold", "bg": "#0f0b00", "surface": "#1c1500", "border": "#3d2e00",
     "primary": "#f59e0b", "accent": "#fbbf24", "text": "#fefce8", "muted": "#c4a44a"},
    # 3 — Rose Pink (consumer / lifestyle / e-commerce)
    {"name": "Rose Pink", "bg": "#120008", "surface": "#1f0011", "border": "#3d0020",
     "primary": "#ec4899", "accent": "#f9a8d4", "text": "#fce7f3", "muted": "#c06080"},
    # 4 — Electric Blue (devtools / security / infrastructure)
    {"name": "Electric Blue", "bg": "#020817", "surface": "#0a1628", "border": "#1e3a5f",
     "primary": "#3b82f6", "accent": "#60a5fa", "text": "#eff6ff", "muted": "#648ab5"},
    # 5 — Crimson Red (sports / gaming / competitive)
    {"name": "Crimson Red", "bg": "#110406", "surface": "#1f080b", "border": "#3d1015",
     "primary": "#ef4444", "accent": "#fca5a5", "text": "#fef2f2", "muted": "#b05555"},
    # 6 — Slate + Cyan (analytics / BI / data)
    {"name": "Slate Cyan", "bg": "#080d10", "surface": "#101820", "border": "#1e3040",
     "primary": "#06b6d4", "accent": "#67e8f9", "text": "#ecfeff", "muted": "#5a9aab"},
    # 7 — Warm Coral (creative / marketing / agency)
    {"name": "Warm Coral", "bg": "#110800", "surface": "#1f1000", "border": "#3d2000",
     "primary": "#f97316", "accent": "#fb923c", "text": "#fff7ed", "muted": "#c07040"},
    # 8 — Violet-Indigo (AI / productivity / workspace) — NOT purple
    {"name": "Indigo", "bg": "#06050f", "surface": "#0e0d20", "border": "#201e45",
     "primary": "#6366f1", "accent": "#818cf8", "text": "#eef2ff", "muted": "#6870a0"},
    # 9 — Emerald + Gold (premium / luxury / consulting)
    {"name": "Emerald Gold", "bg": "#060f08", "surface": "#0d1f12", "border": "#1a3a20",
     "primary": "#10b981", "accent": "#d4af37", "text": "#ecfdf5", "muted": "#5a9a75"},
]


def _pick_palette(project_context: str) -> dict:
    """Deterministically pick a brand palette from the project name/context.

    Uses a simple hash of the product name so the SAME project always gets
    the SAME palette across all its screens, but different projects get
    different palettes. Falls back to index 4 (Electric Blue) if name is empty.
    """
    import hashlib
    # Extract product name from context (first line: "Product: XYZ")
    product_name = ""
    for line in (project_context or "").splitlines():
        if line.lower().startswith("product:"):
            product_name = line.split(":", 1)[-1].strip()
            break
    seed = product_name.lower() if product_name else "default"
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(_PALETTES)
    return _PALETTES[idx]


# ── Full Design DNA system ────────────────────────────────────────────────────
# Each product gets a deterministic combination of 7 independent design
# dimensions, producing thousands of distinct visual fingerprints.

_COMPONENT_STYLES = [
    # 0 — Flat/Material
    {
        "name": "flat",
        "card_css": "background: var(--surface); border: 1px solid var(--border); box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset;",
        "btn_css": "background: linear-gradient(135deg, var(--primary), color-mix(in srgb, var(--primary) 80%, var(--accent))); border: none; box-shadow: 0 2px 10px color-mix(in srgb, var(--primary) 30%, transparent); letter-spacing: 0.02em; font-weight: 600;",
        "input_css": "background: color-mix(in srgb, var(--bg) 70%, var(--surface) 30%); border: 1px solid var(--border); box-shadow: 0 1px 4px rgba(0,0,0,0.15) inset;",
        "radius": "8px",
        "icon_container_css": "background: color-mix(in srgb, var(--primary) 15%, transparent); border-radius: 8px; padding: 8px;",
        "badge_css": "background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;",
    },
    # 1 — Glassmorphism
    {
        "name": "glass",
        "card_css": "background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.08) inset;",
        "btn_css": "background: linear-gradient(135deg, var(--primary), var(--accent)); border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 4px 20px color-mix(in srgb, var(--primary) 40%, transparent); font-weight: 600;",
        "input_css": "background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); backdrop-filter: blur(6px); box-shadow: 0 2px 8px rgba(0,0,0,0.2) inset;",
        "radius": "16px",
        "icon_container_css": "background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 10px; backdrop-filter: blur(8px);",
        "badge_css": "background: color-mix(in srgb, var(--primary) 25%, transparent); color: var(--primary); border: 1px solid color-mix(in srgb, var(--primary) 35%, transparent); padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; backdrop-filter: blur(4px);",
    },
    # 2 — High-contrast outlined (editorial, NOT wireframe — has filled surface + accent border)
    {
        "name": "outlined",
        "card_css": "background: color-mix(in srgb, var(--surface) 90%, var(--primary) 10%); border: 2px solid var(--primary); box-shadow: 0 0 20px color-mix(in srgb, var(--primary) 12%, transparent);",
        "btn_css": "background: var(--primary); color: var(--bg); border: 2px solid var(--primary); font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; box-shadow: 3px 3px 0 color-mix(in srgb, var(--primary) 40%, transparent);",
        "input_css": "background: color-mix(in srgb, var(--bg) 85%, var(--primary) 15%); border: 2px solid var(--border); box-shadow: none;",
        "radius": "4px",
        "icon_container_css": "background: var(--primary); border-radius: 4px; padding: 8px; color: var(--bg);",
        "badge_css": "background: transparent; color: var(--primary); border: 2px solid var(--primary); padding: 2px 8px; border-radius: 2px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em;",
        "style_note": "IMPORTANT: Cards must have filled backgrounds (color-mix surface+primary). Buttons must be FILLED with var(--primary) background — NOT hollow outlines. This is high-contrast editorial, not a wireframe.",
    },
    # 3 — Elevated/depth
    {
        "name": "elevated",
        "card_css": "background: var(--surface); border: 1px solid var(--border); box-shadow: 0 12px 40px rgba(0,0,0,0.45), 0 2px 0 rgba(255,255,255,0.06) inset, 0 -1px 0 rgba(0,0,0,0.3) inset;",
        "btn_css": "background: linear-gradient(180deg, var(--primary) 0%, color-mix(in srgb, var(--primary) 75%, #000) 100%); border: none; box-shadow: 0 6px 20px color-mix(in srgb, var(--primary) 45%, transparent), 0 1px 0 rgba(255,255,255,0.15) inset; font-weight: 700;",
        "input_css": "background: var(--bg); border: 1px solid var(--border); box-shadow: 0 3px 10px rgba(0,0,0,0.25) inset, 0 1px 0 rgba(255,255,255,0.04) inset;",
        "radius": "12px",
        "icon_container_css": "background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 25%, transparent), color-mix(in srgb, var(--accent) 15%, transparent)); border: 1px solid color-mix(in srgb, var(--primary) 20%, transparent); border-radius: 12px; padding: 10px;",
        "badge_css": "background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 20%, transparent), color-mix(in srgb, var(--primary) 15%, transparent)); color: var(--text); border: 1px solid color-mix(in srgb, var(--accent) 25%, transparent); padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;",
    },
    # 4 — Brutalist / editorial
    {
        "name": "brutalist",
        "card_css": "background: var(--surface); border: 3px solid var(--text); box-shadow: 6px 6px 0 var(--primary);",
        "btn_css": "background: var(--primary); color: var(--bg); border: 3px solid var(--text); box-shadow: 4px 4px 0 var(--text); font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em;",
        "input_css": "background: var(--bg); border: 3px solid var(--text); box-shadow: none;",
        "radius": "0px",
        "icon_container_css": "background: var(--primary); border: 3px solid var(--text); border-radius: 0; padding: 8px; color: var(--bg);",
        "badge_css": "background: var(--primary); color: var(--bg); border: 2px solid var(--text); padding: 2px 8px; border-radius: 0; font-size: 11px; font-weight: 900; text-transform: uppercase;",
    },
    # 5 — Pill / hyper-rounded
    {
        "name": "pill",
        "card_css": "background: var(--surface); border: 1px solid var(--border); box-shadow: 0 4px 24px rgba(0,0,0,0.2), 0 1px 0 rgba(255,255,255,0.05) inset;",
        "btn_css": "background: linear-gradient(135deg, var(--primary), var(--accent)); border: none; box-shadow: 0 6px 18px color-mix(in srgb, var(--primary) 40%, transparent); font-weight: 600; letter-spacing: 0.01em;",
        "input_css": "background: var(--bg); border: 1px solid var(--border); box-shadow: 0 2px 6px rgba(0,0,0,0.15) inset;",
        "radius": "999px",  # Fully pill-shaped buttons/inputs; cards use 24px
        "card_radius": "28px",
        "icon_container_css": "background: color-mix(in srgb, var(--primary) 18%, transparent); border-radius: 999px; padding: 10px;",
        "badge_css": "background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); padding: 3px 12px; border-radius: 999px; font-size: 11px; font-weight: 700;",
    },
    # 6 — Minimal / whitespace-first
    {
        "name": "minimal",
        "card_css": "background: var(--surface); border: none; border-bottom: 1px solid var(--border); box-shadow: none;",
        "btn_css": "background: var(--primary); color: var(--bg); border: none; font-weight: 600; letter-spacing: 0.04em;",
        "input_css": "background: transparent; border: none; border-bottom: 2px solid var(--border); border-radius: 0; padding: 8px 0;",
        "radius": "8px",
        "icon_container_css": "background: transparent; border-bottom: 2px solid var(--primary); padding: 6px; border-radius: 0;",
        "badge_css": "background: transparent; color: var(--muted); border: 1px solid var(--border); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;",
        "style_note": "Minimal style uses maximum whitespace. Cards have NO border other than a bottom separator. ALL content weight comes from typography scale — mix display-size numbers with fine uppercase labels.",
    },
    # 7 — Neo-soft / neumorphic feel
    {
        "name": "neo-soft",
        "card_css": "background: var(--surface); border: none; box-shadow: 8px 8px 20px rgba(0,0,0,0.4), -4px -4px 12px rgba(255,255,255,0.04);",
        "btn_css": "background: var(--primary); color: var(--bg); border: none; box-shadow: 5px 5px 12px rgba(0,0,0,0.4), -2px -2px 8px rgba(255,255,255,0.05); font-weight: 700;",
        "input_css": "background: var(--bg); border: none; box-shadow: 4px 4px 10px rgba(0,0,0,0.35) inset, -2px -2px 6px rgba(255,255,255,0.04) inset;",
        "radius": "18px",
        "icon_container_css": "background: var(--surface); border-radius: 14px; padding: 10px; box-shadow: 4px 4px 10px rgba(0,0,0,0.3), -2px -2px 6px rgba(255,255,255,0.04);",
        "badge_css": "background: var(--surface); color: var(--primary); box-shadow: 3px 3px 8px rgba(0,0,0,0.3), -1px -1px 4px rgba(255,255,255,0.04); padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;",
    },
    # 8 — Bento / tile mosaic
    {
        "name": "bento",
        "card_css": "background: var(--surface); border: 1px solid var(--border); box-shadow: 0 2px 12px rgba(0,0,0,0.2);",
        "btn_css": "background: linear-gradient(135deg, var(--primary), var(--accent)); color: var(--bg); border: none; font-weight: 700; box-shadow: 0 4px 14px color-mix(in srgb, var(--primary) 35%, transparent);",
        "input_css": "background: color-mix(in srgb, var(--bg) 75%, var(--surface) 25%); border: 1px solid var(--border);",
        "radius": "20px",
        "card_radius": "20px",
        "icon_container_css": "background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 20%, transparent), color-mix(in srgb, var(--accent) 12%, transparent)); border-radius: 14px; padding: 10px;",
        "badge_css": "background: color-mix(in srgb, var(--primary) 18%, transparent); color: var(--primary); border: 1px solid color-mix(in srgb, var(--primary) 25%, transparent); padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 700;",
        "layout_hint": "Use a CSS grid bento-box layout with varying tile sizes (some span 2 cols, some 1 col, mixed heights). Avoid uniform card grids.",
    },
    # 9 — Dark luxury
    {
        "name": "luxury",
        "card_css": "background: linear-gradient(145deg, var(--surface), color-mix(in srgb, var(--surface) 70%, var(--primary) 30%)); border: 1px solid color-mix(in srgb, var(--primary) 35%, transparent); box-shadow: 0 12px 48px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.06) inset;",
        "btn_css": "background: linear-gradient(90deg, var(--primary), var(--accent)); color: var(--bg); border: none; box-shadow: 0 6px 24px color-mix(in srgb, var(--primary) 50%, transparent); font-weight: 700; letter-spacing: 0.08em;",
        "input_css": "background: color-mix(in srgb, var(--bg) 75%, var(--primary) 25%); border: 1px solid color-mix(in srgb, var(--primary) 30%, transparent); box-shadow: 0 2px 8px rgba(0,0,0,0.3) inset;",
        "radius": "10px",
        "icon_container_css": "background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 30%, transparent), color-mix(in srgb, var(--accent) 20%, transparent)); border: 1px solid color-mix(in srgb, var(--primary) 35%, transparent); border-radius: 10px; padding: 10px;",
        "badge_css": "background: linear-gradient(90deg, color-mix(in srgb, var(--primary) 20%, transparent), color-mix(in srgb, var(--accent) 12%, transparent)); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); padding: 3px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; letter-spacing: 0.05em;",
    },
]

_TYPOGRAPHY_SPECS = [
    # 0 — Clean geometric (modern SaaS)
    {
        "name": "geometric",
        "font_import": "",
        "font_stack": "Inter, 'DM Sans', system-ui, -apple-system, sans-serif",
        "heading_weight": "700",
        "heading_tracking": "-0.02em",
        "body_size": "14px",
        "body_weight": "400",
        "body_tracking": "0",
        "mono_stack": "'JetBrains Mono', 'Fira Code', monospace",
    },
    # 1 — Wide/spaced editorial
    {
        "name": "editorial",
        "font_import": "",
        "font_stack": "'Helvetica Neue', Arial, 'Segoe UI', sans-serif",
        "heading_weight": "900",
        "heading_tracking": "-0.04em",
        "body_size": "15px",
        "body_weight": "300",
        "body_tracking": "0.01em",
        "mono_stack": "'Courier New', Courier, monospace",
    },
    # 2 — Rounded/friendly
    {
        "name": "rounded",
        "font_import": "",
        "font_stack": "Nunito, 'Segoe UI', Roboto, system-ui, sans-serif",
        "heading_weight": "800",
        "heading_tracking": "-0.01em",
        "body_size": "14.5px",
        "body_weight": "500",
        "body_tracking": "0.005em",
        "mono_stack": "'JetBrains Mono', monospace",
    },
    # 3 — Monospace/technical
    {
        "name": "technical",
        "font_import": "",
        "font_stack": "'JetBrains Mono', 'Fira Code', 'Roboto Mono', monospace",
        "heading_weight": "700",
        "heading_tracking": "-0.01em",
        "body_size": "13px",
        "body_weight": "400",
        "body_tracking": "0",
        "mono_stack": "'JetBrains Mono', monospace",
    },
    # 4 — Serif/authoritative
    {
        "name": "serif",
        "font_import": "",
        "font_stack": "Georgia, 'Times New Roman', serif",
        "heading_weight": "700",
        "heading_tracking": "-0.02em",
        "body_size": "15px",
        "body_weight": "400",
        "body_tracking": "0.01em",
        "mono_stack": "'Courier New', monospace",
    },
]

_NAV_PATTERNS = [
    # 0 — Left sidebar
    {
        "name": "sidebar",
        "description": "Left sidebar navigation (200-240px wide) + top bar + main content area on the right",
        "layout_css": "display: grid; grid-template-columns: 220px 1fr; min-height: calc(100vh - 56px);",
    },
    # 1 — Top navigation only
    {
        "name": "topnav",
        "description": "Top navigation bar only — no sidebar. Full-width main content below",
        "layout_css": "display: block; padding: 24px;",
    },
    # 2 — Wide sidebar (command-palette style)
    {
        "name": "wide-sidebar",
        "description": "Wide left panel (280-320px) with icon+label nav items + large main content area",
        "layout_css": "display: grid; grid-template-columns: 300px 1fr; min-height: calc(100vh - 56px);",
    },
    # 3 — Horizontal tabs + content
    {
        "name": "tabs",
        "description": "Horizontal tab bar beneath the top nav — content area switches based on active tab",
        "layout_css": "display: flex; flex-direction: column; min-height: calc(100vh - 56px);",
    },
]

_SPACING_DENSITIES = [
    # 0 — Compact (data-heavy tools)
    {"name": "compact", "card_padding": "12px 14px", "section_gap": "10px", "body_padding": "14px"},
    # 1 — Balanced
    {"name": "balanced", "card_padding": "18px 20px", "section_gap": "16px", "body_padding": "22px"},
    # 2 — Airy/editorial
    {"name": "airy", "card_padding": "28px 32px", "section_gap": "28px", "body_padding": "36px"},
]

_ACCENT_TREATMENTS = [
    # 0 — Gradient hero
    {"name": "gradient-hero", "hero_bg": "background: linear-gradient(135deg, var(--bg) 0%, var(--surface) 100%);", "hero_accent": "background: radial-gradient(600px 400px at 30% 0%, color-mix(in srgb, var(--primary) 20%, transparent), transparent 70%);"},
    # 1 — Solid brand
    {"name": "solid-brand", "hero_bg": "background: var(--primary);", "hero_accent": ""},
    # 2 — Mesh gradient
    {"name": "mesh", "hero_bg": "background: var(--bg);", "hero_accent": "background: radial-gradient(800px 600px at 80% 0%, color-mix(in srgb, var(--accent) 15%, transparent), transparent 60%), radial-gradient(600px 400px at 10% 100%, color-mix(in srgb, var(--primary) 12%, transparent), transparent 60%);"},
    # 3 — High-contrast dark
    {"name": "high-contrast", "hero_bg": "background: #000;", "hero_accent": "background: linear-gradient(180deg, color-mix(in srgb, var(--primary) 8%, transparent) 0%, transparent 40%);"},
    # 4 — Diagonal split
    {"name": "diagonal-split", "hero_bg": "background: var(--bg);", "hero_accent": "background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 18%, transparent) 0%, transparent 50%);"},
    # 5 — Aurora / animated-feel
    {"name": "aurora", "hero_bg": "background: var(--bg);", "hero_accent": "background: conic-gradient(from 180deg at 50% 50%, color-mix(in srgb, var(--primary) 12%, transparent), color-mix(in srgb, var(--accent) 8%, transparent), transparent 60%);"},
]

# ── Layout Archetypes — macro structural personality of the entire product ──
_LAYOUT_ARCHETYPES = [
    # 0 — Dashboard command center: sidebar + dense data panels
    {
        "name": "command-center",
        "description": "Dense command-center dashboard. Left sidebar (200-240px) with icon nav, main content area with KPI tiles, data tables, activity feed. Think Linear or Vercel dashboard.",
        "structure_hint": "sidebar nav | main: KPI row + chart + table ; compact spacing; breadcrumb top bar",
    },
    # 1 — Bento mosaic: asymmetric tile layout
    {
        "name": "bento-mosaic",
        "description": "Bento-box mosaic: asymmetric CSS grid with tiles of different sizes. Some tiles span 2 columns, some are tall. Top nav only. No uniform card grid.",
        "structure_hint": "top nav | full-page bento grid: mix of 1x1, 2x1, 1x2, 2x2 tiles with rounded corners; hero tile top-left spanning 2 cols",
    },
    # 2 — Magazine editorial: full-bleed sections, bold typography
    {
        "name": "magazine",
        "description": "Editorial magazine layout. Full-bleed hero with large typography, horizontal rule separators, alternating full-width sections, pull quotes. Think Stripe or Linear marketing.",
        "structure_hint": "full-width hero (60vh) | alternating left/right content blocks | full-bleed color band section | footer; no card borders on body sections",
    },
    # 3 — Canvas/workspace: infinite-feel, floating panels
    {
        "name": "canvas-workspace",
        "description": "Canvas-style workspace. Dark background, floating panels/toolbars. Tool palette on left, property inspector on right, central work area. Think Figma or Miro.",
        "structure_hint": "floating left toolbar | center canvas area | floating right properties panel | top menubar; panels use box-shadow for depth, no visible page border",
    },
    # 4 — Split-screen: two balanced halves
    {
        "name": "split-screen",
        "description": "50/50 or 60/40 vertical split layout. Left side: rich visual/media/branding. Right side: forms, lists, detail pane. Works for auth, settings, and detail views.",
        "structure_hint": "left (45-50%): full-height gradient/image/brand side | right (50-55%): scrollable content; a single dividing vertical line or subtle border",
    },
    # 5 — Feed/timeline: vertically scrolling content stream
    {
        "name": "feed-timeline",
        "description": "Twitter/Slack-style feed. Left nav sidebar, center scrolling feed with cards, right sidebar with supplementary info or filters. Wide gutters around feed.",
        "structure_hint": "left nav (200px) | center feed (max 680px centered) | right sidebar (260px); feed items have avatar, timestamp, content; NOT a grid",
    },
    # 6 — Landing hero: marketing page with distinct sections
    {
        "name": "landing-hero",
        "description": "Polished SaaS landing page. Full-viewport hero with headline + CTA, feature grid section, social proof/testimonials, pricing cards, footer. Each section visually distinct.",
        "structure_hint": "sticky top nav | hero (90vh, gradient bg) | feature section (3-col icon grid) | social proof band | pricing section | footer; no app chrome",
    },
    # 7 — Minimal single-task: ultra-focused, lots of whitespace
    {
        "name": "minimal-focus",
        "description": "Ultra-minimal, single-purpose. Centered content, generous whitespace, one clear action hierarchy. No sidebars. Think Linear issue detail or Notion page.",
        "structure_hint": "minimal top nav | centered single-column (max 760px) | large heading | content body | action footer; no decorative panels or sidebars",
    },
]


def _derive_design_dna(project_context: str) -> dict:
    """Deterministically derive a full 8-dimension design DNA from the product name.

    Returns a dict with all design specs. Same product → same DNA every time.
    Different products get visually distinct identities.
    """
    import hashlib

    product_name = ""
    for line in (project_context or "").splitlines():
        if line.lower().startswith("product:"):
            product_name = line.split(":", 1)[-1].strip()
            break
    seed = product_name.lower() if product_name else "default"
    h = hashlib.md5(seed.encode()).hexdigest()

    # Use different byte ranges so each dimension is independent
    palette_idx      = int(h[0:4],  16) % len(_PALETTES)
    component_idx    = int(h[4:6],  16) % len(_COMPONENT_STYLES)
    typography_idx   = int(h[6:8],  16) % len(_TYPOGRAPHY_SPECS)
    nav_idx          = int(h[8:10], 16) % len(_NAV_PATTERNS)
    spacing_idx      = int(h[10:12],16) % len(_SPACING_DENSITIES)
    accent_idx       = int(h[12:14],16) % len(_ACCENT_TREATMENTS)
    archetype_idx    = int(h[14:16],16) % len(_LAYOUT_ARCHETYPES)

    return {
        "product_name": product_name or "Product",
        "palette":      _PALETTES[palette_idx],
        "component":    _COMPONENT_STYLES[component_idx],
        "typography":   _TYPOGRAPHY_SPECS[typography_idx],
        "nav":          _NAV_PATTERNS[nav_idx],
        "spacing":      _SPACING_DENSITIES[spacing_idx],
        "accent":       _ACCENT_TREATMENTS[accent_idx],
        "archetype":    _LAYOUT_ARCHETYPES[archetype_idx],
    }


def _archetype_html_skeleton(name: str) -> str:
    """Return a terse HTML/CSS structural template for the given archetype."""
    skeletons = {
        "command-center": """
    <div class="shell"> ← display:grid; grid-template-columns:220px 1fr
      <aside class="sidebar"> icon nav items </aside>
      <div class="main">
        <header class="topbar"> breadcrumb + avatar </header>
        <div class="kpi-strip"> ← display:flex; gap:12px; NOT a uniform 4-card row — use 1 wide hero-stat + 2-3 smaller
        <div class="body-row"> ← display:grid; grid-template-columns:2fr 1fr
          <section class="chart-area"> CSS bar chart (divs) </section>
          <section class="feed"> activity list </section>
        </div>
      </div>
    </div>""",

        "bento-mosaic": """
    <header class="topnav"> logo + links </header>
    <main class="bento-grid"> ← display:grid; grid-template-columns:repeat(4,1fr); grid-auto-rows:140px; gap:12px
      <div class="tile hero" style="grid-column:span 2; grid-row:span 2"> big hero tile </div>
      <div class="tile tall" style="grid-row:span 2"> tall narrow tile </div>
      <div class="tile"> 1×1 tile </div>
      <div class="tile wide" style="grid-column:span 2"> wide tile </div>
      <div class="tile"> 1×1 tile </div>
    </main>""",

        "magazine": """
    <nav class="topnav sticky"> logo + links + CTA </nav>
    <section class="hero full-bleed"> ← min-height:60vh; large headline; NO card border
    <section class="alternating-left"> text left | visual right </section>
    <section class="color-band full-bleed" style="background:var(--primary)"> pull-quote or stat </section>
    <section class="alternating-right"> visual left | text right </section>
    <footer> links </footer>""",

        "canvas-workspace": """
    <header class="menubar"> File Edit View + status </header>
    <div class="workspace"> ← display:grid; grid-template-columns:52px 1fr 280px; height:calc(100vh-40px)
      <aside class="tool-palette"> vertical icon tools </aside>
      <main class="canvas-area" style="background:#1a1a2e; overflow:auto"> artboard </main>
      <aside class="properties"> inspector fields </aside>
    </div>""",

        "split-screen": """
    <div class="split"> ← display:grid; grid-template-columns:45% 55%; min-height:100vh
      <div class="brand-side" style="background:var(--primary)"> logo + tagline + visuals </div>
      <div class="content-side" style="overflow-y:auto; padding:48px"> scrollable main content </div>
    </div>""",

        "feed-timeline": """
    <div class="app"> ← display:grid; grid-template-columns:200px 1fr 260px
      <nav class="left-nav"> icon + label links </nav>
      <main class="feed" style="max-width:680px; margin:0 auto; padding:24px"> feed items with avatar/timestamp </main>
      <aside class="right-panel"> filters + trending </aside>
    </div>""",

        "landing-hero": """
    <nav class="topnav sticky"> logo + links + CTA button </nav>
    <section class="hero" style="min-height:90vh; background:gradient"> headline + subhead + CTAs + hero visual </section>
    <section class="features"> 3-col icon-grid feature cards </section>
    <section class="social-proof"> testimonial band </section>
    <section class="pricing"> pricing tier cards </section>
    <footer> columns of links </footer>""",

        "minimal-focus": """
    <nav class="topnav minimal"> logo (left) + minimal links (right) </nav>
    <main style="max-width:760px; margin:0 auto; padding:48px 24px">
      <h1 class="display"> large heading </h1>
      <div class="content-body"> primary content, no card containers </div>
      <footer class="action-footer"> sticky or inline action buttons </footer>
    </main>""",
    }
    return skeletons.get(name, "Build layout specific to this archetype. Avoid uniform card grids.")


def _format_design_dna_block(dna: dict) -> str:
    """Format the full design DNA as a concrete CSS + instruction block for the prompt."""
    p = dna["palette"]
    c = dna["component"]
    t = dna["typography"]
    n = dna["nav"]
    s = dna["spacing"]
    a = dna["accent"]
    arch = dna.get("archetype", _LAYOUT_ARCHETYPES[0])
    card_r = c.get("card_radius", c["radius"])
    layout_hint = c.get("layout_hint", "")

    # Determine theme label from bg luminance (simple: if bg starts with a very dark hex, it's dark)
    bg_hex = p['bg'].lstrip('#')
    try:
        r, g, b = int(bg_hex[0:2],16), int(bg_hex[2:4],16), int(bg_hex[4:6],16)
        luminance = 0.299*r + 0.587*g + 0.114*b
        theme_mode = "DARK" if luminance < 80 else "LIGHT"
    except Exception:
        theme_mode = "DARK"

    forbidden_bg = ("white, #fff, #ffffff, #fafafa, #f9fafb, #f5f5f5, #f0f0f0"
                    if theme_mode == "DARK"
                    else "black, #000, #000000, #0a0a0a, #111, #111111")

    return f"""
══════════════════════════════════════════════════════
THIS PRODUCT'S DESIGN DNA — ALL screens must match this exactly
THEME MODE: {theme_mode}  ← every screen must be {theme_mode}, no exceptions
══════════════════════════════════════════════════════

## 1. REQUIRED CSS FOUNDATION
Copy this block VERBATIM — no changes, no additions, no overrides:

  :root {{
    --bg:      {p['bg']};
    --surface: {p['surface']};
    --border:  {p['border']};
    --primary: {p['primary']};
    --accent:  {p['accent']};
    --text:    {p['text']};
    --muted:   {p['muted']};
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    background-color: {p['bg']};
    color: {p['text']};
    font-family: {t['font_stack']};
    font-size: {t['body_size']};
    min-height: 100vh;
  }}

## 2. COMPONENT STYLE  ({c['name']})  — palette: {p['name']}
Cards/panels:    {c['card_css']}  border-radius: {card_r};
Primary buttons: {c['btn_css']}  border-radius: {c['radius']};
Text inputs:     {c['input_css']}  border-radius: {c['radius']};
Icon containers: {c.get('icon_container_css', 'background: color-mix(in srgb, var(--primary) 15%, transparent); border-radius: 8px; padding: 8px;')}
Status badges:   {c.get('badge_css', 'background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 700;')}
{('⚠️ Style note: ' + c['style_note']) if c.get('style_note') else ''}
{('Layout note: ' + layout_hint) if layout_hint else ''}

## 3. TYPOGRAPHY  ({t['name']})
  Headings (h1–h3):  font-weight: {t['heading_weight']}; letter-spacing: {t['heading_tracking']};
  Body text:         font-weight: {t['body_weight']}; letter-spacing: {t['body_tracking']};

## 4. NAVIGATION PATTERN  ({n['name']})
  {n['description']}
  Layout CSS: {n['layout_css']}

## 5. SPACING DENSITY  ({s['name']})
  Card padding: {s['card_padding']} | Section gap: {s['section_gap']} | Page padding: {s['body_padding']}

## 6. HERO / SECTION ACCENT  ({a['name']})
  {a['hero_bg']}  Overlay: {a['hero_accent']}

## 7. MACRO LAYOUT ARCHETYPE  ({arch['name']})  ← THE STRUCTURAL LAW — non-negotiable
  {arch['description']}
  Structure: {arch['structure_hint']}

  PAGE SKELETON — build HTML that EXACTLY follows this architecture:
  {_archetype_html_skeleton(arch['name'])}

## 8. STRICT RULES — VIOLATIONS WILL BREAK THE DESIGN
- THE #{arch['name'].upper()} ARCHETYPE IS LAW — build the skeleton above, not a generic card grid
- THIS IS A {theme_mode} THEME — NEVER use {forbidden_bg} as any background color
- The html/body background MUST be {p['bg']} — do NOT override it anywhere
- ONLY use CSS variables (--bg, --surface, --border, --primary, --accent, --text, --muted) for ALL colors
- NEVER introduce inline hex colors outside of the :root block above
- NEVER introduce purple (#7c5cff, #6f59ff, #8b5cf6) unless --primary above is already purple
- FOLLOW the macro layout archetype (#7) — avoid uniform 3/4-column card grids
- NO lorem ipsum — all copy must be specific to this product
══════════════════════════════════════════════════════
"""


def _pick_palette(project_context: str) -> dict:
    """Kept for backward compat — use _derive_design_dna for new code."""
    return _derive_design_dna(project_context)["palette"]


def _build_project_context(project: Project, cdo_analysis: CSuiteAnalysis | None, db=None) -> str:
    idea_context = ""
    if project.idea and project.idea.content:
        idea_context = project.idea.content

    cdo_suggestions = ""
    if cdo_analysis and cdo_analysis.analysis:
        cdo_suggestions = cdo_analysis.analysis

    # Pull the Design System Foundation artifact if available
    design_system_text = ""
    if db is not None:
        dsf = db.query(Artifact).filter(
            Artifact.project_id == project.id,
            Artifact.artifact_type == ArtifactType.design_system,
            Artifact.status == AgentStatus.complete,
        ).first()
        if dsf and dsf.content:
            raw = dsf.content.get("text") if isinstance(dsf.content, dict) else str(dsf.content)
            if raw and raw.strip():
                design_system_text = raw.strip()
    return compose_project_context(
        product_name=project.name,
        description=project.description,
        target_audience=project.target_audience,
        idea=idea_context,
        cdo_analysis=cdo_suggestions,
        design_system_text=design_system_text,
    )


async def _discover_screens_from_context(project_context: str, user_id: str | None = None) -> list[dict]:
    """Return discovered screen definitions from LLM, with a safe fallback."""
    screen_system = """You are a senior product designer. Given a product description (including its Design System Foundation and CDO recommendations), determine ALL the screens/pages this product needs for a complete, polished MVP.

Do NOT limit yourself to a fixed number — infer the right count from the product's complexity:
- A simple tool might need 4-5 screens
- A SaaS platform might need 8-12 screens
- An e-commerce app might need 10-15 screens
Aim for completeness, not brevity.

Respond with ONLY valid JSON:
{
    "screens": [
        {
            "name": "Dashboard",
            "description": "Main user dashboard showing key metrics and recent activity",
            "priority": "critical"
        }
    ]
}

Priority: "critical", "important", or "nice_to_have"
Order by priority (critical first).
MANDATORY screens (always include as critical, in this order):
1. Landing Page — marketing/conversion page with hero, features, testimonials, CTA, footer
2. Login / Register — authentication pages with login and signup forms
3. Dashboard — main user dashboard with metrics, activity, and navigation
Then add 2-4 more product-specific screens as important or nice_to_have."""

    try:
        mc = _resolve_design_model(user_id)
        call_kwargs = _build_litellm_kwargs(mc, [
            {"role": "system", "content": screen_system},
            {"role": "user", "content": project_context},
        ], temperature=0.7, max_tokens=2000)
        resp = await litellm.acompletion(**call_kwargs)
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        import re
        match = re.search(r'\{[\s\S]*\}', text)
        screens_data = json.loads(match.group() if match else text)
        screens = screens_data.get("screens", [])
        if not isinstance(screens, list):
            screens = []
    except Exception:
        screens = []

    if not screens:
        screens = [
            {"name": "Landing Page", "description": "Main marketing landing page with hero, features, testimonials, pricing, CTA, and footer", "priority": "critical"},
            {"name": "Login / Register", "description": "Authentication pages with login and signup forms, mock auth flow", "priority": "critical"},
            {"name": "Dashboard", "description": "User dashboard with sidebar navigation, KPI metrics, activity feed, and data tables", "priority": "critical"},
            {"name": "Settings", "description": "User settings and preferences", "priority": "important"},
        ]

    # Ensure Landing Page first + critical
    filtered = [s for s in screens if str(s.get("name", "")).strip().lower() != "landing page"]
    landing = {
        "name": "Landing Page",
        "description": "Stunning marketing + conversion page with hero, features, testimonials, pricing, CTA, and footer",
        "priority": "critical",
    }

    # Ensure Login/Register is present
    auth_names = {"login", "register", "sign up", "signup", "login / register", "authentication", "auth"}
    has_auth = any(str(s.get("name", "")).strip().lower() in auth_names for s in filtered)
    if not has_auth:
        filtered.insert(0, {
            "name": "Login / Register",
            "description": "Authentication pages with beautiful login and signup forms",
            "priority": "critical",
        })

    return [landing] + filtered


def _priority_to_enum(priority: str | None) -> MockupPriority:
    mapping = {
        "critical": MockupPriority.high,
        "important": MockupPriority.medium,
        "nice_to_have": MockupPriority.low,
        "high": MockupPriority.high,
        "medium": MockupPriority.medium,
        "low": MockupPriority.low,
    }
    return mapping.get((priority or "medium").lower(), MockupPriority.medium)


def _strip_code_fences(text: str) -> str:
    out = (text or "").strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[1] if "\n" in out else out[3:]
        if out.endswith("```"):
            out = out[:-3]
    return out.strip()


def _screen_variant(screen_desc: str) -> str:
    return _screen_variant_impl(screen_desc)


def _fallback_mockup_html(project_name: str, screen_desc: str, project_context: str | None = None) -> str:
    """Deterministic visible fallback UI when model output is invalid/blank."""
    html = _fallback_mockup_html_impl(project_name, screen_desc)
    if project_context:
        try:
            return _enforce_theme_css(html, _derive_design_dna(project_context))
        except Exception:
            return html
    return html


def _fallback_mockup_html_LEGACY(project_name: str, screen_desc: str) -> str:
    """LEGACY — superseded by design_fallbacks.py. Safe to delete in next cleanup."""
    title = (screen_desc.split("\n", 1)[0].replace("Screen:", "").strip() or "Product Screen")
    subtitle = ""
    if "Description:" in screen_desc:
        subtitle = screen_desc.split("Description:", 1)[1].strip()

    variant = _screen_variant(screen_desc)
    if variant == "auth":
        action_text = "Sign Up" if "sign up" in title.lower() else "Sign In"
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{ --bg:#0a0d1a; --panel:#121832; --border:#2d3a66; --text:#e8eeff; --muted:#9db0de; --primary:#7c5cff; --secondary:#20305a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; color:var(--text); min-height:100vh; background:radial-gradient(900px 550px at 18% 0%,#253177 0%,transparent 65%), var(--bg); display:grid; place-items:center; padding:24px; }}
    .shell {{ width:min(960px,100%); background:rgba(17,23,42,.76); border:1px solid var(--border); border-radius:20px; display:grid; grid-template-columns:1.1fr .9fr; overflow:hidden; }}
    .promo {{ padding:34px; border-right:1px solid var(--border); }}
    .badge {{ display:inline-block; padding:4px 10px; font-size:11px; border-radius:999px; background:#1a2953; border:1px solid var(--border); color:#c2d3ff; }}
    .promo h1 {{ margin:14px 0 10px; font-size:34px; line-height:1.1; }}
    .promo p {{ margin:0; color:var(--muted); line-height:1.55; }}
    .points {{ margin-top:20px; display:grid; gap:10px; color:#cdd8f8; font-size:14px; }}
    .form {{ padding:34px; display:grid; gap:12px; }}
    label {{ font-size:12px; color:var(--muted); }}
    input {{ width:100%; height:42px; border-radius:10px; border:1px solid var(--border); background:#0c1228; color:var(--text); padding:0 12px; }}
    .row {{ display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--muted); }}
    .btn {{ height:44px; border-radius:10px; border:1px solid var(--border); background:var(--secondary); color:var(--text); font-weight:600; cursor:pointer; }}
    .btn.primary {{ border:0; background:linear-gradient(90deg,#7c5cff,#5e7bff); }}
    .foot {{ text-align:center; font-size:12px; color:var(--muted); }}
    @media (max-width: 860px) {{ .shell {{ grid-template-columns:1fr; }} .promo {{ border-right:0; border-bottom:1px solid var(--border); }} }}
  </style>
</head>
<body>
  <main class=\"shell\">
    <section class=\"promo\">
      <div class=\"badge\">{project_name}</div>
      <h1>{title}</h1>
      <p>{subtitle or "Authenticate quickly and continue your workflow without interruption."}</p>
      <div class=\"points\">
        <div>Secure email and password authentication</div>
        <div>Google OAuth for faster onboarding</div>
        <div>Session persistence across devices</div>
      </div>
    </section>
    <section class=\"form\">
      <div><label>Email</label><input type=\"email\" placeholder=\"you@company.com\" /></div>
      <div><label>Password</label><input type=\"password\" placeholder=\"Enter your password\" /></div>
      <div class=\"row\"><span><input type=\"checkbox\" style=\"height:auto;width:auto;vertical-align:middle;margin-right:6px\" />Remember me</span><span>Forgot password?</span></div>
      <button class=\"btn primary\">{action_text}</button>
      <button class=\"btn\">Continue with Google</button>
      <div class=\"foot\">No account yet? Create one</div>
    </section>
  </main>
</body>
</html>"""

    if variant == "landing":
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{ --bg:#080b18; --panel:#111934; --border:#2a3b6b; --text:#ecf0ff; --muted:#9aabd8; --primary:#6f59ff; --accent:#38c993; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; background:radial-gradient(1400px 700px at 75% -15%,#2f2d8a 0%,transparent 62%), var(--bg); color:var(--text); }}
    .wrap {{ width:min(1120px,100%); margin:0 auto; padding:22px; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; }}
    .btn {{ height:40px; border-radius:10px; border:1px solid var(--border); background:#162349; color:var(--text); padding:0 14px; font-weight:600; }}
    .btn.primary {{ border:0; background:linear-gradient(90deg,#6f59ff,#4f85ff); }}
    .hero {{ display:grid; grid-template-columns:1.2fr .8fr; gap:18px; margin-top:20px; }}
    .card {{ border:1px solid var(--border); border-radius:16px; background:rgba(17,25,52,.78); padding:20px; }}
    h1 {{ margin:8px 0 10px; font-size:48px; line-height:1.05; }}
    p {{ margin:0; color:var(--muted); line-height:1.55; }}
    .cta {{ margin-top:20px; display:flex; gap:10px; flex-wrap:wrap; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }}
    .feature h3 {{ margin:0 0 8px; }}
    .price {{ font-size:32px; font-weight:700; margin:8px 0; }}
    .quote {{ margin-top:16px; border-left:3px solid var(--accent); padding-left:10px; color:#d4e8ff; font-size:14px; }}
    @media (max-width: 960px) {{ h1 {{ font-size:36px; }} .hero, .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <header class=\"top\">
      <strong>{project_name}</strong>
      <div style=\"display:flex;gap:8px\"><button class=\"btn\">View Demo</button><button class=\"btn primary\">Start Free</button></div>
    </header>
    <section class=\"hero\">
      <article class=\"card\">
        <div style=\"font-size:12px;color:#b4c5f7\">Launch Faster</div>
        <h1>{title}</h1>
        <p>{subtitle or "A high-conversion landing experience with clear value messaging, trust signals, and direct CTAs."}</p>
        <div class=\"cta\"><button class=\"btn primary\">Get Started</button><button class=\"btn\">Book a Demo</button></div>
      </article>
      <aside class=\"card\">
        <h3 style=\"margin:0 0 6px\">Trusted by product teams</h3>
        <p>Used by startups and enterprise teams to ship polished experiences quickly.</p>
        <div class=\"quote\">\"Setup took minutes and the conversion uplift was immediate.\"</div>
      </aside>
    </section>
    <section class=\"grid\">
      <article class=\"card feature\"><h3>Faster onboarding</h3><p>Guided setup that gets users to value quickly.</p></article>
      <article class=\"card feature\"><h3>Actionable analytics</h3><p>See conversion blockers and fix friction fast.</p></article>
      <article class=\"card feature\"><h3>Reusable components</h3><p>Maintain visual consistency at scale.</p></article>
    </section>
    <section class=\"card\" style=\"margin-top:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;\">
      <div><div style=\"font-size:12px;color:#a8bbe9\">Starting at</div><div class=\"price\">$29<span style=\"font-size:16px;color:var(--muted)\">/month</span></div></div>
      <button class=\"btn primary\">Choose Plan</button>
    </section>
  </div>
</body>
</html>"""

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{ --bg:#0a0d1a; --panel:#11172a; --border:#2a3557; --text:#e8eeff; --muted:#9aa7ce; --primary:#7c5cff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; background:radial-gradient(1200px 700px at 10% -10%, #1a2455 0%, transparent 60%), var(--bg); color:var(--text); min-height:100vh; }}
    .top {{ height:64px; border-bottom:1px solid var(--border); background:rgba(9,13,27,.9); display:flex; align-items:center; justify-content:space-between; padding:0 22px; }}
    .btn {{ border:1px solid var(--border); background:#151c33; color:var(--text); border-radius:10px; padding:10px 14px; font-weight:600; font-size:13px; }}
    .btn.primary {{ background:linear-gradient(90deg,var(--primary),#5e7bff); border:0; }}
    .layout {{ display:grid; grid-template-columns:260px 1fr; gap:16px; padding:18px; }}
    .card {{ background:#0f1529; border:1px solid var(--border); border-radius:12px; padding:14px; }}
    .muted {{ color:var(--muted); font-size:13px; line-height:1.45; }}
    .list {{ display:grid; gap:10px; margin-top:12px; }}
    @media (max-width:980px) {{ .layout {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header class=\"top\">
    <strong>{project_name}</strong>
    <div style=\"display:flex; gap:8px;\"><button class=\"btn\">Secondary</button><button class=\"btn primary\">Primary Action</button></div>
  </header>
  <div class=\"layout\">
    <aside class=\"card\"><div class=\"muted\">Navigation</div><div class=\"list\"><div class=\"card\">Overview</div><div class=\"card\">Analytics</div><div class=\"card\">Team</div></div></aside>
    <main class=\"card\"><h1 style=\"margin-top:0\">{title}</h1><p class=\"muted\">{subtitle or "High-fidelity fallback layout generated to ensure visible UI rendering."}</p><section class=\"list\"><article class=\"card\">Primary panel content</article><article class=\"card\">Secondary panel content</article><article class=\"card\">Actionable controls</article></section></main>
  </div>
</body>
</html>"""


def _enforce_theme_css(html: str, dna: dict) -> str:
    """Post-process: inject body background/color override and strip rogue light backgrounds."""
    if not html:
        return html
    p = dna["palette"]
    bg = p["bg"]
    text = p["text"]

    # Compute whether this is dark or light
    bg_hex = bg.lstrip("#")
    try:
        r, g, b = int(bg_hex[0:2],16), int(bg_hex[2:4],16), int(bg_hex[4:6],16)
        is_dark = (0.299*r + 0.587*g + 0.114*b) < 80
    except Exception:
        is_dark = True

    # Build the override style block
    override = (
        f"\n  /* === THEME LOCK === */\n"
        f"  html, body {{ background-color: {bg} !important; color: {text} !important; }}\n"
    )

    # Inject right after the opening <style> tag if present, else append a new <style>
    if re.search(r"<style[^>]*>", html, flags=re.I):
        html = re.sub(
            r"(<style[^>]*>)",
            r"\1" + override,
            html, count=1, flags=re.I
        )
    else:
        html = html.replace("</head>", f"<style>{override}</style>\n</head>", 1)

    if is_dark:
        # Replace hardcoded white/near-white backgrounds that override our dark theme
        # Only replace standalone #fff/#ffffff/white outside of the :root block
        html = re.sub(
            r"background(?:-color)?\s*:\s*(?:#fff(?:fff)?|white|#fafafa|#f9fafb|#f8fafc|#f5f5f5|#f0f0f0)\b",
            "background-color: var(--surface)",
            html, flags=re.I
        )
        # Replace color: #000 / black on body-level text that would be invisible on dark bg
        html = re.sub(
            r"(?<=\s)color\s*:\s*(?:#000(?:000)?|black)\b",
            "color: var(--text)",
            html, flags=re.I
        )

    return html


def _project_name_from_context(project_context: str) -> str:
    return extract_product_name(project_context)


def _screen_specific_requirements(screen_desc: str) -> str:
    return _screen_specific_requirements_impl(screen_desc)


def _get_mockup_reference_summaries(
    db: Session,
    project_id: str,
    *,
    exclude_mockup_id: str | None = None,
    limit: int = 8,
) -> list[dict[str, str]]:
    query = (
        db.query(DesignMockup)
        .filter(
            DesignMockup.project_id == project_id,
            DesignMockup.status.in_([MockupStatus.complete, MockupStatus.approved]),
        )
        .order_by(DesignMockup.sort_order.asc())
    )
    if exclude_mockup_id:
        query = query.filter(DesignMockup.id != exclude_mockup_id)

    refs = []
    for m in query.limit(limit).all():
        refs.append({
            "name": m.screen_name,
            "description": m.description or "",
            "status": m.status.value,
        })
    return refs


def _looks_like_ai_cliche_html(code: str) -> list[str]:
    lower = (code or "").lower()
    issues: list[str] = []

    if any(token in lower for token in ("#7c5cff", "#8338ec", "#a78bfa", "#ff00", "#00e5ff")) and "gradient" in lower:
        issues.append("Palette leans toward default AI purple/cyan gradient clichés.")
    if lower.count("box-shadow") >= 8 and lower.count("linear-gradient") >= 6:
        issues.append("Visual treatment may be over-stylized instead of product-authentic.")
    if lower.count("kpi") >= 2 or lower.count("metric") >= 4:
        issues.append("Layout appears too close to a generic dashboard template.")
    if "lorem ipsum" in lower or "placeholder" in lower:
        issues.append("Output still contains placeholder content.")

    return issues


def _build_design_brief_text(
    project_context: str,
    *,
    screen_desc: str,
    direction: str | None = None,
    references: list[dict[str, str]] | None = None,
    compact: bool = False,
) -> tuple[dict, dict, str]:
    brief = build_design_brief(
        project_context,
        screen_desc=screen_desc,
        direction=direction,
        approved_mockups=references,
    )
    compiled_spec = build_compiled_design_spec(
        project_context,
        screen_desc=screen_desc,
        direction=direction,
        approved_mockups=references,
    )
    combined = "\n\n".join([
        format_compiled_design_spec(compiled_spec, compact=compact),
        format_design_brief(brief, compact=compact),
    ]).strip()
    return brief, compiled_spec, combined


def _looks_like_react_or_tsx(code: str) -> bool:
    snippet = (code or "")[:1200]
    patterns = [
        r"\bimport\s+React\b",
        r"\bexport\s+default\b",
        r"\bfunction\s+[A-Z][A-Za-z0-9_]*\s*\(",
        r"\breturn\s*\(",
        r"className=",
    ]
    return any(re.search(p, snippet) for p in patterns)


def _ensure_html_document(code: str) -> str:
    c = _strip_code_fences(code)
    if "<html" in c.lower() or "<!doctype" in c.lower():
        return c
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Design Mockup</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #0b1020; color: #e5e7eb; }}
  </style>
</head>
<body>
{c}
</body>
</html>"""


def _is_visually_thin_html(code: str) -> bool:
    c = (code or "")
    # Quick quality gate: ensure there is enough structure and visible text
    tags = len(re.findall(r"<(header|nav|main|section|article|aside|div|button|input|form|card|ul|li|table)\b", c, flags=re.I))
    text_len = len(re.sub(r"<[^>]+>", "", c).strip())
    has_layout = re.search(r"display\s*:\s*(grid|flex)", c, flags=re.I) is not None
    return tags < 8 or text_len < 140 or not has_layout


def _strip_script_tags(code: str) -> str:
    """Remove all <script>...</script> blocks so LLM output with JS is still renderable."""
    return re.sub(r"<script[\s\S]*?</script>", "", code, flags=re.I).strip()


def _is_renderable_ui_html(code: str) -> bool:
    # Strip scripts first — we never run JS in the preview, don't want to reject good HTML
    c = _strip_script_tags(code or "")
    if not c.strip():
        return False
    lower = c.lower()
    if "<body" not in lower and "<div" not in lower and "<main" not in lower:
        return False
    if _looks_like_react_or_tsx(c):
        return False
    if _is_visually_thin_html(c):
        return False
    # Must have enough visible text after removing style/tag blocks
    content = re.sub(r"<style[\s\S]*?</style>", "", c, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", content)
    return len(re.sub(r"\s+", " ", text).strip()) >= 80


def _is_visually_complete_html(code: str) -> bool:
    """Completeness gate: only retry truly skeletal/empty designs."""
    c = re.sub(r"<style[\s\S]*?</style>", "", code, flags=re.I)
    c = re.sub(r"<script[\s\S]*?</script>", "", c, flags=re.I)
    tags = len(re.findall(r"<(header|nav|main|section|article|aside|footer|div|button|input|form|ul|li|table|p|h[1-6])\b", c, flags=re.I))
    text = re.sub(r"<[^>]+>", " ", c)
    text_len = len(re.sub(r"\s+", " ", text).strip())
    interactive = len(re.findall(r"<(button|input|a\s|a>|img|h[1-6])\b", c, flags=re.I))
    # Loosened: only reject truly empty/skeletal output, not just "thin but real"
    return tags >= 8 and text_len >= 150 and interactive >= 2


def _screen_specific_quality_notes(code: str, screen_desc: str) -> list[str]:
    c = re.sub(r"<style[\s\S]*?</style>", "", code or "", flags=re.I)
    lower = c.lower()
    text = re.sub(r"<[^>]+>", " ", c)
    text_len = len(re.sub(r"\s+", " ", text).strip())
    section_like = len(re.findall(r"<(header|nav|main|section|article|aside|footer|form|table|ul|ol)\b", c, flags=re.I))
    button_count = len(re.findall(r"<button\b", c, flags=re.I))
    input_count = len(re.findall(r"<(input|select|textarea)\b", c, flags=re.I))
    row_count = len(re.findall(r"<(tr|li)\b", c, flags=re.I))
    variant = _screen_variant(screen_desc)
    screen_lower = (screen_desc or "").lower()
    notes: list[str] = []

    if text_len < 260 or section_like < 3:
        notes.append("The screen feels underfilled; add more role-appropriate content blocks, support details, and realistic UI density.")

    if variant == "settings" and (input_count < 4 or button_count < 2):
        notes.append("Settings screens must include multiple populated settings groups, clear save/cancel actions, and enough controls to feel production-ready.")

    if variant in ("dashboard", "analytics") and not any(token in lower for token in ("chart", "trend", "activity", "alerts", "report", "overview")):
        notes.append("Analytical screens need a clear primary data surface plus supporting context, not just isolated cards or headings.")

    if variant == "list" and row_count < 4:
        notes.append("List and gallery screens need a convincingly populated set of rows or cards rather than a sparse placeholder layout.")

    if variant == "detail" and not any(token in lower for token in ("status", "priority", "activity", "metadata", "details", "comments")):
        notes.append("Detail screens should show both primary content and supporting metadata or activity, not a mostly empty body.")

    if "alert" in screen_lower and not any(token in lower for token in ("email", "sms", "push", "threshold", "digest", "notification")):
        notes.append("Alert configuration screens should show real notification rules, channels, thresholds, or escalation settings instead of an empty shell.")

    if any(token in screen_lower for token in ("log", "history", "timeline", "intervention")) and row_count < 3:
        notes.append("Log and history screens should contain multiple visible entries, timestamps, or recent records so the page feels active and complete.")

    deduped: list[str] = []
    for note in notes:
        if note not in deduped:
            deduped.append(note)
    return deduped


async def _transform_to_static_html(raw_code: str, screen_desc: str, project_context: str, user_id: str | None = None) -> str:
    """Convert TSX/fragment-like output into renderable static HTML/CSS."""
    dna = _derive_design_dna(project_context)
    dna_block = _format_design_dna_block(dna)
    bg = dna["palette"]["bg"]
    bg_hex = bg.lstrip("#")
    try:
        _r, _g, _b = int(bg_hex[0:2],16), int(bg_hex[2:4],16), int(bg_hex[4:6],16)
        _theme = "DARK" if (0.299*_r + 0.587*_g + 0.114*_b) < 80 else "LIGHT"
        _forbidden = "white, #fff, #ffffff, #fafafa" if _theme == "DARK" else "black, #000"
    except Exception:
        _theme, _forbidden, bg = "DARK", "white, #fff, #ffffff", bg

    system = f"""Convert the provided UI code into a COMPLETE standalone HTML document.

{dna_block}

Rules:
- Output ONLY HTML + CSS (no JavaScript, no JSX/TSX, no imports/exports, no className)
- Include <!DOCTYPE html>, <html>, <head>, <style>, and <body>
- MUST start <style> with the :root vars and html/body rules from the design DNA above, verbatim
- This is a {_theme} THEME — body background MUST be {bg}. NEVER use {_forbidden}.
- Render a rich visible interface with at least 6 visible UI elements
- Content and layout must match the target screen — not a generic dashboard
- Do not return markdown fences or explanations
{_screen_specific_requirements(screen_desc)}
"""
    mc = _resolve_design_model(user_id)
    call_kwargs = _build_litellm_kwargs(mc, [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Project context:\n{project_context}\n\nScreen:\n{screen_desc}\n\nCode to convert:\n{raw_code}",
        },
    ], temperature=0.4, max_tokens=4000)
    resp = await litellm.acompletion(**call_kwargs)
    result = _strip_code_fences(resp.choices[0].message.content.strip())
    return _enforce_theme_css(result, dna)


# ── Schemas ──────────────────────────────────────────────────────────────────

class RevisionRequest(BaseModel):
    notes: str

class GenerateAllRequest(BaseModel):
    design_mode: str = "dna"  # "dna" | "ai_free"
    direction: Optional[str] = None  # chosen direction description/style to follow

class AddScreenRequest(BaseModel):
    name: str
    description: str = ""
    priority: str = "important"


# ── Design Directions ────────────────────────────────────────────────────────

TARGET_DIRECTION_COUNT = 10


def _fallback_direction_proposals() -> list[dict]:
    return [
        {"name": "Editorial Trust", "description": "Composed, typographic, and trustworthy with strong hierarchy", "palette": ["#F6F2EA", "#FFFDF8", "#3D5A73", "#C98B4B", "#1E1B18"], "style_keywords": ["editorial", "precise", "credible"], "layout_approach": "Structured columns with strong information hierarchy"},
        {"name": "Soft Humanist", "description": "Approachable, warm, and human-centered with calm surfaces", "palette": ["#F7F3EC", "#FFFDF9", "#5E7C6B", "#C9865B", "#2A2926"], "style_keywords": ["warm", "human", "calm", "refined"], "layout_approach": "Breathing-room layout with gentle grouping and low-friction forms"},
        {"name": "Operational Clarity", "description": "Discipline and clarity for dense workflows without generic dashboard clichés", "palette": ["#F4F7FA", "#FFFFFF", "#1F4E79", "#4FA3A5", "#17212B"], "style_keywords": ["systematic", "clear", "analytical"], "layout_approach": "Information-dense shell with focused primary and secondary work zones"},
        {"name": "Material Depth", "description": "Layered surfaces and tactile controls with controlled depth", "palette": ["#10151C", "#18212B", "#8EA4BF", "#D2A679", "#E7EDF3"], "style_keywords": ["layered", "tactile", "composed"], "layout_approach": "Stacked depth cues with framed content and measured contrast"},
        {"name": "Expressive Brand System", "description": "Memorable and brand-forward with stronger personality and compositional rhythm", "palette": ["#FBF6F0", "#FFFDFC", "#A14D3F", "#2F7A71", "#1D1B1A"], "style_keywords": ["distinctive", "brand-led", "crafted"], "layout_approach": "Hero-led composition with branded moments and editorial rhythm"},
        {"name": "Field-Ready Utility", "description": "Direct, durable, and high-contrast for operational environments where speed matters", "palette": ["#F3F0E8", "#FFFDF9", "#2E3A2F", "#C97B2A", "#191A18"], "style_keywords": ["rugged", "practical", "high-contrast"], "layout_approach": "Utility-first framing with strong action zones and minimal ornament"},
        {"name": "Clinical Precision", "description": "Measured and technical with disciplined data presentation and low-noise surfaces", "palette": ["#F5F8FA", "#FFFFFF", "#2F5D7C", "#7BA7BC", "#13202B"], "style_keywords": ["precise", "clinical", "disciplined"], "layout_approach": "Structured analytical bands with prominent evidence and annotation areas"},
        {"name": "Botanical Journal", "description": "Research-oriented and organic, with quiet type and natural material references", "palette": ["#F3F0E6", "#FCFAF4", "#5A6B52", "#B49A46", "#263026"], "style_keywords": ["botanical", "scholarly", "quiet"], "layout_approach": "Paper-like sections with annotated callouts and calm asymmetry"},
        {"name": "Pre-Dawn Triage", "description": "Low-light monitoring aesthetic for early-morning response workflows and live checks", "palette": ["#0D1320", "#182033", "#6FA3D9", "#E6B655", "#E8EEF8"], "style_keywords": ["night-ops", "focused", "monitoring"], "layout_approach": "Compact command surfaces with clear status hierarchies and restrained glow"},
        {"name": "Acoustic Minimalist", "description": "Swiss-influenced reduction centered on signal clarity, restraint, and breathing room", "palette": ["#F7F7F2", "#FFFFFF", "#2C3E73", "#E08A3B", "#17191C"], "style_keywords": ["minimal", "signal-led", "refined"], "layout_approach": "Sparse but deliberate grids with one strong focal module per section"},
    ]

async def _generate_direction_proposals(project_context: str, user_id: str | None = None) -> list[dict]:
    """Ask LLM for 10 completely different design direction proposals."""
    _, _, brief_text = _build_design_brief_text(
        project_context,
        screen_desc="Direction exploration for the overall product",
        compact=True,
    )
    system = f"""You are a world-class creative director. Given a product description, propose {TARGET_DIRECTION_COUNT} COMPLETELY DIFFERENT design directions. Each direction should be visually and stylistically distinct from the others, while still feeling like something a senior designer might seriously propose for this product.

Respond with ONLY valid JSON:
{{
    "directions": [
        {{
            "name": "Midnight Luxe",
            "description": "Dark, premium aesthetic with gold accents and editorial typography",
            "palette": ["#0A0E1A", "#1A1F36", "#D4AF37", "#F5F0E8", "#8B7355"],
            "style_keywords": ["dark", "premium", "editorial", "gold-accent"],
            "layout_approach": "Full-bleed hero sections with asymmetric grid, magazine-style typography"
        }}
    ]
}}

RULES:
- Exactly {TARGET_DIRECTION_COUNT} directions
- palette: array of exactly 5 hex colours [bg, surface, primary, accent, text]
- Each direction must feel COMPLETELY different in composition, palette mood, and typography attitude
- Offer real variety across restrained, expressive, light, dark, editorial, or product-heavy directions where it makes sense
- style_keywords: 3-5 evocative words
- layout_approach: brief description of the structural/spatial philosophy
- Avoid default AI-looking color clichés and generic dark-purple-gradient SaaS directions
- Keep every direction product-credible and human-centered

{brief_text}"""

    try:
        mc = _resolve_design_model(user_id)
        call_kwargs = _build_litellm_kwargs(mc, [
            {"role": "system", "content": system},
            {"role": "user", "content": project_context},
        ], temperature=1.0, max_tokens=4500)
        resp = await litellm.acompletion(**call_kwargs)
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        match = re.search(r'\{[\s\S]*\}', text)
        data = json.loads(match.group() if match else text)
        directions = data.get("directions", [])
        if isinstance(directions, list) and len(directions) >= 1:
            normalized: list[dict] = []
            for i, item in enumerate(directions[:TARGET_DIRECTION_COUNT]):
                if not isinstance(item, dict):
                    continue
                palette = item.get("palette", [])
                if not isinstance(palette, list):
                    palette = []
                palette = [str(c) for c in palette[:5]]
                while len(palette) < 5:
                    palette.append(["#0A0E1A", "#1A1F36", "#7C5CFC", "#A78BFA", "#E8E0D4"][len(palette)])

                style_keywords = item.get("style_keywords", [])
                if not isinstance(style_keywords, list):
                    style_keywords = []

                normalized.append({
                    "name": str(item.get("name") or f"Direction {i + 1}"),
                    "description": str(item.get("description") or ""),
                    "palette": palette,
                    "style_keywords": [str(k) for k in style_keywords[:5]],
                    "layout_approach": str(item.get("layout_approach") or ""),
                })

            if normalized:
                existing_names = {item["name"].strip().lower() for item in normalized if item.get("name")}
                for fallback in _fallback_direction_proposals():
                    fallback_name = str(fallback.get("name") or "").strip().lower()
                    if fallback_name in existing_names:
                        continue
                    normalized.append(fallback)
                    existing_names.add(fallback_name)
                    if len(normalized) >= TARGET_DIRECTION_COUNT:
                        break
                return normalized[:TARGET_DIRECTION_COUNT]
    except Exception as e:
        print(f"❌ Direction proposals failed: {e}")

    # Fallback
    return _fallback_direction_proposals()


async def _generate_direction_swatch(direction: dict, product_name: str, user_id: str | None = None) -> str:
    """Generate a mini HTML swatch card (~380×240 viewport) for a design direction."""
    if not isinstance(direction, dict):
        direction = {}
    palette = direction.get("palette", ["#0A0E1A", "#1A1F36", "#7C5CFC", "#A78BFA", "#E8E0D4"])
    bg, surface, primary, accent, text_col = palette[0], palette[1], palette[2], palette[3], palette[4]
    name = direction.get("name", "Direction")
    desc = direction.get("description", "")
    layout = direction.get("layout_approach", "")
    keywords = direction.get("style_keywords", [])

    system = f"""You are a UI designer creating a MINI PREVIEW SWATCH (380×240px viewport) to showcase a design direction.
This is a tiny rendered card that gives a FEELING of the design — not a full page.

Direction: {name}
Description: {desc}
Style: {', '.join(keywords)}
Layout Philosophy: {layout}
Product: {product_name}

Palette:
- Background: {bg}
- Surface: {surface}
- Primary: {primary}
- Accent: {accent}
- Text: {text_col}

CREATE a complete <!DOCTYPE html> document that:
- Uses width: 380px, height: 240px as the body size (overflow: hidden)
- Shows a mini hero section with a bold headline (product name), a short tagline, a CTA button
- Uses the EXACT palette colours above
- Includes subtle CSS animations (fade-in, gentle gradient shift, or pulse)
- Makes it feel like a zoomed-out snapshot of a full page
- All text must be product-specific for "{product_name}"
- Raw HTML only, no markdown fences, no scripts"""

    try:
        mc = _resolve_design_model(user_id)
        call_kwargs = _build_litellm_kwargs(mc, [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Generate the swatch for: {name}"},
        ], temperature=0.9, max_tokens=2000)
        resp = await litellm.acompletion(**call_kwargs)
        raw = _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))
        return _ensure_html_document(raw)
    except Exception as e:
        print(f"⚠️ Swatch generation failed for {name}: {e}")
        # Inline fallback swatch
        return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:380px;height:240px;overflow:hidden;background:{bg};color:{text_col};font-family:system-ui,sans-serif;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:24px}}
h1{{font-size:22px;margin-bottom:8px;color:{text_col}}}
p{{font-size:11px;opacity:.7;margin-bottom:16px;max-width:90%}}
button{{background:{primary};color:#fff;border:none;padding:8px 20px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px {primary}40}}
.tag{{display:inline-block;background:{accent}20;color:{accent};font-size:9px;padding:2px 8px;border-radius:99px;margin-bottom:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px}}
</style></head><body>
<span class="tag">{name}</span>
<h1>{product_name}</h1>
<p>{desc}</p>
<button>Get Started</button>
</body></html>"""


# ── Human-centered mockup pipeline ───────────────────────────────────────────

def _build_product_system_guardrails(screen_desc: str, *, has_north_star: bool) -> str:
    variant = _screen_variant(screen_desc)
    density_requirements = {
        "auth": "Balance the promotional and form areas so neither side feels empty or placeholder-like.",
        "landing": "Carry the page through multiple finished sections beyond the hero so it reads like a launched marketing site.",
        "onboarding": "Show enough explanation, selectable options, and progress/navigation controls to feel like a real step in a flow.",
        "dashboard": "Anchor the page with a primary workflow surface and supporting secondary content instead of isolated summary cards.",
        "settings": "Populate the main area with multiple real settings groups and controls rather than a single sparse form block.",
        "detail": "Fill both the main pane and supporting metadata area with concrete information, status, and activity.",
        "list": "Show a convincingly populated set of rows or cards so the screen feels active and in use.",
        "analytics": "Provide a meaningful analytical composition with comparison, hierarchy, and supporting detail instead of a thin placeholder view.",
        "editor": "Use all major panels with credible tools, canvas content, and property controls; do not leave large blank slabs.",
        "app": "Use enough role-specific content and supporting detail that the page feels shipped, not staged.",
    }
    nav_rule = (
        "Reuse the same navigation pattern, shell proportions, and page framing established by the north-star."
        if has_north_star
        else "Choose one navigation pattern and shell structure that can anchor the rest of the product, then stay consistent with it."
    )
    return f"""Product-system lock:
- {nav_rule}
- Preserve the same spacing rhythm across screens: comparable section gaps, card padding, corner radius, border weight, and shadow intensity
- Keep typography roles stable: headline treatment, body copy tone, label sizing, and CTA emphasis should feel like one system
- Keep palette semantics stable: background for page canvas, surface for panels, primary for main interactive emphasis, accent for supporting emphasis only
- Adapt the screen to its function without switching to a different product genre or inventing a new brand language
- {density_requirements.get(variant, density_requirements['app'])}"""

def _build_mockup_system_prompt(
    *,
    product_name: str,
    screen_desc: str,
    brief_text: str,
    revision_context: str,
    direction: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
    creative_mode: str = "guided",
) -> str:
    direction_block = ""
    if direction:
        direction_block = f"""
User-requested direction:
{direction}

Treat this as a strong stylistic preference, but execute it with human product-design judgement rather than generic AI styling.
"""

    if north_star_css:
        html_ref_block = ""
        if north_star_html:
            truncated = north_star_html[:6000]
            if len(north_star_html) > 6000:
                truncated += "\n<!-- … truncated for reference -->"
            html_ref_block = f"""

North-star HTML reference:
```html
{truncated}
```"""

        return f"""You are a principal product designer building the NEXT SCREEN of an existing application.
This screen must feel like it belongs to the same product family as the approved/generated north-star, while still being fit for its own job.

Product name: "{product_name}"

{brief_text}
{direction_block}
North-star style contract:
```css
{north_star_css}
```
{html_ref_block}

Consistency requirements:
- Preserve the same product identity, visual language, tone, and navigation conventions as the north-star
- Reuse the same CSS variables, typography family, spacing logic, and surface treatment
- Treat this product-system lock as non-negotiable:
{_build_product_system_guardrails(screen_desc, has_north_star=True)}
- You may adapt composition and content hierarchy for this screen's purpose, but do not invent a new brand
- Keep the same level of realism and polish as a human product designer would
- Avoid generic AI-looking colors, empty glow-heavy styling, or synthetic dashboard clichés

Screen to design:
{screen_desc}

Functional requirements:
{_screen_specific_requirements(screen_desc)}

Output requirements:
- Output a complete standalone <!DOCTYPE html> document with embedded CSS
- Raw HTML only, no markdown fences, no explanations, no scripts
- Use realistic product-specific copy for "{product_name}"
- The screen must look finished, credible, and production-minded
{revision_context}"""

    freedom_line = (
        "You have broad creative freedom, but every decision must be justified by the product, audience, CDO guidance, and Design System Foundation."
        if creative_mode == "ai_free"
        else "Use creative judgement, but root the screen in the product reality, CDO guidance, and Design System Foundation."
    )

    return f"""You are an award-winning product designer with strong human craft judgement.
Your job is to create a screen that looks like an experienced designer made it, not like an AI app template.

Product name: "{product_name}"

{brief_text}
{direction_block}
{freedom_line}

Treat the compiled design spec above as a hard contract for non-negotiables, forbidden moves, and screen obligations.

Design principles:
- Do not default to dark mode, glassmorphism, purple/cyan AI gradients, or generic SaaS styling
- Let the product's industry, trust signals, and audience shape the visual language
- Choose layout, density, typography, and motion intentionally
- Be expressive when appropriate, restrained when appropriate, but always believable
- Surfaces, controls, and hierarchy must feel purposeful and product-specific
- Avoid placeholder-looking sections, repetitive equal-weight cards, and decorative styling with no UX reason

{_build_product_system_guardrails(screen_desc, has_north_star=False)}

Screen to design:
{screen_desc}

Functional requirements:
{_screen_specific_requirements(screen_desc)}

Output requirements:
- Output a complete standalone <!DOCTYPE html> document with embedded CSS
- Raw HTML only, no markdown fences, no explanations, no scripts
- Use realistic product-specific copy for "{product_name}"
- Make it feel like a real shipped product, not a template or wireframe
{revision_context}"""


async def _transform_to_static_html_authentic(
    raw_code: str,
    screen_desc: str,
    project_context: str,
    brief_text: str,
    user_id: str | None = None,
    direction: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
) -> str:
    mc = _resolve_design_model(user_id)
    product_name = _project_name_from_context(project_context)
    
    revision_context = """
Convert the provided UI code into a COMPLETE standalone HTML document.
Rules:
- Output ONLY HTML + CSS (no JavaScript, no JSX/TSX, no imports/exports, no className)
- Include <!DOCTYPE html>, <html>, <head>, <style>, and <body>
- Make the result visually credible and product-specific, not a generic dashboard
- Honor the functional requirements of the target screen
- Use realistic content and fully rendered sections
- No markdown fences or explanations"""

    system = _build_mockup_system_prompt(
        product_name=product_name,
        screen_desc=screen_desc,
        brief_text=brief_text,
        revision_context=revision_context,
        direction=direction,
        north_star_css=north_star_css,
        north_star_html=north_star_html,
        creative_mode="guided",
    )
    
    call_kwargs = _build_litellm_kwargs(mc, [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Project context:\n{project_context}\n\nScreen:\n{screen_desc}\n\nCode to convert:\n{raw_code}",
        },
    ], temperature=0.3, max_tokens=4200)
    resp = await litellm.acompletion(**call_kwargs)
    return _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))


async def _repair_html_authentic(
    candidate: str,
    screen_desc: str,
    project_context: str,
    brief_text: str,
    attempt: int,
    user_id: str | None = None,
    direction: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
) -> str:
    mc = _resolve_design_model(user_id)
    product_name = _project_name_from_context(project_context)
    
    revision_context = f"""
The HTML mockup below is incomplete, thin, or visually unconvincing.
This is repair attempt {attempt}.

Fix the following:
- Fill blank or placeholder areas with realistic, visible content
- Make the composition feel intentional and product-specific
- Remove any AI-looking clichés if present
- Ensure the page feels complete, coherent, and believable
- Return ONLY the corrected complete HTML document with embedded CSS
- No explanations, no markdown fences, no scripts"""

    system = _build_mockup_system_prompt(
        product_name=product_name,
        screen_desc=screen_desc,
        brief_text=brief_text,
        revision_context=revision_context,
        direction=direction,
        north_star_css=north_star_css,
        north_star_html=north_star_html,
        creative_mode="guided",
    )
    
    call_kwargs = _build_litellm_kwargs(mc, [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Project context:\n{project_context}\n\nHTML to repair:\n{candidate}"},
    ], temperature=0.55, max_tokens=4500)
    resp = await litellm.acompletion(**call_kwargs)
    return _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))


async def _review_mockup_authenticity(
    candidate: str,
    screen_desc: str,
    brief_text: str,
    user_id: str | None = None,
) -> dict:
    heuristic_notes = _looks_like_ai_cliche_html(candidate)
    mc = _resolve_design_model(user_id)
    system = f"""You are a principal design reviewer.
Review the HTML mockup against the design brief and decide whether it feels like thoughtful human product design rather than generic AI output.

Return ONLY valid JSON:
{{
  "pass": true,
  "notes": ["..."]
}}

Review criteria:
- Is the design aligned with the brief and product context?
- Does it satisfy the compiled screen obligations and consistency contract?
- Does it avoid default AI color clichés and synthetic styling?
- Does the hierarchy feel intentional and screen-appropriate?
- Does it look like part of a real product rather than a template?

{brief_text}"""
    try:
        call_kwargs = _build_litellm_kwargs(mc, [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Screen:\n{screen_desc}\n\nHTML:\n{candidate}"},
        ], temperature=0.2, max_tokens=700)
        resp = await litellm.acompletion(**call_kwargs)
        raw = _strip_code_fences(resp.choices[0].message.content.strip())
        match = re.search(r"\{[\s\S]*\}", raw)
        data = json.loads(match.group(0) if match else raw)
        notes = [str(note).strip() for note in data.get("notes", []) if str(note).strip()]
        if heuristic_notes:
            notes = list(dict.fromkeys(heuristic_notes + notes))
        passed = bool(data.get("pass", False)) and not heuristic_notes
        return {"pass": passed, "notes": notes}
    except Exception:
        return {"pass": not heuristic_notes, "notes": heuristic_notes}


async def _revise_mockup_from_review(
    candidate: str,
    screen_desc: str,
    project_context: str,
    brief_text: str,
    review_notes: list[str],
    user_id: str | None = None,
    direction: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
) -> str:
    mc = _resolve_design_model(user_id)
    product_name = _project_name_from_context(project_context)
    
    str_notes = chr(10).join(f"- {note}" for note in review_notes)
    revision_context = f"""
You are revising an HTML mockup after senior design review.

Review notes to address:
{str_notes}

Rules:
- Keep the screen's intent and structure, but improve the craft and authenticity
- Remove generic AI-looking decisions
- Preserve realism, polish, and consistency
- Return ONLY the revised complete HTML document with embedded CSS
- No markdown fences, no explanations, no scripts"""

    system = _build_mockup_system_prompt(
        product_name=product_name,
        screen_desc=screen_desc,
        brief_text=brief_text,
        revision_context=revision_context,
        direction=direction,
        north_star_css=north_star_css,
        north_star_html=north_star_html,
        creative_mode="guided",
    )
    
    call_kwargs = _build_litellm_kwargs(mc, [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Project context:\n{project_context}\n\nScreen:\n{screen_desc}\n\nHTML to revise:\n{candidate}"},
    ], temperature=0.55, max_tokens=5000)
    resp = await litellm.acompletion(**call_kwargs)
    return _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))


def _load_consistency_contract(
    db: Session,
    project_id: str,
    *,
    exclude_mockup_id: str | None = None,
) -> tuple[str | None, str | None]:
    query = (
        db.query(DesignMockup)
        .filter(
            DesignMockup.project_id == project_id,
            DesignMockup.status.in_([MockupStatus.complete, MockupStatus.approved]),
        )
        .order_by(DesignMockup.sort_order.asc())
    )
    if exclude_mockup_id:
        query = query.filter(DesignMockup.id != exclude_mockup_id)
    ref = query.first()
    if not ref or not ref.component_code:
        return None, None
    html = ref.component_code
    return _extract_north_star_css(html) or None, html


async def _generate_mockup_with_design_brief(
    mockup_id: str,
    project_context: str,
    screen_desc: str,
    *,
    creative_mode: str = "guided",
    user_id: str | None = None,
    direction: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
) -> None:
    from models import SessionLocal

    if mockup_id in _cancelled_mockups:
        _cancelled_mockups.discard(mockup_id)
        return

    db = SessionLocal()
    try:
        mockup = db.query(DesignMockup).filter(DesignMockup.id == mockup_id).first()
        if not mockup:
            return

        mockup.status = MockupStatus.generating
        db.commit()

        if not north_star_css and not north_star_html:
            auto_css, auto_html = _load_consistency_contract(
                db, mockup.project_id, exclude_mockup_id=mockup_id
            )
            north_star_css = north_star_css or auto_css
            north_star_html = north_star_html or auto_html

        references = _get_mockup_reference_summaries(
            db, mockup.project_id, exclude_mockup_id=mockup_id
        )
        brief, _, brief_text = _build_design_brief_text(
            project_context,
            screen_desc=screen_desc,
            direction=direction,
            references=references,
            compact=False,
        )
        revision_context = f"\n\nRevision notes from user: {mockup.prompt}" if mockup.prompt else ""
        product_name = _project_name_from_context(project_context)
        system = _build_mockup_system_prompt(
            product_name=product_name,
            screen_desc=screen_desc,
            brief_text=brief_text,
            revision_context=revision_context,
            direction=direction,
            north_star_css=north_star_css,
            north_star_html=north_star_html,
            creative_mode=creative_mode,
        )

        mc = _resolve_design_model(user_id)
        call_kwargs = _build_litellm_kwargs(mc, [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Product context:\n{project_context}\n\nScreen:\n{screen_desc}"},
        ], temperature=0.95 if creative_mode == "ai_free" and not north_star_css else 0.7, max_tokens=5000)
        resp = await litellm.acompletion(**call_kwargs)

        if mockup_id in _cancelled_mockups:
            _cancelled_mockups.discard(mockup_id)
            return

        candidate = _ensure_html_document(
            _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))
        )

        if not _is_renderable_ui_html(candidate):
            print(f"🔧 [{screen_desc[:40]}] Converting non-renderable output to static HTML")
            transformed = await _transform_to_static_html_authentic(
                candidate, screen_desc, project_context, brief_text, user_id=user_id,
                direction=direction, north_star_css=north_star_css, north_star_html=north_star_html
            )
            candidate = _ensure_html_document(transformed)

        if not (_is_renderable_ui_html(candidate) and _is_visually_complete_html(candidate)):
            if _is_renderable_ui_html(candidate):
                print(f"🔄 [{screen_desc[:40]}] Repairing thin output")
                repaired = await _repair_html_authentic(
                    candidate, screen_desc, project_context, brief_text, 1, user_id=user_id,
                    direction=direction, north_star_css=north_star_css, north_star_html=north_star_html
                )
                candidate = _ensure_html_document(repaired)
            else:
                print(f"⚠️ [{screen_desc[:40]}] Falling back after non-renderable output")
                candidate = _fallback_mockup_html(product_name, screen_desc, project_context)

        review = await _review_mockup_authenticity(
            candidate, screen_desc, brief_text, user_id=user_id
        )
        review_notes = list(review.get("notes") or [])
        review_notes.extend(_screen_specific_quality_notes(candidate, screen_desc))

        deduped_review_notes: list[str] = []
        for note in review_notes:
            if note and note not in deduped_review_notes:
                deduped_review_notes.append(note)

        if deduped_review_notes and _is_renderable_ui_html(candidate):
            print(f"🧠 [{screen_desc[:40]}] Revising after authenticity review")
            revised = await _revise_mockup_from_review(
                candidate,
                screen_desc,
                project_context,
                brief_text,
                deduped_review_notes,
                user_id=user_id,
                direction=direction,
                north_star_css=north_star_css,
                north_star_html=north_star_html
            )
            candidate = _ensure_html_document(_strip_script_tags(revised))

        if not _is_renderable_ui_html(candidate):
            candidate = _fallback_mockup_html(product_name, screen_desc, project_context)

        mockup.component_code = candidate
        mockup.status = MockupStatus.complete
        mockup.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        if "mockup" in locals() and mockup is not None:
            mockup.status = MockupStatus.error
            mockup.component_code = f"<div style='padding:2rem;color:red'>Generation failed: {str(e)}</div>"
            mockup.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


# ── Background generation ────────────────────────────────────────────────────

async def _self_repair_html(candidate: str, screen_desc: str, project_context: str, attempt: int, user_id: str | None = None) -> str:
    """Ask the model to review its own incomplete output and fill in missing sections."""
    dna = _derive_design_dna(project_context)
    dna_block = _format_design_dna_block(dna)
    mc = _resolve_design_model(user_id)
    bg = dna["palette"]["bg"]
    bg_hex = bg.lstrip("#")
    try:
        _r, _g, _b = int(bg_hex[0:2],16), int(bg_hex[2:4],16), int(bg_hex[4:6],16)
        _theme = "DARK" if (0.299*_r + 0.587*_g + 0.114*_b) < 80 else "LIGHT"
        _forbidden = "white, #fff, #ffffff, #fafafa" if _theme == "DARK" else "black, #000"
    except Exception:
        _theme, _forbidden = "DARK", "white, #fff, #ffffff"

    repair_prompt = f"""The HTML mockup below is INCOMPLETE or has blank/empty sections.
This is attempt {attempt} of a self-repair pass.

{dna_block}

Target screen: {screen_desc}

This is a {_theme} THEME — body background MUST be {bg}. NEVER use {_forbidden}.

Problems to fix:
- Fill every blank, placeholder, or empty div with real visible content
- Ensure the FULL page renders with all sections: navigation, hero/main content, supporting panels, footer
- Remove any <script> blocks — pure HTML/CSS only
- Do NOT truncate — output the complete finished document

Return ONLY the corrected complete HTML document, no explanations."""
    call_kwargs = _build_litellm_kwargs(mc, [
        {"role": "system", "content": repair_prompt},
        {"role": "user", "content": f"Incomplete HTML to fix:\n\n{candidate}"},
    ], temperature=0.7, max_tokens=4500)
    resp = await litellm.acompletion(**call_kwargs)
    result = _strip_script_tags(_strip_code_fences(resp.choices[0].message.content.strip()))
    return _enforce_theme_css(result, dna)


async def _generate_mockup_component(
    mockup_id: str,
    project_context: str,
    screen_desc: str,
    user_id: str | None = None,
    north_star_css: str | None = None,
    north_star_html: str | None = None,
):
    """Generate a single mockup as an HTML/CSS component (with up to 3 self-repair attempts).

    When north_star_css / north_star_html are supplied the prompt will include a
    consistency block that forces the LLM to replicate the north-star's exact
    CSS and HTML structure — preventing late screens from diverging.
    """
    return await _generate_mockup_with_design_brief(
        mockup_id,
        project_context,
        screen_desc,
        creative_mode="guided",
        user_id=user_id,
        north_star_css=north_star_css,
        north_star_html=north_star_html,
    )



# ── AI Creative Freedom generation ───────────────────────────────────────────

def _extract_north_star_css(html: str) -> str:
    """Extract the FULL stylesheet from the north-star HTML so subsequent screens
    can reproduce every visual pattern — not just :root vars but also component
    styles, keyframes, and layout rules.
    """
    parts: list[str] = []

    # ── 1. Google Fonts <link> tags ──────────────────────────────────────────
    for link_match in re.finditer(
        r'<link[^>]+href=["\']([^"\']*fonts\.googleapis\.com[^"\']*)["\'][^>]*/?>',
        html, re.IGNORECASE,
    ):
        imp_line = f'@import url("{link_match.group(1)}");'
        if imp_line not in parts:
            parts.append(imp_line)

    # ── 2. Inline @import url(...) for fonts ─────────────────────────────────
    for imp in re.finditer(r'@import\s+url\([^)]+\)[^;]*;', html):
        if imp.group(0) not in parts:
            parts.append(imp.group(0))

    # ── 3. Full <style> contents (captures EVERYTHING: keyframes, component
    #        rules, media queries, etc.) ──────────────────────────────────────
    style_blocks: list[str] = []
    for style_match in re.finditer(
        r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE,
    ):
        style_blocks.append(style_match.group(1).strip())

    if style_blocks:
        # Deduplicate: join all <style> contents. This gives the LLM the full
        # button, card, nav, typography, keyframe, and media-query rules — not
        # just the :root variables.
        full_css = "\n\n".join(style_blocks)
        parts.append(full_css)
    else:
        # Fallback: no <style> tags found — scrape what we can (legacy path)
        # @font-face blocks
        for ff in re.finditer(r'@font-face\s*\{[^}]+\}', html, re.DOTALL):
            parts.append(ff.group(0))

        # :root variables
        root_match = re.search(r':root\s*\{([^}]+)\}', html, re.DOTALL)
        if root_match:
            parts.append(f":root {{{root_match.group(1)}}}")

        # *, *::before, *::after reset
        reset_match = re.search(
            r'\*\s*(?:,\s*\*::(?:before|after)\s*)*\{[^}]+\}', html, re.DOTALL,
        )
        if reset_match:
            parts.append(reset_match.group(0))

        # html, body rules
        body_match = re.search(
            r'html\s*,?\s*body\s*\{([^}]+)\}', html, re.DOTALL | re.IGNORECASE,
        )
        if body_match:
            parts.append(f"html, body {{{body_match.group(1)}}}")
        else:
            body_only = re.search(
                r'(?<!\w)body\s*\{([^}]+)\}', html, re.DOTALL | re.IGNORECASE,
            )
            if body_only:
                parts.append(f"body {{{body_only.group(1)}}}")

    result = "\n".join(parts).strip()

    # Safety cap: if the extracted CSS is huge (>12 KB), the LLM context will
    # bloat.  Truncate to the first 12 000 chars — still captures all design
    # tokens, component rules, and the most important keyframes.
    if len(result) > 12_000:
        result = result[:12_000] + "\n/* … truncated for brevity — follow the patterns above */"

    return result


async def _generate_mockup_ai_free(
    mockup_id: str,
    project_context: str,
    screen_desc: str,
    north_star_css: str | None,
    user_id: str | None = None,
    direction: str | None = None,
    north_star_html: str | None = None,
):
    """Generate a single mockup with full AI creative freedom.

    When north_star_css is None this is the north-star screen (AI chooses everything).
    Otherwise, AI must replicate the extracted CSS design system.
    direction: optional chosen design direction description to guide the north-star style.
    north_star_html: full HTML of the north-star screen for deeper style extraction.
    """
    return await _generate_mockup_with_design_brief(
        mockup_id,
        project_context,
        screen_desc,
        creative_mode="ai_free",
        user_id=user_id,
        direction=direction,
        north_star_css=north_star_css,
        north_star_html=north_star_html,
    )



async def _generate_all_mockups_ai_free(project_id: str, direction: str | None = None):
    """AI creative freedom: first screen (landing/home) is the north star; all others follow it."""
    import traceback
    from models import SessionLocal

    # ── Phase 1: setup — discover screens and persist mockup rows ────────────
    project_context: str = ""
    user_id: str | None = None
    mockup_ids: list[tuple[str, dict]] = []

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        cdo_analysis = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.cdo,
        ).first()
        project_context = _build_project_context(project, cdo_analysis, db=db)
        user_id = project.user_id

        screens = await _discover_screens_from_context(project_context, user_id=user_id)

        db.query(DesignMockup).filter(DesignMockup.project_id == project_id).delete()
        db.commit()

        # Prioritise landing/hero/home/dashboard first — it becomes the north star
        def _north_star_priority(s: dict) -> int:
            t = (s.get("name", "") + " " + s.get("description", "")).lower()
            if any(w in t for w in ("landing", "hero", "home", "dashboard", "main", "overview")):
                return 0
            return 1

        screens_sorted = sorted(enumerate(screens), key=lambda x: _north_star_priority(x[1]))
        ordered = [(orig_i, s) for orig_i, s in screens_sorted]

        for new_order, (_, screen) in enumerate(ordered):
            m = DesignMockup(
                id=str(uuid.uuid4()),
                project_id=project_id,
                screen_name=screen["name"],
                description=screen.get("description", ""),
                priority=_priority_to_enum(screen.get("priority")),
                status=MockupStatus.pending,
                sort_order=new_order,
            )
            db.add(m)
            mockup_ids.append((m.id, screen))
        db.commit()

    except Exception as exc:
        print(f"❌ _generate_all_mockups_ai_free setup failed: {exc}")
        traceback.print_exc()
        db.rollback()
        # Mark ALL pending mockups for this project as error so the frontend stops polling
        try:
            pending = db.query(DesignMockup).filter(
                DesignMockup.project_id == project_id,
                DesignMockup.status.in_([MockupStatus.pending, MockupStatus.generating]),
            ).all()
            for m in pending:
                m.status = MockupStatus.error
                m.component_code = f"<div style='padding:2rem;color:red'>Setup failed: {exc}</div>"
                m.updated_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass
        return
    finally:
        db.close()

    if not mockup_ids:
        print(f"❌ _generate_all_mockups_ai_free: no mockup_ids after setup — aborting")
        return

    # ── Phase 2: generate ────────────────────────────────────────────────────
    try:
        # Step 1 — generate north-star screen (sequential, awaited)
        first_id, first_screen = mockup_ids[0]
        first_desc = f"Screen: {first_screen['name']}\nDescription: {first_screen.get('description', '')}"
        print(f"🌟 AI-Free: generating north-star screen '{first_screen['name']}'" + (f" [direction: {direction[:50]}]" if direction else ""))
        await _generate_mockup_ai_free(first_id, project_context, first_desc, north_star_css=None, user_id=user_id, direction=direction)

        # Step 2 — extract north-star CSS and full HTML from generated screen
        db2 = SessionLocal()
        north_star_html = ""
        try:
            first_mockup = db2.query(DesignMockup).filter(DesignMockup.id == first_id).first()
            north_star_html = first_mockup.component_code or "" if first_mockup else ""
            north_star_css = _extract_north_star_css(north_star_html) if north_star_html else ""
            print(f"🌟 North star CSS extracted ({len(north_star_css)} chars) from '{first_screen['name']}'")
        finally:
            db2.close()

        # Step 3 — generate remaining screens in parallel, all following north-star style + direction
        remaining_tasks = [
            _generate_mockup_ai_free(
                mid, project_context,
                f"Screen: {s['name']}\nDescription: {s.get('description', '')}",
                north_star_css=north_star_css or None,
                user_id=user_id,
                direction=direction,
                north_star_html=north_star_html or None,
            )
            for mid, s in mockup_ids[1:]
        ]
        if remaining_tasks:
            await asyncio.gather(*remaining_tasks, return_exceptions=True)

    except Exception as exc:
        print(f"❌ _generate_all_mockups_ai_free generation failed: {exc}")
        traceback.print_exc()
        # Mark remaining pending mockups as error
        db3 = SessionLocal()
        try:
            for mid, _ in mockup_ids:
                m = db3.query(DesignMockup).filter(DesignMockup.id == mid).first()
                if m and m.status in (MockupStatus.pending, MockupStatus.generating):
                    m.status = MockupStatus.error
                    m.component_code = f"<div style='padding:2rem;color:red'>Generation failed: {exc}</div>"
                    m.updated_at = datetime.utcnow()
            db3.commit()
        except Exception:
            pass
        finally:
            db3.close()


async def _generate_all_mockups(project_id: str):
    """Determine screens needed and generate mockups.

    Uses a north-star pattern: the landing/hero screen is generated FIRST,
    its CSS is extracted, and every subsequent screen receives that CSS as
    a binding style contract so all screens look like one product.
    """
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        cdo_analysis = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.cdo,
        ).first()
        project_context = _build_project_context(project, cdo_analysis, db=db)
        user_id = project.user_id
        screens = await _discover_screens_from_context(project_context, user_id=user_id)

        # Clear existing mockups for regeneration
        db.query(DesignMockup).filter(DesignMockup.project_id == project_id).delete()
        db.commit()

        # Prioritise landing/hero/home/dashboard first — it becomes the north star
        def _north_star_priority(s: dict) -> int:
            t = (s.get("name", "") + " " + s.get("description", "")).lower()
            if any(w in t for w in ("landing", "hero", "home", "dashboard", "main", "overview")):
                return 0
            return 1

        screens_sorted = sorted(enumerate(screens), key=lambda x: _north_star_priority(x[1]))
        ordered = [(orig_i, s) for orig_i, s in screens_sorted]

        # Create mockup records
        mockup_ids: list[tuple[str, dict]] = []
        for new_order, (_, screen) in enumerate(ordered):
            mockup = DesignMockup(
                id=str(uuid.uuid4()),
                project_id=project_id,
                screen_name=screen["name"],
                description=screen.get("description", ""),
                priority=_priority_to_enum(screen.get("priority")),
                status=MockupStatus.pending,
                sort_order=new_order,
            )
            db.add(mockup)
            mockup_ids.append((mockup.id, screen))
        db.commit()
    finally:
        db.close()

    if not mockup_ids:
        return

    # ── Phase 2: north-star first, then remaining in parallel ────────────────
    first_id, first_screen = mockup_ids[0]
    first_desc = f"Screen: {first_screen['name']}\nDescription: {first_screen.get('description', '')}"
    print(f"🌟 DNA: generating north-star screen '{first_screen['name']}'")
    await _generate_mockup_component(first_id, project_context, first_desc, user_id=user_id)

    # Extract north-star CSS + HTML
    db2 = SessionLocal()
    north_star_html = ""
    north_star_css = ""
    try:
        first_mockup = db2.query(DesignMockup).filter(DesignMockup.id == first_id).first()
        north_star_html = first_mockup.component_code or "" if first_mockup else ""
        north_star_css = _extract_north_star_css(north_star_html) if north_star_html else ""
        print(f"🌟 North star CSS extracted ({len(north_star_css)} chars) from '{first_screen['name']}'")
    finally:
        db2.close()

    # Generate remaining screens in parallel with north-star context
    remaining_tasks = [
        _generate_mockup_component(
            mid, project_context,
            f"Screen: {s['name']}\nDescription: {s.get('description', '')}",
            user_id=user_id,
            north_star_css=north_star_css or None,
            north_star_html=north_star_html or None,
        )
        for mid, s in mockup_ids[1:]
    ]
    if remaining_tasks:
        await asyncio.gather(*remaining_tasks, return_exceptions=True)


async def _generate_existing_mockups(project_id: str):
    """Generate components for existing mockup rows using north-star pattern.

    The first mockup (by sort_order) is generated first, its CSS is extracted,
    and the remaining screens receive it as a consistency contract.
    """
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        cdo_analysis = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.cdo,
        ).first()
        project_context = _build_project_context(project, cdo_analysis, db=db)

        mockups = db.query(DesignMockup).filter(
            DesignMockup.project_id == project_id
        ).order_by(DesignMockup.sort_order.asc()).all()

        if not mockups:
            return

        user_id = project.user_id
    finally:
        db.close()

    # Phase 1: generate north-star (first by sort_order)
    first = mockups[0]
    first_desc = f"Screen: {first.screen_name}\nDescription: {first.description or ''}"
    print(f"🌟 Existing: generating north-star screen '{first.screen_name}'")
    await _generate_mockup_component(first.id, project_context, first_desc, user_id=user_id)

    # Extract CSS + HTML
    db2 = SessionLocal()
    north_star_html = ""
    north_star_css = ""
    try:
        first_m = db2.query(DesignMockup).filter(DesignMockup.id == first.id).first()
        north_star_html = first_m.component_code or "" if first_m else ""
        north_star_css = _extract_north_star_css(north_star_html) if north_star_html else ""
        print(f"🌟 North star CSS extracted ({len(north_star_css)} chars)")
    finally:
        db2.close()

    # Phase 2: remaining in parallel
    remaining_tasks = [
        _generate_mockup_component(
            m.id, project_context,
            f"Screen: {m.screen_name}\nDescription: {m.description or ''}",
            user_id=user_id,
            north_star_css=north_star_css or None,
            north_star_html=north_star_html or None,
        )
        for m in mockups[1:]
    ]
    if remaining_tasks:
        await asyncio.gather(*remaining_tasks, return_exceptions=True)


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/{project_id}/design/mockups")
async def list_mockups(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockups = db.query(DesignMockup).filter(
        DesignMockup.project_id == project_id
    ).order_by(DesignMockup.sort_order).all()

    healed = False
    for m in mockups:
        # Never touch mockups that are still generating, pending, or in error state
        if m.status in (MockupStatus.generating, MockupStatus.pending, MockupStatus.error):
            continue
        if not m.component_code:
            continue
        # Strip any script tags before quality checks (LLM sometimes adds JS)
        clean = _strip_script_tags(m.component_code)
        normalized = _ensure_html_document(clean)
        if not _is_renderable_ui_html(normalized):
            # Only substitute fallback for complete/approved mockups with bad HTML
            m.component_code = _fallback_mockup_html(project.name, f"Screen: {m.screen_name}\nDescription: {m.description or ''}")
            m.updated_at = datetime.utcnow()
            healed = True
        elif normalized != m.component_code:
            m.component_code = normalized
            m.updated_at = datetime.utcnow()
            healed = True

    if healed:
        db.commit()

    return {
        "mockups": [
            {
                "id": m.id,
                "name": m.screen_name,
                "description": m.description,
                "priority": m.priority.value,
                "status": m.status.value,
                "component_code": m.component_code,
                "revision_notes": m.prompt,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mockups
        ]
    }


@router.post("/{project_id}/design/generate")
async def generate_mockups(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="design/generate.requested",
                data={"project_id": project_id},
            ))
            print(f"📨 Inngest event: design/generate.requested for {project_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_all_mockups, project_id)
    else:
        background_tasks.add_task(_generate_all_mockups, project_id)
    return {"status": "generating"}


@router.post("/{project_id}/design/discover")
async def discover_design_screens(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Discover and persist prioritized screens with mini-prompts (without generating code)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cdo_analysis = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role == CSuiteRole.cdo,
    ).first()
    project_context = _build_project_context(project, cdo_analysis, db=db)
    screens = await _discover_screens_from_context(project_context, user_id=user.id)

    db.query(DesignMockup).filter(DesignMockup.project_id == project_id).delete()
    db.commit()

    created = []
    for i, screen in enumerate(screens):
        prompt = (
            f"Create the {screen.get('name')} screen for {project.name}. "
            f"Follow consistent design system and navigation. "
            f"Priority: {screen.get('priority', 'important')}."
        )
        mockup = DesignMockup(
            id=str(uuid.uuid4()),
            project_id=project_id,
            screen_name=screen.get("name", f"Screen {i+1}"),
            description=screen.get("description", ""),
            priority=_priority_to_enum(screen.get("priority")),
            prompt=prompt,
            status=MockupStatus.pending,
            sort_order=i,
        )
        db.add(mockup)
        created.append(mockup)
    db.commit()

    return {
        "status": "discovered",
        "screens": [
            {
                "id": m.id,
                "name": m.screen_name,
                "description": m.description,
                "priority": m.priority.value,
                "prompt": m.prompt,
                "status": m.status.value,
            }
            for m in created
        ]
    }


@router.post("/{project_id}/design/directions")
async def get_design_directions(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate 10 completely different design direction proposals with rendered HTML swatches."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cdo_analysis = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role == CSuiteRole.cdo,
    ).first()
    project_context = _build_project_context(project, cdo_analysis, db=db)
    product_name = project.name

    # Step 1: Get 5 direction proposals from LLM
    directions = await _generate_direction_proposals(project_context, user_id=user.id)

    # Step 2: Generate mini HTML swatches in parallel
    swatch_tasks = [
        _generate_direction_swatch(d, product_name, user_id=user.id)
        for d in directions
    ]
    swatches = await asyncio.gather(*swatch_tasks, return_exceptions=True)

    results = []
    for i, d in enumerate(directions):
        if not isinstance(d, dict):
            d = {}
        html = swatches[i] if not isinstance(swatches[i], Exception) else ""
        results.append({
            "id": str(uuid.uuid4()),
            "name": d.get("name", f"Direction {i+1}"),
            "description": d.get("description", ""),
            "palette": d.get("palette", []),
            "style_keywords": d.get("style_keywords", []),
            "layout_approach": d.get("layout_approach", ""),
            "html_swatch": html,
        })

    return {"directions": results}


@router.post("/{project_id}/design/mockups/add")
async def add_screen(
    project_id: str,
    body: AddScreenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new screen/mockup to the project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    max_order = db.query(DesignMockup).filter(
        DesignMockup.project_id == project_id,
    ).count()

    mockup = DesignMockup(
        id=str(uuid.uuid4()),
        project_id=project_id,
        screen_name=body.name,
        description=body.description,
        priority=_priority_to_enum(body.priority),
        status=MockupStatus.pending,
        sort_order=max_order,
    )
    db.add(mockup)
    db.commit()

    return {
        "id": mockup.id,
        "name": mockup.screen_name,
        "description": mockup.description,
        "priority": mockup.priority.value,
        "status": mockup.status.value,
    }


@router.post("/{project_id}/design/generate-all")
async def generate_all_mockups(
    project_id: str,
    background_tasks: BackgroundTasks,
    body: GenerateAllRequest = GenerateAllRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate all mockups — design_mode: 'dna' (default) or 'ai_free' (AI chooses style)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Mark ALL mockups as pending IMMEDIATELY (synchronous, before the
    # background task starts).  This is critical: the frontend poller will
    # hit /design/mockups within ~2.5 s.  If the old mockups still show
    # "complete" the poller concludes generation is done and stops.  By
    # flipping them to pending here we guarantee the poller keeps running
    # until the background task finishes.
    existing_mockups = db.query(DesignMockup).filter(
        DesignMockup.project_id == project_id,
    ).all()
    for m in existing_mockups:
        m.status = MockupStatus.pending
        m.component_code = None          # clear stale HTML
    if existing_mockups:
        db.commit()

    if body.design_mode == "ai_free":
        task_name = "ai_free"
    else:
        existing_count = len(existing_mockups)
        task_name = "generate_all" if existing_count == 0 else "generate_existing"

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="design/generate-all.requested",
                data={
                    "project_id": project_id,
                    "design_mode": body.design_mode,
                    "direction": body.direction,
                    "task": task_name,
                },
            ))
            print(f"📨 Inngest event: design/generate-all.requested for {project_id[:8]} task={task_name}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            if task_name == "ai_free":
                background_tasks.add_task(_generate_all_mockups_ai_free, project_id, body.direction)
            elif task_name == "generate_existing":
                background_tasks.add_task(_generate_existing_mockups, project_id)
            else:
                background_tasks.add_task(_generate_all_mockups, project_id)
    else:
        if task_name == "ai_free":
            background_tasks.add_task(_generate_all_mockups_ai_free, project_id, body.direction)
        elif task_name == "generate_existing":
            background_tasks.add_task(_generate_existing_mockups, project_id)
        else:
            background_tasks.add_task(_generate_all_mockups, project_id)

    return {"status": "generating", "design_mode": body.design_mode}


@router.post("/{project_id}/design/generate/{mockup_id}")
async def generate_single_mockup(
    project_id: str,
    mockup_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate one mockup component by mockup id."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockup = db.query(DesignMockup).filter(
        DesignMockup.id == mockup_id,
        DesignMockup.project_id == project_id,
    ).first()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")

    cdo_analysis = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role == CSuiteRole.cdo,
    ).first()
    project_context = _build_project_context(project, cdo_analysis, db=db)
    screen_desc = f"Screen: {mockup.screen_name}\nDescription: {mockup.description or ''}\nPrompt: {mockup.prompt or ''}"

    mockup.status = MockupStatus.pending
    db.commit()

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="design/generate-single.requested",
                data={"mockup_id": mockup_id, "project_context": project_context, "screen_desc": screen_desc, "user_id": user.id},
            ))
            print(f"📨 Inngest event: design/generate-single.requested for {mockup_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc, user.id)
    else:
        background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc, user.id)
    return {"status": "generating", "mockup_id": mockup_id}


@router.post("/{project_id}/design/mockups/{mockup_id}/approve")
async def approve_mockup(
    project_id: str,
    mockup_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockup = db.query(DesignMockup).filter(
        DesignMockup.id == mockup_id,
        DesignMockup.project_id == project_id,
    ).first()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")

    mockup.status = MockupStatus.approved
    mockup.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "approved"}


@router.post("/{project_id}/design/mockups/{mockup_id}/revise")
async def request_revision(
    project_id: str,
    mockup_id: str,
    body: RevisionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockup = db.query(DesignMockup).filter(
        DesignMockup.id == mockup_id,
        DesignMockup.project_id == project_id,
    ).first()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")

    mockup.prompt = body.notes
    mockup.status = MockupStatus.pending
    db.commit()

    cdo_analysis = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role == CSuiteRole.cdo,
    ).first()
    project_context = _build_project_context(project, cdo_analysis, db=db)
    screen_desc = f"Screen: {mockup.screen_name}\nDescription: {mockup.description}\nPrevious feedback: {body.notes}"

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="design/revision.requested",
                data={"mockup_id": mockup_id, "project_context": project_context, "screen_desc": screen_desc, "user_id": user.id},
            ))
            print(f"📨 Inngest event: design/revision.requested for {mockup_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc, user.id)
    else:
        background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc, user.id)

    return {"status": "revising"}


@router.post("/{project_id}/design/stop")
async def stop_all_generations(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel all in-progress or pending mockup generations for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    active = db.query(DesignMockup).filter(
        DesignMockup.project_id == project_id,
        DesignMockup.status.in_([MockupStatus.generating, MockupStatus.pending]),
    ).all()

    cancelled_ids = []
    for m in active:
        _cancelled_mockups.add(m.id)
        m.status = MockupStatus.pending   # leave as pending so user can re-generate
        cancelled_ids.append(m.id)

    db.commit()
    return {"status": "stopped", "cancelled_count": len(cancelled_ids)}


@router.post("/{project_id}/design/mockups/{mockup_id}/stop")
async def stop_single_generation(
    project_id: str,
    mockup_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a single in-progress mockup generation."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockup = db.query(DesignMockup).filter(
        DesignMockup.id == mockup_id,
        DesignMockup.project_id == project_id,
    ).first()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")

    _cancelled_mockups.add(mockup_id)
    if mockup.status in (MockupStatus.generating, MockupStatus.pending):
        mockup.status = MockupStatus.pending
        db.commit()

    return {"status": "stopped", "mockup_id": mockup_id}


@router.delete("/{project_id}/design/mockups/{mockup_id}")
async def delete_mockup(
    project_id: str,
    mockup_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a single design mockup."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mockup = db.query(DesignMockup).filter(
        DesignMockup.id == mockup_id,
        DesignMockup.project_id == project_id,
    ).first()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")

    db.delete(mockup)
    db.commit()
    return {"status": "deleted", "mockup_id": mockup_id}
