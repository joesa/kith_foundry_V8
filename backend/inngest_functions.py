"""
Inngest functions for background pipelines.

Events handled:
  C-Suite:
    csuite/run.requested             — data: {project_id, correction_notes?}
    csuite/refine.requested          — data: {project_id, correction_notes}
    csuite/improve.apply.requested   — data: {project_id, roles, enhanced_context}

  Design Engine:
    design-engine/generate.requested — data: {project_id, user_id?, design_mode?, design_style?}

  Artifacts:
    artifacts/generate.requested        — data: {project_id, user_id?}
    artifacts/generate-single.requested — data: {project_id, artifact_key, artifact_def, context, user_id?}
    artifacts/regenerate.requested      — data: {project_id, artifact_key, artifact_def, context, user_id?}

  Sandbox:
    sandbox/provision.requested      — data: {project_id, user_id?}

Design note:
  Each function `await`s the background task directly — this is safe on localhost
  since there is no HTTP timeout. For production (Inngest Cloud behind a public
  URL), consider splitting long pipelines into per-step functions.
"""
import asyncio
import json
import inngest
from inngest_client import client


# ── C-Suite ──────────────────────────────────────────────────────────────────

from csuite_agent import run_all_agents_background, run_selected_agents_background
from artifacts_api import _generate_all_artifacts, _generate_single_artifact


