"""
Artifacts API — Generate and manage project artifacts (PRD, tech spec, etc.).
"""
import uuid
import json
import os
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from rate_limiter import limiter

import litellm

from models import (
    get_db, User, Project, Artifact, CSuiteAnalysis,
    ArtifactType, AgentStatus,
)
from auth import get_current_user
from design_context import get_design_context

import inngest
from inngest_client import client as inngest_client, use_inngest
import billing_api as billing

litellm.drop_params = True
router = APIRouter(prefix="/api/v1/projects", tags=["artifacts"])


# ── Artifact definitions ─────────────────────────────────────────────────────

ARTIFACT_DEFS = {
    "executive_brief": {
        "type": ArtifactType.exec_summary,
        "title": "Executive Brief",
        "prompt": """Write a comprehensive Executive Brief for this product. Include:
- Vision statement
- Problem being solved
- Proposed solution
- Key value propositions
- Target market overview
- Success metrics
- 90-day milestones

Format as a professional document with clear sections.""",
    },
    "prd": {
        "type": ArtifactType.product_requirements,
        "title": "Product Requirements Document",
        "prompt": """Write a detailed Product Requirements Document (PRD). Include:
- Product overview and objectives
- User stories (at least 10)
- Functional requirements
- Non-functional requirements
- MVP feature scope
- Out-of-scope items
- Success criteria
- Dependencies and assumptions

Format as a professional PRD with numbered sections.""",
    },
    "tech_spec": {
        "type": ArtifactType.tech_architecture,
        "title": "Technical Specification",
        "prompt": """Write a Technical Architecture Specification. Include:
- System architecture overview
- Tech stack recommendations with rationale
- Database schema design
- API endpoint design
- Third-party integrations
- Security considerations
- Scalability plan
- CI/CD and deployment strategy
- Development environment setup

Format as a professional technical document.""",
    },
    "market_analysis": {
        "type": ArtifactType.market_analysis,
        "title": "Market Analysis",
        "prompt": """Write a Market Analysis report. Include:
- Total Addressable Market (TAM)
- Serviceable Addressable Market (SAM)
- Serviceable Obtainable Market (SOM)
- Market trends and growth drivers
- Customer segments
- Competitive landscape overview
- Market entry barriers
- Pricing benchmarks

Use realistic estimates and cite reasoning.""",
    },
    "go_to_market": {
        "type": ArtifactType.gtm_plan,
        "title": "Go-to-Market Plan",
        "prompt": """Write a Go-to-Market Launch Plan. Include:
- Launch strategy and timeline
- Marketing channels (ranked by priority)
- Content marketing plan
- Paid acquisition strategy
- Partnerships and collaborations
- Community building plan
- PR and media strategy
- Key metrics to track
- Budget allocation recommendations

Be specific and actionable.""",
    },
    "user_personas": {
        "type": ArtifactType.user_personas,
        "title": "User Personas",
        "prompt": """Create 3-5 detailed User Personas. For each persona include:
- Name and demographic info
- Job title and company type
- Goals and motivations
- Pain points and frustrations
- Tech savviness level
- A day-in-the-life scenario
- How they would discover and use this product
- Key features they value most

Make personas realistic and distinct from each other.""",
    },
    "competitive_matrix": {
        "type": ArtifactType.competitive_matrix,
        "title": "Competitive Matrix",
        "prompt": """Create a Competitive Analysis Matrix. Include:
- Identify 5-8 direct and indirect competitors
- Feature comparison table
- Pricing comparison
- Strengths and weaknesses of each
- Our differentiation strategy
- Opportunities in competitive gaps
- Threats to watch

Format with clear tables and analysis sections.""",
    },
    "roadmap": {
        "type": ArtifactType.roadmap,
        "title": "Product Roadmap",
        "prompt": """Create a Product Roadmap. Include:
- Phase 1: MVP (Weeks 1-4) — must-have features
- Phase 2: Growth (Weeks 5-12) — key additions
- Phase 3: Scale (Months 4-6) — advanced features
- Phase 4: Maturity (Months 7-12) — platform expansion
- Dependencies between phases
- Key milestones and deliverables
- Risk factors per phase

Be specific about features in each phase.""",
    },
    "monetization": {
        "type": ArtifactType.monetization,
        "title": "Monetization Plan",
        "prompt": """Create a Monetization Strategy. Include:
- Revenue model(s) recommendation
- Pricing tiers and strategy
- Free vs paid feature breakdown
- Revenue projections (Month 1, 3, 6, 12)
- Customer acquisition cost estimates
- Lifetime value estimates
- Break-even analysis
- Upsell and expansion revenue opportunities

Use realistic numbers with clear assumptions.""",
    },
    "design_system": {
        "type": ArtifactType.design_system,
        "title": "Design System Foundation",
        "prompt": """Create a comprehensive Design System Foundation document. Include:

## 1. Brand Identity
- Primary, secondary, and accent color palette (exact hex values)
- Typography scale (font families, sizes, weights, line heights)
- Logo usage guidelines and spacing rules

## 2. Design Tokens
- Color tokens (background, surface, text, border, status colors)
- Spacing scale (4px base unit system)
- Border radius values
- Shadow/elevation levels
- Transition/animation timing

## 3. Component Library Specification
- Buttons (primary, secondary, ghost, destructive — all states)
- Input fields (text, select, checkbox, radio, toggle — all states)
- Cards (content card, action card, stat card)
- Navigation (top bar, sidebar, breadcrumbs, tabs)
- Modals and dialogs
- Toast/notification system
- Tables and data display
- Loading states and skeletons

## 4. Layout System
- Grid system (columns, gutters, breakpoints)
- Page layout templates
- Responsive breakpoints and behavior
- Container max-widths

## 5. Iconography & Imagery
- Icon library: lucide-react (specify which icons to use for common actions)
- Image treatment guidelines
- Illustration style direction

## 6. Accessibility
- Color contrast requirements (WCAG AA minimum)
- Focus indicator styles
- Touch target sizes
- Screen reader considerations

## 7. Animation & Motion System
- Page transition patterns (specify framer-motion variants: fade, slide, scale with exact durations and easings)
- Scroll-triggered entrance animations (useInView thresholds, stagger delays between children)
- Parallax scroll specifications (useScroll/useTransform ranges for hero background layers)
- Hover/focus micro-interactions (scale values, brightness changes, transition durations)
- Loading state animations (skeleton shimmer CSS keyframes, spinner styles)
- Number counter animations for dashboard metrics (duration, easing curve)
- Sidebar collapse/expand animation (width transition, content fade timing)
- AnimatePresence exit animations for route transitions

## 8. Tailwind Theme Extension
- Map all design tokens to Tailwind CSS custom properties
- Provide the exact tailwind.config.js theme.extend block for custom colors, spacing, etc.
- Define custom utility classes for glass-morphism, gradient text, glow effects
- Specify responsive breakpoint behavior for each component pattern

Provide exact CSS variable names and values where applicable. Format tokens as CSS custom properties ready to use in implementation. All animation specs should include exact framer-motion prop values.""",
    },
}

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"

