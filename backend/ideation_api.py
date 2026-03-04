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
    GeneratedIdeaGlobal, ProjectStatus, IdeaSource,
)
from auth import get_current_user
from ideation_prompts import QUESTIONNAIRE_QUESTIONS, QUESTIONNAIRE_IDEA_PROMPT

litellm.drop_params = True
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


async def _llm_json(system: str, user_msg: str, user_id: str | None = None) -> dict:
    """Call LLM and parse JSON response."""
    try:
        mc = _resolve_ideation_model(user_id)
        call_kwargs = {
            "model": mc["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.9,
            "max_tokens": 4000,
        }
        if mc.get("api_key"):
            call_kwargs["api_key"] = mc["api_key"]
        if mc.get("api_base"):
            call_kwargs["api_base"] = mc["api_base"]
        resp = await litellm.acompletion(**call_kwargs)
        text = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


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

    # Try up to 3 times to get a unique idea
    for attempt in range(3):
        result = await _llm_json(system, f"Generate attempt {attempt + 1}. Be creative and specific. Avoid common ideas like 'AI writing assistant' or 'project management tool'.", user_id=user.id)

        # Hash the idea for dedup
        idea_hash = hashlib.sha256(
            json.dumps({"name": result.get("name", ""), "desc": result.get("description", "")[:100]}, sort_keys=True).encode()
        ).hexdigest()

        existing = db.query(GeneratedIdeaGlobal).filter(GeneratedIdeaGlobal.idea_hash == idea_hash).first()
        if not existing:
            # It's unique! Store in global table
            global_idea = GeneratedIdeaGlobal(
                id=str(uuid.uuid4()),
                idea_hash=idea_hash,
                summary=f"{result.get('name', '')}: {result.get('description', '')[:200]}",
            )
            db.add(global_idea)
            db.commit()
            return {"idea": result}

    # If all attempts collided (very unlikely), still return the last one
    return {"idea": result}


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

    # Dedup each idea
    for idea in result.get("ideas", []):
        idea_hash = hashlib.sha256(
            json.dumps({"name": idea.get("name", ""), "desc": idea.get("description", "")[:100]}, sort_keys=True).encode()
        ).hexdigest()
        existing = db.query(GeneratedIdeaGlobal).filter(GeneratedIdeaGlobal.idea_hash == idea_hash).first()
        if not existing:
            global_idea = GeneratedIdeaGlobal(
                id=str(uuid.uuid4()),
                idea_hash=idea_hash,
                summary=f"{idea.get('name', '')}: {idea.get('description', '')[:200]}",
            )
            db.add(global_idea)
    db.commit()

    return result


@router.get("/questionnaire/questions")
async def get_questionnaire_questions(user: User = Depends(get_current_user)):
    """Return the canonical 15-question questionnaire definition."""
    return {"questions": QUESTIONNAIRE_QUESTIONS}