@client.create_function(
    fn_id="csuite-run",
    trigger=inngest.TriggerEvent(event="csuite/run.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=25, key="event.data.user_id")],
)
async def csuite_run_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    correction_notes: str | None = ctx.event.data.get("correction_notes")
    print(f"🚀 Inngest csuite-run executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-run complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "csuite_update", "status": "complete"})
    print(f"🔗 Auto-triggering artifact generation for {project_id[:8]}")
    await _generate_all_artifacts(project_id, user_id)
    await publish_project_update(project_id, {"type": "artifacts_update", "status": "complete"})
    # Auto-trigger build pipeline now that CSuite + artifacts are done
    print(f"\U0001f517 Auto-triggering build pipeline for {project_id[:8]}")
    await client.send(inngest.Event(
        name="forge.project.build.started",
        data={"project_id": project_id, "user_id": user_id or ""},
    ))
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="csuite-refine",
    trigger=inngest.TriggerEvent(event="csuite/refine.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=25, key="event.data.user_id")],
)
async def csuite_refine_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    correction_notes: str = ctx.event.data.get("correction_notes", "")
    print(f"🚀 Inngest csuite-refine executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-refine complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "csuite_update", "status": "complete"})
    print(f"🔗 Auto-triggering artifact generation for {project_id[:8]}")
    await _generate_all_artifacts(project_id, user_id)
    await publish_project_update(project_id, {"type": "artifacts_update", "status": "complete"})
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="csuite-improve-apply",
    trigger=inngest.TriggerEvent(event="csuite/improve.apply.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=25, key="event.data.user_id")],
)
async def csuite_improve_apply_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    roles: list[str] = ctx.event.data["roles"]
    enhanced_context: str = ctx.event.data.get("enhanced_context", "")
    print(f"🚀 Inngest csuite-improve-apply executing for {project_id[:8]}, roles={roles}")
    await run_selected_agents_background(project_id, roles, enhanced_context)
    print(f"✅ Inngest csuite-improve-apply complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "csuite_update", "status": "complete", "roles": roles})
    return {"status": "complete", "project_id": project_id, "roles": roles}


# ── Design Engine (GPT Engine pipeline) ──────────────────────────────────────

@client.create_function(
    fn_id="design-engine-generate",
    trigger=inngest.TriggerEvent(event="design/engine-generate.requested"),
    retries=2,
    concurrency=[inngest.Concurrency(limit=10, key="event.data.user_id")],
)
async def design_engine_generate_fn(ctx: inngest.Context) -> dict:
    """Run the GPT Design Engine pipeline and persist design system artifacts."""
    from design_engine import run_full_design_pipeline
    from models import SessionLocal, Project
    from model_resolver import resolve_model_for_task

    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    model_id: str = ctx.event.data.get("model_id", "anthropic/claude-sonnet-4-6")
    design_mode: str | None = ctx.event.data.get("design_mode")
    design_style: str | None = ctx.event.data.get("design_style")
    print(f"🚀 Inngest design-engine-generate for {project_id[:8]}")
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # User routing is authoritative when user context is available.
        if user_id:
            mc = resolve_model_for_task(user_id, "design", db=db)
            if mc.get("error"):
                raise ValueError(mc["error"])
            effective_model = mc["model"]
            llm_kwargs = {}
            if mc.get("api_key"):
                llm_kwargs["api_key"] = mc["api_key"]
            if mc.get("api_base"):
                llm_kwargs["api_base"] = mc["api_base"]
        else:
            effective_model = model_id
            llm_kwargs = {}

        result = await run_full_design_pipeline(
            project,
            db,
            effective_model,
            llm_kwargs,
            design_mode=design_mode,
            design_style=design_style,
        )
        if result.get("error"):
            raise RuntimeError(result["error"])

        print(f"✅ Inngest design-engine-generate complete for {project_id[:8]}")
        from redis_state import publish_project_update
        await publish_project_update(project_id, {
            "type": "design_engine_update",
            "status": "complete",
        })
        return {"status": "complete", "project_id": project_id}
    except Exception as e:
        print(f"❌ Inngest design-engine-generate failed for {project_id[:8]}: {e}")
        from redis_state import publish_project_update
        await publish_project_update(project_id, {
            "type": "design_engine_update",
            "status": "error",
            "message": str(e),
        })
        raise
    finally:
        db.close()


# ── Artifacts ────────────────────────────────────────────────────────────────


@client.create_function(
    fn_id="artifacts-generate",
    trigger=inngest.TriggerEvent(event="artifacts/generate.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def artifacts_generate_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest artifacts-generate executing for {project_id[:8]}")
    await _generate_all_artifacts(project_id, user_id)
    print(f"✅ Inngest artifacts-generate complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "artifacts_update", "status": "complete"})
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="artifacts-generate-single",
    trigger=inngest.TriggerEvent(event="artifacts/generate-single.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def artifacts_generate_single_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    artifact_key: str = ctx.event.data["artifact_key"]
    artifact_def: dict = ctx.event.data["artifact_def"]
    context: str = ctx.event.data["context"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest artifacts-generate-single executing for {project_id[:8]}/{artifact_key}")
    await _generate_single_artifact(project_id, artifact_key, artifact_def, context, user_id)
    print(f"✅ Inngest artifacts-generate-single complete for {project_id[:8]}/{artifact_key}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "artifacts_update", "status": "complete", "artifact_key": artifact_key})
    return {"status": "complete", "project_id": project_id, "artifact_key": artifact_key}


# ── Sandbox provisioning (background Fly machine creation) ───────────────────

from nf_service import NfSandboxWorker as FlySandboxWorker


@client.create_function(
    fn_id="sandbox-provision",
    trigger=inngest.TriggerEvent(event="sandbox/provision.requested"),
    retries=2,
    concurrency=[inngest.Concurrency(limit=10)],
)
async def sandbox_provision_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    from redis_state import (
        get_sandbox_meta_async,
        set_sandbox_meta_async,
        publish_sandbox_event,
    )

    # If already provisioned, re-broadcast the ready event and return
    existing = await get_sandbox_meta_async(project_id)
    if existing and existing.get("preview_url"):
        await publish_sandbox_event(project_id, {"status": "ready", **existing})
        return {"status": "already_exists", "project_id": project_id}

    await publish_sandbox_event(
        project_id, {"status": "progress", "message": "Allocating sandbox VM..."}
    )
    try:
        worker = FlySandboxWorker(project_id)
        await asyncio.to_thread(worker.create)
        meta = worker.to_metadata()
        await set_sandbox_meta_async(project_id, meta)
        await publish_sandbox_event(project_id, {"status": "ready", **meta})
        print(f"✅ Inngest sandbox-provision complete for {project_id[:8]}: {worker.preview_url}")
        return {"status": "created", "preview_url": worker.preview_url}
    except Exception as e:
        await publish_sandbox_event(project_id, {"status": "error", "error": str(e)})
        raise


# ── Sandbox pool fill (cron every 10 min) ────────────────────────────────────

@client.create_function(
    fn_id="sandbox-pool-fill",
    trigger=inngest.TriggerCron(cron="*/10 * * * *"),
    retries=0,
)
async def sandbox_pool_fill_fn(ctx: inngest.Context) -> dict:
    """Refill the pre-warm sandbox pool in a background thread (blocking I/O)."""
    import os
    # Only run in environments where Fly is configured
    if not os.getenv("FLY_API_TOKEN"):
        print("[sandbox_pool] FLY_API_TOKEN not set — skipping pool fill")
        return {"skipped": True}

    from sandbox_pool import fill_pool, pool_size
    before = pool_size()
    added = await asyncio.to_thread(fill_pool, 3)
    after = pool_size()
    print(f"[sandbox_pool] Pool fill complete: {before} → {after} (+{added} added)")
    return {"added": added, "pool_size": after}


# ── Chat message (WebSocket fire-and-forget LLM pipeline) ────────────────────

@client.create_function(
    fn_id="chat-message",
    trigger=inngest.TriggerEvent(event="chat/message.requested"),
    retries=0,  # streaming LLM — retrying would duplicate DB writes
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def chat_message_fn(ctx: inngest.Context) -> dict:
    job_id: str = ctx.event.data["job_id"]
    user_prompt: str = ctx.event.data["user_prompt"]
    project_id: str = ctx.event.data["project_id"]
    model_id: str = ctx.event.data.get("model_id", "default")
    images: list = ctx.event.data.get("images", [])
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest chat-message job={job_id[:8]} project={project_id[:8]}")

    from models import SessionLocal
    from agent import classify_intent, _resolve_llm_credentials, process_conversation
    from agent_pipeline import run_multi_agent_pipeline
    from redis_state import ws_job_channel
    from redis_client import get_async_redis

    channel = ws_job_channel(job_id)
    r = get_async_redis()
    db = SessionLocal()
    try:
        effective_model, llm_kwargs = await _resolve_llm_credentials(model_id, user_id)
        intent_class = await classify_intent(user_prompt, effective_model, llm_kwargs)

        if intent_class == "conversation":
            async for step in process_conversation(
                user_prompt, project_id, effective_model, llm_kwargs, db=db, images=images
            ):
                await r.publish(channel, json.dumps(step))
        else:
            async for step in run_multi_agent_pipeline(
                user_prompt, project_id, effective_model, llm_kwargs, db,
                images=images, user_id=user_id,
            ):
                await r.publish(channel, json.dumps(step))
    finally:
        db.close()

    await r.publish(channel, json.dumps({"status": "job_complete"}))
    print(f"✅ Inngest chat-message complete job={job_id[:8]}")
    return {"status": "complete", "job_id": job_id}


# ── C-Suite improve plan (async offload) ─────────────────────────────────────

@client.create_function(
    fn_id="csuite-improve",
    trigger=inngest.TriggerEvent(event="csuite/improve.requested"),
    retries=2,
    concurrency=[inngest.Concurrency(limit=10, key="event.data.user_id")],
)
async def csuite_improve_fn(ctx: inngest.Context) -> dict:
    job_id: str = ctx.event.data["job_id"]
    project_id: str = ctx.event.data["project_id"]
    roles: list[str] | None = ctx.event.data.get("roles")
    print(f"🚀 Inngest csuite-improve job={job_id[:8]} project={project_id[:8]}")

    from csuite_agent import generate_improvement_plan
    from redis_state import store_improve_plan, publish_project_update

    plan = await generate_improvement_plan(project_id, roles)
    await store_improve_plan(job_id, plan, ttl=300)
    await publish_project_update(project_id, {
        "type": "improve_plan_ready",
        "job_id": job_id,
        "has_error": "error" in plan,
    })
    print(f"✅ Inngest csuite-improve complete job={job_id[:8]}")
    return {"status": "complete", "job_id": job_id}


# ── Idea expiry (7-day soft-hold) ────────────────────────────────────────────

@client.create_function(
    fn_id="idea-expiry-check",
    trigger=inngest.TriggerEvent(event="forge.idea.saved"),
    retries=1,
)
async def idea_expiry_check_fn(ctx: inngest.Context) -> dict:
    idea_id: str = ctx.event.data["idea_id"]
    print(f"[idea-expiry] Scheduled expiry check for idea {idea_id[:8]}")

    await ctx.step.sleep("wait-7-days", 7 * 24 * 60 * 60)

    from models import SessionLocal, SavedIdea
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        idea = db.query(SavedIdea).filter(SavedIdea.id == idea_id).first()
        if not idea:
            return {"status": "not_found", "idea_id": idea_id}

        if idea.saved_expires_at and idea.saved_expires_at > datetime.utcnow():
            return {"status": "still_valid", "idea_id": idea_id}

        idea.uniqueness_degraded = True
        db.commit()
        print(f"[idea-expiry] Idea {idea_id[:8]} marked as uniqueness_degraded")
        return {"status": "degraded", "idea_id": idea_id}
    finally:
        db.close()


# ── Build pipeline (multi-step orchestration) ────────────────────────────────

@client.create_function(
    fn_id="build-pipeline",
    trigger=inngest.TriggerEvent(event="forge.project.build.started"),
    retries=1,
    concurrency=[inngest.Concurrency(limit=5, key="event.data.user_id")],
)
async def build_pipeline_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"[build-pipeline] Starting for {project_id[:8]}")

    from models import SessionLocal, Project, ProjectStatus
    from redis_state import publish_project_update

    async def _publish(stage: str, status: str, **extra):
        await publish_project_update(project_id, {
            "type": "build_stage",
            "stage": stage,
            "status": status,
            **extra,
        })

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"status": "not_found"}

        await _publish("prd", "running")
        project.status = ProjectStatus.prd_generating
        db.commit()
        await asyncio.sleep(2)
        project.status = ProjectStatus.prd_complete
        db.commit()
        await _publish("prd", "complete")

        await _publish("design", "running")
        project.status = ProjectStatus.design_generating
        db.commit()
        await asyncio.sleep(2)
        project.status = ProjectStatus.design_complete
        db.commit()
        await _publish("design", "complete")

        await _publish("capability_gate", "running")
        project.status = ProjectStatus.capability_gate
        db.commit()
        await _publish("capability_gate", "waiting")

        await _publish("secrets", "running")
        project.status = ProjectStatus.secrets_pending
        db.commit()
        await _publish("secrets", "waiting")

        await _publish("sandbox", "running")
        try:
            worker_mod = __import__("nf_service")
            worker = worker_mod.NfSandboxWorker(project_id)
            await asyncio.to_thread(worker.create)
            await _publish("sandbox", "complete")
        except Exception as e:
            await _publish("sandbox", "error", message=str(e))

        await _publish("code_gen", "running")
        await asyncio.sleep(2)
        await _publish("code_gen", "complete")

        await _publish("validation", "running")
        await asyncio.sleep(1)
        await _publish("validation", "complete")

        project.status = ProjectStatus.build_complete
        db.commit()
        await _publish("complete", "complete")

        print(f"[build-pipeline] Complete for {project_id[:8]}")
        return {"status": "complete", "project_id": project_id}
    finally:
        db.close()


# ── Secret rotation ──────────────────────────────────────────────────────────

@client.create_function(
    fn_id="secret-rotation",
    trigger=inngest.TriggerEvent(event="forge.secret.rotation.requested"),
    retries=2,
)
async def secret_rotation_fn(ctx: inngest.Context) -> dict:
    secret_id: str = ctx.event.data["secret_id"]
    project_id: str = ctx.event.data["project_id"]
    print(f"[secret-rotation] Rotating secret {secret_id[:8]} for project {project_id[:8]}")

    from models import SessionLocal, EncryptedUserSecret, SecretAccessAudit
    from datetime import datetime

    db = SessionLocal()
    try:
        secret = db.query(EncryptedUserSecret).filter(
            EncryptedUserSecret.id == secret_id,
            EncryptedUserSecret.project_id == project_id,
        ).first()
        if not secret:
            return {"status": "not_found", "secret_id": secret_id}

        if secret.revoked_at:
            return {"status": "already_revoked", "secret_id": secret_id}

        secret.revoked_at = datetime.utcnow()
        db.add(SecretAccessAudit(
            secret_id=secret_id,
            action="rotated",
            performed_by="system:inngest",
        ))
        db.commit()
        print(f"[secret-rotation] Secret {secret_id[:8]} revoked for rotation")

        from redis_state import publish_project_update
        await publish_project_update(project_id, {
            "type": "secret_rotated",
            "secret_id": secret_id,
        })

        return {"status": "rotated", "secret_id": secret_id}
    finally:
        db.close()


# ── Export all functions for main.py registration ────────────────────────────

all_functions = [
    # C-Suite
    csuite_run_fn,
    csuite_refine_fn,
    csuite_improve_apply_fn,
    csuite_improve_fn,
    # Chat (WebSocket fire-and-forget)
    chat_message_fn,
    # Design Engine
    design_engine_generate_fn,
    # Artifacts
    artifacts_generate_fn,
    artifacts_generate_single_fn,
    # Sandbox
    sandbox_provision_fn,
    # Pool
    sandbox_pool_fill_fn,
    # Forge overhaul
    idea_expiry_check_fn,
    build_pipeline_fn,
    secret_rotation_fn,
]
