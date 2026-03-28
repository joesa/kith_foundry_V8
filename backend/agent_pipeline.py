"""
Multi-Agent Code Generation Pipeline — Phase 2

Replaces the single SURGEON_PROMPT call with a structured agent pipeline:

    User Prompt
        → Intent Agent    (classify + decompose)
        → Layout Agent    (page structure + routing)
        → Component Agent (component manifest + props + visual spec)
        → Code Agent      (SURGEON_PROMPT — generates actual code)

Each agent produces structured JSON that feeds the next stage.
The pipeline also populates the Project Brain tables after code generation.
"""
from __future__ import annotations

import json
import os
import re
import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncIterator

import litellm
from sqlalchemy.orm import Session

from models import (
    File, Project, SessionLocal,
)
from prompts import (
    INTENT_AGENT_PROMPT,
    LAYOUT_AGENT_PROMPT,
    COMPONENT_AGENT_PROMPT,
    SURGEON_PROMPT,
    ROUTER_PROMPT,
    CONVERSATIONAL_PROMPT,
    FIX_PROMPT,
)
from circuit_breaker import llm_breaker, CircuitOpenError
from design_engine import (
    get_design_system_from_artifacts,
    build_design_context_for_agent,
    extract_design_tokens_css,
)
from brain_service import (
    upsert_page, upsert_component, upsert_feature, add_decision,
    get_project_brain_context, PageStatus, FeatureStatus, DecisionType,
)


# ── JSON extraction (shared with agent.py) ─────────────────────────────────

def _extract_json_block(text: str) -> str | None:
    """Find the outermost JSON object or array via bracket depth tracking."""
    start = None
    open_char = None
    close_char = None
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if start is None and ch in ('{', '['):
            start = i
            open_char = ch
            close_char = '}' if ch == '{' else ']'
            depth = 1
        elif start is not None:
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


def _parse_json_response(raw: str) -> dict | list | None:
    """Clean + parse LLM JSON output."""
    clean = raw.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0].strip()
    block = _extract_json_block(clean)
    if block:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return None


async def _call_agent(
    system_prompt: str,
    user_prompt: str,
    model_id: str,
    llm_kwargs: dict,
    agent_name: str,
    temperature: float = 0.3,
) -> dict | None:
    """Call an agent LLM and return parsed JSON."""
    provider = llm_breaker.extract_provider(model_id)
    try:
        llm_breaker.check(provider)
        response = await llm_breaker.call(
            provider,
            litellm.acompletion(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                stream=False,
                timeout=llm_breaker.default_timeout,
                **llm_kwargs,
            ),
        )
        raw = response.choices[0].message.content or ""
        result = _parse_json_response(raw)
        if isinstance(result, dict):
            return result
        print(f"[{agent_name}] Non-dict response: {type(result)}")
        return None
    except CircuitOpenError as e:
        print(f"[{agent_name}] Circuit open: {e}")
        return None
    except Exception as e:
        print(f"[{agent_name}] Failed: {e}")
        return None


# ── Pipeline Stages ────────────────────────────────────────────────────────────

async def run_intent_agent(
    prompt: str,
    project_context: str,
    brain_context: dict | None,
    model_id: str,
    llm_kwargs: dict,
) -> dict | None:
    """Stage 1: Analyze user intent and decompose into structured plan."""
    brain_section = ""
    if brain_context:
        brain_section = f"""

**Project Brain (current knowledge):**
```json
{json.dumps(brain_context, indent=2, default=str)[:4000]}
```"""

    user_msg = f"""User Request: {prompt}

**Current Project State:**
{project_context}
{brain_section}

Analyze the intent and produce the structured intent JSON."""

    return await _call_agent(
        INTENT_AGENT_PROMPT, user_msg, model_id, llm_kwargs, "IntentAgent",
    )


