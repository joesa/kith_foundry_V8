"""
Ideation API — Enhance prompts, generate unique ideas, run questionnaire flow.
"""
import uuid
import hashlib
import json
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Any

import litellm

from models import (
    get_db, User, Project, Idea, IdeaQuestionnaireResponse,
    GeneratedIdeaGlobal, SavedIdea, ProjectStatus, IdeaSource,
)
from auth import get_current_user
from ideation_prompts import QUESTIONNAIRE_QUESTIONS, QUESTIONNAIRE_IDEA_PROMPT

litellm.drop_params = True
if os.getenv("LITELLM_DEBUG") == "1":
    litellm._turn_on_debug()  # Logs full request/response; do not use in production (logs API keys)
router = APIRouter(prefix="/api/v1/ideation", tags=["ideation"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class EnhanceRequest(BaseModel):
    prompt: str

class AcceptIdeaRequest(BaseModel):
    name: str
    description: str
    target_audience: Optional[str] = None
    problem_statement: Optional[str] = None
    source: str = "user_prompt"
    original_prompt: Optional[str] = None
    idea_content: Optional[dict] = None

class QuestionnaireRequest(BaseModel):
    responses: dict

class SaveIdeaRequest(BaseModel):
    name: str
    content: dict
    score: Optional[int] = None
    source: str = "questionnaire"


# ── LLM helpers ──────────────────────────────────────────────────────────────

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"

def _get_model():
    return os.getenv("IDEATION_MODEL", DEFAULT_MODEL)


def _resolve_ideation_model(user_id: str | None = None) -> dict:
    """Resolve model config for ideation task."""
    if user_id:
        from model_resolver import resolve_model_for_task
        return resolve_model_for_task(user_id, "ideation")
    return {"model": _get_model(), "api_key": None, "api_base": None, "provider_name": "Default"}


def _compute_idea_hash(idea: dict[str, Any]) -> str:
    """Stable hash for deduping ideas across users and sessions."""
    payload = {
        "name": (idea.get("name") or "").strip().lower(),
        "description": (idea.get("description") or "").strip().lower()[:220],
        "target_market": (idea.get("target_market") or idea.get("target_audience") or "").strip().lower()[:140],
        "why_now": (idea.get("why_now") or "").strip().lower()[:140],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _repair_json(text: str) -> dict | None:
    """Attempt to repair truncated JSON from LLM output."""
    import re
    # Extract the outermost JSON object
    match = re.search(r'\{[\s\S]*', text)
    if not match:
        return None
    fragment = match.group()

    # Try parsing as-is first
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        pass

    # Truncated JSON repair: close open strings, arrays, objects
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False
    for ch in fragment:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1

    # If we're inside a string, close it
    repaired = fragment
    if in_string:
        repaired += '"'
    # Close any open arrays/objects
    repaired += ']' * max(0, depth_bracket)
    repaired += '}' * max(0, depth_brace)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        # Last resort: strip trailing garbage after last complete element and close
        # Find last valid comma or colon-value boundary
        for trim in range(min(200, len(repaired)), 0, -1):
            candidate = fragment[:len(fragment) - trim]
            # Remove trailing partial value
            candidate = re.sub(r',\s*$', '', candidate)
            candidate = re.sub(r',\s*"[^"]*$', '', candidate)
            closing = ']' * candidate.count('[') + '}' * candidate.count('{')
            closing = closing[::-1]  # Not quite right, need matched pairs
            # Simple approach: count opens minus closes
            ob = candidate.count('{') - candidate.count('}')
            ab = candidate.count('[') - candidate.count(']')
            candidate += ']' * max(0, ab) + '}' * max(0, ob)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


async def _llm_json(system: str, user_msg: str, user_id: str | None = None, retries: int = 2) -> dict:
    """Call LLM and parse JSON response, with retry on truncation."""
    import re
    last_error = None

    for attempt in range(retries + 1):
        try:
            mc = _resolve_ideation_model(user_id)
            if mc.get("error"):
                raise HTTPException(status_code=400, detail=mc["error"])
            call_kwargs = {
                "model": mc["model"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.9,
                "max_tokens": 8000,
            }
            if mc.get("api_key"):
                call_kwargs["api_key"] = mc["api_key"]
            elif "anthropic/" in str(mc.get("model", "")):
                # Explicitly pass env key for default anthropic model
                key = os.getenv("ANTHROPIC_API_KEY")
                if key:
                    call_kwargs["api_key"] = key
            if mc.get("api_base"):
                call_kwargs["api_base"] = mc["api_base"]
            resp = await litellm.acompletion(**call_kwargs)
            text = resp.choices[0].message.content.strip()

            # Check if response was truncated
            finish_reason = getattr(resp.choices[0], 'finish_reason', None)
            truncated = finish_reason == 'length'

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            # Try direct parse
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # Try extracting JSON object
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

            # Try repairing truncated JSON
            repaired = _repair_json(text)
            if repaired:
                print(f"[ideation] Repaired truncated JSON on attempt {attempt + 1}")
                return repaired

            if truncated and attempt < retries:
                print(f"[ideation] Response truncated, retrying ({attempt + 1}/{retries})...")
                continue

            last_error = "LLM returned invalid JSON"

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            if attempt < retries:
                print(f"[ideation] JSON error, retrying ({attempt + 1}/{retries})...")
                continue
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            err_msg = str(e)
            print(f"[ideation] LLM error: {err_msg}")
            traceback.print_exc()
            # Include model info to help debug
            try:
                mc = _resolve_ideation_model(user_id)
                print(f"[ideation] Model config: model={mc.get('model')}, provider={mc.get('provider_name')}, has_api_key={bool(mc.get('api_key'))}")
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"LLM error: {err_msg}")

    raise HTTPException(status_code=500, detail=last_error or "LLM returned invalid JSON")


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/enhance")
async def enhance_prompt(body: EnhanceRequest, user: User = Depends(get_current_user)):
    """Take user's raw prompt and return 3 enhanced variations."""
    system = """You are a world-class startup ideation expert. The user will describe a product idea.
Your job is to create 3 DISTINCT, ENHANCED variations of their idea — each should be a viable standalone product.

Respond with ONLY valid JSON (no markdown):
{
    "enhancements": [
        {
            "name": "Short catchy product name",
            "description": "2-3 sentence enhanced description",
            "differentiators": ["unique point 1", "unique point 2", "unique point 3"],
            "target_market": "specific target market"
        }
    ]
}"""
    result = await _llm_json(system, f"My idea: {body.prompt}", user_id=user.id)
    return result


@router.post("/accept")
async def accept_idea(body: AcceptIdeaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Accept an idea (enhanced or original) and create a Project + Idea record."""
    idea_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    # Determine IdeaSource enum
    try:
        source_enum = IdeaSource(body.source)
    except ValueError:
        source_enum = IdeaSource.user_prompt

    # Create Idea record
    idea_content = body.idea_content or {
        "name": body.name,
        "description": body.description,
        "target_audience": body.target_audience,
        "problem_statement": body.problem_statement,
        "original_prompt": body.original_prompt,
    }

    idea = Idea(
        id=idea_id,
        user_id=user.id,
        name=body.name,
        content=idea_content,
        source=source_enum,
        is_used=True,
    )
    db.add(idea)

    # Create Project record
    project = Project(
        id=project_id,
        user_id=user.id,
        name=body.name,
        description=body.description,
        target_audience=body.target_audience,
        problem_statement=body.problem_statement,
        status=ProjectStatus.csuite_pending,
        idea_id=idea_id,
    )
    db.add(project)

    # Claim the idea globally — no other user can build the same idea
    idea_hash = hashlib.sha256(
        json.dumps({"name": body.name, "desc": (body.description or "")[:100]}, sort_keys=True).encode()
    ).hexdigest()
    global_idea = db.query(GeneratedIdeaGlobal).filter(GeneratedIdeaGlobal.idea_hash == idea_hash).first()
    if global_idea:
        global_idea.claimed_by = user.id
        global_idea.claimed_at = datetime.utcnow()
    else:
        db.add(GeneratedIdeaGlobal(
            id=str(uuid.uuid4()),
            idea_hash=idea_hash,
            summary=f"{body.name}: {(body.description or '')[:200]}",
            claimed_by=user.id,
            claimed_at=datetime.utcnow(),
        ))

    # If this was a saved idea, mark it as claimed
    saved = db.query(SavedIdea).filter(
        SavedIdea.user_id == user.id,
        SavedIdea.idea_hash == idea_hash,
    ).first()
    if saved:
        saved.is_claimed = True

    db.commit()

    return {"project_id": project_id, "idea_id": idea_id}


@router.post("/generate-unique")
async def generate_unique_idea(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a globally unique idea that has never been shown to anyone."""
    system = """You are a visionary startup idea generator. Generate ONE completely unique, novel startup idea.
This idea must be:
- Highly specific (not generic like "AI for X")
- Immediately actionable as a SaaS product
- Targeting a real, underserved market need
- Feasible to build as an MVP in 2-4 weeks

Respond with ONLY valid JSON:
{
    "name": "Product Name",
    "description": "2-3 sentence description",
    "target_market": "who uses this",
    "revenue_potential": "$X/mo estimate",
    "why_now": "why this is timely",
    "score": 75
}"""

    # Build anti-repeat context from recent global ideas and user history.
    recent_global = db.query(GeneratedIdeaGlobal).order_by(GeneratedIdeaGlobal.created_at.desc()).limit(120).all()
    recent_summaries = [g.summary for g in recent_global if g.summary]
    recent_names = [s.split(":", 1)[0].strip() for s in recent_summaries[:60]]

    user_saved = (
        db.query(SavedIdea)
        .filter(SavedIdea.user_id == user.id)
        .order_by(SavedIdea.created_at.desc())
        .limit(40)
        .all()
    )
    user_projects = (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
        .limit(40)
        .all()
    )
    user_used_names = [s.name for s in user_saved if s.name] + [p.name for p in user_projects if p.name]

    avoid_names = [n for n in (recent_names + user_used_names) if n][:80]
    avoid_block = "\n".join(f"- {n}" for n in avoid_names)
    seen_hashes_this_request: set[str] = set()
    last_result: dict[str, Any] | None = None

    # Try multiple times to guarantee novelty.
    for attempt in range(8):
        nonce = str(uuid.uuid4())[:10]
        user_msg = (
            f"Generate attempt {attempt + 1} (nonce={nonce}). "
            "Be creative and specific. Avoid common ideas like 'AI writing assistant' or 'project management tool'.\n\n"
            "Do NOT generate anything similar to these previously seen ideas:\n"
            f"{avoid_block}"
        )
        result = await _llm_json(system, user_msg, user_id=user.id)
        last_result = result

        idea_hash = _compute_idea_hash(result)
        if idea_hash in seen_hashes_this_request:
            continue
        seen_hashes_this_request.add(idea_hash)

        # Any existing hash means this idea has been shown before; reject it.
        existing = db.query(GeneratedIdeaGlobal).filter(GeneratedIdeaGlobal.idea_hash == idea_hash).first()
        if existing:
            continue

        # It's globally new. Store in global table so it can never be shown again.
        global_idea = GeneratedIdeaGlobal(
            id=str(uuid.uuid4()),
            idea_hash=idea_hash,
            summary=f"{result.get('name', '')}: {result.get('description', '')[:200]}",
        )
        db.add(global_idea)
        db.commit()
        return {"idea": result}

    # If all attempts collided (very unlikely), still return the last one
    if last_result:
        return {"idea": last_result}
    raise HTTPException(status_code=500, detail="Could not generate an idea")


@router.post("/questionnaire")
async def submit_questionnaire(body: QuestionnaireRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Process questionnaire answers and generate 3 personalized ideas."""
    # Save questionnaire responses
    qr = IdeaQuestionnaireResponse(
        id=str(uuid.uuid4()),
        user_id=user.id,
        responses=body.responses,
    )
    db.add(qr)
    db.commit()

    # Build context from answers
    answers_text = json.dumps(body.responses, indent=2)

    result = await _llm_json(QUESTIONNAIRE_IDEA_PROMPT, f"Here are my questionnaire answers:\n{answers_text}", user_id=user.id)

    # Dedup each idea + filter out claimed ideas
    filtered_ideas = []
    for idea in result.get("ideas", []):
        idea_hash = hashlib.sha256(
            json.dumps({"name": idea.get("name", ""), "desc": idea.get("description", "")[:100]}, sort_keys=True).encode()
        ).hexdigest()
        existing = db.query(GeneratedIdeaGlobal).filter(GeneratedIdeaGlobal.idea_hash == idea_hash).first()
        if existing and existing.claimed_by and existing.claimed_by != user.id:
            # Another user is already building this — skip it
            continue
        if not existing:
            global_idea = GeneratedIdeaGlobal(
                id=str(uuid.uuid4()),
                idea_hash=idea_hash,
                summary=f"{idea.get('name', '')}: {idea.get('description', '')[:200]}",
            )
            db.add(global_idea)
        idea["_idea_hash"] = idea_hash
        filtered_ideas.append(idea)
    db.commit()

    result["ideas"] = filtered_ideas
    return result


@router.get("/questionnaire/questions")
async def get_questionnaire_questions(user: User = Depends(get_current_user)):
    """Return the canonical 15-question questionnaire definition."""
    return {"questions": QUESTIONNAIRE_QUESTIONS}


# ── Saved Ideas ──────────────────────────────────────────────────────────────

@router.post("/save")
async def save_idea(body: SaveIdeaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save an idea for later without claiming exclusivity."""
    # Compute idea hash
    idea_hash = hashlib.sha256(
        json.dumps({"name": body.name, "desc": body.content.get("description", "")[:100]}, sort_keys=True).encode()
    ).hexdigest()

    # Check if user already saved this exact idea
    existing = db.query(SavedIdea).filter(
        SavedIdea.user_id == user.id,
        SavedIdea.idea_hash == idea_hash,
    ).first()
    if existing:
        return {"saved_idea_id": existing.id, "message": "Already saved"}

    try:
        source_enum = IdeaSource(body.source)
    except ValueError:
        source_enum = IdeaSource.questionnaire

    saved = SavedIdea(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        content=body.content,
        score=body.score,
        source=source_enum,
        idea_hash=idea_hash,
        is_claimed=False,
    )
    db.add(saved)
    db.commit()

    return {"saved_idea_id": saved.id, "message": "Idea saved for later"}


@router.get("/saved")
async def list_saved_ideas(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all saved ideas for the current user, with claim status."""
    saved = (
        db.query(SavedIdea)
        .filter(SavedIdea.user_id == user.id)
        .order_by(SavedIdea.created_at.desc())
        .all()
    )
    result = []
    for s in saved:
        # Check if another user has claimed this idea (started building)
        claimed_by_other = False
        if s.idea_hash:
            global_idea = db.query(GeneratedIdeaGlobal).filter(
                GeneratedIdeaGlobal.idea_hash == s.idea_hash,
                GeneratedIdeaGlobal.claimed_by != None,
                GeneratedIdeaGlobal.claimed_by != user.id,
            ).first()
            claimed_by_other = global_idea is not None

        result.append({
            "id": s.id,
            "name": s.name,
            "content": s.content,
            "score": s.score,
            "source": s.source.value if s.source else None,
            "is_claimed": s.is_claimed,
            "claimed_by_other": claimed_by_other,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return {"saved_ideas": result}


@router.delete("/saved/{saved_id}")
async def unsave_idea(saved_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a saved idea (only if not yet claimed/building)."""
    saved = db.query(SavedIdea).filter(
        SavedIdea.id == saved_id,
        SavedIdea.user_id == user.id,
    ).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved idea not found")
    if saved.is_claimed:
        raise HTTPException(status_code=400, detail="Cannot unsave — you've already started building this idea")
    db.delete(saved)
    db.commit()
    return {"message": "Idea removed from saved"}
