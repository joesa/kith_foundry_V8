"""
C-Suite agent orchestration and prompts.
"""
import json
import os
import asyncio
from datetime import datetime

import litellm

from models import Project, CSuiteAnalysis, ProjectStatus, CSuiteRole, AgentStatus

litellm.drop_params = True

CSUITE_PROMPTS = {
    CSuiteRole.ceo: """You are the CEO evaluating this startup idea. Assess:
- Overall strategic vision and market opportunity
- Scalability and long-term potential
- Team feasibility (can this be built by 1-2 people initially?)
- Competitive landscape and defensibility""",
    CSuiteRole.cto: """You are the CTO evaluating this startup idea technically. Assess:
- Technical feasibility for a small team MVP
- Architecture complexity and scalability concerns
- Key technical risks and unknowns
- Recommended tech stack and infrastructure needs
- Time-to-MVP estimate""",
    CSuiteRole.cfo: """You are the CFO evaluating this startup's financial viability. Assess:
- Revenue model strength and pricing strategy
- Unit economics potential (LTV/CAC estimates)
- Capital requirements and burn rate estimates
- Path to profitability
- Financial risks""",
    CSuiteRole.cmo: """You are the CMO evaluating the go-to-market strategy. Assess:
- Target market clarity and size (TAM/SAM/SOM)
- Marketing channel viability
- Customer acquisition strategy
- Brand positioning and differentiation
- Growth potential and viral mechanics""",
    CSuiteRole.cpo: """You are the CPO evaluating the product strategy. Assess:
- Problem-solution fit clarity
- MVP feature scope (is it too broad or too narrow?)
- User experience considerations
- Product differentiation from alternatives
- Feature prioritization recommendations""",
    CSuiteRole.coo: """You are the COO evaluating operational feasibility. Assess:
- Day-to-day operational complexity
- Regulatory and compliance considerations
- Supply chain or service delivery challenges
- Scalability of operations
- Key operational risks""",
    CSuiteRole.cdo: """You are the CDO (Chief Design Officer) evaluating design needs. Assess:
- Design complexity for MVP
- Key screens/components needed
- Brand identity requirements
- UX patterns to consider
- Design system recommendations
- Accessibility considerations""",
}

RESPONSE_SCHEMA = """Respond with ONLY valid JSON:
{
    "score": 75,
    "verdict": "go",
    "recommendation": "2-3 sentence summary recommendation",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "risks": ["risk 1", "risk 2"],
    "suggestions": ["actionable suggestion 1", "actionable suggestion 2"]
}

Score: 0-100 (be honest and critical)
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

        analysis.status = AgentStatus.running
        db.commit()

        project_context = _build_project_context(project, correction_notes)
        system_prompt = CSUITE_PROMPTS[role] + "\n\n" + RESPONSE_SCHEMA

        try:
            model_config = _resolve_csuite_model(project.user_id, db=db)
            call_kwargs = {
                "model": model_config["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": project_context},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
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

            import re
            match = re.search(r'\{[\s\S]*\}', text)
            result = json.loads(match.group() if match else text)

            analysis.analysis = result
            analysis.score = min(100, max(0, int(result.get("score", 50))))
            analysis.status = AgentStatus.complete
            analysis.completed_at = datetime.utcnow()
        except Exception as e:
            analysis.status = AgentStatus.error
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()


async def run_all_agents_background(project_id: str, correction_notes: str | None = None):
    from models import SessionLocal

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = ProjectStatus.csuite_running
        db.commit()

        analyses = db.query(CSuiteAnalysis).filter(CSuiteAnalysis.project_id == project_id).all()
        _ = project.idea

        tasks = [
            run_single_agent(project, analysis.agent_role, analysis.id, correction_notes)
            for analysis in analyses
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

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
            run_single_agent(project, analysis.agent_role, analysis.id, correction_notes)
            for analysis in analyses
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

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
