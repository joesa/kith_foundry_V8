"""
Inngest functions for background pipelines.

Events handled:
  C-Suite:
    csuite/run.requested             — data: {project_id, correction_notes?}
    csuite/refine.requested          — data: {project_id, correction_notes}
    csuite/improve.apply.requested   — data: {project_id, roles, enhanced_context}

  Design / Mockups:
    design/generate.requested        — data: {project_id}
    design/generate-all.requested    — data: {project_id, design_mode, direction?}
    design/generate-single.requested — data: {mockup_id, project_context, screen_desc, user_id?}
    design/revision.requested        — data: {mockup_id, project_context, screen_desc, user_id?}

  Artifacts:
    artifacts/generate.requested        — data: {project_id, user_id?}
    artifacts/generate-single.requested — data: {project_id, artifact_key, artifact_def, context, user_id?}
    artifacts/regenerate.requested      — data: {project_id, artifact_key, artifact_def, context, user_id?}

Design note:
  Each function `await`s the background task directly — this is safe on localhost
  since there is no HTTP timeout. For production (Inngest Cloud behind a public
  URL), consider splitting long pipelines into per-step functions.
"""
import inngest
from inngest_client import client


# ── C-Suite ──────────────────────────────────────────────────────────────────

from csuite_agent import run_all_agents_background, run_selected_agents_background


@client.create_function(
    fn_id="csuite-run",
    trigger=inngest.TriggerEvent(event="csuite/run.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
)
async def csuite_run_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    correction_notes: str | None = ctx.event.data.get("correction_notes")
    print(f"🚀 Inngest csuite-run executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-run complete for {project_id[:8]}")
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="csuite-refine",
    trigger=inngest.TriggerEvent(event="csuite/refine.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
)
async def csuite_refine_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    correction_notes: str = ctx.event.data.get("correction_notes", "")
    print(f"🚀 Inngest csuite-refine executing for {project_id[:8]}")
    await run_all_agents_background(project_id, correction_notes)
    print(f"✅ Inngest csuite-refine complete for {project_id[:8]}")
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="csuite-improve-apply",
    trigger=inngest.TriggerEvent(event="csuite/improve.apply.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
)
async def csuite_improve_apply_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    roles: list[str] = ctx.event.data["roles"]
    enhanced_context: str = ctx.event.data.get("enhanced_context", "")
    print(f"🚀 Inngest csuite-improve-apply executing for {project_id[:8]}, roles={roles}")
    await run_selected_agents_background(project_id, roles, enhanced_context)
    print(f"✅ Inngest csuite-improve-apply complete for {project_id[:8]}")
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
    retries=0,
    concurrency=[inngest.Concurrency(limit=3)],
)
async def design_generate_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    print(f"🚀 Inngest design-generate executing for {project_id[:8]}")
    await _generate_all_mockups(project_id)
    print(f"✅ Inngest design-generate complete for {project_id[:8]}")
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="design-generate-all",
    trigger=inngest.TriggerEvent(event="design/generate-all.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=3)],
)
async def design_generate_all_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    design_mode: str = ctx.event.data.get("design_mode", "dna")
    direction: str | None = ctx.event.data.get("direction")
    task: str = ctx.event.data.get("task", "generate_all")  # generate_all | generate_existing | ai_free
    print(f"🚀 Inngest design-generate-all executing for {project_id[:8]} mode={design_mode} task={task}")
    if task == "ai_free":
        await _generate_all_mockups_ai_free(project_id, direction)
    elif task == "generate_existing":
        await _generate_existing_mockups(project_id)
    else:
        await _generate_all_mockups(project_id)
    print(f"✅ Inngest design-generate-all complete for {project_id[:8]}")
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="design-generate-single",
    trigger=inngest.TriggerEvent(event="design/generate-single.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
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
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
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
    retries=0,
    concurrency=[inngest.Concurrency(limit=3)],
)
async def artifacts_generate_fn(ctx: inngest.Context) -> dict:
    project_id: str = ctx.event.data["project_id"]
    user_id: str | None = ctx.event.data.get("user_id")
    print(f"🚀 Inngest artifacts-generate executing for {project_id[:8]}")
    await _generate_all_artifacts(project_id, user_id)
    print(f"✅ Inngest artifacts-generate complete for {project_id[:8]}")
    return {"status": "complete", "project_id": project_id}


@client.create_function(
    fn_id="artifacts-generate-single",
    trigger=inngest.TriggerEvent(event="artifacts/generate-single.requested"),
    retries=0,
    concurrency=[inngest.Concurrency(limit=5)],
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
    return {"status": "complete", "project_id": project_id, "artifact_key": artifact_key}


# ── Export all functions for main.py registration ────────────────────────────

all_functions = [
    # C-Suite
    csuite_run_fn,
    csuite_refine_fn,
    csuite_improve_apply_fn,
    # Design
    design_generate_fn,
    design_generate_all_fn,
    design_generate_single_fn,
    design_revision_fn,
    # Artifacts
    artifacts_generate_fn,
    artifacts_generate_single_fn,
]
