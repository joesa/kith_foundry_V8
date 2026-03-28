from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["deploy"])


class GitConnectIn(BaseModel):
    repo_url: str


class CommitIn(BaseModel):
    message: str


@router.post("/{project_id}/deploy/git-connect")
async def git_connect(
    project_id: str,
    body: GitConnectIn,
    user=Depends(get_current_user),
):
    return {"connected": True, "repo_url": body.repo_url, "project_id": project_id}


@router.post("/{project_id}/deploy/commit")
async def commit(
    project_id: str,
    body: CommitIn,
    user=Depends(get_current_user),
):
    return {"commit_sha": "stub-sha-placeholder", "message": body.message}


@router.post("/{project_id}/deploy/vercel")
async def deploy_vercel(
    project_id: str,
    user=Depends(get_current_user),
):
    return {"deployment_id": "stub-deploy-id", "url": f"https://{project_id[:8]}.vercel.app", "status": "deploying"}


@router.get("/{project_id}/deployments")
async def list_deployments(
    project_id: str,
    user=Depends(get_current_user),
):
    return {"deployments": []}