def _get_model():
    return os.getenv("ARTIFACT_MODEL", DEFAULT_MODEL)


def _build_project_context(project: Project) -> str:
    """Build generation context from project + idea + C-Suite analyses."""
    idea_context = ""
    if project.idea and project.idea.content:
        idea_context = json.dumps(project.idea.content, indent=2)

    csuite_summaries = []
    for analysis in project.csuite_analyses:
        if analysis.analysis:
            csuite_summaries.append(
                f"**{analysis.agent_role.value.upper()}** (Score: {analysis.score}/100): "
                f"{analysis.analysis.get('recommendation', 'N/A')}"
            )

    return f"""Product: {project.name}
Description: {project.description or 'N/A'}
Target Audience: {project.target_audience or 'N/A'}
Problem Statement: {project.problem_statement or 'N/A'}

Idea Details:
{idea_context}

C-Suite Analysis Summaries:
{chr(10).join(csuite_summaries) if csuite_summaries else 'Not yet analyzed'}"""


def _find_artifact_by_id_or_key(db: Session, project_id: str, artifact_id: str) -> Artifact | None:
    """Find artifact by DB id first, then by known artifact key."""
    artifact = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.id == artifact_id,
    ).first()
    if artifact:
        return artifact

    artifact_def = ARTIFACT_DEFS.get(artifact_id)
    if not artifact_def:
        return None

    return db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.title == artifact_def["title"],
    ).first()


