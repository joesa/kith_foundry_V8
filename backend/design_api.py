"""
Design Studio API — GPT Design Engine endpoints.
"""
import json
import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

import litellm

from models import get_db, User, Project, Artifact, ArtifactType, AgentStatus
from auth import get_current_user
from brain_service import (
    list_project_design_mode_history,
    lock_project_design_mode,
    unlock_project_design_mode,
    update_project_design_mode,
)
from design_mode_service import ModeClassificationResult, design_mode_service

litellm.drop_params = True
router = APIRouter(prefix="/api/v1/projects", tags=["design"])


DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"

def _get_model():
    return os.getenv("DESIGN_MODEL", DEFAULT_MODEL)


def _resolve_design_model(user_id: str | None = None, db=None) -> dict:
    """Resolve model config for design task."""
    if user_id:
        from model_resolver import resolve_model_for_task
        model_config = resolve_model_for_task(user_id, "design", db=db)
    else:
        model_config = {
            "model": _get_model(),
            "api_key": None,
            "api_base": None,
            "provider_name": "Default",
        }

    if model_config.get("error"):
        raise HTTPException(status_code=400, detail=model_config["error"])

    if not model_config.get("model"):
        raise HTTPException(
            status_code=500,
            detail="Design model resolution failed: no model configured.",
        )

    llm_kwargs: dict = {}
    if model_config.get("api_key"):
        llm_kwargs["api_key"] = model_config["api_key"]
    if model_config.get("api_base"):
        llm_kwargs["api_base"] = model_config["api_base"]
    model_config["llm_kwargs"] = llm_kwargs
    return model_config


def _build_litellm_kwargs(model_config: dict, messages: list, **extra) -> dict:
    """Build litellm.acompletion kwargs from model config."""
    if model_config.get("error"):
        raise HTTPException(status_code=400, detail=model_config["error"])
    kwargs = {"model": model_config["model"], "messages": messages, **extra}
    if model_config.get("api_key"):
        kwargs["api_key"] = model_config["api_key"]
    if model_config.get("api_base"):
        kwargs["api_base"] = model_config["api_base"]
    return kwargs


def _should_retry_design_with_env_fallback(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_markers = (
        "rate limit",
        "ratelimit",
        "quota exceeded",
        '"code": 429',
        "authentication",
        "invalid api key",
        "permission denied",
        "service unavailable",
        "overloaded",
        "resource exhausted",
        "timed out",
        "timeout",
        "provider not provided",
        "not found. passed model=",
        "connection error",
        "connection refused",
    )
    return any(marker in text for marker in retry_markers)


# Limit concurrent LLM calls per-worker for design generation
_DESIGN_SEMAPHORE = asyncio.Semaphore(10)


async def _design_acompletion(
    model_config: dict,
    messages: list,
    *,
    user_id: str | None = None,
    reference_images: list[str] | None = None,
    **extra,
):
    """Call LiteLLM for design tasks with automatic server-env fallback on provider failure."""
    if reference_images:
        # If reference images are provided, find the last user message and convert it to a multimodal message
        for msg in reversed(messages):
            if msg.get("role") == "user":
                original_content = msg.get("content", "")
                new_content = []
                for img_b64 in reference_images:
                    new_content.append({ # type: ignore
                        "type": "image_url",
                        "image_url": {"url": img_b64}
                    })

                if isinstance(original_content, str):
                    new_content.append({"type": "text", "text": original_content})
                else:
                    new_content.extend(original_content)

                new_content.append({
                    "type": "text",
                    "text": "\n\nCRITICAL MANDATE: The images above are for structural and stylistic inspiration ONLY. You MUST NOT copy the text, brand names, or specific content from these images. You MUST design the screen requested in the text prompt using your own layout, adapted entirely to the specified product. If your output looks exactly like the reference image, it is a FAILURE. Create a unique, distinct variation."
                })
                msg["content"] = new_content
                break

    primary_kwargs = _build_litellm_kwargs(model_config, messages, **extra)
    try:
        async with _DESIGN_SEMAPHORE:
            return await litellm.acompletion(**primary_kwargs)
    except Exception as exc:
        if not user_id or not _should_retry_design_with_env_fallback(exc):
            raise

        from model_resolver import _env_fallback

        fallback_model = _env_fallback()
        if fallback_model.get("error"):
            raise

        same_provider = (
            fallback_model.get("model") == model_config.get("model")
            and fallback_model.get("api_key") == model_config.get("api_key")
            and fallback_model.get("api_base") == model_config.get("api_base")
        )
        if same_provider:
            raise

        provider_name = model_config.get("provider_name") or model_config.get("model") or "configured provider"
        fallback_name = fallback_model.get("provider_name") or fallback_model.get("model") or "server fallback"
        print(
            f"⚠️ Design model fallback: {provider_name} failed ({exc}). "
            f"Retrying with {fallback_name}."
        )
        fallback_kwargs = _build_litellm_kwargs(fallback_model, messages, **extra)
        async with _DESIGN_SEMAPHORE:
            return await litellm.acompletion(**fallback_kwargs)



# ══════════════════════════════════════════════════════════════════════════════
# GPT Design Engine endpoints (Phase 1)
# ══════════════════════════════════════════════════════════════════════════════
class DesignEngineRequest(BaseModel):
    design_mode: Optional[str] = None
    design_style: Optional[str] = None
    lock_selection: bool = False


class ClassifyDesignModeRequest(BaseModel):
    projectId: Optional[str] = None
    prompt: str
    appName: Optional[str] = None
    appType: Optional[str] = None
    description: Optional[str] = None
    features: Optional[list[str]] = None
    targetAudience: Optional[str] = None
    preferredStyle: Optional[str] = None
    forceReclassify: bool = False


class DesignModeLockRequest(BaseModel):
    productMode: str
    styleMode: str
    confidence: Optional[float] = 1.0


def _get_owned_project(project_id: str, user_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _validate_design_mode_inputs(product_mode: str | None, style_mode: str | None) -> None:
    if product_mode and not design_mode_service.validate_product_mode(product_mode):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid design_mode '{product_mode}'. See GET /{{project_id}}/design/mode-options for all available modes.",
        )
    if style_mode and not design_mode_service.validate_style_mode(style_mode):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid design_style '{style_mode}'. See GET /{{project_id}}/design/mode-options for all available styles.",
        )


