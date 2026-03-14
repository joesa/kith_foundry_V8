"""
Projects API — CRUD endpoints for user projects.

Uses AsyncSession (asyncpg) for non-blocking PostgreSQL access.
The ``run_sync`` bridge lets existing ORM query code run inside the
async session without rewriting every query to use SQLAlchemy 2.0 syntax.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models import get_async_db, SessionLocal, Project, ProjectStatus, User
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

def _project_to_dict(p: Project) -> dict:
    # Compute overall score from csuite analyses
    analyses = p.csuite_analyses or []
    completed = [a for a in analyses if a.score is not None]
    overall_score = round(sum(a.score for a in completed) / len(completed)) if completed else None

    # Determine verdict: go if avg >= 70, conditional 50-69, no_go < 50
    overall_verdict = None
    if overall_score is not None:
        if overall_score >= 70:
            overall_verdict = "go"
        elif overall_score >= 50:
            overall_verdict = "conditional"
        else:
            overall_verdict = "no_go"

    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "target_audience": p.target_audience,
        "problem_statement": p.problem_statement,
        "status": p.status.value if p.status else "ideation",
        "overall_score": overall_score,
        "overall_verdict": overall_verdict,
        "idea_source": p.idea.source.value if p.idea else None,
        "preview_url": p.preview_url,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(s: Session):
        projects = s.query(Project).filter(Project.user_id == user.id).order_by(
            Project.updated_at.desc()
        ).all()
        return [_project_to_dict(p) for p in projects]

    return {"projects": await db.run_sync(_query)}


@router.post("")
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _create(s: Session):
        project = Project(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=body.name,
            description=body.description,
            target_audience=body.target_audience,
            problem_statement=body.problem_statement,
            status=ProjectStatus.ideation,
        )
        s.add(project)
        s.commit()
        s.refresh(project)
        return _project_to_dict(project)

    return await db.run_sync(_create)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(s: Session):
        p = s.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
        if not p:
            return None
        return _project_to_dict(p)

    result = await db.run_sync(_query)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _update(s: Session):
        project = s.query(Project).filter(
            Project.id == project_id, Project.user_id == user.id
        ).first()
        if not project:
            return None
        if body.name is not None:
            project.name = body.name
        if body.description is not None:
            project.description = body.description
        if body.target_audience is not None:
            project.target_audience = body.target_audience
        if body.problem_statement is not None:
            project.problem_statement = body.problem_statement
        if body.status is not None:
            try:
                project.status = ProjectStatus(body.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
        project.updated_at = datetime.utcnow()
        s.commit()
        s.refresh(project)
        return _project_to_dict(project)

    result = await db.run_sync(_update)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Wipe Nhost Storage files first (runs in thread via asyncio.to_thread inside)
    try:
        import asyncio
        from storage_service import delete_all_project_files_sync
        await asyncio.to_thread(delete_all_project_files_sync, project_id)
    except Exception as e:
        print(f"[delete_project] Storage wipe warning (continuing): {e}")

    def _delete(s: Session):
        project = s.query(Project).filter(
            Project.id == project_id, Project.user_id == user.id
        ).first()
        if not project:
            return False
        s.delete(project)
        s.commit()
        return True

    deleted = await db.run_sync(_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


# ── Context Compression / Reindex ─────────────────────────────────────────────

@router.post("/{project_id}/reindex")
async def reindex_project_embeddings(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Re-embed all project source files and brain entities for semantic search.

    This populates the project_embeddings table (pgvector) used by the
    context compression system to select relevant code for LLM prompts.
    """
    import asyncio as _aio
    from agent import read_all_project_files
    from embedding_service import reindex_project as _reindex
    from brain_service import delete_project_embeddings

    # Verify ownership
    def _check(s: Session):
        return s.query(Project).filter(
            Project.id == project_id, Project.user_id == user.id
        ).first()

    project = await db.run_sync(_check)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Read all source files using a sync session for compatibility
    sync_session = SessionLocal()
    try:
        all_files = await read_all_project_files(sync_session, project_id)

        if not all_files:
            return {"status": "empty", "message": "No source files to index"}

        # Clear stale embeddings and re-index
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
    db: AsyncSession = Depends(get_async_db),
):
    """Check the current embedding index status for a project."""
    from brain_service import embedding_count, has_embeddings

    def _check(s: Session):
        proj = s.query(Project).filter(
            Project.id == project_id, Project.user_id == user.id
        ).first()
        if not proj:
            return None
        return {
            "has_embeddings": has_embeddings(s, project_id),
            "embedding_count": embedding_count(s, project_id),
        }

    result = await db.run_sync(_check)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result