def _bootstrap_payload_from_artifact(project_id: str, artifact: Artifact) -> dict:
    content = artifact.content if isinstance(artifact.content, dict) else {"text": str(artifact.content or "")}
    prompt_text = content.get("text", "")
    word_count = content.get("word_count") or len(prompt_text.split())
    token_estimate = content.get("token_estimate") or max(1, len(prompt_text) // 4)
    return {
        "project_id": project_id,
        "prompt": prompt_text,
        "word_count": word_count,
        "token_estimate": token_estimate,
    }


def _build_bootstrap_prompt_artifact(db: Session, project: Project) -> Artifact:
    artifacts = db.query(Artifact).filter(
        Artifact.project_id == project.id,
        Artifact.status == AgentStatus.complete,
        Artifact.artifact_type != ArtifactType.bootstrap_prompt,
    ).all()

    ordered_sections = []
    for key, defn in ARTIFACT_DEFS.items():
        art = next((a for a in artifacts if a.title == defn["title"]), None)
        if not art or not art.content:
            continue
        content_text = art.content.get("text") if isinstance(art.content, dict) else str(art.content)
        if not content_text:
            continue
        ordered_sections.append(f"## {defn['title']}\n\n{content_text}")

    if not ordered_sections:
        raise HTTPException(status_code=400, detail="No completed artifacts available")

    design_block = get_design_context(project.id)

    prompt = f"""You are an expert senior full-stack engineer.
Build the product described below as a production-quality MVP.

Project: {project.name}
Description: {project.description or 'N/A'}
Target Audience: {project.target_audience or 'N/A'}
Problem Statement: {project.problem_statement or 'N/A'}

Requirements package:

{chr(10).join(ordered_sections)}
{design_block}

Available libraries (pre-installed, ready to import):
- react-router-dom (BrowserRouter already wraps App in main.tsx)
- framer-motion (motion, AnimatePresence, useScroll, useTransform, useInView)
- lucide-react (named icon imports — use for ALL icons, never emoji)
- tailwindcss v3 (via PostCSS — App.css must start with @tailwind base; @tailwind components; @tailwind utilities;)

Implementation requirements:
- Build the COMPLETE application in a single generation — every page fully built
- Use react-router-dom for all navigation between pages
- Use Tailwind CSS utility classes with CSS custom properties for theming
- Use framer-motion for all animations, transitions, and scroll effects
- Use lucide-react for all icons throughout the application

BUILD PHASES (all in one output):

Phase 1 — STUNNING LANDING PAGE:
- Hero with framer-motion entrance animations (fade-up stagger), parallax scroll via useScroll/useTransform
- Floating animated decorative elements (gradient orbs, glowing accents)
- Feature grid with useInView scroll-triggered staggered reveal animations
- Social proof / testimonials section with animated cards
- Pricing or value proposition section
- Strong CTA sections with animated gradient backgrounds
- Professional footer with nav links and copyright
- ALL copy must be compelling and specific to the product — NEVER lorem ipsum

Phase 2 — AUTH FLOW (Login + Register):
- Beautiful full-screen auth layouts with animated form transitions
- Mock authentication — accept ANY email/password, store in localStorage, redirect to dashboard
- NO real backend — simulate a brief loading animation then redirect
- Animated transitions between Login and Register pages
- Social login buttons (Google, GitHub) as beautiful non-functional UI
- "Forgot password" link (can show a simple message)

Phase 3 — DASHBOARD:
- Full layout with collapsible sidebar (lucide-react icons, active states, animated collapse)
- Top header with user avatar, notification bell, search
- Metrics/KPI cards (4-6) with animated number counters and trend indicators
- Recent activity list with staggered entrance animations
- Quick action buttons
- Data table or content grid with proper structure
- All sidebar links navigate to real routes
- Responsive: sidebar collapses to hamburger on mobile

Phase 4 — ALL REMAINING SCREENS:
- Build every screen referenced in the design mockups and requirements as a full route
- Each page has real structured content, not placeholder text
- Wrap authenticated pages in the dashboard layout

Design standards:
- Dark mode by default with premium SaaS aesthetic
- CSS custom properties for theme colors, Tailwind utilities for layout/spacing
- Glass-morphism effects (backdrop-blur, semi-transparent surfaces)
- Smooth transitions on ALL interactive elements
- Consistent border-radius, shadows, and spacing throughout
- Professional typography hierarchy
- If Design Mockups are provided above, use them as the PRIMARY visual reference.
  Translate the HTML/CSS layout, colors, typography, and component structure
  into React/TSX components + Tailwind + App.css variables. Preserve the exact look and feel.
- Follow any CDO Design Foundation guidelines (color palette, spacing, UX patterns).
"""

    payload = {
        "text": prompt,
        "word_count": len(prompt.split()),
        "token_estimate": max(1, len(prompt) // 4),
    }

    existing_bootstrap = db.query(Artifact).filter(
        Artifact.project_id == project.id,
        Artifact.artifact_type == ArtifactType.bootstrap_prompt,
    ).first()

    if existing_bootstrap:
        existing_bootstrap.title = "AI Bootstrap Prompt"
        existing_bootstrap.content = payload
        existing_bootstrap.status = AgentStatus.complete
        existing_bootstrap.updated_at = datetime.utcnow()
        artifact = existing_bootstrap
    else:
        artifact = Artifact(
            id=str(uuid.uuid4()),
            project_id=project.id,
            artifact_type=ArtifactType.bootstrap_prompt,
            title="AI Bootstrap Prompt",
            content=payload,
            status=AgentStatus.complete,
        )
        db.add(artifact)

    db.commit()
    db.refresh(artifact)
    return artifact


def _all_primary_artifacts_complete(db: Session, project_id: str) -> bool:
    completed_titles = {
        title for (title,) in db.query(Artifact.title).filter(
            Artifact.project_id == project_id,
            Artifact.status == AgentStatus.complete,
            Artifact.artifact_type != ArtifactType.bootstrap_prompt,
        ).all()
    }
    return all(defn["title"] in completed_titles for defn in ARTIFACT_DEFS.values())


def _maybe_refresh_bootstrap_prompt(db: Session, project_id: str) -> None:
    if not _all_primary_artifacts_complete(db, project_id):
        return

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    _build_bootstrap_prompt_artifact(db, project)


# ── Background generation ────────────────────────────────────────────────────

def _resolve_artifact_model(user_id: str | None, db=None) -> dict:
    """Resolve model config for artifact generation, with user's key."""
    if user_id:
        from model_resolver import resolve_model_for_task
        from models import ModelRouting

        # Prefer artifacts-specific routing when configured; otherwise mirror
        # the design routing so artifacts behave like mockup generation by default.
        has_artifacts_routing = False
        close_db = False
        if db is None:
            from models import SessionLocal
            db = SessionLocal()
            close_db = True
        try:
            has_artifacts_routing = (
                db.query(ModelRouting)
                .filter(ModelRouting.user_id == user_id, ModelRouting.task_type == "artifacts")
                .first()
                is not None
            )
        finally:
            if close_db:
                db.close()

        if has_artifacts_routing:
            return resolve_model_for_task(user_id, "artifacts", db=db)
        return resolve_model_for_task(user_id, "design", db=db)
    return {"model": _get_model(), "api_key": None, "api_base": None, "provider_name": "Default"}


# Limit concurrent LLM calls per-worker (raised from 3 for 1M/day throughput)
_ARTIFACT_SEMAPHORE = asyncio.Semaphore(10)


async def _generate_single_artifact(project_id: str, artifact_key: str, artifact_def: dict, context: str, user_id: str | None = None):
    """Generate a single artifact via LLM."""
    from models import SessionLocal

    db = SessionLocal()
    try:
        artifact = db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.title == artifact_def["title"],
        ).first()
        if not artifact:
            return

        artifact.status = AgentStatus.running
        db.commit()

        try:
            model_config = _resolve_artifact_model(user_id, db=db)
            if model_config.get("error"):
                raise HTTPException(status_code=400, detail=model_config["error"])
            call_kwargs = {
                "model": model_config["model"],
                "messages": [
                    {"role": "system", "content": f"You are a senior product strategist and business analyst. Generate a professional, detailed document.\n\n{artifact_def['prompt']}"},
                    {"role": "user", "content": context},
                ],
                "temperature": 0.7,
                "max_tokens": 4000,
            }
            if model_config.get("api_key"):
                call_kwargs["api_key"] = model_config["api_key"]
            if model_config.get("api_base"):
                call_kwargs["api_base"] = model_config["api_base"]
            print(f"📄 Artifact [{artifact_key}] using: {model_config['model']} via {model_config['provider_name']}")
            resp = await litellm.acompletion(**call_kwargs)
            content_text = resp.choices[0].message.content.strip()
            artifact.content = {"text": content_text}
            artifact.status = AgentStatus.complete
        except Exception as e:
            print(f"❌ Artifact [{artifact_key}] error: {e}")
            artifact.status = AgentStatus.error
            artifact.content = {"error": str(e)}

        artifact.updated_at = datetime.utcnow()
        db.commit()

        if artifact.status == AgentStatus.complete:
            _maybe_refresh_bootstrap_prompt(db, project_id)
    finally:
        db.close()


async def _throttled_artifact(project_id, key, artifact_def, context, user_id):
    """Wrapper that throttles concurrent API calls."""
    async with _ARTIFACT_SEMAPHORE:
        await _generate_single_artifact(project_id, key, artifact_def, context, user_id)


async def _generate_all_artifacts(project_id: str, user_id: str | None = None):
    """Generate all artifacts for a project in parallel (skips already complete ones)."""
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        context = _build_project_context(project)
        uid = user_id or project.user_id

        # Only generate artifacts that aren't already complete
        pending = db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.status != AgentStatus.complete,
        ).all()
        pending_titles = {a.title for a in pending}

        tasks = []
        for key, artifact_def in ARTIFACT_DEFS.items():
            if artifact_def["title"] in pending_titles:
                tasks.append(_throttled_artifact(project_id, key, artifact_def, context, uid))

        if tasks:
            await asyncio.gather(*tasks)

        _maybe_refresh_bootstrap_prompt(db, project_id)
    finally:
        db.close()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/{project_id}/artifacts")
