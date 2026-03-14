"""
GPT Design Engine — Phase 1

Replaces the vendor-CSV + Design DNA hash system with an LLM-driven
design architect pipeline.  The engine produces a structured design
system (tokens, layout, components, interactions, builder prompt)
that downstream agents and the code generator consume.

Pipeline:
    product_context  →  Design Brief Agent  →  Design Architect Agent
                                                    ↓
                                         Structured Design System JSON
                                                    ↓
                                   builder_prompt  +  design_tokens CSS
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import litellm
from sqlalchemy.orm import Session

from models import (
    Artifact, ArtifactType, AgentStatus, Project, CSuiteAnalysis,
    DesignMockup, MockupStatus,
)
from prompts import DESIGN_ARCHITECT_PROMPT, DESIGN_BRIEF_PROMPT
from circuit_breaker import llm_breaker, CircuitOpenError


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | list | None:
    """Extract the first valid JSON object/array from LLM output."""
    import re
    # Strip markdown fences
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0].strip()

    # Bracket-depth extraction for reliability
    start = None
    open_ch = None
    close_ch = None
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(clean):
        if esc:
            esc = False
            continue
        if ch == '\\' and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if start is None and ch in ('{', '['):
            start = i
            open_ch = ch
            close_ch = '}' if ch == '{' else ']'
            depth = 1
        elif start is not None:
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(clean[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


def _compose_project_context(project: Project, db: Session) -> str:
    """Build a markdown context block from project + C-Suite data."""
    parts: list[str] = []
    parts.append(f"**Product:** {project.name}")
    if project.description:
        parts.append(f"**Description:** {project.description}")
    if project.target_audience:
        parts.append(f"**Target Audience:** {project.target_audience}")
    if project.problem_statement:
        parts.append(f"**Problem:** {project.problem_statement}")

    # Pull C-Suite analyses if available
    analyses = (
        db.query(CSuiteAnalysis)
        .filter(CSuiteAnalysis.project_id == project.id, CSuiteAnalysis.analysis.isnot(None))
        .all()
    )
    if analyses:
        parts.append("\n**C-Suite Analysis Context:**")
        for a in analyses:
            role = a.agent_role.value.upper() if a.agent_role else "UNKNOWN"
            summary = json.dumps(a.analysis) if isinstance(a.analysis, dict) else str(a.analysis)
            # Truncate long analyses
            if len(summary) > 1500:
                summary = summary[:1500] + "..."
            parts.append(f"- **{role}:** {summary}")

    # Pull design preferences if set
    if project.design_preferences:
        parts.append(f"\n**Design Preferences:** {json.dumps(project.design_preferences)}")

    return "\n".join(parts)


async def _call_llm(
    system_prompt: str,
    user_prompt: str,
    model_id: str,
    llm_kwargs: dict,
    temperature: float = 0.4,
) -> dict | None:
    """Make a single LLM call and parse JSON output."""
    provider = llm_breaker.extract_provider(model_id)
    try:
        llm_breaker.check(provider)
        response = await llm_breaker.call(
            provider,
            litellm.acompletion(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                stream=False,
                timeout=llm_breaker.default_timeout,
                **llm_kwargs,
            ),
        )
        raw = response.choices[0].message.content or ""
        result = _extract_json(raw)
        if isinstance(result, dict):
            return result
        print(f"[design_engine] LLM returned non-dict JSON: {type(result)}")
        return None
    except CircuitOpenError as e:
        print(f"[design_engine] Circuit open: {e}")
        return None
    except Exception as e:
        print(f"[design_engine] LLM call failed: {e}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def generate_design_brief(
    project: Project,
    db: Session,
    model_id: str,
    llm_kwargs: dict,
) -> dict | None:
    """
    Step 1 of the Design Engine pipeline.
    Generates a design intelligence brief from project context.
    """
    context = _compose_project_context(project, db)
    user_prompt = f"""Generate a design intelligence brief for this product:

{context}