def _mode_options_response(project: Project | None = None) -> dict:
    options = design_mode_service.get_mode_options()
    payload = {
        **options,
        "exampleCombinations": [
            {"mode": "Analytics Dashboard", "style": "Stripe SaaS"},
            {"mode": "AI Chat Interface", "style": "OpenAI Minimal"},
            {"mode": "Photography Portfolio", "style": "Apple Editorial"},
            {"mode": "Ecommerce Store", "style": "Luxury Brand"},
            {"mode": "SaaS Dashboard", "style": "Linear Dark"},
            {"mode": "Creative Agency", "style": "Swiss Modern"},
            {"mode": "Habit Tracker", "style": "Notion Productivity"},
        ],
    }
    if project:
        payload["currentDesignMode"] = {
            "productMode": project.product_mode,
            "styleMode": project.style_mode,
            "confidence": float(project.mode_confidence) if project.mode_confidence is not None else None,
            "lockedByUser": bool(project.design_mode_locked),
        }
    return payload


@router.get("/{project_id}/design/mode-options")
async def get_design_mode_options(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the pack-backed product modes and style modes available to a project."""
    project = _get_owned_project(project_id, user.id, db)
    return _mode_options_response(project)


@router.post("/{project_id}/design/classify-mode")
async def classify_project_design_mode(
    project_id: str,
    body: ClassifyDesignModeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Classify the best product mode and style mode for the project."""
    project = _get_owned_project(project_id, user.id, db)
    if body.projectId and body.projectId != project_id:
        raise HTTPException(status_code=422, detail="Body projectId does not match route project_id")

    if body.preferredStyle and not design_mode_service.validate_style_mode(body.preferredStyle):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid preferredStyle '{body.preferredStyle}'. See GET /{{project_id}}/design/mode-options.",
        )

    if project.design_mode_locked and project.product_mode and project.style_mode and not body.forceReclassify:
        classification = ModeClassificationResult(
            productMode=project.product_mode,
            styleMode=project.style_mode,
            confidence=float(project.mode_confidence) if project.mode_confidence is not None else 1.0,
            alternatives=[],
            reasoning={},
        )
        locked_by_user = True
    else:
        # Enrich classification with PRD + Design System Foundation context
        prd_text = _fetch_artifact_text(db, project_id, ArtifactType.product_requirements)
        dsf_text = _fetch_artifact_text(db, project_id, ArtifactType.design_system)

        mc = _resolve_design_model(user.id, db)
        classification = await design_mode_service.classify_design_mode(
            model_id=mc["model"],
            llm_kwargs=mc.get("llm_kwargs", {}),
            prompt=body.prompt,
            app_name=body.appName or project.name,
            app_type=body.appType,
            description=body.description or project.description or project.problem_statement,
            features=body.features,
            target_audience=body.targetAudience or project.target_audience,
            preferred_style=body.preferredStyle,
            prd_context=prd_text,
            design_foundation_context=dsf_text,
        )
        locked_by_user = bool(project.design_mode_locked)
        if not project.design_mode_locked:
            update_project_design_mode(
                db,
                project_id,
                product_mode=classification.productMode,
                style_mode=classification.styleMode,
                confidence=classification.confidence,
                source="auto",
                locked_by_user=False,
                record_history=True,
            )

    mode_context = design_mode_service.get_mode_context(
        classification.productMode,
        classification.styleMode,
        confidence=classification.confidence,
        locked_by_user=locked_by_user,
    )
    return {
        "classification": classification.model_dump(),
        "blueprint": mode_context.get("blueprint"),
        "recommendedPatterns": mode_context.get("recommendedPatterns", []),
    }


