import csv
import json
import re
from pathlib import Path
from typing import Any


_VENDOR_DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "vendor"
    / "ui-ux-pro-max-skill"
    / "src"
    / "ui-ux-pro-max"
    / "data"
)


_VENDOR_CONFIG = {
    "product": {
        "file": "products.csv",
        "search_cols": ["Product Type", "Keywords", "Primary Style Recommendation", "Key Considerations"],
    },
    "style": {
        "file": "styles.csv",
        "search_cols": ["Style Category", "Keywords", "Best For", "Type", "AI Prompt Keywords"],
    },
    "color": {
        "file": "colors.csv",
        "search_cols": ["Product Type", "Notes"],
    },
    "landing": {
        "file": "landing.csv",
        "search_cols": ["Pattern Name", "Keywords", "Conversion Optimization", "Section Order"],
    },
    "typography": {
        "file": "typography.csv",
        "search_cols": ["Font Pairing Name", "Category", "Mood/Style Keywords", "Best For", "Heading Font", "Body Font"],
    },
    "reasoning": {
        "file": "ui-reasoning.csv",
        "search_cols": ["UI_Category", "Recommended_Pattern", "Style_Priority", "Color_Mood", "Typography_Mood", "Anti_Patterns"],
    },
    "ux": {
        "file": "ux-guidelines.csv",
        "search_cols": ["Category", "Issue", "Description", "Platform"],
    },
}


_FALLBACK_RULES = [
    {
        "name": "Regulated Enterprise",
        "keywords": ["compliance", "legal", "policy", "security", "audit", "safety", "document", "enterprise", "insurance"],
        "style_family": "Trust-first editorial product UI",
        "layout": "Structured, calm, hierarchical, with strong navigation and reassuring whitespace",
        "palette_mood": "Measured, restrained, credible, no neon theatrics",
        "typography": "Precise sans-serif hierarchy with strong labels and readable body text",
        "anti_patterns": [
            "AI purple/pink gradients",
            "crypto-looking glows",
            "gaming UI energy",
            "floating random KPI tiles without context",
        ],
    },
    {
        "name": "Healthcare / Wellness",
        "keywords": ["health", "clinic", "medical", "therapy", "wellness", "care", "patient", "spa"],
        "style_family": "Human-centered calm interface",
        "layout": "Breathing room, approachable forms, visual reassurance, soft but not childish",
        "palette_mood": "Natural, restorative, emotionally safe",
        "typography": "Warm, accessible typography with gentle contrast and clear form labels",
        "anti_patterns": [
            "aggressive dark mode by default",
            "harsh neon contrast",
            "cold sci-fi chrome",
            "overly sterile templates",
        ],
    },
    {
        "name": "Fintech / Data / Operations",
        "keywords": ["finance", "bank", "fintech", "trading", "analytics", "ops", "monitoring", "dashboard", "forecast"],
        "style_family": "Analytical, composed, data-confident interface",
        "layout": "Information-dense where needed, but with strong grouping and executive clarity",
        "palette_mood": "Confident, disciplined, signal-driven",
        "typography": "High-legibility sans-serif with crisp metric hierarchy",
        "anti_patterns": [
            "generic startup hero gradients",
            "decorative glows overpowering data",
            "too many equal-weight cards",
            "crypto / AI-native visual tropes",
        ],
    },
    {
        "name": "Creative / Brand / Consumer",
        "keywords": ["brand", "creative", "agency", "portfolio", "music", "fashion", "creator", "consumer", "ecommerce"],
        "style_family": "Expressive brand-led digital product",
        "layout": "Intentional composition, rhythm, asymmetry, and memorable moments",
        "palette_mood": "Expressive and ownable, but still coherent",
        "typography": "A distinct personality pairing with strong display and editorial rhythm",
        "anti_patterns": [
            "safe generic SaaS layout",
            "random dribbble-style decoration without product logic",
            "default AI gradients",
            "template-looking symmetry everywhere",
        ],
    },
]