async def list_artifacts(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()

    # Build reverse lookup: title → ARTIFACT_DEFS key
    title_to_key = {defn["title"]: key for key, defn in ARTIFACT_DEFS.items()}

    def _map_status(status_val: str) -> str:
        """Map backend status to frontend-expected status."""
        if status_val == "running":
            return "generating"
        return status_val

    result = []
    for a in artifacts:
        content_text = None
        if a.content:
            content_text = a.content.get("text") if isinstance(a.content, dict) else str(a.content)
        artifact_key = title_to_key.get(a.title, a.title.lower().replace(" ", "_"))
        result.append({
            "type": artifact_key,
            "title": a.title,
            "status": _map_status(a.status.value),
            "content": content_text,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        })

    # Add missing artifact types as pending
    existing_titles = {a.title for a in artifacts}
    for key, defn in ARTIFACT_DEFS.items():
        if defn["title"] not in existing_titles:
            result.append({
                "type": key,
                "title": defn["title"],
                "status": "pending",
                "content": None,
                "updated_at": None,
            })

    return {"artifacts": result}


@router.post("/{project_id}/artifacts/generate")
@limiter.limit("30/minute")
async def generate_artifacts(
    request: Request,
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Enforce monthly artifact set limit (raises 402 if over limit)
    billing.enforce_artifact_limit(db, user)

    # Create artifact records — only reset incomplete ones
    for key, defn in ARTIFACT_DEFS.items():
        existing = db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.title == defn["title"],
        ).first()

        if not existing:
            artifact = Artifact(
                id=str(uuid.uuid4()),
                project_id=project_id,
                artifact_type=defn["type"],
                title=defn["title"],
                status=AgentStatus.pending,
            )
            db.add(artifact)
        elif existing.status != AgentStatus.complete:
            existing.status = AgentStatus.pending
            existing.content = None

    db.commit()

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="artifacts/generate.requested",
                data={"project_id": project_id, "user_id": user.id},
            ))
            print(f"📨 Inngest event: artifacts/generate.requested for {project_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_all_artifacts, project_id, user.id)
    else:
        background_tasks.add_task(_generate_all_artifacts, project_id, user.id)

    billing.record_artifact_set(db, user.id)
    return {"status": "generating"}


@router.get("/{project_id}/artifacts/{artifact_id}")
async def get_artifact(
    project_id: str,
    artifact_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = _find_artifact_by_id_or_key(db, project_id, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    content_text = None
    if artifact.content:
        content_text = artifact.content.get("text") if isinstance(artifact.content, dict) else str(artifact.content)

    return {
        "id": artifact.id,
        "type": artifact.artifact_type.value,
        "title": artifact.title,
        "status": artifact.status.value,
        "content": content_text,
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
    }


@router.post("/{project_id}/artifacts/generate-single/{artifact_key}")
@limiter.limit("30/minute")
async def generate_single_artifact_endpoint(
    request: Request,
    project_id: str,
    artifact_key: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) a single artifact by its key name."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact_def = ARTIFACT_DEFS.get(artifact_key)
    if not artifact_def:
        raise HTTPException(status_code=400, detail=f"Unknown artifact type: {artifact_key}")

    # Create or reset the DB record
    existing = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.title == artifact_def["title"],
    ).first()

    if existing:
        existing.status = AgentStatus.pending
        existing.content = None
        existing.updated_at = datetime.utcnow()
    else:
        existing = Artifact(
            id=str(uuid.uuid4()),
            project_id=project_id,
            artifact_type=artifact_def["type"],
            title=artifact_def["title"],
            status=AgentStatus.pending,
        )
        db.add(existing)
    db.commit()

    context = _build_project_context(project)
    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="artifacts/generate-single.requested",
                data={"project_id": project_id, "artifact_key": artifact_key, "artifact_def": artifact_def, "context": context, "user_id": user.id},
            ))
            print(f"📨 Inngest event: artifacts/generate-single.requested for {project_id[:8]}/{artifact_key}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_single_artifact, project_id, artifact_key, artifact_def, context, user.id)
    else:
        background_tasks.add_task(_generate_single_artifact, project_id, artifact_key, artifact_def, context, user.id)


@router.post("/{project_id}/artifacts/regenerate-all")
@limiter.limit("30/minute")
async def regenerate_all_artifacts(
    request: Request,
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate all artifacts by resetting their statuses to pending."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Reset all artifact statuses to pending
    artifacts_to_reset = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.artifact_type != ArtifactType.bootstrap_prompt,
    ).all()
    for art in artifacts_to_reset:
        art.status = AgentStatus.pending
        art.content = None
        art.updated_at = datetime.utcnow()
    db.commit()

    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="artifacts/regenerate-all.requested",
                data={"project_id": project_id, "user_id": user.id},
            ))
            print(f"📨 Inngest event: artifacts/regenerate-all.requested for {project_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_all_artifacts, project_id, user.id)
    else:
        background_tasks.add_task(_generate_all_artifacts, project_id, user.id)

    return {"status": "regenerating"}

    return {"status": "generating", "artifact_key": artifact_key}


@router.post("/{project_id}/artifacts/{artifact_id}/regenerate")
@limiter.limit("30/minute")
async def regenerate_artifact(
    request: Request,
    project_id: str,
    artifact_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = _find_artifact_by_id_or_key(db, project_id, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact_key = None
    artifact_def = None
    for key, defn in ARTIFACT_DEFS.items():
        if defn["title"] == artifact.title:
            artifact_key = key
            artifact_def = defn
            break

    if not artifact_def or not artifact_key:
        raise HTTPException(status_code=400, detail="Unsupported artifact type")

    artifact.status = AgentStatus.pending
    artifact.content = None
    artifact.updated_at = datetime.utcnow()
    db.commit()

    context = _build_project_context(project)
    if use_inngest():
        try:
            await inngest_client.send(inngest.Event(
                name="artifacts/generate-single.requested",
                data={"project_id": project_id, "artifact_key": artifact_key, "artifact_def": artifact_def, "context": context, "user_id": user.id},
            ))
            print(f"📨 Inngest event: artifacts/generate-single.requested (regen) for {project_id[:8]}/{artifact_key}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(_generate_single_artifact, project_id, artifact_key, artifact_def, context, user.id)
    else:
        background_tasks.add_task(_generate_single_artifact, project_id, artifact_key, artifact_def, context, user.id)

    return {"status": "generating", "artifact_id": artifact.id}


@router.post("/{project_id}/bootstrap-prompt")
async def build_bootstrap_prompt(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    artifact = _build_bootstrap_prompt_artifact(db, project)
    return _bootstrap_payload_from_artifact(project_id, artifact)


@router.get("/{project_id}/bootstrap-prompt")
async def get_bootstrap_prompt(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.artifact_type == ArtifactType.bootstrap_prompt,
        Artifact.status == AgentStatus.complete,
    ).first()
    if not artifact:
        return {"prompt": None, "word_count": 0, "token_estimate": 0}

    return _bootstrap_payload_from_artifact(project_id, artifact)
