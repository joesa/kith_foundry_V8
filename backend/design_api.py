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
)
from auth import get_current_user
from design_fallbacks import (
    screen_variant as _screen_variant_impl,
    screen_specific_requirements as _screen_specific_requirements_impl,
    fallback_mockup_html as _fallback_mockup_html_impl,
)

litellm.drop_params = True
router = APIRouter(prefix="/api/v1/projects", tags=["design"])


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
    kwargs = {"model": model_config["model"], "messages": messages, **extra}
    if model_config.get("api_key"):
        kwargs["api_key"] = model_config["api_key"]
    if model_config.get("api_base"):
        kwargs["api_base"] = model_config["api_base"]
    return kwargs


def _build_project_context(project: Project, cdo_analysis: CSuiteAnalysis | None) -> str:
    idea_context = ""
    if project.idea and project.idea.content:
        idea_context = json.dumps(project.idea.content, indent=2)

    cdo_suggestions = ""
    if cdo_analysis and cdo_analysis.analysis:
        cdo_suggestions = json.dumps(cdo_analysis.analysis, indent=2)

    return f"""Product: {project.name}
Description: {project.description or 'N/A'}
Target Audience: {project.target_audience or 'N/A'}

Idea: {idea_context}

CDO Design Recommendations: {cdo_suggestions or 'None available'}"""


async def _discover_screens_from_context(project_context: str, user_id: str | None = None) -> list[dict]:
    """Return discovered screen definitions from LLM, with a safe fallback."""
    screen_system = """You are a product designer. Given a product description, determine the 5-7 most important screens/pages needed for the MVP.

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
Landing Page must always be included as critical and first in output."""

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
            {"name": "Landing Page", "description": "Main marketing landing page", "priority": "critical"},
            {"name": "Dashboard", "description": "User dashboard with key metrics", "priority": "critical"},
            {"name": "Settings", "description": "User settings and preferences", "priority": "important"},
        ]

    # Ensure Landing Page first + critical
    filtered = [s for s in screens if str(s.get("name", "")).strip().lower() != "landing page"]
    landing = {
        "name": "Landing Page",
        "description": "Primary marketing + conversion experience with clear CTA",
        "priority": "critical",
    }
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


def _fallback_mockup_html(project_name: str, screen_desc: str) -> str:
    """Deterministic visible fallback UI when model output is invalid/blank."""
    return _fallback_mockup_html_impl(project_name, screen_desc)


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


def _project_name_from_context(project_context: str) -> str:
    try:
        for line in (project_context or "").splitlines():
            if line.lower().startswith("product:"):
                return line.split(":", 1)[1].strip() or "Product"
    except Exception:
        pass
    return "Product"


def _screen_specific_requirements(screen_desc: str) -> str:
    return _screen_specific_requirements_impl(screen_desc)


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


