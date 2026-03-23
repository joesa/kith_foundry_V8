"""
C-Suite agent orchestration and prompts.
"""
import json
import os
import asyncio
import time
from datetime import datetime
import re

import litellm
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, DisconnectionError, DBAPIError

from models import Project, CSuiteAnalysis, ProjectStatus, CSuiteRole, AgentStatus

litellm.drop_params = True


def _normalize_analysis_result(result: dict, fallback_text: str = "") -> dict:
    """Normalize/guard LLM payload so DB/UI always get a valid shape."""
    score_raw = result.get("score", 50)
    try:
        score = int(float(score_raw))
    except (TypeError, ValueError):
        score = 50
    score = min(100, max(0, score))

    verdict_raw = str(result.get("verdict", "")).strip().lower()
    if verdict_raw not in {"go", "conditional", "no_go"}:
        if score >= 70:
            verdict_raw = "go"
        elif score >= 50:
            verdict_raw = "conditional"
        else:
            verdict_raw = "no_go"

    recommendation = str(result.get("recommendation") or "").strip()
    if not recommendation:
        recommendation = "Model output was partially malformed; generated a safe fallback summary."

    deep_analysis = str(result.get("deep_analysis") or "").strip()
    if not deep_analysis:
        deep_analysis = (fallback_text or recommendation)[:4000]

    def _as_list(value):
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "score": score,
        "verdict": verdict_raw,
        "recommendation": recommendation,
        "deep_analysis": deep_analysis,
        "strengths": _as_list(result.get("strengths")),
        "risks": _as_list(result.get("risks")),
        "suggestions": _as_list(result.get("suggestions")),
        "key_metrics": _as_list(result.get("key_metrics")),
        "timeline": str(result.get("timeline") or "").strip(),
        "priority_actions": _as_list(result.get("priority_actions")),
        "competitive_note": str(result.get("competitive_note") or "").strip(),
    }


def _extract_score_from_text(raw_text: str) -> int:
    """Best-effort score extraction when model JSON is malformed."""
    match = re.search(r'"?score"?\s*[:=]\s*(\d{1,3})', raw_text, flags=re.IGNORECASE)
    if match:
        try:
            return min(100, max(0, int(match.group(1))))
        except ValueError:
            pass
    return 50


def _build_fallback_result(raw_text: str) -> dict:
    """Last-resort payload so a role does not fail solely due to parser issues."""
    score = _extract_score_from_text(raw_text)
    verdict = "go" if score >= 70 else ("conditional" if score >= 50 else "no_go")
    summary = raw_text.strip() or "No parseable analysis content returned by model."
    return {
        "score": score,
        "verdict": verdict,
        "recommendation": "Recovered partial response after JSON parse failure. Review deep_analysis for raw model output.",
        "deep_analysis": summary[:4000],
        "strengths": [],
        "risks": ["Structured JSON parse failed; analysis may be incomplete."],
        "suggestions": ["Retry this role to obtain a fully structured response."],
        "key_metrics": [],
        "timeline": "",
        "priority_actions": [],
        "competitive_note": "",
    }


def _write_analysis_result_with_retry(
    analysis_id: str,
    project_id: str,
    result: dict,
    max_attempts: int = 3,
) -> None:
    """Persist completed role result using fresh sessions to survive stale/disconnected connections."""
    from models import SessionLocal

    last_error = None
    for attempt in range(1, max_attempts + 1):
        db = SessionLocal()
        try:
            analysis = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.id == analysis_id).first()
            if not analysis:
                return

            if analysis_id in _CANCELLED_ANALYSES or project_id in _CANCELLED_PROJECTS:
                return

            analysis.analysis = result
            analysis.score = min(100, max(0, int(result.get("score", 50))))
            analysis.status = AgentStatus.complete
            analysis.error_message = None
            analysis.completed_at = datetime.utcnow()
            db.commit()
            return
        except (OperationalError, DisconnectionError, DBAPIError) as e:
            last_error = e
            db.rollback()
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)
            else:
                raise
        finally:
            db.close()

    if last_error:
        raise last_error


