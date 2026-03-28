"""
Design context helper — builds a compact design-reference block
that the coding AI agent can consume alongside user prompts.

Used by:
  - artifacts_api.py  (appended to the bootstrap prompt)
  - agent.py          (silently injected into every LLM call)
"""
import json
from models import (
    SessionLocal, Project, CSuiteAnalysis,
    CSuiteRole, Artifact, ArtifactType, AgentStatus,
)
from design_intelligence import (
    compose_project_context,
    build_design_brief,
    build_compiled_design_spec,
    format_design_brief,
    format_compiled_design_spec,
)
import re as _re

# CSS custom-property names that belong to the brand/palette token contract.
# We match vars for color, typography scale, and surface/border naming conventions.
_PALETTE_VAR_PAT = _re.compile(
    r'^\s*(--(?:bg|background|surface|primary|secondary|accent|cta|text|muted|border|color'
    r'|font(?:-family|-size|-weight|-display|-scale)?|foreground|line-height|letter-spacing)'
    r'[^:]*\s*:[^;]+;)',
    _re.IGNORECASE | _re.MULTILINE,
)


def _extract_design_contract_css(project_id: str, db, project_context: str) -> str:
    """Derive a locked CSS :root block from the best available design source.

    Priority order:
      1. GPT Engine design tokens — structured tokens from the design engine
      2. Design System Foundation artifact :root block
      2.5 Persisted design_tokens artifact — previously derived contract (stable)
      3. Vendor brief palette → synthetic CSS vars (derived then auto-persisted
         so subsequent calls reuse the same tokens, preventing visual drift)

    Returns a ready-to-embed :root { ... } string, or empty string if no data.
    """
    # ── Priority 1: GPT Engine design tokens (structured) ─────────────────
    dsf = (
        db.query(Artifact)
        .filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == ArtifactType.design_system,
            Artifact.status == AgentStatus.complete,
        )
        .first()
    )
    if dsf and isinstance(dsf.content, dict) and dsf.content.get("design_tokens"):
        try:
            from design_engine import extract_design_tokens_css
            css = extract_design_tokens_css(dsf.content)
            if css and css.strip() not in ("", ":root {\n}"):
                return css
        except Exception:
            pass  # Fall through to :root extraction

    # ── Priority 2: Design System Foundation artifact :root block ─────────
    if dsf and dsf.content:
        text = dsf.content.get("text") if isinstance(dsf.content, dict) else str(dsf.content)
        root_m = _re.search(r':root\s*\{([^}]+)\}', text or "", _re.DOTALL)
        if root_m:
            lines = [m.group(1).strip() for m in _PALETTE_VAR_PAT.finditer(root_m.group(1))]
            if lines:
                return ":root {\n  " + "\n  ".join(lines) + "\n}"

    # ── Priority 2.5: persisted design_tokens artifact ────────────────────
    # Checked BEFORE vendor synthesis so a previously-derived contract is re-used
    # across all Editor builds, preventing token drift between prompts.
    dt = (
        db.query(Artifact)
        .filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == ArtifactType.design_tokens,
            Artifact.status == AgentStatus.complete,
        )
        .first()
    )
    if dt and dt.content:
        dt_css = dt.content.get("css") if isinstance(dt.content, dict) else str(dt.content)
        if dt_css and dt_css.strip():
            return dt_css.strip()

    # ── Priority 3: vendor brief palette → synthetic tokens ───────────────
    # Key mapping: palette keys in build_design_brief are
    #   background, primary, secondary, cta, text, border
    # Typography: use heading_font / body_font directly (not the pairing name string)
    brief = build_design_brief(project_context)
    rec = brief.get("reasoned_recommendation", {})
    palette = rec.get("palette", {})
    typography = rec.get("typography_direction", {})
    lines = []
    for var, val in [
        ("--bg", palette.get("background")),
        ("--primary", palette.get("primary")),
        ("--secondary", palette.get("secondary")),
        ("--cta", palette.get("cta")),
        ("--text", palette.get("text")),
        ("--border", palette.get("border")),
    ]:
        if val and val.strip():
            lines.append(f"  {var}: {val.strip()};")
    h_font = typography.get("heading_font", "").strip()
    b_font = typography.get("body_font", "").strip()
    if h_font:
        lines.append(f"  --font-heading: '{h_font}', sans-serif;")
    if b_font and b_font != h_font:
        lines.append(f"  --font-body: '{b_font}', sans-serif;")
    if not lines:
        return ""

    css = ":root {\n" + "\n".join(lines) + "\n}"

    # Auto-persist so every subsequent Editor call uses the same locked tokens.
    # Without this, re-running build_design_brief on a different prompt could
    # match a different colors.csv row and drift the palette.
    try:
        new_dt = Artifact(
            project_id=project_id,
            artifact_type=ArtifactType.design_tokens,
            status=AgentStatus.complete,
            content={"css": css, "source": "vendor_synthesis",
                     "style_family": rec.get("style_family", ""),
                     "industry": brief.get("industry_category", "")},
        )
        db.add(new_dt)
        db.commit()
    except Exception:
        db.rollback()  # non-fatal — contract is returned even if persistence fails

    return css