_DEFAULT_ANTI_PATTERNS = [
    "AI purple + cyan gradient clichés unless explicitly justified by the brand",
    "default dark SaaS dashboards with no industry-specific reasoning",
    "placeholder lorem ipsum or empty decorative cards",
    "same card grid reused on every screen",
    "visual styles that fight the CDO guidance or Design System Foundation",
    "Generic startup/SaaS template patterns that could belong to any product",
    "Reusing common hero layouts, feature grids, or pricing card arrangements seen across typical AI-generated apps",
    "Cookie-cutter visual structures — every product must have a unique compositional fingerprint",
]


def compose_project_context(
    *,
    product_name: str,
    description: str | None = None,
    target_audience: str | None = None,
    idea: Any = None,
    cdo_analysis: Any = None,
    design_system_text: str | None = None,
) -> str:
    idea_text = ""
    if idea:
        try:
            idea_text = json.dumps(idea, indent=2, default=str)
        except Exception:
            idea_text = str(idea)

    cdo_text = ""
    if cdo_analysis:
        try:
            cdo_text = json.dumps(cdo_analysis, indent=2, default=str)
        except Exception:
            cdo_text = str(cdo_analysis)

    return f"""Product: {product_name}
Description: {description or 'N/A'}
Target Audience: {target_audience or 'N/A'}

Idea: {idea_text}

CDO Design Recommendations: {cdo_text or 'None available'}

Design System Foundation:
{(design_system_text or '').strip() or 'Not yet generated — use product context and human-centered design reasoning.'}"""


def extract_product_name(project_context: str) -> str:
    for line in (project_context or "").splitlines():
        if line.lower().startswith("product:"):
            return line.split(":", 1)[1].strip() or "Product"
    return "Product"


def _extract_named_block(project_context: str, title: str) -> str:
    pattern = rf"{re.escape(title)}:\s*(.*?)(?:\n[A-Z][A-Za-z ]+:\s|$)"
    match = re.search(pattern, project_context or "", flags=re.S)
    return (match.group(1).strip() if match else "").strip()


_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "they", "their", "them",
    "will", "would", "could", "should", "what", "when", "where", "which", "who", "why",
    "how", "has", "have", "had", "been", "are", "was", "were", "but", "not", "all",
    "any", "can", "into", "our", "out", "over", "under", "through", "about", "after",
    "before", "between", "during", "without", "within", "must", "these", "those",
    "such", "many", "much", "very", "most", "some", "other", "only", "also", "then",
    "than", "there", "here", "just", "like",
}

def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\-/+]*", (text or "").lower())
    return [t for t in tokens if len(t) > 2 and t not in _STOP_WORDS]


def _load_vendor_rows(kind: str) -> list[dict[str, str]]:
    config = _VENDOR_CONFIG[kind]
    path = _VENDOR_DATA_DIR / config["file"]
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _search_vendor(kind: str, query: str, limit: int = 3) -> list[dict[str, str]]:
    rows = _load_vendor_rows(kind)
    if not rows:
        return []

    config = _VENDOR_CONFIG[kind]
    query_tokens = _tokenize(query)
    scored: list[tuple[int, dict[str, str]]] = []

    for row in rows:
        haystack = " ".join(str(row.get(col, "")) for col in config["search_cols"]).lower()
        score = 0
        for token in query_tokens:
            if token in haystack:
                score += 1
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]


def _match_fallback_rule(query: str) -> dict[str, Any]:
    query_lower = query.lower()
    best = _FALLBACK_RULES[0]
    best_score = -1
    for rule in _FALLBACK_RULES:
        score = sum(1 for kw in rule["keywords"] if kw in query_lower)
        if score > best_score:
            best = rule
            best_score = score
    return best