async def run_layout_agent(
    intent: dict,
    design_ref: str,
    model_id: str,
    llm_kwargs: dict,
) -> dict | None:
    """Stage 2: Produce page layout plan from intent + design system."""
    user_msg = f"""**Intent (from Intent Agent):**
```json
{json.dumps(intent, indent=2)}
```

{design_ref}

Produce the detailed layout plan JSON for every page that needs to be built or modified."""

    return await _call_agent(
        LAYOUT_AGENT_PROMPT, user_msg, model_id, llm_kwargs, "LayoutAgent",
        temperature=0.3,
    )


async def run_component_agent(
    layout_plan: dict,
    design_ref: str,
    model_id: str,
    llm_kwargs: dict,
) -> dict | None:
    """Stage 3: Produce component manifest from layout plan + design system."""
    user_msg = f"""**Layout Plan (from Layout Agent):**
```json
{json.dumps(layout_plan, indent=2)}
```

{design_ref}

Produce the component manifest JSON with every component to generate."""

    return await _call_agent(
        COMPONENT_AGENT_PROMPT, user_msg, model_id, llm_kwargs, "ComponentAgent",
        temperature=0.3,
    )


def _build_code_agent_prompt(
    user_prompt: str,
    intent: dict | None,
    layout_plan: dict | None,
    component_manifest: dict | None,
    design_ref: str,
    file_tree_str: str,
    project_context: str,
) -> str:
    """Build the enriched prompt for the Code Agent (SURGEON_PROMPT).

    Injects structured context from upstream agents so the code agent
    has maximum guidance rather than guessing.
    """
    parts: list[str] = [f"User Request: {user_prompt}"]

    if design_ref:
        parts.append(design_ref)

    if intent:
        parts.append(f"""
**Agent Pipeline Context — Intent Analysis:**
- Type: {intent.get('intent_type', 'unknown')}
- Scope: {intent.get('scope', 'unknown')}
- Description: {intent.get('description', '')}""")

        if intent.get("intent_type") == "initial_build":
            parts.append(
                """
**Initial Build Guardrails:**
- This is an initial build. Treat any existing scaffold/template files as non-authoritative.
- Requirements/design context override existing file contents.
- Replace unrelated scaffold branding/copy/navigation if present.
- Build the requested product domain exactly; do not preserve a house-template app shell.
- Output full root app files in this generation: src/main.tsx, src/App.tsx, and src/App.css, plus required feature pages/components.
"""
            )

        new_pages = intent.get("new_pages_needed", [])
        if new_pages:
            parts.append("- New pages needed:")
            for p in new_pages:
                parts.append(f"  - {p.get('name', '?')} at {p.get('route', '?')}: {p.get('purpose', '')}")

    if layout_plan:
        parts.append(f"""
**Agent Pipeline Context — Layout Plan:**
```json
{json.dumps(layout_plan, indent=2)[:3000]}
```""")

    if component_manifest:
        # Include design_token_css if present (capped to avoid TPM overflow)
        token_css = component_manifest.get("design_token_css", "")
        if token_css:
            parts.append(f"""
**Agent Pipeline Context — Design Token CSS:**
```css
{token_css[:2_000]}
```""")

        # Include file order
        file_order = component_manifest.get("file_order", [])
        if file_order:
            parts.append(f"\n**Agent Pipeline Context — File Generation Order:** {', '.join(file_order)}")

        # Include component specs (truncated)
        components = component_manifest.get("components", [])
        if components:
            parts.append("\n**Agent Pipeline Context — Component Specs:**")
            for c in components[:20]:  # cap at 20 to avoid token overflow
                parts.append(f"- **{c.get('name', '?')}** ({c.get('file_path', '?')}): {c.get('purpose', '')}")
                vs = c.get("visual_spec", {})
                if vs:
                    parts.append(f"  Visual: {vs.get('style', '')}. Layout: {vs.get('layout', '')}. Animations: {vs.get('animations', '')}")

    parts.append(f"""
Current project file tree:
```json
{file_tree_str}
```

Current project files:{project_context}

Output a JSON object with a "files" array. Each entry has "file_path" and "content". Output ONLY valid JSON.""")

    return "\n".join(parts)


# ── Full Pipeline Orchestrator ─────────────────────────────────────────────────

