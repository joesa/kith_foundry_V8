from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from models import get_async_db, Project
from auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["sandbox"])


@router.get("/{project_id}/sandbox/status")
async def sandbox_status(
    project_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(session):
        return session.query(Project).filter_by(id=project_id, user_id=user.id).first()

    proj = await db.run_sync(_query)
    if not proj:
        raise HTTPException(404, "Project not found")
    return {
        "id": proj.fly_sandbox_id,
        "project_id": proj.id,
        "status": "running" if proj.fly_sandbox_id else "stopped",
        "fly_app_id": proj.fly_sandbox_id,
        "preview_url": proj.preview_url,
    }


@router.get("/{project_id}/sandbox/logs")
async def sandbox_logs(
    project_id: str,
    tail: Optional[int] = Query(100, ge=1, le=1000),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(session):
        return session.query(Project).filter_by(id=project_id, user_id=user.id).first()

    proj = await db.run_sync(_query)
    if not proj:
        raise HTTPException(404, "Project not found")
    if not proj.fly_sandbox_id:
        return {"logs": [], "message": "No sandbox provisioned"}
    return {"logs": [], "message": "Log streaming will be wired to Fly.io logs API"}
