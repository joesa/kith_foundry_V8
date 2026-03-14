"""
Context Compression — builds a token-efficient project context by
selecting only the most relevant code via semantic similarity.

Replaces the old approach of dumping ALL source files into the prompt.
Implements the 5-layer compression scheme from the spec:

    1. Project Summary    (~500 tokens)  — brain overview
    2. Architecture Map   (~1000 tokens) — pages, routes, component tree
    3. Dependency Graph   (~500 tokens)  — import analysis
    4. Relevant Files     (~2500 tokens) — semantic search top-k
    5. Active Snippets    (~500 tokens)  — recent decisions

Target: 150k LOC → 3k–5k tokens (97% compression).
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from brain_service import get_project_brain_context


# ── Token estimation ───────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for code, ~3.5 for English."""
    return max(1, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... (truncated)"


# ── Layer 1: Project Summary ──────────────────────────────────────────────────

def _build_project_summary(brain_context: dict | None) -> str:
    """Compact project overview from Brain tables."""
    if not brain_context:
        return "(New project — no existing structure)"

    parts: list[str] = []

    pages = brain_context.get("pages", [])
    if pages:
        page_list = ", ".join(
            f"{p['name']} ({p['route']})" for p in pages[:15]
        )
        parts.append(f"**Pages ({len(pages)}):** {page_list}")

    components = brain_context.get("components", [])
    if components:
        comp_list = ", ".join(c["name"] for c in components[:20])
        parts.append(f"**Components ({len(components)}):** {comp_list}")

    features = brain_context.get("features", [])
    if features:
        feat_summary = ", ".join(
            f"{f['name']} [{f.get('status', '?')}]" for f in features[:10]
        )
        parts.append(f"**Features ({len(features)}):** {feat_summary}")

    return "\n".join(parts) if parts else "(No brain data yet)"


# ── Layer 2: Architecture Map ─────────────────────────────────────────────────

def _build_architecture_map(
    brain_context: dict | None,
    all_files: dict[str, str] | None,
) -> str:
    """Page routes, component hierarchy, and file tree."""
    parts: list[str] = []

    # Routes from brain
    if brain_context:
        pages = brain_context.get("pages", [])
        if pages:
            routes = []
            for p in pages:
                sections = p.get("sections", [])
                sec_str = f" → [{', '.join(s.get('name', '?') for s in sections[:5])}]" if sections else ""
                routes.append(f"  {p['route']} → {p['name']}{sec_str}")
            parts.append("**Routing:**\n" + "\n".join(routes))

    # File tree from actual files
    if all_files:
        tree_lines: list[str] = []
        for path in sorted(all_files.keys()):
            size = len(all_files[path])
            tree_lines.append(f"  {path} ({size} chars)")
        parts.append("**File Tree:**\n" + "\n".join(tree_lines[:30]))

    return "\n".join(parts) if parts else "(No architecture data)"


# ── Layer 3: Dependency Graph ─────────────────────────────────────────────────

_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w{},\s*]+)\s+from\s+['"]([^'"]+)['"]"""
    r"""|require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
)


def _build_dependency_graph(all_files: dict[str, str] | None) -> str:
    """Extract import relationships between project files."""
    if not all_files:
        return "(No files to analyze)"

    deps: dict[str, list[str]] = {}
    for path, content in all_files.items():
        if not path.endswith(('.tsx', '.ts', '.jsx', '.js')):
            continue
        imports = []
        for m in _IMPORT_RE.finditer(content):
            source = m.group(1) or m.group(2)
            # Only include local imports (starting with ./ or ../)
            if source and source.startswith(('./', '../')):
                imports.append(source)
        if imports:
            deps[path] = imports

    if not deps:
        return "(No local import dependencies found)"

    lines = []
    for path, imports in sorted(deps.items()):
        lines.append(f"  {path} imports: {', '.join(imports)}")
    return "**Dependencies:**\n" + "\n".join(lines[:25])


# ── Layer 4: Relevant Files (semantic search) ────────────────────────────────