def _fetch_artifact_text(db: Session, project_id: str, artifact_type: ArtifactType, max_chars: int = 6000) -> str | None:
    """Fetch a completed artifact's content as a text string, truncated for LLM context."""
    artifact = (
        db.query(Artifact)
        .filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == artifact_type,
            Artifact.status == AgentStatus.complete,
        )
        .first()
    )
    if not artifact or not artifact.content:
        return None
    raw = json.dumps(artifact.content, indent=2) if isinstance(artifact.content, (dict, list)) else str(artifact.content)
    if len(raw) > max_chars:
        raw = raw[:max_chars] + "\n... (truncated)"
    return raw


@router.post("/{project_id}/design/auto-select-mode")
async def auto_select_design_mode(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Auto-select design mode using PRD + Design System Foundation context.

    Called automatically when the Design Studio is opened if no mode is
    currently selected/locked.  Pulls the PRD and Design System Foundation
    artifacts from the database and feeds them as enriched context to the
    mode classifier for a more accurate selection.
    """
    project = _get_owned_project(project_id, user.id, db)

    # If mode is already locked, return existing selection immediately
    if project.design_mode_locked and project.product_mode and project.style_mode:
        classification = ModeClassificationResult(
            productMode=project.product_mode,
            styleMode=project.style_mode,
            confidence=float(project.mode_confidence) if project.mode_confidence is not None else 1.0,
            alternatives=[],
            reasoning={},
        )
        mode_context = design_mode_service.get_mode_context(
            classification.productMode,
            classification.styleMode,
            confidence=classification.confidence,
            locked_by_user=True,
        )
        return {
            "classification": classification.model_dump(),
            "blueprint": mode_context.get("blueprint"),
            "recommendedPatterns": mode_context.get("recommendedPatterns", []),
            "source": "locked",
        }

    # Fetch PRD and Design System Foundation for enriched classification
    prd_text = _fetch_artifact_text(db, project_id, ArtifactType.product_requirements)
    dsf_text = _fetch_artifact_text(db, project_id, ArtifactType.design_system)

    # Extract feature list from project context
    features: list[str] | None = None
    if project.problem_statement:
        features = [project.problem_statement]
    if isinstance(project.design_preferences, dict):
        raw_feat = project.design_preferences.get("features")
        if isinstance(raw_feat, list):
            features = (features or []) + [str(f) for f in raw_feat if f]

    mc = _resolve_design_model(user.id, db)
    classification = await design_mode_service.classify_design_mode(
        model_id=mc["model"],
        llm_kwargs=mc.get("llm_kwargs", {}),
        prompt="Auto-classify the best design mode and style based on project context, PRD, and Design System Foundation.",
        app_name=project.name,
        description=project.description or project.problem_statement,
        features=features,
        target_audience=project.target_audience,
        prd_context=prd_text,
        design_foundation_context=dsf_text,
    )

    # Persist the auto-detected mode (but don't lock — user can change later)
    update_project_design_mode(
        db,
        project_id,
        product_mode=classification.productMode,
        style_mode=classification.styleMode,
        confidence=classification.confidence,
        source="auto",
        locked_by_user=False,
        record_history=True,
    )

    mode_context = design_mode_service.get_mode_context(
        classification.productMode,
        classification.styleMode,
        confidence=classification.confidence,
        locked_by_user=False,
    )
    return {
        "classification": classification.model_dump(),
        "blueprint": mode_context.get("blueprint"),
        "recommendedPatterns": mode_context.get("recommendedPatterns", []),
        "source": "auto",
        "contextUsed": {
            "prd": prd_text is not None,
            "designSystemFoundation": dsf_text is not None,
        },
    }


@router.post("/{project_id}/design/lock-mode")
async def lock_design_mode_selection(
    project_id: str,
    body: DesignModeLockRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist and lock a user-selected product mode and style mode."""
    _get_owned_project(project_id, user.id, db)
    _validate_design_mode_inputs(body.productMode, body.styleMode)
    project = lock_project_design_mode(
        db,
        project_id,
        product_mode=body.productMode,
        style_mode=body.styleMode,
        confidence=body.confidence,
    )
    return {
        "status": "locked",
        "designMode": {
            "productMode": project.product_mode,
            "styleMode": project.style_mode,
            "confidence": float(project.mode_confidence) if project.mode_confidence is not None else None,
            "lockedByUser": True,
        },
    }


@router.post("/{project_id}/design/unlock-mode")
async def unlock_design_mode_selection(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlock project design mode so future generation may auto-classify again."""
    _get_owned_project(project_id, user.id, db)
    project = unlock_project_design_mode(db, project_id)
    return {
        "status": "unlocked",
        "designMode": {
            "productMode": project.product_mode,
            "styleMode": project.style_mode,
            "confidence": float(project.mode_confidence) if project.mode_confidence is not None else None,
            "lockedByUser": False,
        },
    }


@router.get("/{project_id}/design/mode-history")
async def get_design_mode_history(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the recent history of auto and user design mode selections."""
    _get_owned_project(project_id, user.id, db)
    return {"history": list_project_design_mode_history(db, project_id)}


@router.post("/{project_id}/design/engine/brief")
async def generate_engine_brief(
    project_id: str,
    body: DesignEngineRequest = DesignEngineRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a design intelligence brief using the GPT Design Engine.

    Optional body fields:
    - ``design_mode``: structural blueprint (e.g. "Analytics Dashboard", "AI Chat Interface").
      See GET /{project_id}/design/engine/modes for the full list.
    - ``design_style``: visual language (e.g. "Stripe SaaS", "Apple Editorial", "Neo-Brutalism").

    When combined, Mode drives layout/structure and Style drives visual aesthetics.
    """
    from design_engine import generate_design_brief

    _validate_design_mode_inputs(body.design_mode, body.design_style)
    project = _get_owned_project(project_id, user.id, db)

    mc = _resolve_design_model(user.id, db)
    resolved_mode = body.design_mode or project.product_mode
    resolved_style = body.design_style or project.style_mode
    mode_context = None
    if resolved_mode and resolved_style:
        mode_context = design_mode_service.get_mode_context(
            resolved_mode,
            resolved_style,
            confidence=float(project.mode_confidence) if project.mode_confidence is not None else None,
            locked_by_user=bool(project.design_mode_locked),
        )
    brief = await generate_design_brief(
        project, db, mc["model"], mc.get("llm_kwargs", {}),
        design_mode=resolved_mode, design_style=resolved_style, mode_context=mode_context,
    )
    if not brief:
        raise HTTPException(status_code=500, detail="Design brief generation failed")

    return {
        "status": "complete",
        "brief": brief,
        "design_mode": resolved_mode,
        "design_style": resolved_style,
    }


@router.post("/{project_id}/design/engine/generate")
async def generate_engine_design_system(
    project_id: str,
    body: DesignEngineRequest = DesignEngineRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the full GPT Design Engine pipeline (brief → design system).

    Optional body fields:
    - ``design_mode``: structural blueprint — determines layout framework, navigation
      pattern, page hierarchy, and component types. 200+ modes available.
    - ``design_style``: visual language — determines color palette, typography
      personality, spacing density, and UI aesthetic. 35+ styles available.

    See GET /{project_id}/design/engine/modes for all valid values.
    Omit both to let the AI auto-infer the best mode + style from project context.
    """
    from design_engine import run_full_design_pipeline

    _validate_design_mode_inputs(body.design_mode, body.design_style)
    project = _get_owned_project(project_id, user.id, db)

    mc = _resolve_design_model(user.id, db)
    result = await run_full_design_pipeline(
        project, db, mc["model"], mc.get("llm_kwargs", {}),
        design_mode=body.design_mode, design_style=body.design_style,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    if body.lock_selection and result.get("design_mode") and result.get("design_style"):
        lock_project_design_mode(
            db,
            project_id,
            product_mode=result["design_mode"],
            style_mode=result["design_style"],
            confidence=result.get("classification", {}).get("confidence"),
        )

    return {
        "status": "complete",
        "design_system": result.get("design_system"),
        "brief": result.get("brief"),
        "builder_prompt": result.get("builder_prompt", ""),
        "design_mode": result.get("design_mode"),
        "design_style": result.get("design_style"),
        "classification": result.get("classification"),
        "mode_context": result.get("mode_context"),
    }


@router.get("/{project_id}/design/engine/modes")
async def list_design_modes(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all available design modes and styles for the GPT Design Engine.

    Modes control structure (layout, pages, navigation).
    Styles control visual language (colors, typography, spacing).
    Combine them: e.g. mode='Analytics Dashboard' + style='Stripe SaaS'.
    """
    project = _get_owned_project(project_id, user.id, db)
    return _mode_options_response(project)


@router.get("/{project_id}/design/engine/system")
async def get_engine_design_system(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a previously generated GPT Design Engine system."""
    from design_engine import get_design_system_from_artifacts

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ds = get_design_system_from_artifacts(db, project_id)
    if not ds:
        raise HTTPException(status_code=404, detail="No design system found. Run the engine first.")

    return {"status": "found", "design_system": ds}