def get_design_contract_css(project_id: str) -> str:
    """Standalone export: return the locked CSS :root contract for a project.

    Used by agent.py for deterministic post-generation token enforcement —
    same concept as _transplant_root_vars in the mockup pipeline.
    Returns empty string if no design data exists yet.
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return ""
        project_context = compose_project_context(
            product_name=project.name,
            description=project.description,
            target_audience=project.target_audience,
            idea=project.idea.content if project.idea else None,
        )
        return _extract_design_contract_css(project_id, db, project_context)
    finally:
        db.close()


def get_design_context(project_id: str) -> str:
    """Return a markdown-formatted design context block for the coding agent.

    Includes:
      1. CDO design-system recommendations (if available)
      2. Per-screen mockup component code (HTML/CSS) for every completed mockup

    Returns an empty string when there are no designs or CDO analysis.
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return ""

        # ── Engine-first: prefer GPT Design Engine output ─────────────────
        _engine_art = (
            db.query(Artifact)
            .filter(
                Artifact.project_id == project_id,
                Artifact.artifact_type == ArtifactType.design_system,
                Artifact.status == AgentStatus.complete,
            )
            .first()
        )
        if _engine_art and isinstance(_engine_art.content, dict) and _engine_art.content.get("design_tokens"):
            try:
                from design_engine import build_design_context_for_agent
                engine_ref = build_design_context_for_agent(_engine_art.content)
                if engine_ref:
                    return (
                        "\n\n# ── Design Reference (GPT Design Engine) ──────────────\n\n"
                        + engine_ref
                        + "\n"
                    )
            except Exception as _e:
                print(f"Engine design context failed, falling back to legacy: {_e}")

        sections: list[str] = []

        cdo_data = None
        design_system_text = ""

        # ── CDO Design Foundation ────────────────────────────────────────
        cdo = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.cdo,
        ).first()

        if cdo and cdo.analysis:
            analysis = cdo.analysis if isinstance(cdo.analysis, dict) else {}
            cdo_data = analysis
            parts = []
            if analysis.get("recommendation"):
                parts.append(f"Recommendation: {analysis['recommendation']}")
            if analysis.get("suggestions"):
                parts.append("Design-system suggestions:")
                for s in analysis["suggestions"]:
                    parts.append(f"  - {s}")
            if analysis.get("strengths"):
                parts.append("Design strengths:")
                for s in analysis["strengths"]:
                    parts.append(f"  - {s}")
            if analysis.get("risks"):
                parts.append("Design risks to mitigate:")
                for r in analysis["risks"]:
                    parts.append(f"  - {r}")
            if parts:
                sections.append(
                    "## CDO Design Foundation\n\n" + "\n".join(parts)
                )

        # ── Executive Strategy (Synthesizer) ─────────────────────────────
        synth = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.synthesizer,
        ).first()

        if synth and synth.analysis:
            sa = synth.analysis if isinstance(synth.analysis, dict) else {}
            synth_parts = []
            if sa.get("recommendation"):
                synth_parts.append(f"Strategic Direction: {sa['recommendation']}")
            if sa.get("priority_actions"):
                synth_parts.append("Priority Actions:")
                for a in sa["priority_actions"][:5]:
                    synth_parts.append(f"  - {a}")
            if synth_parts:
                sections.append(
                    "## Executive Strategy\n\n" + "\n".join(synth_parts)
                )

        # ── Design System Foundation artifact ────────────────────────────
        dsf = _engine_art or db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == ArtifactType.design_system,
            Artifact.status == AgentStatus.complete,
        ).first()

        if dsf and dsf.content:
            dsf_text = dsf.content.get("text") if isinstance(dsf.content, dict) else str(dsf.content)
            if dsf_text and dsf_text.strip():
                design_system_text = dsf_text.strip()
                sections.append(
                    "## Design System Foundation\n\n"
                    "The following design system was generated as a project artifact. "
                    "Use these exact tokens, colors, typography, spacing, and component "
                    "specifications when building or modifying any UI component.\n\n"
                    + design_system_text
                )

        brief_refs = []

        project_context = compose_project_context(
            product_name=project.name,
            description=project.description,
            target_audience=project.target_audience,
            idea=project.idea.content if project.idea else None,
            cdo_analysis=cdo_data,
            design_system_text=design_system_text,
        )
        brief = build_design_brief(project_context, approved_mockups=brief_refs)
        compiled_spec = build_compiled_design_spec(project_context, approved_mockups=brief_refs)
        sections.insert(0, format_design_brief(brief, compact=False))
        sections.insert(0, format_compiled_design_spec(compiled_spec, compact=False))

        # ── Mandatory Design Contract (CSS token lock) ────────────────────
        # Inserted at index 0 so the LLM reads it before everything else.
        contract_css = _extract_design_contract_css(project_id, db, project_context)
        if contract_css:
            sections.insert(0, (
                "## ⚠ MANDATORY DESIGN CONTRACT\n\n"
                "Copy these exact CSS tokens into `src/App.css` `:root {}` verbatim. "
                "Do NOT invent alternative colors. Use `var(--token)` for all "
                "backgrounds, surfaces, and brand colors:\n\n"
                f"```css\n{contract_css}\n```\n\n"
                "**Forbidden:** AI purple/cyan/pink gradient clichés · "
                "glassmorphism without purpose · emoji as UI icons (use lucide-react) · "
                "hardcoded hex values for backgrounds or brand.\n"
                "**Required:** `cursor: pointer` on all interactive elements · "
                "`@media (prefers-reduced-motion: reduce)` whenever you write @keyframes · "
                "hover transitions 150–300 ms on interactive elements."
            ))

        if not sections:
            return ""

        return (
            "\n\n# ── Design Reference (from Design Studio) ──────────────\n\n"
            + "\n\n".join(sections)
            + "\n"
        )

    finally:
        db.close()


