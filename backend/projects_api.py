"""
Projects API — CRUD endpoints for user projects.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models import get_db, Project, ProjectStatus, User
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
async def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.updated_at.desc()).all()
    return {"projects": [_project_to_dict(p) for p in projects]}


@router.post("")
async def create_project(body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        description=body.description,
        target_audience=body.target_audience,
        problem_statement=body.problem_statement,
        status=ProjectStatus.ideation,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


@router.get("/{project_id}")
async def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_dict(project)


@router.patch("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}