async def run_multi_agent_pipeline(
    prompt: str,
    project_id: str,
    model_id: str,
    llm_kwargs: dict,
    db: Session,
    *,
    images: list | None = None,
    user_id: str | None = None,
) -> AsyncIterator[dict]:
    """Run the full multi-agent code generation pipeline.

    Yields status events compatible with the existing WebSocket handler:
      - analyzing, reading, generating, file_stream_start, code_token,
        file_stream_end, stream_end, execution_complete, error, etc.
    """
    yield {"status": "analyzing", "message": f"🧠 Intent Agent analyzing request..."}

    # ── Read project files ─────────────────────────────────────────────────
    from agent import read_all_project_files
    all_files = await read_all_project_files(db, project_id)
    file_tree_str = json.dumps(
        [{"name": os.path.basename(p), "path": p, "type": "file"} for p in sorted(all_files.keys())],
        indent=2,
    ) if all_files else '[{"name": "App.tsx", "path": "src/App.tsx", "type": "file"}]'

    # ── Context compression (Phase 4) ─────────────────────────────────────
    # Use semantic compression for Intent/Layout/Component agents (saves tokens).
    # The Code Agent still gets full file contents for accurate code generation.
    from context_compression import compress_context, get_compressed_project_context
    from brain_service import has_embeddings

    _has_embeds = False
    try:
        _has_embeds = await asyncio.to_thread(has_embeddings, db, project_id)
    except Exception as e:
        print(f"[pipeline] Embedding check failed: {e}")

    compressed_result = None
    compressed_context = ""
    if _has_embeds or all_files:
        try:
            compressed_result = await compress_context(
                db, project_id, prompt, all_files, token_budget=5000,
            )
            compressed_context = compressed_result["text"]
            _ratio = compressed_result.get("compression_ratio", 0)
            _tok = compressed_result.get("total_tokens", 0)
            _semantic = compressed_result.get("used_semantic", False)
            print(f"[pipeline] Context compressed: {_tok} tokens, "
                  f"{_ratio:.0%} reduction, semantic={_semantic}")
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[pipeline] Context compression failed, using truncated: {e}")

    # Fallback: truncated full context if compression failed
    if not compressed_context:
        project_context = ""
        if all_files:
            for path, content in sorted(all_files.items()):
                ext = path.rsplit('.', 1)[-1] if '.' in path else 'txt'
                lang = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css', 'jsx': 'jsx', 'js': 'javascript'}.get(ext, ext)
                project_context += f"\n--- {path} ---\n```{lang}\n{content}\n```\n"
        else:
            project_context = "\n(No existing files — this is a fresh project)\n"
        compressed_context = project_context[:16_000]

    # Full project context for the Code Agent (needs complete file content)
    # Hard cap at ~12 000 chars (~3 000 tokens) so we never blow past the provider TPM limit
    # on gpt-4o tier-1 accounts (30k TPM) — SURGEON_PROMPT + layout plan already consume ~10k.
    _CODE_CONTEXT_LIMIT = 12_000
    full_project_context = ""
    if all_files:
        for path, content in sorted(all_files.items()):
            ext = path.rsplit('.', 1)[-1] if '.' in path else 'txt'
            lang = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css', 'jsx': 'jsx', 'js': 'javascript'}.get(ext, ext)
            chunk = f"\n--- {path} ---\n```{lang}\n{content}\n```\n"
            if len(full_project_context) + len(chunk) > _CODE_CONTEXT_LIMIT:
                full_project_context += "\n... (remaining files omitted to stay within token budget)\n"
                break
            full_project_context += chunk
    else:
        full_project_context = "\n(No existing files — this is a fresh project)\n"

    # ── Load Design System (GPT Engine or legacy) ──────────────────────────
    _DESIGN_REF_LIMIT = 8_000  # ~2k tokens — hard cap to stay within TPM budget
    design_system = get_design_system_from_artifacts(db, project_id)
    if design_system:
        design_ref = build_design_context_for_agent(design_system)
    else:
        # Fall back to legacy design context
        try:
            from design_context import get_design_context, get_design_context_compact
            _design_keywords = ("design", "mockup", "visual", "style", "color", "layout",
                                "theme", "ui", "ux", "brand", "font", "typography",
                                "foundational", "foundation", "cdo")
            _use_full = any(kw in prompt.lower() for kw in _design_keywords)
            if _use_full:
                design_ref = await asyncio.to_thread(get_design_context, project_id)
            else:
                design_ref = ""
            if not design_ref:
                design_ref = await asyncio.to_thread(get_design_context_compact, project_id)
        except Exception as e:
            print(f"[pipeline] Design context fetch skipped: {e}")
            design_ref = ""
    # Universal cap — applies to both artifacts and legacy paths
    if design_ref and len(design_ref) > _DESIGN_REF_LIMIT:
        design_ref = design_ref[:_DESIGN_REF_LIMIT]

    # ── Load Brain context ─────────────────────────────────────────────────
    try:
        brain_context = await asyncio.to_thread(get_project_brain_context, db, project_id)
    except Exception as e:
        print(f"[pipeline] Brain context fetch skipped: {e}")
        brain_context = None

    # ── Stage 1: Intent Agent ──────────────────────────────────────────────
    intent = await run_intent_agent(
        prompt, compressed_context[:4000], brain_context, model_id, llm_kwargs,
    )
    if intent:
        yield {
            "status": "analyzing",
            "message": f"📋 Intent: {intent.get('intent_type', '?')} — {intent.get('scope', '?')}",
        }
        print(f"[IntentAgent] type={intent.get('intent_type')}, scope={intent.get('scope')}")
    else:
        print("[IntentAgent] Failed — proceeding with direct code gen")

    # ── Stage 2: Layout Agent (skip for small edits) ───────────────────────
    layout_plan = None
    _scope = (intent or {}).get("scope", "")
    _type = (intent or {}).get("intent_type", "")
    _needs_layout = _scope in ("full_app", "single_page") or _type == "initial_build"

    if intent and _needs_layout:
        yield {"status": "analyzing", "message": "📐 Layout Agent planning page structure..."}
        layout_plan = await run_layout_agent(intent, design_ref, model_id, llm_kwargs)
        if layout_plan:
            page_count = len(layout_plan.get("pages", []))
            print(f"[LayoutAgent] Planned {page_count} pages")
        else:
            print("[LayoutAgent] Failed — Code Agent will plan layout itself")

    # ── Stage 3: Component Agent (skip for bug fixes / small edits) ────────
    component_manifest = None
    if layout_plan and _scope != "style_only" and _type != "fix_bug":
        yield {"status": "analyzing", "message": "🧩 Component Agent defining components..."}
        component_manifest = await run_component_agent(layout_plan, design_ref, model_id, llm_kwargs)
        if component_manifest:
            comp_count = len(component_manifest.get("components", []))
            print(f"[ComponentAgent] Defined {comp_count} components")
        else:
            print("[ComponentAgent] Failed — Code Agent will define components itself")

    # ── Stage 4: Code Agent (SURGEON_PROMPT with enriched context) ─────────
    yield {"status": "generating", "message": "⚡ Code Agent generating files..."}

    enriched_prompt = _build_code_agent_prompt(
        prompt, intent, layout_plan, component_manifest,
        design_ref, file_tree_str, full_project_context,
    )

    # Stream code generation (reuse existing streaming state machine from agent.py)
    async for step in _stream_code_generation(
        enriched_prompt, model_id, llm_kwargs, images, project_id,
    ):
        yield step

    # ── Stage 5: Brain Population (after code gen) ─────────────────────────
    # This is done in main.py after execution_complete to avoid blocking the stream