def _parse_reasoning_rule(rule: dict[str, str]) -> dict[str, Any]:
    decision_rules: dict[str, Any] = {}
    raw_decisions = rule.get("Decision_Rules", "")
    if raw_decisions:
        try:
            decision_rules = json.loads(raw_decisions)
        except Exception:
            decision_rules = {}
    return {
        "pattern": rule.get("Recommended_Pattern", ""),
        "style_priority": [item.strip() for item in rule.get("Style_Priority", "").split("+") if item.strip()],
        "color_mood": rule.get("Color_Mood", ""),
        "typography_mood": rule.get("Typography_Mood", ""),
        "key_effects": rule.get("Key_Effects", ""),
        "anti_patterns": [item.strip() for item in re.split(r"[;,]", rule.get("Anti_Patterns", "")) if item.strip()],
        "decision_rules": decision_rules,
    }


def _infer_screen_kind(screen_desc: str | None) -> str:
    lower = (screen_desc or "").lower()
    if any(token in lower for token in ("settings", "profile", "company profile", "preferences", "permissions")):
        return "settings"
    if any(token in lower for token in ("dashboard", "analytics", "oversight", "risk", "reporting")):
        return "dashboard"
    if any(token in lower for token in ("home", "landing", "overview", "north-star", "north star")):
        return "home"
    if any(token in lower for token in ("list", "table", "inventory", "directory")):
        return "list"
    if any(token in lower for token in ("form", "create", "edit", "wizard", "onboarding")):
        return "form"
    return "general"


def _screen_obligations(screen_desc: str | None, *, industry_category: str, product_name: str) -> list[str]:
    screen_kind = _infer_screen_kind(screen_desc)
    base = [
        f"Make the screen feel native to {product_name}, with visible product logic instead of a generic app template.",
        "Use realistic product copy, labels, and states that reflect actual operations rather than placeholder content.",
        "Preserve strong grouping, hierarchy, and navigation cues so a busy user can understand the page quickly.",
    ]

    if screen_kind == "home":
        base.extend([
            "Treat this as a north-star reference screen that establishes the product's visual language for later screens.",
            "Prioritize a trustworthy top-level summary, meaningful actions, and one clearly valuable operational data surface.",
            "Avoid decorative KPI spam or a hero area that feels more like marketing than software.",
        ])
    elif screen_kind == "dashboard":
        base.extend([
            "Increase information density only where it improves decision-making; avoid equal-weight card soup.",
            "Use comparisons, alerts, tables, and summaries that feel operationally grounded for this product category.",
            "Keep the composition disciplined enough for executives or operations leads working under pressure.",
        ])
    elif screen_kind == "settings":
        base.extend([
            "Make the screen calmer than the dashboard, but equally intentional and cohesive with the rest of the product.",
            "Structure settings into thoughtful groups with clear labels, descriptions, and practical controls.",
            "Avoid fallback account-page tropes such as anonymous avatar-first layouts, generic preference toggles, or disconnected admin templates.",
        ])
    elif screen_kind == "list":
        base.extend([
            "Make the primary table or list genuinely useful, with obvious status, filtering, and next-action patterns.",
            "Use surrounding summary and controls to support the list, not distract from it.",
        ])
    elif screen_kind == "form":
        base.extend([
            "Guide the user through the task with clear steps, supportive copy, and visible cause-and-effect.",
            "Use form density and spacing that feel calm and reliable rather than bureaucratic or empty.",
        ])
    else:
        base.extend([
            f"Shape the page around the job implied by the screen description and the realities of {industry_category}.",
            "Prefer a defendable, product-specific composition over a broad dashboard shell.",
        ])

    return base


