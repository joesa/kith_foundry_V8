"""
C-Suite API — Run parallel C-Suite agent analysis on a project.
"""
import uuid
import os
import inngest
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from rate_limiter import limiter
from pydantic import BaseModel

from models import (
    get_db, User, Project, CSuiteAnalysis, ProjectStatus,
    CSuiteRole, AgentStatus,
)
from auth import get_current_user
from csuite_agent import run_all_agents_background, run_selected_agents_background, generate_improvement_plan, mark_cancelled_project, mark_cancelled_analysis
from inngest_client import client as inngest_client, use_inngest
import billing_api as billing
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
@limiter.limit("30/minute")
async def run_csuite(
    request: Request,
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start C-Suite analysis for a project (runs 7 agents in parallel)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Enforce monthly C-Suite run limit (raises 402 if over limit)
    billing.enforce_csuite_limit(db, user)

    # Guard: don't re-run if agents are already in-flight
    # (prevents the frontend race where all-pending status triggers a duplicate POST /run)
    active_count = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.status.in_([AgentStatus.pending, AgentStatus.running]),
    ).count()
    if active_count > 0:
        project_name = db.query(Project).filter(Project.id == project_id).first()
        raise HTTPException(
            status_code=409,
            detail={"code": "already_running", "project_name": project_name.name if project_name else ""},
        )

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

    # Record usage
    billing.record_csuite_run(db, user.id)

    # Run agents — via Inngest when USE_INNGEST=1, else FastAPI BackgroundTasks
    if use_inngest():
        try:
            result = await inngest_client.send(
                inngest.Event(
                    name="csuite/run.requested",
                    data={"project_id": project_id, "user_id": user.id},
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


@router.post("/{project_id}/stop")
async def stop_all_csuite(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Immediately stop all pending/running agents for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Signal in-flight coroutines not to write their results
    mark_cancelled_project(project_id)

    # Mark all non-complete agents as stopped in the DB
    db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.status.in_([AgentStatus.pending, AgentStatus.running]),
    ).update(
        {"status": AgentStatus.error, "error_message": "Stopped by user"},
        synchronize_session=False,
    )
    project.status = ProjectStatus.csuite_complete
    db.commit()
    return {"status": "stopped"}


@router.post("/{project_id}/stop/{role}")
async def stop_single_csuite(
    project_id: str,
    role: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stop a single agent by role name."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        role_enum = CSuiteRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")

    analysis = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.agent_role == role_enum,
        CSuiteAnalysis.status.in_([AgentStatus.pending, AgentStatus.running]),
    ).first()

    if analysis:
        mark_cancelled_analysis(analysis.id)
        analysis.status = AgentStatus.error
        analysis.error_message = "Stopped by user"
        db.commit()

    # If all agents are now done, mark project complete
    remaining = db.query(CSuiteAnalysis).filter(
        CSuiteAnalysis.project_id == project_id,
        CSuiteAnalysis.status.in_([AgentStatus.pending, AgentStatus.running]),
    ).count()
    if remaining == 0:
        project.status = ProjectStatus.csuite_complete
        db.commit()

    return {"status": "stopped", "role": role}


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
@limiter.limit("30/minute")
async def refine_csuite(
    request: Request,
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
                    data={"project_id": project_id, "correction_notes": body.corrections, "user_id": user.id},
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
@limiter.limit("30/minute")
async def improve_csuite(
    request: Request,
    project_id: str,
    body: ImproveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI self-analyzes current scores and generates an improvement plan."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if use_inngest():
        job_id = str(uuid.uuid4())
        await inngest_client.send(inngest.Event(
            name="csuite/improve.requested",
            data={
                "job_id": job_id,
                "project_id": project_id,
                "roles": body.roles,
                "user_id": user.id,
            }
        ))
        return {"status": "pending", "job_id": job_id}

    # Dev fallback — run inline when Inngest is not available
    plan = await generate_improvement_plan(project_id, body.roles)
    if "error" in plan:
        raise HTTPException(status_code=400, detail=plan["error"])

    return plan


@router.get("/{project_id}/improve-plan/{job_id}")
async def get_improve_plan_endpoint(
    project_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll for an improvement plan generated asynchronously via Inngest."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from redis_state import get_improve_plan
    plan = await get_improve_plan(job_id)
    if plan is None:
        return {"status": "pending"}
    if "error" in plan:
        raise HTTPException(status_code=400, detail=plan["error"])
    return {"status": "ready", **plan}


@router.post("/{project_id}/improve/apply")
@limiter.limit("30/minute")
async def apply_improvement(
    request: Request,
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
                        "user_id": user.id,
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
