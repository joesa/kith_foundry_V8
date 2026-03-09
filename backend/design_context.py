"""
Design context helper — builds a compact design-reference block
that the coding AI agent can consume alongside user prompts.

Used by:
  - artifacts_api.py  (appended to the bootstrap prompt)
  - agent.py          (silently injected into every LLM call)
"""
import json
from models import (
    SessionLocal, Project, DesignMockup, CSuiteAnalysis,
    CSuiteRole, MockupStatus, Artifact, ArtifactType, AgentStatus,
)
from design_intelligence import (
    compose_project_context,
    build_design_brief,
    build_compiled_design_spec,
    format_design_brief,
    format_compiled_design_spec,
)


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

        # ── Design System Foundation artifact ────────────────────────────
        dsf = db.query(Artifact).filter(
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

        # ── User-Approved Mockups only ─────────────────────────────────────
        mockups = (
            db.query(DesignMockup)
            .filter(
                DesignMockup.project_id == project_id,
                DesignMockup.status == MockupStatus.approved,
            )
            .order_by(DesignMockup.sort_order)
            .all()
        )

        if mockups:
            screen_blocks = []
            brief_refs = []
            for m in mockups:
                code = (m.component_code or "").strip()
                if not code:
                    continue
                brief_refs.append({
                    "name": m.screen_name,
                    "description": m.description or "N/A",
                    "status": m.status.value,
                })
                screen_blocks.append(
                    f"### {m.screen_name}\n"
                    f"Description: {m.description or 'N/A'}\n"
                    f"Priority: {m.priority.value}\n\n"
                    f"```html\n{code}\n```"
                )

            if screen_blocks:
                sections.append(
                    "## Design Mockups\n\n"
                    "The following HTML/CSS mockups have been explicitly approved by the user "
                    "in the Design Studio. Use them as the authoritative visual reference for "
                    "layout, color palette, typography, spacing, and component structure when "
                    "building React components. Translate the HTML/CSS patterns into "
                    "React/TSX + App.css, preserving the exact visual design.\n\n"
                    + "\n\n".join(screen_blocks)
                )
        else:
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
        dsf = db.query(Artifact).filter(
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

        # Screen inventory — approved only (no full HTML)
        mockups = (
            db.query(DesignMockup)
            .filter(
                DesignMockup.project_id == project_id,
                DesignMockup.status == MockupStatus.approved,
            )
            .order_by(DesignMockup.sort_order)
            .all()
        )

        brief_refs = []
        if mockups:
            # Extract CSS custom properties from the first approved mockup
            # to give the agent the exact brand color palette.
            css_vars = ""
            for m in mockups:
                if m.component_code:
                    import re as _re
                    root_match = _re.search(r':root\s*\{([^}]+)\}', m.component_code)
                    if root_match:
                        css_vars = f"\n\nBrand CSS variables (use these in your React/Tailwind code):\n```css\n:root {{\n{root_match.group(1).strip()}\n}}\n```"
                        break

            lines = [
                "## Design Screen Inventory",
                "User-approved screens from Design Studio (implement these screens with visual consistency):",
            ]
            for m in mockups:
                brief_refs.append({
                    "name": m.screen_name,
                    "description": m.description or "N/A",
                    "status": m.status.value,
                })
                lines.append(f"  - **{m.screen_name}** ({m.priority.value}): {m.description or 'N/A'}")
            if css_vars:
                lines.append(css_vars)
            sections.append("\n".join(lines))

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

        if not sections:
            return ""

        return (
            "\n# ── Design Reference ──\n\n"
            + "\n\n".join(sections)
            + "\n"
        )
    finally:
        db.close()