def _mark_analysis_error_with_retry(
    analysis_id: str,
    error_message: str,
    max_attempts: int = 3,
) -> None:
    """Persist error status with retries on transient DB disconnects."""
    from models import SessionLocal

    last_error = None
    for attempt in range(1, max_attempts + 1):
        db = SessionLocal()
        try:
            analysis = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.id == analysis_id).first()
            if not analysis or analysis.status == AgentStatus.complete:
                return

            analysis.status = AgentStatus.error
            analysis.error_message = error_message
            analysis.completed_at = datetime.utcnow()
            db.commit()
            return
        except (OperationalError, DisconnectionError, DBAPIError) as e:
            last_error = e
            db.rollback()
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)
            else:
                raise
        finally:
            db.close()

    if last_error:
        raise last_error


def _repair_json(raw: str) -> dict | None:
    """
    Attempt to repair truncated JSON from an LLM response.
    Common issue: max_tokens cuts off mid-string, leaving unterminated strings/arrays.
    Strategy: close open strings, arrays, objects and re-parse.
    """
    s = raw.rstrip()
    # Close any open string literal
    # Count unescaped quotes — if odd, close the string
    quotes = len(re.findall(r'(?<!\\)"', s))
    if quotes % 2 == 1:
        s += '"'
    # Now iteratively close open brackets/braces
    for _ in range(20):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            stripped = s.rstrip().rstrip(',')
            # Check what needs closing
            open_b = stripped.count('[') - stripped.count(']')
            open_o = stripped.count('{') - stripped.count('}')
            if open_b > 0:
                stripped += ']'
            elif open_o > 0:
                stripped += '}'
            else:
                break
            s = stripped
    # Final attempt
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None