Output strict JSON as specified. Focus on making the design direction authentic
to this specific product — not a generic template."""

    return await _call_llm(DESIGN_BRIEF_PROMPT, user_prompt, model_id, llm_kwargs)


async def generate_design_system(
    project: Project,
    db: Session,
    model_id: str,
    llm_kwargs: dict,
    *,
    design_brief: dict | None = None,
) -> dict | None:
    """
    Step 2 of the Design Engine pipeline.
    Generates a complete structured design system (tokens, layout, components,
    interactions, builder prompt).

    If a design_brief is provided, it's included as additional context.
    """
    context = _compose_project_context(project, db)

    brief_section = ""
    if design_brief:
        brief_section = f"""

**Design Intelligence Brief (from research phase):**
```json
{json.dumps(design_brief, indent=2)}
```
Use this brief to inform your design decisions — respect its style family,
color direction, typography direction, and anti-patterns."""

    user_prompt = f"""Generate a complete design system for this product:

{context}
{brief_section}

Generate ALL pages needed for a fully functional application.
Every navigation link must have a corresponding page. No placeholder pages.
Output strict JSON as specified."""

    return await _call_llm(DESIGN_ARCHITECT_PROMPT, user_prompt, model_id, llm_kwargs, temperature=0.5)


async def run_full_design_pipeline(
    project: Project,
    db: Session,
    model_id: str,
    llm_kwargs: dict,
    *,
    progress_callback=None,
) -> dict:
    """
    Run the complete Design Engine pipeline:
      1. Generate design brief
      2. Generate full design system
      3. Persist artifacts to DB
      4. Return the design system

    progress_callback(stage: str, data: dict) is called at each step
    if provided (for WebSocket status updates).
    """
    if progress_callback:
        await progress_callback("design_brief_started", {})

    # Step 1: Design Brief
    brief = await generate_design_brief(project, db, model_id, llm_kwargs)
    if progress_callback:
        await progress_callback("design_brief_complete", {"brief": brief})

    # Step 2: Full Design System
    if progress_callback:
        await progress_callback("design_system_started", {})

    design_system = await generate_design_system(
        project, db, model_id, llm_kwargs, design_brief=brief
    )

    if not design_system:
        return {"error": "Design system generation failed", "brief": brief}

    if progress_callback:
        await progress_callback("design_system_complete", {"design_system": design_system})

    # Step 3: Persist artifacts
    _persist_design_artifacts(db, project.id, brief, design_system)

    return {
        "brief": brief,
        "design_system": design_system,
        "builder_prompt": design_system.get("builder_prompt", ""),
    }


def _persist_design_artifacts(
    db: Session,
    project_id: str,
    brief: dict | None,
    design_system: dict,
) -> None:
    """Persist the design engine output as Artifact rows."""
    now = datetime.utcnow()

    # Upsert design_tokens artifact
    tokens = design_system.get("design_tokens", {})
    _upsert_artifact(
        db, project_id, ArtifactType.design_tokens,
        "Design Tokens", tokens, now,
    )

    # Upsert design_system artifact (full system)
    _upsert_artifact(
        db, project_id, ArtifactType.design_system,
        "Design System (GPT Engine)", design_system, now,
    )

    # Upsert design_components artifact (component library)
    components = design_system.get("component_library", [])
    _upsert_artifact(
        db, project_id, ArtifactType.design_components,
        "Component Library", {"components": components}, now,
    )

    db.commit()


def _upsert_artifact(
    db: Session,
    project_id: str,
    artifact_type: ArtifactType,
    title: str,
    content: Any,
    now: datetime,
) -> None:
    existing = (
        db.query(Artifact)
        .filter_by(project_id=project_id, artifact_type=artifact_type)
        .first()
    )
    if existing:
        existing.content = content
        existing.status = AgentStatus.complete
        existing.updated_at = now
    else:
        db.add(Artifact(
            id=str(uuid.uuid4()),
            project_id=project_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            status=AgentStatus.complete,
        ))


# ── Design Token Extraction ───────────────────────────────────────────────────

def extract_design_tokens_css(design_system: dict) -> str:
    """Convert design_system.design_tokens into a CSS :root block.

    This is injected into App.css by the code agent and used for
    design contract enforcement.
    """
    tokens = design_system.get("design_tokens", {})
    colors = tokens.get("colors", {})
    typography = tokens.get("typography", {})
    borders = tokens.get("borders", {})
    shadows = tokens.get("shadows", {})
    spacing = tokens.get("spacing", {})

    lines: list[str] = [":root {"]

    # Colors
    for key, val in colors.items():
        css_name = key.replace("_", "-")
        lines.append(f"  --{css_name}: {val};")

    # Typography
    if typography.get("font_heading"):
        lines.append(f"  --font-heading: '{typography['font_heading']}', system-ui, sans-serif;")
    if typography.get("font_body"):
        lines.append(f"  --font-body: '{typography['font_body']}', system-ui, sans-serif;")

    # Borders
    for key, val in borders.items():
        css_name = key.replace("_", "-")
        lines.append(f"  --{css_name}: {val};")

    # Shadows
    for key, val in shadows.items():
        lines.append(f"  --shadow-{key}: {val};")

    # Spacing
    if spacing.get("section_gap"):
        lines.append(f"  --section-gap: {spacing['section_gap']};")
    if spacing.get("card_padding"):
        lines.append(f"  --card-padding: {spacing['card_padding']};")

    lines.append("}")
    return "\n".join(lines)


def build_design_context_for_agent(design_system: dict) -> str:
    """Build a compact design reference markdown block for code agents.

    This replaces design_context.py's get_design_context() when a GPT
    Design Engine system is available.
    """
    if not design_system:
        return ""

    parts: list[str] = ["## Design Reference (GPT Design Engine)\n"]

    # Product overview
    overview = design_system.get("product_overview", {})
    if overview:
        parts.append(f"**Product:** {overview.get('name', 'Unknown')}")
        parts.append(f"**Tone:** {overview.get('tone', '')}")
        parts.append(f"**Type:** {overview.get('product_type', '')}\n")

    # Design tokens CSS
    css = extract_design_tokens_css(design_system)
    if css:
        parts.append("## ⚠ MANDATORY DESIGN CONTRACT")
        parts.append(f"```css\n{css}\n```\n")

    # Layout architecture
    layout = design_system.get("layout_architecture", {})
    if layout.get("pages"):
        parts.append("**Pages:**")
        for page in layout["pages"]:
            sections = ", ".join(page.get("sections", []))
            parts.append(f"- **{page['name']}** (`{page.get('route', '/')}`) — {page.get('purpose', '')} — Sections: {sections}")
        parts.append("")

    # Navigation
    nav = layout.get("navigation", {})
    if nav.get("items"):
        parts.append(f"**Navigation Pattern:** {nav.get('pattern', 'sidebar')}")
        for item in nav["items"]:
            parts.append(f"  - {item.get('label', '')} → `{item.get('route', '')}` (icon: {item.get('icon', '')})")
        parts.append("")

    # Component library
    components = design_system.get("component_library", [])
    if components:
        parts.append("**Component Library:**")
        for c in components:
            props = ", ".join(c.get("props", []))
            parts.append(f"- **{c['name']}** ({props}) — {c.get('purpose', '')}")
        parts.append("")

    # Interaction design
    interactions = design_system.get("interaction_design", {})
    if interactions:
        parts.append("**Interactions:**")
        for key, val in interactions.items():
            parts.append(f"- {key.replace('_', ' ').title()}: {val}")
        parts.append("")

    # Anti-patterns
    anti = design_system.get("anti_patterns", [])
    if anti:
        parts.append("**Anti-Patterns (AVOID):**")
        for a in anti:
            parts.append(f"- ❌ {a}")

    return "\n".join(parts)


def get_design_system_from_artifacts(db: Session, project_id: str) -> dict | None:
    """Load a previously generated GPT Design Engine system from the DB."""
    artifact = (
        db.query(Artifact)
        .filter_by(
            project_id=project_id,
            artifact_type=ArtifactType.design_system,
            status=AgentStatus.complete,
        )
        .first()
    )
    if artifact and isinstance(artifact.content, dict):
        return artifact.content
    return None
