"""
C-Suite API — Run parallel C-Suite agent analysis on a project.
"""
import uuid
import os
import inngest
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import (
    get_db, User, Project, CSuiteAnalysis, ProjectStatus,
    CSuiteRole, AgentStatus,
)
from auth import get_current_user
from csuite_agent import run_all_agents_background, run_selected_agents_background, generate_improvement_plan
from inngest_client import client as inngest_client, use_inngest
router = APIRouter(prefix="/api/v1/csuite", tags=["csuite"])


class RefineRequest(BaseModel):
    corrections: str


class ImproveRequest(BaseModel):
    roles: list[str] | None = None  # None = all roles that need improvement


class ApplyImprovementRequest(BaseModel):
    roles: list[str]
    enhanced_context: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/{project_id}/run")
async def run_csuite(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start C-Suite analysis for a project (runs 7 agents in parallel)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up any existing analyses for re-runs
    db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).delete()
    db.commit()

    # Create analysis records for each role
    for role in CSuiteRole:
        analysis = CSuiteAnalysis(
            id=str(uuid.uuid4()),
            project_id=project_id,
            agent_role=role,
            status=AgentStatus.pending,
        )
        db.add(analysis)

    project.status = ProjectStatus.csuite_pending
    db.commit()

    # Run agents — via Inngest when USE_INNGEST=1, else FastAPI BackgroundTasks
    if use_inngest():
        try:
            result = await inngest_client.send(
                inngest.Event(
                    name="csuite/run.requested",
                    data={"project_id": project_id},
                )
            )
            print(f"📨 Inngest event sent: csuite/run.requested for {project_id[:8]} → {result}")
        except Exception as e:
            import traceback
            print(f"⚠️  Inngest send FAILED ({type(e).__name__}: {e}) — falling back to BackgroundTasks")
            traceback.print_exc()
            background_tasks.add_task(run_all_agents_background, project_id)
    else:
        print(f"▶️  BackgroundTask: run_all_agents_background for {project_id[:8]}")
        background_tasks.add_task(run_all_agents_background, project_id)

    return {"status": "started", "project_name": project.name}


@router.get("/{project_id}/status")
async def csuite_status(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current status of all C-Suite agents for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    analyses = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).all()

    agents = []
    for a in analyses:
        result = a.analysis or {}
        agents.append({
            "role": a.agent_role.value,
            "status": a.status.value,
            "score": a.score,
            "error_message": a.error_message,
            "recommendation": result.get("recommendation"),
            "strengths": result.get("strengths", []),
            "risks": result.get("risks", []),
            "suggestions": result.get("suggestions", []),
            "verdict": result.get("verdict"),
        })

    # Compute overall
    completed = [a for a in agents if a["score"] is not None]
    overall_score = round(sum(a["score"] for a in completed) / len(completed)) if completed else None
    overall_verdict = None
    if overall_score is not None:
        if overall_score >= 70:
            overall_verdict = "go"
        elif overall_score >= 50:
            overall_verdict = "conditional"
        else:
            overall_verdict = "no_go"

    return {
        "project_name": project.name,
        "agents": agents,
        "overall_score": overall_score,
        "overall_verdict": overall_verdict,
    }


@router.get("/{project_id}/results")
async def csuite_results(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return completed analyses and aggregate score/verdict."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    analyses = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).all()

    completed = []
    for a in analyses:
        if a.status != AgentStatus.complete:
            continue
        result = a.analysis or {}
        completed.append({
            "role": a.agent_role.value,
            "status": a.status.value,
            "score": a.score,
            "recommendation": result.get("recommendation"),
            "strengths": result.get("strengths", []),
            "risks": result.get("risks", []),
            "suggestions": result.get("suggestions", []),
            "verdict": result.get("verdict"),
        })

    overall_score = round(sum(a["score"] for a in completed if a["score"] is not None) / len(completed)) if completed else None
    overall_verdict = None
    if overall_score is not None:
        if overall_score >= 70:
            overall_verdict = "go"
        elif overall_score >= 50:
            overall_verdict = "conditional"
        else:
            overall_verdict = "no_go"

    return {
        "project_name": project.name,
        "agents": completed,
        "overall_score": overall_score,
        "overall_verdict": overall_verdict,
    }


@router.post("/{project_id}/refine")
async def refine_csuite(
    project_id: str,
    body: RefineRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run C-Suite with user corrections/context."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).delete()
    db.commit()

    for role in CSuiteRole:
        analysis = CSuiteAnalysis(
            id=str(uuid.uuid4()),
            project_id=project_id,
            agent_role=role,
            status=AgentStatus.pending,
        )
        db.add(analysis)

    project.status = ProjectStatus.csuite_pending
    db.commit()

    if use_inngest():
        try:
            await inngest_client.send(
                inngest.Event(
                    name="csuite/refine.requested",
                    data={"project_id": project_id, "correction_notes": body.corrections},
                )
            )
            print(f"📨 Inngest event sent: csuite/refine.requested for {project_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(run_all_agents_background, project_id, body.corrections)
    else:
        background_tasks.add_task(run_all_agents_background, project_id, body.corrections)

    return {"status": "started", "project_name": project.name, "mode": "refine"}


@router.post("/{project_id}/improve")
async def improve_csuite(
    project_id: str,
    body: ImproveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI self-analyzes current scores and generates an improvement plan."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = await generate_improvement_plan(project_id, body.roles)
    if "error" in plan:
        raise HTTPException(status_code=400, detail=plan["error"])

    return plan


@router.post("/{project_id}/improve/apply")
async def apply_improvement(
    project_id: str,
    body: ApplyImprovementRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept AI improvements and re-run affected agents with enhanced context."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    role_enums = [CSuiteRole(r) for r in body.roles]

    # Reset only the affected analyses
    db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role.in_(role_enums),
    ).delete(synchronize_session=False)
    db.commit()

    for role_str in body.roles:
        analysis = CSuiteAnalysis(
            id=str(uuid.uuid4()),
            project_id=project_id,
            agent_role=CSuiteRole(role_str),
            status=AgentStatus.pending,
        )
        db.add(analysis)
    db.commit()

    if use_inngest():
        try:
            await inngest_client.send(
                inngest.Event(
                    name="csuite/improve.apply.requested",
                    data={
                        "project_id": project_id,
                        "roles": body.roles,
                        "enhanced_context": body.enhanced_context,
                    },
                )
            )
            print(f"📨 Inngest event sent: csuite/improve.apply.requested for {project_id[:8]}")
        except Exception as e:
            print(f"⚠️  Inngest send failed ({e}) — falling back to BackgroundTasks")
            background_tasks.add_task(
                run_selected_agents_background, project_id, body.roles, body.enhanced_context
            )
    else:
        background_tasks.add_task(
            run_selected_agents_background, project_id, body.roles, body.enhanced_context
        )

    return {"status": "started", "roles": body.roles, "mode": "improve"}
