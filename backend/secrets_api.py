import uuid
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from cryptography.fernet import Fernet

from models import get_async_db, EncryptedUserSecret, SecretAccessAudit, Project
from auth import get_current_user

ENCRYPTION_KEY = os.getenv("SECRET_ENCRYPTION_KEY", Fernet.generate_key().decode())
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

router = APIRouter(tags=["secrets"])


class SecretSubmitIn(BaseModel):
    provider: str
    label: str
    value: str


class SecretOut(BaseModel):
    id: str
    provider: str
    label: str
    created_at: str
    last_accessed_at: Optional[str] = None


@router.get("/api/v1/projects/{project_id}/secrets")
async def list_secrets(
    project_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _query(session):
        proj = session.query(Project).filter_by(id=project_id, user_id=user.id).first()
        if not proj:
            return None
        secrets = (
            session.query(EncryptedUserSecret)
            .filter_by(project_id=project_id, user_id=user.id)
            .filter(EncryptedUserSecret.revoked_at.is_(None))
            .order_by(EncryptedUserSecret.created_at.desc())
            .all()
        )
        return secrets

    results = await db.run_sync(_query)
    if results is None:
        raise HTTPException(404, "Project not found")
    return {
        "secrets": [
            {
                "id": s.id,
                "provider": s.provider,
                "label": s.label,
                "created_at": str(s.created_at),
                "last_accessed_at": str(s.last_accessed_at) if s.last_accessed_at else None,
            }
            for s in results
        ]
    }


@router.post("/api/v1/projects/{project_id}/secrets")
async def submit_secret(
    project_id: str,
    body: SecretSubmitIn,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    encrypted = _fernet.encrypt(body.value.encode()).decode()

    def _create(session):
        proj = session.query(Project).filter_by(id=project_id, user_id=user.id).first()
        if not proj:
            return None
        secret = EncryptedUserSecret(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=user.id,
            provider=body.provider,
            label=body.label,
            encrypted_value=encrypted,
        )
        session.add(secret)
        audit = SecretAccessAudit(
            id=str(uuid.uuid4()),
            secret_id=secret.id,
            accessed_by=user.id,
            action="created",
        )
        session.add(audit)
        session.flush()
        return secret

    result = await db.run_sync(_create)
    if result is None:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return {"id": result.id, "provider": result.provider, "label": result.label}


@router.post("/api/v1/secrets/{secret_id}/revoke")
async def revoke_secret(
    secret_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    def _revoke(session):
        secret = (
            session.query(EncryptedUserSecret)
            .filter_by(id=secret_id, user_id=user.id)
            .first()
        )
        if not secret:
            return False
        secret.revoked_at = datetime.utcnow()
        audit = SecretAccessAudit(
            id=str(uuid.uuid4()),
            secret_id=secret.id,
            accessed_by=user.id,
            action="revoked",
        )
        session.add(audit)
        session.flush()
        return True

    found = await db.run_sync(_revoke)
    if not found:
        raise HTTPException(404, "Secret not found")
    await db.commit()
    return {"revoked": True}