CSUITE_PROMPTS = {
    CSuiteRole.ceo: """You are the CEO of a seasoned venture-backed company evaluating this startup idea as if you were deciding whether to found it or invest. This is a DEEP, HONEST, CRITICAL analysis — not cheerleading.

Cover ALL of the following with depth and specificity:
1. Strategic Vision & Market Timing — is this the right idea at the right time? What macro/micro trends support or threaten it?
2. Founder-Market Fit — what expertise and unfair advantages does this opportunity demand?
3. Scalability Ceiling — what is the realistic scale ceiling (local niche vs. global platform)? What breaks at scale?
4. Competitive Moat — what are the realistic defensibility mechanisms (network effects, data, switching costs, brand)?  Who are the serious threats and why would users choose this over them?
5. Exit Potential — realistic acquirers, IPO viability, strategic value?
6. Team & Execution Risk — what are the most likely execution failure modes?
7. Overall Verdict — a hard, honest recommendation with the 3 things that MUST be true for this to succeed.""",

    CSuiteRole.cto: """You are a senior CTO with experience scaling systems from 0 to millions of users. Evaluate this idea with deep technical rigour — not surface-level "it's feasible".

Cover ALL of the following:
1. Technical Feasibility — can this actually be built? What are the genuinely hard technical problems (don't skip this)?
2. MVP Architecture — specific, opinionated tech stack recommendation with justification. What databases, frameworks, infra, and third-party APIs are appropriate?
3. Time-to-MVP — realistic estimate broken down by phase (weeks, not vague ranges). What are the critical-path items?
4. Scalability Risks — what breaks first at 1k, 10k, 100k users? What requires re-architecture?
5. Security & Compliance — specific data protection, auth, and regulatory considerations (GDPR, HIPAA, PCI etc. as relevant)?
6. Technical Debt Traps — what shortcuts in the MVP will cause the most pain later?
7. Build vs. Buy — which components should be custom-built vs. third-party services, and why?
8. Biggest Technical Unknown — the one technical bet that could kill the project if wrong.""",

    CSuiteRole.cfo: """You are a CFO with deep startup finance experience. Provide a rigorous financial analysis — use real numbers and realistic ranges, not vague optimism.

Cover ALL of the following:
1. Revenue Model Analysis — evaluate each revenue stream: how defensible is pricing, what is the realistic ARPU/ACV range, and what are the model's weaknesses?
2. Unit Economics — estimate realistic CAC ranges by likely channel, LTV estimates, LTV:CAC ratio, and payback period. Be honest if these are unknown and what assumptions are needed.
3. Capital Requirements — how much runway is needed to reach key milestones (MVP, first $10k MRR, first $100k MRR)? What are the major cost drivers?
4. Burn Rate Scenarios — conservative, base, and optimistic monthly burn estimates for a 2-person founding team in Year 1.
5. Path to Profitability — what revenue level triggers profitability, and how long realistically to get there?
6. Fundraising Landscape — is this venture-fundable, bootstrappable, or requires grants/strategic partnerships? What milestones unlock each funding stage?
7. Financial Risks — top 3 financial risks that could render the business non-viable.
8. Key Financial KPIs — the 5 metrics the CFO would monitor weekly.""",

    CSuiteRole.cmo: """You are a CMO with experience taking both B2B and B2C products from zero to significant market presence. Provide deep go-to-market analysis — not a generic marketing checklist.

Cover ALL of the following:
1. ICP (Ideal Customer Profile) — be extremely specific: job title, company size, industry, pain intensity, existing solution they're using today, and what makes them switch?
2. TAM/SAM/SOM — concrete estimates with methodology (bottom-up or top-down) and sources of truth.
3. Channel Strategy — evaluate 4-5 specific acquisition channels with expected CAC ranges, conversion rates, and scalability ceiling for this specific product.
4. Messaging & Positioning — what is the single most compelling message? What headline would convert? What is the positioning relative to the top 3 alternatives?
5. Content & SEO Moat — is there an organic content angle? What search terms, communities, or media properties hold the target audience?
6. Viral & Referral Mechanics — does this product have inherent virality or referral potential? How would you engineer it?
7. Launch Strategy — a specific 90-day launch plan with channels, tactics, and success metrics.
8. Brand Risk — what brand/reputation risks exist and how to mitigate?""",

    CSuiteRole.cpo: """You are a CPO who has shipped multiple products from 0 to product-market fit. Provide a rigorous product strategy analysis — challenge assumptions and be specific.

Cover ALL of the following:
1. Problem Validation — how well-defined and validated is the core problem? What evidence exists that people have this pain urgently enough to pay?
2. Solution Clarity — is the proposed solution the best way to solve the problem, or are there simpler/more elegant approaches being overlooked?
3. MVP Scope — define the absolute minimum feature set for the first release. What should explicitly NOT be in v1? What scope creep traps exist?
4. User Journey — describe the critical path user journey step-by-step. Where will users drop off and why?
5. Differentiation — what makes this product genuinely different from the top 3 alternatives a user might choose? Is the differentiation durable?
6. Product Risks — top failure modes: wrong problem, wrong solution, wrong user, or wrong timing?
7. Instrumentation — what are the 5 core product metrics, and what specific events need to be tracked from day 1?
8. Roadmap Philosophy — what should v2 and v3 look like, and what customer signals should trigger each evolution?""",

    CSuiteRole.coo: """You are a COO with experience building operational frameworks for early-stage startups. Provide a detailed operational feasibility analysis.

Cover ALL of the following:
1. Operational Complexity Audit — map out the key operational processes required: customer onboarding, support, fulfillment, data ops, etc. Rate each by complexity.
2. Regulatory & Compliance Landscape — specific laws, regulations, licenses, or certifications required. Flag any hard blockers.
3. Supplier & Partner Dependencies — what third-party services, APIs, or partners are mission-critical? What is the risk if they fail or raise prices?
4. Staffing & Org Design — what roles are required for MVP vs. Series A? What is the sequencing for hiring?
5. Customer Success Operations — how will customer support be handled, what SLAs are appropriate, and what does churn look like operationally?
6. Scalability of Ops — what breaks operationally at 100 customers vs. 10,000? What processes need to be automated?
7. Geographic/International Considerations — are there operational barriers to expansion (localization, compliance, logistics)?
8. Key Operational Risks — the 3 operational scenarios most likely to derail the business.""",

    CSuiteRole.cdo: """You are the CDO (Chief Design Officer) — a senior design leader with experience building design systems and product experiences from zero. Provide a deep design strategy analysis.

Cover ALL of the following:
1. UX Complexity Assessment — how complex is the required user experience? What interaction patterns and information architecture challenges exist?
2. Critical Screen Inventory — list ALL screens/states needed for MVP with complexity rating (simple/medium/complex) for each. Include edge cases and empty states.
3. Design System Requirements — what component library, tokens, and patterns are needed? Should they build on existing (Tailwind, shadcn, MUI) or go custom?
4. Brand Identity Needs — what visual identity system is required? Logo, color, typography, iconography, illustration style?
5. Accessibility Requirements — specific WCAG compliance level needed, key accessibility considerations for this product's user base.
6. Mobile vs. Desktop Strategy — where does the primary experience live? What is the responsive/native strategy?
7. User Research Gaps — what assumptions about user behaviour need to be validated through design research before building?
8. Design-to-Engineering Handoff — what design tooling, documentation, and process is recommended to minimize rework?""",
}

