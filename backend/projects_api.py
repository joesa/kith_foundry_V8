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

from models import get_async_db, Project, ProjectStatus, User
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
