"""
Export API — lets authenticated users download their project data
as .md, .docx, or .pdf.

Endpoints:
  GET /api/v1/projects/{project_id}/export/csuite.{fmt}
  GET /api/v1/projects/{project_id}/export/artifact/{artifact_key}.{fmt}
  GET /api/v1/projects/{project_id}/export/artifacts.{fmt}    (all, bundled)
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Literal

from models import get_db, User, Project, CSuiteAnalysis, Artifact
from auth import get_current_user
from export_service import render_csuite, render_artifact, render_all_artifacts

router = APIRouter(prefix="/api/v1/projects", tags=["export"])

Format = Literal["md", "docx", "pdf"]

_FMT_SUFFIX = {"md", "docx", "pdf"}


def _parse_fmt(filename: str) -> Format:
    """Extract and validate the format suffix from a filename like 'csuite.pdf'."""
    parts = filename.rsplit(".", 1)
    if len(parts) != 2 or parts[1] not in _FMT_SUFFIX:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Use .md, .docx, or .pdf")
    return parts[1]  # type: ignore[return-value]


# ── C-Suite export ────────────────────────────────────────────────────────────

@router.get("/{project_id}/export/{filename:path}")
async def export_project_document(
    project_id: str,
    filename: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generic export dispatcher. Supported filenames:
      csuite.md / csuite.docx / csuite.pdf
      artifact/{artifact_key}.md / artifact/{artifact_key}.docx / artifact/{artifact_key}.pdf
      artifacts.md / artifacts.docx / artifacts.pdf   (all artifacts bundled)
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name or "Project"

    # ── Route by prefix ───────────────────────────────────────────────────────

    # csuite.{fmt}
    if filename.startswith("csuite."):
        fmt = _parse_fmt(filename)
        analyses = (
            db.query(CSuiteAnalysis)
            .filter(CSuiteAnalysis.project_id == project_id)
            .all()
        )
        rows = [
            {
                "agent_role": a.agent_role.value if hasattr(a.agent_role, "value") else a.agent_role,
                "status": a.status.value if hasattr(a.status, "value") else a.status,
                "score": a.score,
                "analysis": a.analysis or {},
            }
            for a in analyses
        ]
        data, media_type, dl_name = render_csuite(project_name, rows, fmt)
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{dl_name}"'},
        )

    # artifacts.{fmt}  (all at once)
    if filename.startswith("artifacts."):
        fmt = _parse_fmt(filename)
        arts = (
            db.query(Artifact)
            .filter(Artifact.project_id == project_id)
            .all()
        )
        rows = [
            {
                "title": a.title,
                "artifact_type": a.artifact_type.value if hasattr(a.artifact_type, "value") else a.artifact_type,
                "status": a.status.value if hasattr(a.status, "value") else a.status,
                "content": a.content,
            }
            for a in arts
        ]
        data, media_type, dl_name = render_all_artifacts(project_name, rows, fmt)
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{dl_name}"'},
        )

    # artifact/{key}.{fmt}  (single artifact by key or type slug)
    if filename.startswith("artifact/"):
        rest = filename[len("artifact/"):]
        fmt = _parse_fmt(rest)
        artifact_key = rest.rsplit(".", 1)[0]  # e.g. "prd", "tech_spec"

        # Look up by matching the string value of artifact_type against the key
        all_arts = (
            db.query(Artifact)
            .filter(Artifact.project_id == project_id)
            .all()
        )
        def _type_val(a):
            return a.artifact_type.value if hasattr(a.artifact_type, "value") else str(a.artifact_type)

        art = next((a for a in all_arts if _type_val(a) == artifact_key), None)

        if not art:
            raise HTTPException(status_code=404, detail=f"Artifact '{artifact_key}' not found for this project")
        if (art.status.value if hasattr(art.status, "value") else art.status) != "complete":
            raise HTTPException(status_code=409, detail="Artifact is not yet complete")

        data, media_type, dl_name = render_artifact(
            project_name, art.title, art.content, fmt
        )
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{dl_name}"'},
        )

    raise HTTPException(status_code=400, detail="Unknown export path. See API docs.")