RESPONSE_SCHEMA = """Respond with ONLY valid JSON matching this exact schema:
{
    "score": 75,
    "verdict": "go",
    "recommendation": "3-4 sentence executive summary of the overall assessment and key recommendation.",
    "deep_analysis": "4-6 paragraphs of detailed analysis from your specific executive perspective. This should be substantive, specific to this product, and cover the most critical dimensions of your evaluation. No bullet points here — full prose paragraphs.",
    "strengths": ["detailed strength with specific reasoning", "strength 2", "strength 3", "strength 4"],
    "risks": ["specific risk with explanation of impact", "risk 2", "risk 3"],
    "suggestions": ["concrete actionable suggestion with specifics", "suggestion 2", "suggestion 3"],
    "key_metrics": ["specific metric or benchmark this role tracks", "metric 2", "metric 3"],
    "timeline": "Realistic timeline estimate from your role's perspective with phases.",
    "priority_actions": ["most important immediate action", "second action", "third action"],
    "competitive_note": "1-2 sentences on competitive positioning from your specific role's lens."
}

Score: 0-100 (be critically honest — 75 is a strong idea, 85+ is exceptional, 60-74 is viable with caveats, below 60 has serious issues)
Verdict: "go" (score >= 70), "conditional" (50-69), "no_go" (< 50)"""

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


def _get_model() -> str:
    return os.getenv("CSUITE_MODEL", DEFAULT_MODEL)


def _resolve_csuite_model(user_id: str | None, db=None) -> dict:
    """Resolve model config for csuite task, with fallback to env/default."""
    if user_id:
        from model_resolver import resolve_model_for_task
        return resolve_model_for_task(user_id, "csuite", db=db)
    return {"model": _get_model(), "api_key": None, "api_base": None, "provider_name": "Default"}


def _build_project_context(project: Project, correction_notes: str | None = None) -> str:
    idea_context = ""
    if project.idea and project.idea.content:
        idea_context = json.dumps(project.idea.content, indent=2)

    context = f"""Project: {project.name}
Description: {project.description or 'N/A'}
Target Audience: {project.target_audience or 'N/A'}
Problem Statement: {project.problem_statement or 'N/A'}

Idea Details:
{idea_context}"""

    if correction_notes:
        context += f"\n\nUser Corrections / Extra Context:\n{correction_notes}"

    return context