def get_design_context_compact(project_id: str) -> str:
    """Lighter version — CDO summary + screen names/descriptions only (no full HTML).

    Used by the agent for subsequent (non-bootstrap) requests so it stays
    aware of the design system without bloating the context window.
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return ""

        # ── Engine-first: prefer GPT Design Engine output ─────────────────
        _engine_art = (
            db.query(Artifact)
            .filter(
                Artifact.project_id == project_id,
                Artifact.artifact_type == ArtifactType.design_system,
                Artifact.status == AgentStatus.complete,
            )
            .first()
        )
        if _engine_art and isinstance(_engine_art.content, dict) and _engine_art.content.get("design_tokens"):
            try:
                from design_engine import build_design_context_for_agent
                engine_ref = build_design_context_for_agent(_engine_art.content)
                if engine_ref:
                    return (
                        "\n# ── Design Reference (GPT Design Engine) ──\n\n"
                        + engine_ref
                        + "\n"
                    )
            except Exception as _e:
                print(f"Engine design context (compact) failed, falling back: {_e}")

        sections: list[str] = []

        cdo_data = None
        design_system_text = ""

        # CDO Foundation
        cdo = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.agent_role == CSuiteRole.cdo,
        ).first()

        if cdo and cdo.analysis:
            analysis = cdo.analysis if isinstance(cdo.analysis, dict) else {}
            cdo_data = analysis
            parts = []
            if analysis.get("recommendation"):
                parts.append(f"Recommendation: {analysis['recommendation']}")
            if analysis.get("suggestions"):
                for s in analysis["suggestions"]:
                    parts.append(f"  - {s}")
            if parts:
                sections.append("## CDO Design Foundation\n" + "\n".join(parts))

        # Design System Foundation artifact (compact summary)
        dsf = _engine_art or db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == ArtifactType.design_system,
            Artifact.status == AgentStatus.complete,
        ).first()

        if dsf and dsf.content:
            dsf_text = dsf.content.get("text") if isinstance(dsf.content, dict) else str(dsf.content)
            if dsf_text and dsf_text.strip():
                design_system_text = dsf_text.strip()
                # Include full design system — it's the authoritative style reference
                sections.append(
                    "## Design System Foundation\n"
                    "Follow these tokens, colors, typography, and component specs for all UI work:\n\n"
                    + design_system_text
                )

        brief_refs = []

        project_context = compose_project_context(
            product_name=project.name,
            description=project.description,
            target_audience=project.target_audience,
            idea=project.idea.content if project.idea else None,
            cdo_analysis=cdo_data,
            design_system_text=design_system_text,
        )
        brief = build_design_brief(project_context, approved_mockups=brief_refs)
        compiled_spec = build_compiled_design_spec(project_context, approved_mockups=brief_refs)
        sections.insert(0, format_design_brief(brief, compact=True))
        sections.insert(0, format_compiled_design_spec(compiled_spec, compact=True))

        # ── Mandatory Design Contract (compact — CSS vars only) ───────────
        contract_css = _extract_design_contract_css(project_id, db, project_context)
        if contract_css:
            sections.insert(0, (
                "## ⚠ MANDATORY DESIGN CONTRACT\n\n"
                f"```css\n{contract_css}\n```\n\n"
                "Use `var(--token)` for all brand colors. "
                "Do NOT hardcode hex values for backgrounds or brand elements."
            ))

        if not sections:
            return ""

        return (
            "\n# ── Design Reference ──\n\n"
            + "\n\n".join(sections)
            + "\n"
        )
    finally:
        db.close()