async def _build_relevant_files(
    db: Session,
    project_id: str,
    user_prompt: str,
    all_files: dict[str, str] | None,
    token_budget: int,
) -> str:
    """Select the most relevant source files via embedding similarity.

    Falls back to heuristic keyword matching when embeddings are unavailable.
    """
    # Try semantic search first
    try:
        from embedding_service import search_relevant
        results = await search_relevant(
            db, project_id, user_prompt, top_k=15,
        )
        if results:
            return _format_relevant_from_embeddings(results, all_files, token_budget)
    except Exception as e:
        print(f"[compress] Semantic search unavailable, using heuristic: {e}")

    # Fallback: keyword-based file selection
    if not all_files:
        return "(No project files)"
    return _heuristic_file_selection(user_prompt, all_files, token_budget)


def _format_relevant_from_embeddings(
    results: list[dict],
    all_files: dict[str, str] | None,
    token_budget: int,
) -> str:
    """Format search results, including full file content for top matches."""
    parts: list[str] = []
    tokens_used = 0

    for r in results:
        ref = r.get("content_ref_id", "")
        sim = r.get("similarity", 0)
        content_type = r.get("content_type", "")

        # For file-type results, include actual file content if we have it
        if content_type == "file" and all_files and ref in all_files:
            file_content = all_files[ref]
            file_tokens = _estimate_tokens(file_content)

            if tokens_used + file_tokens <= token_budget:
                ext = ref.rsplit('.', 1)[-1] if '.' in ref else 'txt'
                lang = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css',
                        'jsx': 'jsx', 'js': 'javascript'}.get(ext, ext)
                parts.append(f"\n--- {ref} (relevance: {sim:.2f}) ---\n```{lang}\n{file_content}\n```")
                tokens_used += file_tokens
            else:
                # Include a summary instead of full content
                snippet = file_content[:400]
                parts.append(f"\n--- {ref} (relevance: {sim:.2f}, truncated) ---\n{snippet}...")
                tokens_used += _estimate_tokens(snippet) + 10
        elif content_type in ("component", "decision"):
            # Include the stored text directly
            snippet = r.get("content_text", "")[:600]
            parts.append(f"\n[{content_type}] {ref}: {snippet}")
            tokens_used += _estimate_tokens(snippet) + 5

        if tokens_used >= token_budget:
            break

    return "\n".join(parts) if parts else "(No relevant embeddings found)"


def _heuristic_file_selection(
    user_prompt: str,
    all_files: dict[str, str],
    token_budget: int,
) -> str:
    """Keyword-based fallback when embeddings aren't available.

    Scores files by keyword overlap with the user prompt and returns
    the highest-scoring files within the token budget.
    """
    prompt_lower = user_prompt.lower()
    # Extract meaningful words from prompt (3+ chars, no common stop words)
    _stop = {"the", "and", "for", "that", "this", "with", "from", "have", "are", "was"}
    keywords = {
        w for w in re.findall(r'\b[a-z]{3,}\b', prompt_lower)
        if w not in _stop
    }

    scored: list[tuple[float, str]] = []
    for path, content in all_files.items():
        content_lower = content.lower()
        path_lower = path.lower()

        score = 0.0
        for kw in keywords:
            if kw in path_lower:
                score += 3.0  # Path match is very relevant
            if kw in content_lower:
                score += 1.0

        # Boost core files
        if "App.tsx" in path or "App.css" in path:
            score += 2.0
        if "index" in path:
            score += 1.0

        scored.append((score, path))

    scored.sort(key=lambda x: -x[0])

    parts: list[str] = []
    tokens_used = 0
    for score, path in scored:
        content = all_files[path]
        file_tokens = _estimate_tokens(content)

        if tokens_used + file_tokens <= token_budget:
            ext = path.rsplit('.', 1)[-1] if '.' in path else 'txt'
            lang = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css',
                    'jsx': 'jsx', 'js': 'javascript'}.get(ext, ext)
            parts.append(f"\n--- {path} ---\n```{lang}\n{content}\n```")
            tokens_used += file_tokens
        elif tokens_used < token_budget:
            # Include truncated version
            remaining = (token_budget - tokens_used) * 4
            parts.append(f"\n--- {path} (truncated) ---\n{content[:remaining]}...")
            break
        else:
            break

    return "\n".join(parts) if parts else "(No relevant files found)"


# ── Layer 5: Active Snippets ──────────────────────────────────────────────────

