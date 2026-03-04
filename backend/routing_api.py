"""
Model Routing API — CRUD for per-task AI model assignments.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional

from models import get_db, ModelRouting, ProviderKey, User
from auth import get_current_user

router = APIRouter(prefix="/api/v1/model-routing", tags=["model-routing"])

VALID_TASK_TYPES = {"code_gen", "csuite", "design", "ideation"}

TASK_TYPE_LABELS = {
    "code_gen": "Code Generation",
    "csuite": "C-Suite Analysis",
    "design": "Design Mockups",
    "ideation": "Ideation",
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class RoutingUpsert(BaseModel):
    provider_id: Optional[int] = None
    model_id: Optional[str] = None


class RoutingOut(BaseModel):
    task_type: str
    task_label: str
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    model_id: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_routings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all model routing configs for the current user, including unconfigured task types."""
    routings = (
        db.query(ModelRouting)
        .filter(ModelRouting.user_id == user.id)
        .all()
    )
    routing_map = {r.task_type: r for r in routings}

    result = []
    for task_type in VALID_TASK_TYPES:
        r = routing_map.get(task_type)
        provider_name = None
        if r and r.provider_id:
            pk = db.query(ProviderKey).filter(ProviderKey.id == r.provider_id).first()
            if pk:
                provider_name = pk.name

        result.append({
            "task_type": task_type,
            "task_label": TASK_TYPE_LABELS.get(task_type, task_type),
            "provider_id": r.provider_id if r else None,
            "provider_name": provider_name,
            "model_id": r.model_id if r else None,
        })

    return {"routings": result}


@router.put("/{task_type}")
async def upsert_routing(
    task_type: str,
    body: RoutingUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update the provider + model for a specific task type."""
    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}. Valid: {', '.join(sorted(VALID_TASK_TYPES))}")

    # Validate provider_id belongs to the user (or is a legacy global key with no user_id)
    if body.provider_id:
        pk = db.query(ProviderKey).filter(
            ProviderKey.id == body.provider_id,
            or_(ProviderKey.user_id == user.id, ProviderKey.user_id == None),
        ).first()
        if not pk:
            raise HTTPException(status_code=400, detail="Provider not found or does not belong to this user")

    existing = (
        db.query(ModelRouting)
        .filter(ModelRouting.user_id == user.id, ModelRouting.task_type == task_type)
        .first()
    )

    if existing:
        existing.provider_id = body.provider_id
        existing.model_id = body.model_id
        existing.updated_at = datetime.utcnow()
    else:
        existing = ModelRouting(
            user_id=user.id,
            task_type=task_type,
            provider_id=body.provider_id,
            model_id=body.model_id,
        )
        db.add(existing)

    db.commit()

    provider_name = None
    if body.provider_id:
        pk = db.query(ProviderKey).filter(ProviderKey.id == body.provider_id).first()
        if pk:
            provider_name = pk.name

    return {
        "task_type": task_type,
        "task_label": TASK_TYPE_LABELS.get(task_type, task_type),
        "provider_id": existing.provider_id,
        "provider_name": provider_name,
        "model_id": existing.model_id,
    }


@router.delete("/{task_type}")
async def delete_routing(
    task_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear the task routing (revert to default provider)."""
    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")

    existing = (
        db.query(ModelRouting)
        .filter(ModelRouting.user_id == user.id, ModelRouting.task_type == task_type)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    return {"deleted": True, "task_type": task_type}