def _is_renderable_ui_html(code: str) -> bool:
    c = (code or "")
    if not c.strip():
        return False
    lower = c.lower()
    if "<body" not in lower and "<div" not in lower and "<main" not in lower:
        return False
    if "<script" in lower:
        return False
    if _looks_like_react_or_tsx(c):
        return False
    if _is_visually_thin_html(c):
        return False
    # Must have enough visible text after removing style/script/tag blocks
    content = re.sub(r"<style[\s\S]*?</style>", "", c, flags=re.I)
    content = re.sub(r"<script[\s\S]*?</script>", "", content, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", content)
    return len(re.sub(r"\s+", " ", text).strip()) >= 80


async def _transform_to_static_html(raw_code: str, screen_desc: str, project_context: str, user_id: str | None = None) -> str:
    """Convert TSX/fragment-like output into renderable static HTML/CSS."""
    system = f"""Convert the provided UI code into a COMPLETE standalone HTML document.

Rules:
- Output ONLY HTML + CSS (no JavaScript, no JSX/TSX, no imports/exports)
- Do NOT use Tailwind utility classes or className attributes
- Include <!DOCTYPE html>, <html>, <head>, <style>, and <body>
- Render a rich visible interface with at least:
  - top nav/header
  - primary content area
  - at least 6 visible UI elements (cards, buttons, inputs, labels, etc.)
- Keep style coherent and premium dark SaaS aesthetic
- Do not return markdown fences or explanations
- Ensure the structure and content match the target screen intent, not a generic dashboard.
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
    return _strip_code_fences(resp.choices[0].message.content.strip())


# ── Schemas ──────────────────────────────────────────────────────────────────

class RevisionRequest(BaseModel):
    notes: str


# ── Background generation ────────────────────────────────────────────────────

async def _generate_mockup_component(mockup_id: str, project_context: str, screen_desc: str, user_id: str | None = None):
    """Generate a single mockup as an HTML/CSS component."""
    from models import SessionLocal

    db = SessionLocal()
    try:
        mockup = db.query(DesignMockup).filter(DesignMockup.id == mockup_id).first()
        if not mockup:
            return

        mockup.status = MockupStatus.generating
        db.commit()

        revision_context = ""
        if mockup.prompt:
            revision_context = f"\n\nRevision notes from user: {mockup.prompt}"

        system = f"""You are a world-class UI/UX designer creating a mockup for a SaaS product.

Generate a SINGLE COMPLETE standalone HTML document for the SPECIFIC screen described below.

CRITICAL — SCREEN IDENTITY:
- Each screen in the app has a UNIQUE purpose and must have a UNIQUE layout.
- A Login screen must look like a login page with form fields.
- A Landing Page must look like a marketing page with hero, features, pricing.
- A Settings page must look like a settings page with form fields and toggles.
- A Dashboard must look like a dashboard with KPIs and charts.
- A Detail Panel must look like an item inspector with metadata and comments.
- NEVER produce a generic dashboard for every screen. Match the screen type exactly.

TECHNICAL RULES:
- Output a complete HTML document: <!DOCTYPE html>, <html>, <head>, <style>, <body>
- Use ONLY HTML + inline CSS (no JavaScript, no React/JSX/TSX, no className, no script tags)
- Use CSS Grid or Flexbox for layout
- Modern dark SaaS aesthetic (deep purples, dark backgrounds, subtle borders)
- Include realistic placeholder content — not lorem ipsum
- Include hover states via CSS :hover
- Use Unicode symbols or inline SVG for icons
- Make it responsive with @media queries

SCREEN-SPECIFIC REQUIREMENTS:
{_screen_specific_requirements(screen_desc)}

Do NOT include any JavaScript. Only HTML and CSS.
Output ONLY the raw HTML/CSS code — no markdown fences, no explanations, no commentary.{revision_context}"""

        try:
            mc = _resolve_design_model(user_id)
            call_kwargs = _build_litellm_kwargs(mc, [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Product context:\n{project_context}\n\nScreen to design:\n{screen_desc}"},
            ], temperature=0.8, max_tokens=4000)
            print(f"🎨 Design [{screen_desc[:40]}] using: {mc['model']} via {mc['provider_name']}")
            resp = await litellm.acompletion(**call_kwargs)
            raw_code = _strip_code_fences(resp.choices[0].message.content.strip())
            candidate = _ensure_html_document(raw_code)

            # If output is non-renderable, transform once.
            if not _is_renderable_ui_html(candidate):
                transformed = await _transform_to_static_html(candidate, screen_desc, project_context, user_id=user_id)
                candidate = _ensure_html_document(transformed)

            # Absolute safety net for production UX quality.
            if not _is_renderable_ui_html(candidate):
                candidate = _fallback_mockup_html(_project_name_from_context(project_context), screen_desc)

            mockup.component_code = candidate
            mockup.status = MockupStatus.complete
        except Exception as e:
            mockup.status = MockupStatus.error
            mockup.component_code = f"<div style='padding:2rem;color:red'>Generation failed: {str(e)}</div>"

        mockup.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


async def _generate_all_mockups(project_id: str):
    """Determine screens needed and generate mockups."""
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
        project_context = _build_project_context(project, cdo_analysis)
        screens = await _discover_screens_from_context(project_context, user_id=project.user_id)

        # Clear existing mockups for regeneration
        db.query(DesignMockup).filter(DesignMockup.project_id == project_id).delete()
        db.commit()

        # Create mockup records
        mockup_ids = []
        for i, screen in enumerate(screens):
            mockup = DesignMockup(
                id=str(uuid.uuid4()),
                project_id=project_id,
                screen_name=screen["name"],
                description=screen.get("description", ""),
                priority=_priority_to_enum(screen.get("priority")),
                status=MockupStatus.pending,
                sort_order=i,
            )
            db.add(mockup)
            mockup_ids.append((mockup.id, screen))
        db.commit()

        # Generate all mockups in parallel
        tasks = []
        for mockup_id, screen in mockup_ids:
            screen_desc = f"Screen: {screen['name']}\nDescription: {screen.get('description', '')}"
            tasks.append(_generate_mockup_component(mockup_id, project_context, screen_desc, user_id=project.user_id))

        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        db.close()


async def _generate_existing_mockups(project_id: str):
    """Generate components for existing mockup rows in parallel."""
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
        project_context = _build_project_context(project, cdo_analysis)

        mockups = db.query(DesignMockup).filter(
            DesignMockup.project_id == project_id
        ).order_by(DesignMockup.sort_order.asc()).all()

        tasks = []
        for m in mockups:
            screen_desc = f"Screen: {m.screen_name}\nDescription: {m.description or ''}"
            tasks.append(_generate_mockup_component(m.id, project_context, screen_desc, user_id=project.user_id))

        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        db.close()


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
        if not m.component_code:
            continue
        normalized = _ensure_html_document(m.component_code)
        if not _is_renderable_ui_html(normalized):
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
    project_context = _build_project_context(project, cdo_analysis)
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


@router.post("/{project_id}/design/generate-all")
async def generate_all_mockups(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate all mockups from existing discovered screens (or discover first if empty)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_count = db.query(DesignMockup).filter(DesignMockup.project_id == project_id).count()
    if existing_count == 0:
        background_tasks.add_task(_generate_all_mockups, project_id)
    else:
        background_tasks.add_task(_generate_existing_mockups, project_id)

    return {"status": "generating"}


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
    project_context = _build_project_context(project, cdo_analysis)
    screen_desc = f"Screen: {mockup.screen_name}\nDescription: {mockup.description or ''}\nPrompt: {mockup.prompt or ''}"

    mockup.status = MockupStatus.pending
    db.commit()

    background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc)
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

    # Build project context
    idea_context = ""
    if project.idea and project.idea.content:
        idea_context = json.dumps(project.idea.content, indent=2)

    project_context = f"Product: {project.name}\nDescription: {project.description or 'N/A'}\nIdea: {idea_context}"
    screen_desc = f"Screen: {mockup.screen_name}\nDescription: {mockup.description}\nPrevious feedback: {body.notes}"

    background_tasks.add_task(_generate_mockup_component, mockup_id, project_context, screen_desc)

    return {"status": "revising"}