async def run_single_agent(
    project: Project,
    role: CSuiteRole,
    analysis_id: str,
    correction_notes: str | None = None,
):
    from models import SessionLocal

    db = SessionLocal()
    try:
        analysis = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.id == analysis_id).first()
        if not analysis:
            return

        # Pre-flight cancellation check — an agent may have been waiting for the LLM
        # semaphore while Stop was clicked; the stop endpoint already set status=error,
        # so don't overwrite it back to running.
        if analysis_id in _CANCELLED_ANALYSES or project.id in _CANCELLED_PROJECTS:
            return
        if analysis.status == AgentStatus.error:
            return  # DB row was already stopped/cancelled by the stop endpoint

        analysis.status = AgentStatus.running
        db.commit()

        project_context = _build_project_context(project, correction_notes)
        system_prompt = CSUITE_PROMPTS[role] + "\n\n" + RESPONSE_SCHEMA

        try:
            model_config = _resolve_csuite_model(project.user_id, db=db)
            if model_config.get("error"):
                raise HTTPException(status_code=400, detail=model_config["error"])
            call_kwargs = {
                "model": model_config["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": project_context},
                ],
                "temperature": 0.7,
                "max_tokens": 8000,
            }
            if model_config["api_key"]:
                call_kwargs["api_key"] = model_config["api_key"]
            if model_config["api_base"]:
                call_kwargs["api_base"] = model_config["api_base"]
            print(f"🔑 C-Suite [{role.value}] using: {model_config['model']} via {model_config['provider_name']}")
            resp = await litellm.acompletion(**call_kwargs)
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            match = re.search(r'\{[\s\S]*\}', text)
            raw_json = match.group() if match else text
            try:
                result = json.loads(raw_json)
            except json.JSONDecodeError:
                # LLM output was likely truncated — attempt repair
                result = _repair_json(raw_json)
                if result is None:
                    result = _build_fallback_result(text)

            normalized = _normalize_analysis_result(result, fallback_text=text)
            _write_analysis_result_with_retry(analysis_id, project.id, normalized)
        except Exception as e:
            print(f"❌ C-Suite [{role.value}] crashed: {e}")
            _mark_analysis_error_with_retry(analysis_id, str(e))
    finally:
        db.close()


# Limit concurrent LLM calls per-worker (3 workers × 15 slots = 45 concurrent LLM ops max)
_LLM_SEMAPHORE = asyncio.Semaphore(15)

# Per-project / per-analysis cancellation sets (in-process; cleared on each new run)
_CANCELLED_PROJECTS: set[str] = set()
_CANCELLED_ANALYSES: set[str] = set()


def mark_cancelled_project(project_id: str) -> None:
    """Signal all in-flight agents for a project to abort after their current LLM call."""
    _CANCELLED_PROJECTS.add(project_id)


def mark_cancelled_analysis(analysis_id: str) -> None:
    """Signal a single in-flight agent to abort after its current LLM call."""
    _CANCELLED_ANALYSES.add(analysis_id)


def clear_cancellations(project_id: str) -> None:
    """Remove any stale cancellation marks when a fresh run starts."""
    _CANCELLED_PROJECTS.discard(project_id)
    # analysis IDs change each run so stale entries are harmless, but prune occasionally
    if len(_CANCELLED_ANALYSES) > 500:
        _CANCELLED_ANALYSES.clear()

# Per-project locks — prevents two concurrent runs stomping on each other's DB rows
_PROJECT_LOCKS: dict[str, asyncio.Lock] = {}


async def _throttled_agent(project, role, analysis_id, correction_notes):
    """Wrapper that throttles concurrent API calls and catches errors."""
    async with _LLM_SEMAPHORE:
        try:
            await run_single_agent(project, role, analysis_id, correction_notes)
        except Exception as e:
            print(f"❌ C-Suite [{role.value}] crashed: {e}")
            try:
                # Mark as error so the UI doesn't hang
                _mark_analysis_error_with_retry(analysis_id, str(e))
            except Exception:
                pass  # Row was deleted by a concurrent re-run — safe to ignore


async def run_all_agents_background(project_id: str, correction_notes: str | None = None):
    from models import SessionLocal

    # Acquire per-project lock — if a run is already in flight, cancel the new one
    # so it doesn't delete/recreate rows that the in-flight agents still hold.
    if project_id not in _PROJECT_LOCKS:
        _PROJECT_LOCKS[project_id] = asyncio.Lock()
    lock = _PROJECT_LOCKS[project_id]
    if lock.locked():
        print(f"⚠️  C-Suite [{project_id[:8]}] already running — skipping duplicate run (lock held)")
        return
    print(f"🔓 C-Suite [{project_id[:8]}] lock acquired — starting agents")

    async with lock:
      db = SessionLocal()
      try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        # Clear any stale cancellation marks from a previous stop
        clear_cancellations(project_id)

        project.status = ProjectStatus.csuite_running
        db.commit()

        analyses = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).all()
        _ = project.idea

        tasks = [
            _throttled_agent(project, analysis.agent_role, analysis.id, correction_notes)
            for analysis in analyses
        ]
        await asyncio.gather(*tasks)

        # Safety net: mark any agents still pending/running as error
        db.expire_all()
        stuck = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.status.in_([AgentStatus.pending, AgentStatus.running]),
        ).all()
        for s in stuck:
            s.status = AgentStatus.error
            s.error_message = "Agent did not complete (possible rate limit)"
            s.completed_at = datetime.utcnow()
        if stuck:
            db.commit()

        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = ProjectStatus.csuite_complete
            project.updated_at = datetime.utcnow()
            db.commit()
      finally:
        db.close()


