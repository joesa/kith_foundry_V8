import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from models import get_async_db, CapabilityChoice, Project
from auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["capabilities"])


class CapabilityChoicesIn(BaseModel):
    wants_database: bool = False
    wants_auth: bool = False
    wants_ai: bool = False
    notes: Optional[str] = None


class CapabilityChoicesOut(BaseModel):
    id: str
    project_id: str
    wants_database: bool
    wants_auth: bool
    wants_ai: bool
    notes: Optional[str]
    created_at: str


@router.get("/{project_id}/capabilities")
async def get_capabilities(
    project_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(session):
        proj = session.query(Project).filter_by(id=project_id, user_id=user.id).first()
        if not proj:
            return None
        return session.query(CapabilityChoice).filter_by(project_id=project_id).first()

    result = await db.run_sync(_query)
    if result is None:
        raise HTTPException(404, "Project not found or no capabilities set")
    return {
        "id": result.id,
        "project_id": result.project_id,
        "wants_database": result.wants_database,
        "wants_auth": result.wants_auth,
        "wants_ai": result.wants_ai,
        "notes": result.notes,
        "created_at": str(result.created_at),
    }


@router.post("/{project_id}/capabilities")
async def set_capabilities(
    project_id: str,
    body: CapabilityChoicesIn,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _upsert(session):
        proj = session.query(Project).filter_by(id=project_id, user_id=user.id).first()
        if not proj:
            return None
        existing = session.query(CapabilityChoice).filter_by(project_id=project_id).first()
        if existing:
            existing.wants_database = body.wants_database
            existing.wants_auth = body.wants_auth
            existing.wants_ai = body.wants_ai
            existing.notes = body.notes
            existing.updated_at = datetime.utcnow()
            session.flush()
            return existing
        choice = CapabilityChoice(
            id=str(uuid.uuid4()),
            project_id=project_id,
            wants_database=body.wants_database,
            wants_auth=body.wants_auth,
            wants_ai=body.wants_ai,
            notes=body.notes,
        )
        session.add(choice)
        session.flush()
        return choice

    result = await db.run_sync(_upsert)
    if result is None:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return {
        "id": result.id,
        "project_id": result.project_id,
        "wants_database": result.wants_database,
        "wants_auth": result.wants_auth,
        "wants_ai": result.wants_ai,
        "notes": result.notes,
        "created_at": str(result.created_at),
    }
