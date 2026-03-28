"""
Projects API — CRUD endpoints for user projects.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models import SessionLocal, get_db, Project, ProjectStatus, CSuiteAnalysis, Idea, User
from auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_audience: Optional[str] = None
    problem_statement: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    problem_statement: Optional[str] = None
    status: Optional[str] = None

class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    target_audience: Optional[str]
    problem_statement: Optional[str]
    status: str
    overall_score: Optional[int] = None
    overall_verdict: Optional[str] = None
    idea_source: Optional[str] = None
    preview_url: Optional[str] = None
    created_at: str
    updated_at: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _project_to_out(db: Session, p: Project) -> dict:
    """Serialize a Project ORM object to the API response dict."""
    score_row = db.query(func.round(func.avg(CSuiteAnalysis.score)).label("avg")).filter(
        CSuiteAnalysis.project_id == p.id,
        CSuiteAnalysis.score.isnot(None),
    ).one()
    overall_score = int(score_row.avg) if score_row.avg is not None else None

    overall_verdict = None
    if overall_score is not None:
        if overall_score >= 70:
            overall_verdict = "go"
        elif overall_score >= 50:
            overall_verdict = "conditional"
        else:
            overall_verdict = "no_go"

    idea_source = None
    if p.idea_id:
        idea = db.query(Idea).filter(Idea.id == p.idea_id).first()
        if idea and idea.source:
            idea_source = idea.source.value

    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "target_audience": p.target_audience,
        "problem_statement": p.problem_statement,
        "status": p.status.value if p.status else "ideation",
        "overall_score": overall_score,
        "overall_verdict": overall_verdict,
        "idea_source": idea_source,
        "preview_url": p.preview_url,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.updated_at.desc().nullslast())
        .all()
    )
    return {"projects": [_project_to_out(db, p) for p in projects]}


@router.post("")
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = Project(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        description=body.description,
        target_audience=body.target_audience,
        problem_statement=body.problem_statement,
        status=ProjectStatus.ideation,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_to_out(db, p)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_out(db, p)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.name is not None:
        p.name = body.name
    if body.description is not None:
        p.description = body.description
    if body.target_audience is not None:
        p.target_audience = body.target_audience
    if body.problem_statement is not None:
        p.problem_statement = body.problem_statement
    if body.status is not None:
        valid_statuses = {s.value for s in ProjectStatus}
        if body.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
        p.status = ProjectStatus(body.status)
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return _project_to_out(db, p)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    # Wipe Nhost Storage files first
    try:
        import asyncio
        from storage_service import delete_all_project_files_sync
        await asyncio.to_thread(delete_all_project_files_sync, project_id)
    except Exception as e:
        print(f"[delete_project] Storage wipe warning (continuing): {e}")

    db.delete(p)
    db.commit()
    return {"deleted": True}


# ── Context Compression / Reindex ─────────────────────────────────────────────

@router.post("/{project_id}/reindex")
async def reindex_project_embeddings(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-embed all project source files and brain entities for semantic search."""
    import asyncio as _aio
    from agent import read_all_project_files
    from embedding_service import reindex_project as _reindex
    from brain_service import delete_project_embeddings

    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    sync_session = SessionLocal()
    try:
        all_files = await read_all_project_files(sync_session, project_id)
        if not all_files:
            return {"status": "empty", "message": "No source files to index"}
        delete_project_embeddings(sync_session, project_id)
        sync_session.commit()
        stats = await _reindex(sync_session, project_id, all_files)
        sync_session.commit()
    finally:
        sync_session.close()

    return {
        "status": "complete",
        "files_indexed": stats.get("files_indexed", 0),
        "components_indexed": stats.get("components_indexed", 0),
        "decisions_indexed": stats.get("decisions_indexed", 0),
        "errors": stats.get("errors", 0),
    }


@router.get("/{project_id}/embeddings/status")
async def get_embedding_status(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check the current embedding index status for a project."""
    from brain_service import embedding_count, has_embeddings

    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    sync_session = SessionLocal()
    try:
        return {
            "has_embeddings": has_embeddings(sync_session, project_id),
            "embedding_count": embedding_count(sync_session, project_id),
        }
    finally:
        sync_session.close()

