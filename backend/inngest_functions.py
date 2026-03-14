"""
Inngest functions for background pipelines.

Events handled:
  C-Suite:
    csuite/run.requested             — data: {project_id, correction_notes?}
    csuite/refine.requested          — data: {project_id, correction_notes}
    csuite/improve.apply.requested   — data: {project_id, roles, enhanced_context}

  Design / Mockups:
    design/generate.requested        — data: {project_id}
    design/generate-all.requested    — data: {project_id, design_mode, direction?, reference_images?}
    design/generate-single.requested — data: {mockup_id, project_context, screen_desc, user_id?}
    design/revision.requested        — data: {mockup_id, project_context, screen_desc, user_id?}

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
import inngest
from inngest_client import client


# ── C-Suite ──────────────────────────────────────────────────────────────────

from csuite_agent import run_all_agents_background, run_selected_agents_background


@client.create_function(
    fn_id="csuite-run",
    trigger=inngest.TriggerEvent(event="csuite/run.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=25, key="event.data.user_id")],
)
async def csuite_run_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    correction_notes: str | None = ctx.event.data.get("correction_notes")
    print(f"🚀 Inngest csuite-run executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-run complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "csuite_update", "status": "complete"})
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="csuite-refine",
    trigger=inngest.TriggerEvent(event="csuite/refine.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=25, key="event.data.user_id")],
)
async def csuite_refine_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    correction_notes: str = ctx.event.data.get("correction_notes", "")
    print(f"🚀 Inngest csuite-refine executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-refine complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "csuite_update", "status": "complete"})
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


# ── Design / Mockups ─────────────────────────────────────────────────────────

from design_api import (
    _generate_all_mockups,
    _generate_all_mockups_ai_free,
    _generate_existing_mockups,
    _generate_mockup_component,
)


@client.create_function(
    fn_id="design-generate",
    trigger=inngest.TriggerEvent(event="design/generate.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def design_generate_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    print(f"🚀 Inngest design-generate executing for {project_id[:8]}")
    await _generate_all_mockups(project_id)
    print(f"✅ Inngest design-generate complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "design_update", "status": "complete"})
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="design-generate-all",
    trigger=inngest.TriggerEvent(event="design/generate-all.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=15, key="event.data.user_id")],
)
async def design_generate_all_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    design_mode: str = ctx.event.data.get("design_mode", "dna")
    direction: str | None = ctx.event.data.get("direction")
    reference_images: list[str] | None = ctx.event.data.get("reference_images")
    task: str = ctx.event.data.get("task", "generate_all")  # generate_all | generate_existing | ai_free
    print(f"🚀 Inngest design-generate-all executing for {project_id[:8]} mode={design_mode} task={task}")
    if task == "ai_free":
        await _generate_all_mockups_ai_free(project_id, direction, reference_images)
    elif task == "generate_existing":
        await _generate_existing_mockups(project_id, reference_images)
    else:
        await _generate_all_mockups(project_id)
    print(f"✅ Inngest design-generate-all complete for {project_id[:8]}")
    from redis_state import publish_project_update
    await publish_project_update(project_id, {"type": "design_update", "status": "complete"})
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="design-generate-single",
    trigger=inngest.TriggerEvent(event="design/generate-single.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def design_generate_single_fn(ctx: inngest.Context) -> dict:
    mockup_id: str = ctx.event.data["mockup_id"]
    project_context: str = ctx.event.data["project_context"]
    screen_desc: str = ctx.event.data["screen_desc"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest design-generate-single executing for mockup {mockup_id[:8]}")
    await _generate_mockup_component(mockup_id, project_context, screen_desc, user_id)
    print(f"✅ Inngest design-generate-single complete for mockup {mockup_id[:8]}")
    return {"status": "complete", "mockup_id": mockup_id}


@client.create_function(
    fn_id="design-revision",
    trigger=inngest.TriggerEvent(event="design/revision.requested"),
    retries=3,
    concurrency=[inngest.Concurrency(limit=20, key="event.data.user_id")],
)
async def design_revision_fn(ctx: inngest.Context) -> dict:
    mockup_id: str = ctx.event.data["mockup_id"]
    project_context: str = ctx.event.data["project_context"]
    screen_desc: str = ctx.event.data["screen_desc"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest design-revision executing for mockup {mockup_id[:8]}")
    await _generate_mockup_component(mockup_id, project_context, screen_desc, user_id)
    print(f"✅ Inngest design-revision complete for mockup {mockup_id[:8]}")
    return {"status": "complete", "mockup_id": mockup_id}


# ── Artifacts ────────────────────────────────────────────────────────────────

from artifacts_api import _generate_all_artifacts, _generate_single_artifact


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

from fly_service import FlySandboxWorker


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


# ── Export all functions for main.py registration ────────────────────────────

all_functions = [
    # C-Suite
    csuite_run_fn,
    csuite_refine_fn,
    csuite_improve_apply_fn,
    csuite_improve_fn,
    # Chat (WebSocket fire-and-forget)
    chat_message_fn,
    # Design
    design_generate_fn,
    design_generate_all_fn,
    design_generate_single_fn,
    design_revision_fn,
    # Artifacts
    artifacts_generate_fn,
    artifacts_generate_single_fn,
    # Sandbox
    sandbox_provision_fn,
    # Pool
    sandbox_pool_fill_fn,
]