def build_design_brief(
    project_context: str,
    *,
    screen_desc: str | None = None,
    direction: str | None = None,
    approved_mockups: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    product_name = extract_product_name(project_context)
    description = _extract_named_block(project_context, "Description")
    target_audience = _extract_named_block(project_context, "Target Audience")
    cdo_text = _extract_named_block(project_context, "CDO Design Recommendations")
    dsf_text = _extract_named_block(project_context, "Design System Foundation")
    query = " ".join(
        part for part in [
            product_name,
            description,
            target_audience,
            screen_desc or "",
            cdo_text,
            dsf_text,
            direction or "",
        ] if part
    )

    product_hits = _search_vendor("product", query, limit=1)
    style_hits = _search_vendor("style", query, limit=3)
    color_hits = _search_vendor("color", query, limit=2)
    landing_hits = _search_vendor("landing", query, limit=1)
    type_hits = _search_vendor("typography", query, limit=1)
    reasoning_hits = _search_vendor("reasoning", query, limit=1)
    # UX guidelines: query with screen kind appended so we get interaction/a11y rules relevant to this screen type
    ux_query = f"{query} {_infer_screen_kind(screen_desc)}"
    ux_hits = _search_vendor("ux", ux_query, limit=3)
    fallback = _match_fallback_rule(query)
    reasoning = _parse_reasoning_rule(reasoning_hits[0]) if reasoning_hits else {}

    product_hit = product_hits[0] if product_hits else {}
    style_hit = style_hits[0] if style_hits else {}
    color_hit = color_hits[0] if color_hits else {}
    type_hit = type_hits[0] if type_hits else {}
    landing_hit = landing_hits[0] if landing_hits else {}

    # Harvest richer style data the vendor exposes but we were discarding
    style_ai_prompt_kw = style_hit.get("AI Prompt Keywords", "").strip()
    style_css_kw = style_hit.get("CSS/Technical Keywords", "").strip()
    style_impl_checklist = style_hit.get("Implementation Checklist", "").strip()
    style_effects = style_hit.get("Effects & Animation", "").strip()
    style_do_not_use_for = style_hit.get("Do Not Use For", "").strip()

    # Actionable decision rules from reasoning CSV (e.g. {"if_data_heavy": "add-glassmorphism"})
    decision_rules: dict[str, str] = reasoning.get("decision_rules", {})
    active_decision_rules: list[str] = []
    query_lower = query.lower()
    for condition, action in decision_rules.items():
        keyword = condition.replace("if_", "").replace("must_have", "").replace("_", " ")
        if keyword and keyword.lower() in query_lower:
            active_decision_rules.append(f"{condition}: {action}")
        elif condition.startswith("must_have"):
            active_decision_rules.append(f"Required: {action}")

    # UX guideline Do/Don't rules from matching entries
    ux_dos: list[str] = [h.get("Do", "").strip() for h in ux_hits if h.get("Do", "").strip()]
    ux_donts: list[str] = [h.get("Don't", "").strip() for h in ux_hits if h.get("Don't", "").strip()]

    approved_summaries = approved_mockups or []
    consistent_reference = "yes" if approved_summaries else "no"

    anti_patterns = list(dict.fromkeys(
        _DEFAULT_ANTI_PATTERNS
        + reasoning.get("anti_patterns", [])
        + fallback["anti_patterns"]
    ))

    if "purple" not in " ".join(anti_patterns).lower():
        anti_patterns.append("Unmotivated purple neon, cyan glow, or 'AI app' color tropes")

    style_name = style_hit.get("Style Category") or (reasoning.get("style_priority") or [fallback["style_family"]])[0]
    typography_heading = type_hit.get("Heading Font") or "Inter"
    typography_body = type_hit.get("Body Font") or "Inter"

    brief = {
        "product_name": product_name,
        "industry_category": product_hit.get("Product Type") or fallback["name"],
        "project_summary": description or "No description provided",
        "target_audience": target_audience or "Not specified",
        "screen_desc": screen_desc or "",
        "direction": direction or "",
        "authoritative_inputs": {
            "cdo_present": bool(cdo_text and cdo_text != "None available"),
            "design_system_present": bool(dsf_text and "Not yet generated" not in dsf_text),
            "approved_mockups_present": bool(approved_summaries),
        },
        "reasoned_recommendation": {
            "style_family": style_name,
            "style_notes": style_hit.get("Keywords") or fallback["style_family"],
            "layout_philosophy": landing_hit.get("Pattern Name") or reasoning.get("pattern") or fallback["layout"],
            "layout_notes": landing_hit.get("Section Order") or fallback["layout"],
            "color_mood": color_hit.get("Notes") or reasoning.get("color_mood") or fallback["palette_mood"],
            "palette": {
                "primary": color_hit.get("Primary (Hex)", ""),
                "secondary": color_hit.get("Secondary (Hex)", ""),
                "cta": color_hit.get("CTA (Hex)", ""),
                "background": color_hit.get("Background (Hex)", ""),
                "text": color_hit.get("Text (Hex)", ""),
                "border": color_hit.get("Border (Hex)", ""),
            },
            "typography_direction": {
                "pairing": type_hit.get("Font Pairing Name") or f"{typography_heading} / {typography_body}",
                "heading_font": typography_heading,
                "body_font": typography_body,
                "mood": type_hit.get("Mood/Style Keywords") or reasoning.get("typography_mood") or fallback["typography"],
            },
            "interaction_tone": style_effects or reasoning.get("key_effects") or "Motion should support comprehension and brand tone, not decorate for its own sake.",
            # Vendor-sourced implementation guidance — fed directly into the LLM brief
            "style_ai_prompt_keywords": style_ai_prompt_kw,
            "style_css_keywords": style_css_kw,
            "style_implementation_checklist": style_impl_checklist,
            "style_do_not_use_for": style_do_not_use_for,
            "active_decision_rules": active_decision_rules,
        },
        "ux_guidelines": {
            "dos": ux_dos,
            "donts": ux_donts,
        },
        "creative_freedom": [
            "Do not default to dark mode, glassmorphism, gradient-heavy UI, or AI-native tropes unless the product context genuinely supports them.",
            "Let layout, density, and emotional tone emerge from product reality, the CDO recommendations, and the Design System Foundation.",
            "If a user direction is provided, treat it as a strong preference but still avoid generic AI-looking execution.",
            "Each product must have a genuinely unique visual identity. Derive compositional choices, content hierarchy, section ordering, and illustration metaphors from the specific product context — never reuse template patterns across different products.",
        ],
        "must_honor": [
            "Treat the CDO recommendations and Design System Foundation as the primary sources of truth.",
            "If approved mockups exist, maintain one coherent product language across screens.",
            "Screen-specific functional requirements still matter, but they should not force a single house aesthetic.",
        ],
        "anti_patterns": anti_patterns,
        "five_layer_authenticity_stack": [
            "Product Truth: reflect the product's actual industry, users, and trust requirements rather than a generic app-builder aesthetic.",
            "Brand Realism: use intentional color psychology and typography; avoid default AI purple/cyan and arbitrary startup gradients.",
            "Compositional Intent: choose hierarchy, spacing, and layout rhythm that a human designer would defend for this product.",
            "Interaction Materiality: controls, motion, surfaces, and states should feel considered and consistent with the product's tone.",
            "Human Critique: review for cliché AI signals, visual sameness, and mismatch with CDO or design-system guidance before accepting the output.",
        ],
        "human_centered_iteration_framework": [
            "Interpret the product, audience, and risks before designing.",
            "Propose a visual direction rooted in industry fit and brand intent.",
            "Generate a polished screen with realistic content and purposeful hierarchy.",
            "Critique the result against authenticity, usability, and DSF/CDO alignment.",
            "Refine until the screen feels product-specific, believable, and visually coherent.",
        ],
        "consistency_reference": consistent_reference,
        "approved_mockup_summaries": approved_summaries[:8],
    }
    return brief


def build_compiled_design_spec(
    project_context: str,
    *,
    screen_desc: str | None = None,
    direction: str | None = None,
    approved_mockups: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    brief = build_design_brief(
        project_context,
        screen_desc=screen_desc,
        direction=direction,
        approved_mockups=approved_mockups,
    )
    recommendation = brief.get("reasoned_recommendation", {})
    typography = recommendation.get("typography_direction", {})
    palette = recommendation.get("palette", {})
    screen_kind = _infer_screen_kind(screen_desc)
    product_name = brief.get("product_name", "Product")
    industry_category = brief.get("industry_category", "General product")

    non_negotiables = list(dict.fromkeys([
        "Do not default to dark-SaaS styling, purple/cyan AI gradients, glassmorphism, or glow-heavy surfaces unless the product context explicitly supports them.",
        "The screen must feel like a real shipped product for its industry and audience, not a design exercise or builder template.",
        "Cross-screen consistency is mandatory: typography logic, palette logic, spacing rhythm, navigation language, and component treatment should feel like one system.",
        "Use realistic, product-specific labels, data, and interface copy.",
        *brief.get("must_honor", []),
    ]))

    consistency_contract = {
        "palette_logic": (
            "Use restrained brand colors to guide status, emphasis, and navigation rather than bathing the entire interface in accent color. "
            "Let surfaces and backgrounds support readability first."
        ),
        "typography_logic": (
            f"Use {typography.get('pairing', 'a contextual pairing')} with strong hierarchy: headings establish authority, labels stay crisp, "
            "and body text remains readable under operational density."
        ),
        "spacing_rhythm": (
            "Keep a repeatable spacing rhythm with clear section grouping, deliberate breathing room, and consistent edge alignment. "
            "Do not let one area become airy while another feels cramped."
        ),
        "navigation_language": (
            "Navigation, page headers, filters, and action zones should speak the same product language across screens and preserve the same trust level."
        ),
        "component_treatment": (
            "Cards, forms, tables, indicators, and empty states should share one material system and level of refinement. "
            "Settings screens must not silently downgrade into generic admin UI."
        ),
        "non_negotiables": non_negotiables[:6],
    }

    spec = {
        "product_reality": [
            f"{product_name} should feel like a credible {industry_category} product rather than a generic software shell.",
            f"Audience pressure: {brief.get('target_audience', 'Not specified')}. Optimize for trust, clarity, and quick situational understanding.",
            brief.get("project_summary", "No description provided"),
        ],
        "design_philosophy": [
            recommendation.get("layout_notes") or recommendation.get("layout_philosophy") or "Use a purposeful composition grounded in product reality.",
            recommendation.get("style_notes") or recommendation.get("style_family") or "Let the style family emerge from the product and users.",
            recommendation.get("color_mood") or "Keep the color mood credible and restrained.",
            recommendation.get("interaction_tone") or "Use motion and feedback to support comprehension, not decoration.",
        ],
        "visual_system": {
            "style_family": recommendation.get("style_family", "Context-led product design"),
            "layout_philosophy": recommendation.get("layout_philosophy", "Purpose-built composition"),
            "typography_attitude": typography.get("mood", "Clear, professional typography"),
            "palette_cues": {k: v for k, v in palette.items() if v},
        },
        "screen_kind": screen_kind,
        "screen_obligations": _screen_obligations(
            screen_desc,
            industry_category=industry_category,
            product_name=product_name,
        ),
        "consistency_contract": consistency_contract,
        "forbidden_moves": list(dict.fromkeys([
            *brief.get("anti_patterns", []),
            "Redesigning a revised screen from scratch instead of refining the existing product language.",
            "Using composition tricks or styling flourishes that overpower the product's real job.",
            "Letting settings, profile, or admin surfaces feel less designed than primary workflow screens.",
        ])),
        "revision_guardrails": [
            "When revising, preserve the product language and improve craft, clarity, and composition rather than pivoting to an unrelated style.",
            "Treat user feedback as a targeted refinement request unless it explicitly asks for a new direction.",
            "If a direction pivot is requested, create a new coherent direction without drifting into generic startup aesthetics.",
        ],
        "authoritative_inputs": brief.get("authoritative_inputs", {}),
        "approved_mockup_summaries": brief.get("approved_mockup_summaries", []),
        "direction": brief.get("direction", ""),
        # Vendor-sourced guidance (pass-through from brief)
        "style_ai_prompt_keywords": recommendation.get("style_ai_prompt_keywords", ""),
        "style_css_keywords": recommendation.get("style_css_keywords", ""),
        "style_implementation_checklist": recommendation.get("style_implementation_checklist", ""),
        "style_do_not_use_for": recommendation.get("style_do_not_use_for", ""),
        "active_decision_rules": recommendation.get("active_decision_rules", []),
        "ux_guidelines": brief.get("ux_guidelines", {}),
    }
    return spec


def format_design_brief(brief: dict[str, Any], *, compact: bool = False) -> str:
    recommendation = brief.get("reasoned_recommendation", {})
    typography = recommendation.get("typography_direction", {})
    palette = recommendation.get("palette", {})
    lines = [
        "## Human-Centered Design Intelligence Brief",
        f"Product: {brief.get('product_name', 'Product')}",
        f"Industry fit: {brief.get('industry_category', 'General product')}",
        f"Audience: {brief.get('target_audience', 'Not specified')}",
        f"Style family: {recommendation.get('style_family', 'Context-led product design')}",
        f"Layout philosophy: {recommendation.get('layout_philosophy', 'Purpose-built composition')}",
        f"Typography direction: {typography.get('pairing', 'Contextual pairing')} | {typography.get('mood', '')}".strip(),
    ]

    if any(palette.values()):
        lines.append(
            "Suggested palette cues: "
            + ", ".join(f"{k}={v}" for k, v in palette.items() if v)
        )

    rec = brief.get("reasoned_recommendation", {})

    # Vendor-sourced implementation signals — always include regardless of compact flag
    if rec.get("style_ai_prompt_keywords"):
        lines.extend(["", f"Style prompt guidance: {rec['style_ai_prompt_keywords']}"])
    if rec.get("style_css_keywords"):
        lines.extend(["", f"CSS/Technical keywords for this style: {rec['style_css_keywords']}"])
    if rec.get("active_decision_rules"):
        lines.extend(["", "Active decision rules from reasoning:"] + [f"- {r}" for r in rec["active_decision_rules"]])
    ux = brief.get("ux_guidelines", {})
    if ux.get("dos"):
        lines.extend(["", "Interaction/accessibility rules (DO):"] + [f"- {d}" for d in ux["dos"]])
    if ux.get("donts"):
        lines.extend(["", "Interaction/accessibility rules (DON'T):"] + [f"- {d}" for d in ux["donts"]])

    if not compact:
        lines.extend([
            "",
            "### Must Honor",
            *[f"- {item}" for item in brief.get("must_honor", [])],
            "",
            "### Creative Freedom",
            *[f"- {item}" for item in brief.get("creative_freedom", [])],
            "",
            "### 5-Layer Authenticity Stack",
            *[f"- {item}" for item in brief.get("five_layer_authenticity_stack", [])],
            "",
            "### Human-Centered Iteration Framework",
            *[f"- {item}" for item in brief.get("human_centered_iteration_framework", [])],
            "",
            "### Anti-Patterns To Avoid",
            *[f"- {item}" for item in brief.get("anti_patterns", [])],
        ])
        if rec.get("style_implementation_checklist"):
            lines.extend(["", f"Style implementation checklist: {rec['style_implementation_checklist']}"])
        if rec.get("style_do_not_use_for"):
            lines.extend(["", f"This style should NOT be used for: {rec['style_do_not_use_for']}"])
        approved = brief.get("approved_mockup_summaries") or []
        if approved:
            lines.extend([
                "",
                "### Approved Mockup References",
                *[
                    f"- {item.get('name', 'Screen')}: {item.get('description', 'No description')}"
                    for item in approved
                ],
            ])
    else:
        lines.extend([
            "### Anti-Patterns",
            *[f"- {item}" for item in brief.get("anti_patterns", [])[:6]],
        ])

    return "\n".join(lines).strip()


def format_compiled_design_spec(spec: dict[str, Any], *, compact: bool = False) -> str:
    visual_system = spec.get("visual_system", {})
    consistency = spec.get("consistency_contract", {})
    palette_cues = visual_system.get("palette_cues", {})
    lines = [
        "## Compiled Design Spec",
        f"Screen kind: {spec.get('screen_kind', 'general')}",
        f"Style family: {visual_system.get('style_family', 'Context-led product design')}",
        f"Layout philosophy: {visual_system.get('layout_philosophy', 'Purpose-built composition')}",
        f"Typography attitude: {visual_system.get('typography_attitude', 'Professional and readable')}",
    ]

    if palette_cues:
        lines.append(
            "Palette cues: " + ", ".join(f"{key}={value}" for key, value in palette_cues.items())
        )

    # Vendor-sourced implementation signals — always include regardless of compact flag
    if spec.get("style_ai_prompt_keywords"):
        lines.extend(["", f"Style prompt guidance: {spec['style_ai_prompt_keywords']}"])
    if spec.get("style_css_keywords"):
        lines.extend(["", f"CSS/Technical keywords for this style: {spec['style_css_keywords']}"])
    if spec.get("active_decision_rules"):
        lines.extend(["", "Active decision rules:"] + [f"- {r}" for r in spec["active_decision_rules"]])
    ux = spec.get("ux_guidelines", {})
    if ux.get("dos"):
        lines.extend(["", "Interaction/accessibility rules (DO):"] + [f"- {d}" for d in ux["dos"]])
    if ux.get("donts"):
        lines.extend(["", "Interaction/accessibility rules (DON'T):"] + [f"- {d}" for d in ux["donts"]])

    if compact:
        lines.extend([
            "",
            "### Screen Obligations",
            *[f"- {item}" for item in spec.get("screen_obligations", [])[:4]],
            "",
            "### Non-Negotiables",
            *[f"- {item}" for item in consistency.get("non_negotiables", [])[:4]],
            "",
            "### Forbidden Moves",
            *[f"- {item}" for item in spec.get("forbidden_moves", [])[:6]],
        ])
        return "\n".join(lines).strip()

    lines.extend([
        "",
        "### Product Reality",
        *[f"- {item}" for item in spec.get("product_reality", [])],
        "",
        "### Design Philosophy",
        *[f"- {item}" for item in spec.get("design_philosophy", [])],
        "",
        "### Screen Obligations",
        *[f"- {item}" for item in spec.get("screen_obligations", [])],
        "",
        "### Consistency Contract",
        f"- Palette logic: {consistency.get('palette_logic', '')}",
        f"- Typography logic: {consistency.get('typography_logic', '')}",
        f"- Spacing rhythm: {consistency.get('spacing_rhythm', '')}",
        f"- Navigation language: {consistency.get('navigation_language', '')}",
        f"- Component treatment: {consistency.get('component_treatment', '')}",
        "",
        "### Non-Negotiables",
        *[f"- {item}" for item in consistency.get("non_negotiables", [])],
        "",
        "### Forbidden Moves",
        *[f"- {item}" for item in spec.get("forbidden_moves", [])],
        "",
        "### Revision Guardrails",
        *[f"- {item}" for item in spec.get("revision_guardrails", [])],
    ])

    if spec.get("style_implementation_checklist"):
        lines.extend(["", f"Style implementation checklist: {spec['style_implementation_checklist']}"])
    if spec.get("style_do_not_use_for"):
        lines.extend(["", f"This style should NOT be used for: {spec['style_do_not_use_for']}"])

    approved = spec.get("approved_mockup_summaries") or []
    if approved:
        lines.extend([
            "",
            "### Approved Screen Anchors",
            *[
                f"- {item.get('name', 'Screen')}: {item.get('description', 'No description')}"
                for item in approved
            ],
        ])

    return "\n".join(lines).strip()