async def _stream_code_generation(
    user_prompt: str,
    model_id: str,
    llm_kwargs: dict,
    images: list | None,
    project_id: str,
) -> AsyncIterator[dict]:
    """Stream code generation using SURGEON_PROMPT with the enriched prompt.

    Replicates the streaming state machine from agent.py but receives
    an already-enriched prompt from the pipeline.
    """
    from agent import _enforce_app_css_contract
    from design_context import get_design_contract_css

    # Build user content (with optional images)
    if images:
        user_content: list = []
        for data_url in images:
            user_content.append({"type": "image_url", "image_url": {"url": data_url}})
        user_content.append({"type": "text", "text": user_prompt})
    else:
        user_content = user_prompt

    current_file: str | None = None
    content_accumulator: str = ""
    streamed_files: dict = {}

    _cb_provider = llm_breaker.extract_provider(model_id)

    try:
        llm_breaker.check(_cb_provider)
        response = await litellm.acompletion(
            model=model_id,
            messages=[
                {"role": "system", "content": SURGEON_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=6000,
            stream=True,
            timeout=llm_breaker.default_timeout,
            **llm_kwargs,
        )

        full_response = ""
        inside_content = False
        escape_next = False
        last_processed_index = 0

        async for chunk in response:
            delta = chunk.choices[0].delta
            if not delta.content:
                continue

            token = delta.content
            full_response += token

            # Streaming state machine — identical to agent.py
            if inside_content:
                for char in token:
                    if escape_next:
                        escape_map = {'n': '\n', 't': '\t', '"': '"', '\\': '\\', '/': '/'}
                        actual_char = escape_map.get(char, char)
                        content_accumulator += actual_char
                        yield {"status": "code_token", "file": current_file, "token": actual_char}
                        escape_next = False
                    elif char == '\\':
                        escape_next = True
                    elif char == '"':
                        inside_content = False
                        streamed_files[current_file] = content_accumulator
                        yield {"status": "file_stream_end", "file": current_file, "content": content_accumulator}
                        last_processed_index = len(full_response)
                        current_file = None
                        content_accumulator = ""
                        break
                    else:
                        content_accumulator += char
                        yield {"status": "code_token", "file": current_file, "token": char}

            if not inside_content:
                unprocessed = full_response[last_processed_index:]
                content_marker_re = r'"content"\s*:\s*"'
                file_path_re = r'"(?:file_path|filePath|path|filename|name)"\s*:\s*"([^"]*)"'
                marker_match = re.search(content_marker_re, unprocessed)

                if marker_match:
                    marker_end_local = marker_match.end()
                    marker_start_global = last_processed_index + marker_match.start()

                    preceding = full_response[last_processed_index:marker_start_global]
                    file_paths = list(re.finditer(file_path_re, preceding))

                    if not file_paths:
                        broader = full_response[:marker_start_global]
                        file_paths = list(re.finditer(file_path_re, broader))

                    if file_paths:
                        candidate = file_paths[-1].group(1)
                        if candidate in streamed_files:
                            all_fps = [m.group(1) for m in file_paths if m.group(1) not in streamed_files]
                            current_file = all_fps[-1] if all_fps else None
                        else:
                            current_file = candidate
                    else:
                        current_file = None

                    if current_file is None:
                        last_processed_index += marker_end_local
                        continue

                    inside_content = True
                    escape_next = False
                    content_accumulator = ""
                    yield {"status": "file_stream_start", "file": current_file}
                    last_processed_index += marker_end_local

                    remaining_content = unprocessed[marker_end_local:]
                    for char in remaining_content:
                        if escape_next:
                            escape_map = {'n': '\n', 't': '\t', '"': '"', '\\': '\\', '/': '/'}
                            actual_char = escape_map.get(char, char)
                            content_accumulator += actual_char
                            yield {"status": "code_token", "file": current_file, "token": actual_char}
                            escape_next = False
                        elif char == '\\':
                            escape_next = True
                        elif char == '"':
                            inside_content = False
                            streamed_files[current_file] = content_accumulator
                            yield {"status": "file_stream_end", "file": current_file, "content": content_accumulator}
                            last_processed_index = len(full_response) - len(remaining_content) + remaining_content.find('"') + 1
                            current_file = None
                            content_accumulator = ""
                            break
                        else:
                            content_accumulator += char
                            yield {"status": "code_token", "file": current_file, "token": char}

        yield {"status": "stream_end"}
        llm_breaker.record_success(_cb_provider)

        # Parse final JSON
        edits = []
        try:
            clean = full_response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            json_str = _extract_json_block(clean)
            if json_str:
                clean = json_str
            parsed = json.loads(clean)

            if isinstance(parsed, dict) and "files" in parsed:
                files_list = parsed["files"]
            elif isinstance(parsed, list):
                files_list = parsed
            elif isinstance(parsed, dict):
                files_list = []
                for key in ("data", "output", "result", "edits"):
                    if key in parsed and isinstance(parsed[key], list):
                        files_list = parsed[key]
                        break
            else:
                files_list = []

            for entry in files_list:
                fp = (
                    entry.get("file_path") or entry.get("filePath")
                    or entry.get("path") or entry.get("filename")
                    or entry.get("name") or "src/App.tsx"
                )
                content = entry.get("content", "")
                if content:
                    edits.append({"file_path": fp, "action": "write", "content": content})
        except (json.JSONDecodeError, Exception) as e:
            print(f"[CodeAgent] JSON parse error: {e}")

        # Fallback to streamed files
        if not edits and streamed_files:
            print(f"[CodeAgent] Using {len(streamed_files)} streamed files as fallback")
            for fp, content in streamed_files.items():
                if content:
                    edits.append({"file_path": fp, "action": "write", "content": content})

        if edits:
            # Strip duplicate BrowserRouter from non-main.tsx files
            for _edit in edits:
                _fp = _edit.get("file_path", "")
                if _fp and not _fp.endswith("main.tsx"):
                    _content = _edit.get("content", "")
                    if "BrowserRouter" in _content:
                        # Remove BrowserRouter import
                        _content = re.sub(
                            r',?\s*BrowserRouter\s*,?',
                            lambda m: ', ' if m.group().startswith(',') and m.group().rstrip().endswith(',') else '',
                            _content
                        )
                        # Remove <BrowserRouter> and </BrowserRouter> wrapper tags
                        _content = re.sub(r'\s*<BrowserRouter>\s*\n?', '\n', _content)
                        _content = re.sub(r'\s*</BrowserRouter>\s*\n?', '\n', _content)
                        # Clean up any leftover empty imports like "import {  } from ..."
                        _content = re.sub(r"import\s*\{\s*\}\s*from\s*['\"]react-router-dom['\"]\s*;?\n?", '', _content)
                        if _content != _edit["content"]:
                            print(f"[Sanitizer] Stripped BrowserRouter from {_fp}")
                            _edit["content"] = _content

            # Design contract enforcement
            try:
                _contract = await asyncio.to_thread(get_design_contract_css, project_id)
                if _contract:
                    for _edit in edits:
                        _fp = _edit.get("file_path", "")
                        if _fp.endswith("App.css") or _fp in ("src/index.css", "index.css"):
                            _edit["content"] = _enforce_app_css_contract(_edit["content"], _contract)
                            break
            except Exception as _ce:
                print(f"[CodeAgent] Design contract enforcement skipped: {_ce}")

            # AST Patch Safety validation (Phase 5)
            try:
                from patch_engine import validate_edits_async
                # Pass existing files so safe zones and diffs can be computed
                _existing = streamed_files if streamed_files else None
                validation = await validate_edits_async(edits, _existing)

                if validation.rejected_edits:
                    print(f"[AST] Rejected {len(validation.rejected_edits)} file(s): "
                          f"{[e.get('file_path') for e in validation.rejected_edits]}")
                if validation.issues:
                    issue_summary = [i.to_dict() for i in validation.issues[:10]]
                    yield {
                        "status": "validation_warning",
                        "errors": issue_summary,
                        "message": (
                            f"⚠️ {validation.error_count} error(s), "
                            f"{validation.warning_count} warning(s) detected"
                        ),
                    }
                    print(f"[AST] {validation.error_count} errors, {validation.warning_count} warnings")

                # Use validated edits (rejected files excluded)
                if validation.valid_edits:
                    edits = validation.valid_edits
                # If ALL edits rejected, still try the originals as fallback
                # (Vite will catch real errors and trigger auto-fix)
            except Exception as _ve:
                print(f"[AST] Validation skipped (non-fatal): {_ve}")

            yield {"status": "execution_complete", "edits": edits}
        else:
            snippet = full_response[:800].replace("\n", " ") if full_response else "(empty)"
            print(f"[CodeAgent] No valid outputs. Snippet: {snippet}...")
            yield {"status": "error", "message": "No valid file outputs found in LLM response"}

    except CircuitOpenError as e:
        yield {"status": "error", "message": f"AI provider temporarily unavailable. Retry in {e.retry_after:.0f}s."}
    except Exception as e:
        print(f"[CodeAgent] Error: {e}")
        llm_breaker.record_failure(_cb_provider)
        if current_file and content_accumulator:
            streamed_files[current_file] = content_accumulator
        if streamed_files:
            edits = [{"file_path": fp, "action": "write", "content": c} for fp, c in streamed_files.items() if c]
            if edits:
                yield {"status": "stream_end"}
                yield {"status": "execution_complete", "edits": edits}
                return
        yield {"status": "error", "message": f"Code generation failed: {str(e)}"}


# ── Brain Population (called from main.py after execution_complete) ────────

def populate_brain_from_edits(
    db: Session,
    project_id: str,
    edits: list[dict],
    intent: dict | None = None,
    layout_plan: dict | None = None,
    component_manifest: dict | None = None,
) -> None:
    """Populate Project Brain tables from the agent pipeline results.

    Called after code generation completes and files are persisted.
    Non-blocking, non-fatal — failures are logged but don't break the flow.
    """
    try:
        # Record pages from layout plan
        if layout_plan:
            for page in layout_plan.get("pages", []):
                upsert_page(
                    db, project_id,
                    page_name=page.get("name", "Unknown"),
                    route=page.get("route", "/"),
                    description=page.get("purpose", page.get("description")),
                    layout_json={"sections": page.get("sections", [])},
                    status=PageStatus.implemented,
                )

        # Record components from manifest or edits
        if component_manifest:
            for comp in component_manifest.get("components", []):
                fp = comp.get("file_path", "")
                if fp:
                    upsert_component(
                        db, project_id,
                        component_name=comp.get("name", os.path.basename(fp)),
                        file_path=fp,
                        props_schema_json=comp.get("props"),
                        dependencies_json=comp.get("imports"),
                        description=comp.get("purpose"),
                    )
        else:
            # Infer components from generated files
            for edit in edits:
                fp = edit.get("file_path", "")
                if fp.endswith(".tsx") and "/components/" in fp:
                    name = os.path.basename(fp).replace(".tsx", "")
                    upsert_component(
                        db, project_id,
                        component_name=name,
                        file_path=fp,
                    )

        # Record the generation decision
        add_decision(
            db, project_id,
            decision_type=DecisionType.architecture,
            decision_json={
                "intent": intent,
                "files_generated": [e.get("file_path") for e in edits],
                "layout_pages": len(layout_plan.get("pages", [])) if layout_plan else 0,
                "components_defined": len(component_manifest.get("components", [])) if component_manifest else 0,
            },
            rationale=f"Multi-agent pipeline: {(intent or {}).get('intent_type', 'code')} — {(intent or {}).get('description', '')}",
            agent_role="pipeline",
        )

        db.commit()
        print(f"[brain] Populated brain for project {project_id}")

        # ── Auto-embed new/modified files (Phase 4) ───────────────────────
        try:
            import asyncio
            from embedding_service import embed_and_store_file

            async def _embed_edits():
                for edit in edits:
                    fp = edit.get("file_path", "")
                    content = edit.get("content", "")
                    if fp and content:
                        await embed_and_store_file(db, project_id, fp, content)
                db.commit()

            # Run embedding in background — non-blocking
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_embed_edits())
            else:
                asyncio.run(_embed_edits())
            print(f"[brain] Queued embedding for {len(edits)} files")
        except Exception as _embed_err:
            print(f"[brain] Auto-embed skipped (non-fatal): {_embed_err}")
    except Exception as e:
        print(f"[brain] Population failed (non-fatal): {e}")
        try:
            db.rollback()
        except Exception:
            pass