def _build_active_snippets(brain_context: dict | None) -> str:
    """Recent architectural decisions and active context."""
    if not brain_context:
        return ""

    decisions = brain_context.get("recent_decisions", [])
    if not decisions:
        return ""

    lines: list[str] = []
    for d in decisions[:5]:
        dtype = d.get("type", "?")
        rationale = d.get("rationale", "")
        if rationale:
            lines.append(f"  [{dtype}] {rationale[:200]}")

    return "**Recent Decisions:**\n" + "\n".join(lines) if lines else ""


# ── Main compression function ─────────────────────────────────────────────────

async def compress_context(
    db: Session,
    project_id: str,
    user_prompt: str,
    all_files: dict[str, str] | None = None,
    *,
    token_budget: int = 5000,
) -> dict[str, Any]:
    """Build a compressed project context within the token budget.

    Returns:
        {
            "text": str,           # Formatted context for LLM injection
            "layers": {            # Individual layer texts
                "summary": str,
                "architecture": str,
                "dependencies": str,
                "relevant_files": str,
                "active_snippets": str,
            },
            "total_tokens": int,
            "compression_ratio": float,  # if all_files provided
            "used_semantic": bool,       # whether pgvector search was used
        }
    """
    brain_context = None
    try:
        brain_context = get_project_brain_context(db, project_id)
    except Exception as e:
        print(f"[compress] Brain context unavailable: {e}")

    # ── Allocate token budgets per layer ───────────────────────────────────
    summary_budget = min(500, token_budget // 10)
    arch_budget = min(800, token_budget // 5)
    deps_budget = min(400, token_budget // 10)
    snippet_budget = min(300, token_budget // 10)
    # Remaining budget goes to relevant files (the main payload)
    files_budget = token_budget - summary_budget - arch_budget - deps_budget - snippet_budget

    # ── Build each layer ───────────────────────────────────────────────────
    summary = _truncate_to_tokens(
        _build_project_summary(brain_context), summary_budget
    )
    architecture = _truncate_to_tokens(
        _build_architecture_map(brain_context, all_files), arch_budget
    )
    dependencies = _truncate_to_tokens(
        _build_dependency_graph(all_files), deps_budget
    )
    relevant_files = await _build_relevant_files(
        db, project_id, user_prompt, all_files, files_budget,
    )
    relevant_files = _truncate_to_tokens(relevant_files, files_budget)
    active_snippets = _truncate_to_tokens(
        _build_active_snippets(brain_context), snippet_budget
    )

    # ── Assemble final context ─────────────────────────────────────────────
    sections = [
        ("## Project Overview", summary),
        ("## Architecture", architecture),
        ("## Dependencies", dependencies),
        ("## Relevant Code", relevant_files),
    ]
    if active_snippets:
        sections.append(("## Recent Context", active_snippets))

    text = "\n\n".join(
        f"{heading}\n{content}" for heading, content in sections if content
    )

    total_tokens = _estimate_tokens(text)

    # Compression ratio
    full_size = sum(len(c) for c in (all_files or {}).values())
    compression_ratio = 1.0 - (len(text) / max(1, full_size)) if full_size > 0 else 0.0

    return {
        "text": text,
        "layers": {
            "summary": summary,
            "architecture": architecture,
            "dependencies": dependencies,
            "relevant_files": relevant_files,
            "active_snippets": active_snippets,
        },
        "total_tokens": total_tokens,
        "compression_ratio": max(0.0, compression_ratio),
        "used_semantic": "relevance:" in relevant_files,
    }


# ── Quick helper used by agent_pipeline ────────────────────────────────────────

async def get_compressed_project_context(
    db: Session,
    project_id: str,
    user_prompt: str,
    all_files: dict[str, str] | None = None,
    *,
    token_budget: int = 5000,
) -> tuple[str, str]:
    """Convenience wrapper returning (compressed_context_text, file_tree_json).

    The file_tree is always built from all_files for the full picture,
    while the context text is the compressed version within token budget.
    """
    import json, os

    file_tree_str = "[]"
    if all_files:
        file_tree_str = json.dumps(
            [{"name": os.path.basename(p), "path": p, "type": "file"}
             for p in sorted(all_files.keys())],
            indent=2,
        )

    result = await compress_context(
        db, project_id, user_prompt, all_files, token_budget=token_budget,
    )

    return result["text"], file_tree_str