async def run_selected_agents_background(
    project_id: str,
    roles: list[str],
    correction_notes: str | None = None,
):
    """Re-run only selected C-Suite agents (by role name)."""
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = ProjectStatus.csuite_running
        db.commit()

        role_enums = [CSuiteRole(r) for r in roles]
        analyses = (
            db.query(CSuiteAnalysis)
            .filter(
                CSuiteAnalysis.project_id == project_id,
                CSuiteAnalysis.agent_role.in_(role_enums),
            )
            .all()
        )
        _ = project.idea

        tasks = [
            _throttled_agent(project, analysis.agent_role, analysis.id, correction_notes)
            for analysis in analyses
        ]
        await asyncio.gather(*tasks)

        # Mark project complete after partial re-run
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = ProjectStatus.csuite_complete
            project.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


IMPROVEMENT_PROMPT = """You are a startup strategy expert. Analyze the C-Suite evaluation results below and generate SPECIFIC, ACTIONABLE improvements that would raise each agent's score toward 100.

For each agent that needs improvement, provide:
1. What specific weaknesses lowered the score
2. Concrete improvements to the project description, strategy, or context that would address them
3. A rewritten/enhanced project context paragraph that the agent should receive on re-evaluation

Be specific — don't say "improve marketing strategy", say exactly what the marketing strategy should include.

Current evaluation results:
{results_json}

Original project context:
{project_context}

Respond with ONLY valid JSON:
{{
    "improvements": {{
        "<role>": {{
            "current_score": <number>,
            "key_weaknesses": ["weakness 1", "weakness 2"],
            "recommended_changes": ["specific change 1", "specific change 2"],
            "enhanced_context": "The improved project description/context paragraph that addresses the weaknesses..."
        }}
    }},
    "summary": "One paragraph explaining the overall improvement strategy"
}}

Only include roles that need improvement (score < 85). If a role scored 85+, omit it."""


async def generate_improvement_plan(project_id: str, roles: list[str] | None = None):
    """Use AI to self-analyze current scores and generate an improvement plan."""
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}

        analyses = db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.project_id == project_id,
            CSuiteAnalysis.status == AgentStatus.complete,
        ).all()

        results = {}
        for a in analyses:
            if roles and a.agent_role.value not in roles:
                continue
            result = a.analysis or {}
            results[a.agent_role.value] = {
                "score": a.score,
                "verdict": result.get("verdict"),
                "recommendation": result.get("recommendation"),
                "strengths": result.get("strengths", []),
                "risks": result.get("risks", []),
                "suggestions": result.get("suggestions", []),
            }

        if not results:
            return {"error": "No completed analyses found"}

        project_context = _build_project_context(project)

        prompt = IMPROVEMENT_PROMPT.format(
            results_json=json.dumps(results, indent=2),
            project_context=project_context,
        )

        model_config = _resolve_csuite_model(project.user_id, db=db)
        call_kwargs = {
            "model": model_config["model"],
            "messages": [
                {"role": "system", "content": "You are a startup strategy improvement advisor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
            "max_tokens": 4000,
        }
        if model_config["api_key"]:
            call_kwargs["api_key"] = model_config["api_key"]
        if model_config["api_base"]:
            call_kwargs["api_base"] = model_config["api_base"]
        resp = await litellm.acompletion(**call_kwargs)
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        import re
        match = re.search(r'\{[\s\S]*\}', text)
        plan = json.loads(match.group() if match else text)
        return plan
    finally:
        db.close()
