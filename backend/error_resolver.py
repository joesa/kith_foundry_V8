"""
Auto Error Resolver — silently captures and repairs errors from the user's sandbox app.

Receives error context (browser console errors, Vite build errors),
reads the relevant source files, calls the AI with a targeted FIX_PROMPT,
and returns corrected files for the sandbox to apply.
"""
import json
import re
import time
import asyncio
from datetime import datetime

import litellm

from prompts import FIX_PROMPT
from redis_state import get_fix_state, save_fix_state, delete_fix_state

litellm.drop_params = True

# ── Rate limiting / loop prevention ──────────────────────────────────────────
# Per-project fix state is now stored in Redis so all Gunicorn workers share it.


def reset_fix_cycle(project_id: str):
    """Call after a user-initiated edit to reset the fix attempt counter."""
    delete_fix_state(project_id)


def can_attempt_fix(project_id: str, error_hash: str) -> tuple[bool, str]:
    """Check if we should attempt an auto-fix. Returns (allowed, reason)."""
    state = get_fix_state(project_id)

    MAX_ATTEMPTS = 3
    COOLDOWN_SECONDS = 10.0

    # Max attempts per edit cycle
    if state["attempt_count"] >= MAX_ATTEMPTS:
        return False, f"Max auto-fix attempts reached ({MAX_ATTEMPTS})"

    # Cooldown between attempts
    elapsed = time.time() - state["last_attempt_at"]
    if elapsed < COOLDOWN_SECONDS:
        return False, f"Cooldown ({COOLDOWN_SECONDS - elapsed:.0f}s remaining)"

    # Same error repeating = likely unfixable
    if state["last_error_hash"] == error_hash and state["attempt_count"] > 0:
        return False, "Same error repeated — likely unfixable by auto-repair"

    return True, "ok"


def _hash_errors(errors: list[dict]) -> str:
    """Create a simple hash of error messages for dedup."""
    key = "|".join(sorted(e.get("message", "") for e in errors))
    return str(hash(key))


# ── AST helpers (Steps 2 & 3) ────────────────────────────────────────────────

def _scan_ast_errors(contents: dict[str, str]) -> dict[str, list[dict]]:
    """Run tree-sitter validation on all source files.

    Returns {file_path: [issue_dicts]} for files that have parse errors.
    Only covers .tsx/.ts/.jsx/.js/.css — other extensions are skipped.
    """
    from patch_engine import validate_file
    results: dict[str, list[dict]] = {}
    for fp, content in contents.items():
        if not content:
            continue
        dot = fp.rfind(".")
        ext = fp[dot:] if dot >= 0 else ""
        if ext not in (".tsx", ".ts", ".jsx", ".js", ".css"):
            continue
        issues = validate_file(fp, content)
        if issues:
            results[fp] = [i.to_dict() for i in issues]
    return results


def _select_relevant_files(
    contents: dict[str, str],
    ast_errors: dict[str, list[dict]],
    runtime_errors: list[dict],
) -> set[str]:
    """Choose the minimal set of files the LLM needs to see.

    Includes: files with AST errors, files mentioned in runtime error
    messages/stacks, and one-hop importers of broken files.
    Falls back to all files if nothing is identified.
    """
    broken: set[str] = set(ast_errors.keys())

    # Files mentioned in runtime error messages or stacks
    for err in runtime_errors:
        msg = err.get("message", "") + " " + err.get("stack", "")
        for fp in contents:
            name = fp.split("/")[-1]
            if name in msg or fp in msg:
                broken.add(fp)

    # One-hop importers of broken files (they may need import fixes)
    import_re = re.compile(
        r"""(?:import\s+[^'"]+from\s+|require\s*\(\s*)['\"]([ ^'\"]+)['\"]"""
    )
    broken_bases = {fp.split("/")[-1].rsplit(".", 1)[0] for fp in broken}
    for fp, content in contents.items():
        if fp in broken:
            continue
        for m in import_re.finditer(content):
            dep = m.group(1).split("/")[-1]
            if dep in broken_bases or any(dep in b for b in broken):
                broken.add(fp)
                break

    # Always include entry-point anchors so the LLM can see the app structure
    for fp in contents:
        if fp.split("/")[-1] in ("App.tsx", "App.jsx", "main.tsx", "main.jsx"):
            broken.add(fp)

    # Fallback: nothing identified → send everything (same as old behaviour)
    return broken if broken else set(contents.keys())


# ── Step 4: Deterministic (rule-based) fixes ─────────────────────────────────

# Maximum brace-imbalance we'll attempt to fix without LLM help.
# Larger deltas mean the file is too malformed for a simple append.
_MAX_BRACE_DELTA = 3


def _fix_brace_mismatch_tsx(fp: str, content: str, issues: list[dict]) -> str | None:
    """Append missing closing braces if imbalance is small (≤ _MAX_BRACE_DELTA)."""
    brace_issues = [i for i in issues if i.get("node_type") == "brace_mismatch"]
    if not brace_issues:
        return None

    opens = content.count("{")
    closes = content.count("}")
    delta = opens - closes
    if 1 <= delta <= _MAX_BRACE_DELTA:
        fixed = content.rstrip() + "\n" + "}" * delta + "\n"
        print(f"[rule-fix] {fp}: appended {delta} closing brace(s)")
        return fixed
    return None


def _fix_brace_mismatch_css(fp: str, content: str, issues: list[dict]) -> str | None:
    """Append missing closing braces for CSS files."""
    css_issues = [i for i in issues if i.get("node_type") == "css_brace_mismatch"]
    if not css_issues:
        return None

    opens = content.count("{")
    closes = content.count("}")
    delta = opens - closes
    if 1 <= delta <= _MAX_BRACE_DELTA:
        fixed = content.rstrip() + "\n" + "}" * delta + "\n"
        print(f"[rule-fix] {fp}: appended {delta} CSS closing brace(s)")
        return fixed
    return None


def _fix_empty_default_export(fp: str, content: str, issues: list[dict]) -> str | None:
    """Insert 'return null;' into an empty default export function body."""
    empty_issues = [i for i in issues if i.get("node_type") == "empty_export"]
    if not empty_issues:
        return None

    # Find the empty function body pattern and inject return null
    fixed = re.sub(
        r'(export\s+default\s+function\s+\w+\s*\([^)]*\)\s*\{)(\s*\})',
        r'\1\n  return null;\n\2',
        content,
        flags=re.DOTALL,
    )
    if fixed != content:
        print(f"[rule-fix] {fp}: injected 'return null' into empty default export")
        return fixed
    return None


def _fix_missing_semicolons(fp: str, content: str, issues: list[dict]) -> str | None:
    """Insert missing semicolons at exact MISSING node locations reported by tree-sitter."""
    missing_semi = [
        i for i in issues
        if i.get("node_type") == "MISSING" and ";" in i.get("message", "")
    ]
    if not missing_semi:
        return None

    lines = content.split("\n")
    # Process in reverse line order so earlier insertions don't shift later indices
    for issue in sorted(missing_semi, key=lambda i: i["line"], reverse=True):
        line_idx = issue["line"]
        if 0 <= line_idx < len(lines):
            lines[line_idx] = lines[line_idx].rstrip() + ";"
    fixed = "\n".join(lines)
    if fixed != content:
        print(f"[rule-fix] {fp}: inserted {len(missing_semi)} missing semicolon(s)")
        return fixed
    return None


# Heuristic: if the last non-blank line looks like a truncated expression
# (no closing brace/paren and file ends mid-statement), mark it as truncated.
_TRUNCATION_SIGNATURES = (
    re.compile(r'\bconst\s+\w+\s*=\s*\{?\s*$', re.MULTILINE),
    re.compile(r'\breturn\s*\($', re.MULTILINE),
    re.compile(r',\s*$'),  # trailing comma — common in truncated JSX
)


def _is_likely_truncated(content: str) -> bool:
    """Detect whether a file appears to be a streaming truncation victim."""
    stripped = content.rstrip()
    if not stripped:
        return False
    last_line = stripped.split("\n")[-1].strip()
    # File ends without closing the component function
    if not (last_line.endswith("}") or last_line.endswith(";") or last_line == ""):
        return True
    for sig in _TRUNCATION_SIGNATURES:
        if sig.search(stripped[-500:]):
            return True
    return False


def _apply_deterministic_fixes(
    contents: dict[str, str],
    ast_errors: dict[str, list[dict]],
) -> tuple[dict[str, str], set[str], list[str]]:
    """Attempt rule-based fixes on files with AST errors.

    Returns:
        fixed_contents  — updated content map (only changed files)
        still_broken    — file paths that still have AST errors after rule fixes
        fix_log         — human-readable summary of what was done
    """
    from patch_engine import validate_file

    fixed_contents: dict[str, str] = {}
    still_broken: set[str] = set()
    fix_log: list[str] = []

    for fp, issues in ast_errors.items():
        content = contents.get(fp, "")
        if not content:
            still_broken.add(fp)
            continue

        dot = fp.rfind(".")
        ext = fp[dot:] if dot >= 0 else ""
        candidate = content

        # Detect truncation first — announce it but don't try to fix;
        # mark for LLM regeneration with a clear label.
        if _is_likely_truncated(candidate):
            fix_log.append(f"{fp}: likely streaming truncation — needs LLM regen")
            still_broken.add(fp)
            continue

        # Try each rule in priority order; a rule returns None if it can't help.
        for rule in (_fix_empty_default_export, _fix_missing_semicolons,
                     _fix_brace_mismatch_tsx, _fix_brace_mismatch_css):
            result = rule(fp, candidate, issues)
            if result is not None:
                candidate = result

        if candidate == content:
            # No rule fired
            still_broken.add(fp)
            continue

        # Re-validate — only keep the fix if it actually resolved the errors
        remaining = validate_file(fp, candidate)
        error_issues = [i for i in remaining if i.severity.value == "error"]
        if not error_issues:
            fixed_contents[fp] = candidate
            fix_log.append(f"{fp}: rule-based fix succeeded (0 errors remaining)")
        else:
            # Fix didn't fully resolve — hand off to LLM
            still_broken.add(fp)
            fix_log.append(
                f"{fp}: rule fix partial ({len(error_issues)} errors remain) — escalating to LLM"
            )

    return fixed_contents, still_broken, fix_log


# ── AI Repair ────────────────────────────────────────────────────────────────

async def attempt_fix(
    project_id: str,
    errors: list[dict],
    user_id: str | None = None,
) -> dict | None:
    """
    Attempt to auto-fix errors using the AI.

    Args:
        project_id: The project ID
        errors: List of error dicts with 'source', 'message', 'stack' keys
        user_id: For model resolution

    Returns:
        dict with 'files' list if fix generated, None if skipped/failed
    """
    from models import SessionLocal, File

    error_hash = _hash_errors(errors)
    allowed, reason = can_attempt_fix(project_id, error_hash)
    if not allowed:
        print(f"[auto-fix] Skipped: {reason}")
        return None

    state = get_fix_state(project_id)
    state["attempt_count"] += 1
    state["last_attempt_at"] = time.time()
    state["last_error_hash"] = error_hash
    save_fix_state(project_id, state)

    print(f"[auto-fix] Attempt {state['attempt_count']} for project {project_id[:8]}...")

    db = SessionLocal()
    try:
        # Read current project files (paths from DB, content from Storage)
        stored_files = db.query(File).filter(File.project_id == project_id).all()

        if not stored_files:
            print("[auto-fix] No files in project — skipping")
            return None

        # Download content from Supabase Storage (falls back to DB for legacy rows)
        from storage_service import download_project_files_sync
        file_paths = [f.file_path for f in stored_files]
        db_fallback = {f.file_path: f.content for f in stored_files if f.content}
        contents = download_project_files_sync(project_id, file_paths, db_fallback=db_fallback)

        # ── Step 2: AST scan — precise line/col errors before any LLM call ────
        ast_errors = _scan_ast_errors(contents)
        if ast_errors:
            print(f"[auto-fix] AST errors in {len(ast_errors)} file(s): {list(ast_errors.keys())}")

        # ── Step 4: Rule-based deterministic fixes (no LLM needed) ────────────
        rule_fixed: dict[str, str] = {}
        if ast_errors:
            rule_fixed, still_broken_after_rules, fix_log = _apply_deterministic_fixes(
                contents, ast_errors
            )
            for msg in fix_log:
                print(f"[rule-fix] {msg}")

            if rule_fixed:
                # Merge rule fixes into our working content map
                contents = {**contents, **rule_fixed}
                # Re-scan to update ast_errors for the remaining broken files only
                ast_errors = _scan_ast_errors({fp: contents[fp] for fp in still_broken_after_rules})

            # If all AST errors were resolved deterministically, skip the LLM
            if not ast_errors and not errors:
                print(f"[auto-fix] All {len(rule_fixed)} fix(es) resolved by rules — skipping LLM")
                return {
                    "files": [
                        {"file_path": fp, "content": content}
                        for fp, content in rule_fixed.items()
                    ],
                    "source": "rule-based",
                }

            if rule_fixed and not ast_errors:
                print(
                    f"[auto-fix] Rules fixed {len(rule_fixed)} file(s); "
                    f"runtime errors remain — continuing to LLM for those"
                )

        # ── Step 3: Focused file selection — broken files + importers only ────
        relevant_files = _select_relevant_files(contents, ast_errors, errors)
        print(f"[auto-fix] Context: {len(relevant_files)}/{len(contents)} files selected")

        lang_map = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css', 'jsx': 'jsx', 'js': 'javascript'}
        file_context = ""
        for fp in sorted(relevant_files):
            content = contents.get(fp, "")
            if not content:
                continue
            ext = fp.rsplit('.', 1)[-1] if '.' in fp else 'txt'
            lang = lang_map.get(ext, ext)
            file_context += f"\n--- {fp} ---\n```{lang}\n{content}\n```\n"

        # AST analysis block — exact line/col errors are far more useful than
        # raw Vite output for helping the LLM locate the root cause
        ast_summary = ""
        if ast_errors:
            ast_summary = "\n**AST Analysis (tree-sitter — exact error locations):**\n"
            for fp, issues in ast_errors.items():
                ast_summary += f"  {fp}:\n"
                for issue in issues[:5]:
                    ast_summary += (
                        f"    line {issue['line']}, col {issue['col']} "
                        f"[{issue['severity'].upper()}]: {issue['message']}\n"
                    )

        # Runtime errors from Vite / browser
        error_text = "\n".join(
            f"[{e.get('source', 'unknown')}] {e.get('message', 'Unknown error')}"
            + (f"\n  Stack: {e['stack'][:300]}" if e.get('stack') else "")
            for e in errors
        )

        user_prompt = f"""The following errors occurred in the user's app:
{ast_summary}
**Runtime errors:**
{error_text}

**Relevant project files ({len(relevant_files)} of {len(contents)} total):**
{file_context}

Fix ONLY the files needed to resolve these errors. If the AST analysis shows exact error locations, fix those specific lines. Do NOT change anything unrelated. Output JSON only."""

        # Resolve model
        model_config = _resolve_model(user_id, db)
        if model_config.get("error"):
            raise HTTPException(status_code=400, detail=model_config["error"])

        call_kwargs = {
            "model": model_config["model"],
            "messages": [
                {"role": "system", "content": FIX_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,  # Low temp for precise fixes
            "max_tokens": 8000,
        }
        if model_config.get("api_key"):
            call_kwargs["api_key"] = model_config["api_key"]
        if model_config.get("api_base"):
            call_kwargs["api_base"] = model_config["api_base"]

        print(f"[auto-fix] Using {model_config['model']} via {model_config['provider_name']}")

        resp = await litellm.acompletion(**call_kwargs)
        text = resp.choices[0].message.content.strip()

        # Parse JSON response
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        match = re.search(r'\{[\s\S]*\}', text)
        result = json.loads(match.group() if match else text)

        files = result.get("files", [])
        if not files:
            print("[auto-fix] AI returned no files to fix")
            return None

        # ── Step 1: Validate fix output through AST before sending to sandbox ─
        try:
            from patch_engine import validate_edits
            fix_edits = [
                {"file_path": f["file_path"], "content": f.get("content", ""), "action": "write"}
                for f in files
            ]
            validation = validate_edits(fix_edits, contents)

            if validation.rejected_edits:
                rejected_paths = [e.get("file_path") for e in validation.rejected_edits]
                print(f"[auto-fix] AST rejected {len(validation.rejected_edits)} fix(es) with new errors: {rejected_paths}")
                valid_paths = {e.get("file_path") for e in validation.valid_edits}
                files = [f for f in files if f["file_path"] in valid_paths]
                if not files:
                    print("[auto-fix] All LLM fixes introduced new AST errors — aborting")
                    return None
                result = {**result, "files": files}

            if validation.issues:
                err_c = sum(1 for i in validation.issues if i.severity.value == "error")
                warn_c = sum(1 for i in validation.issues if i.severity.value == "warning")
                print(f"[auto-fix] Fix output validation: {err_c} errors, {warn_c} warnings")
        except Exception as _ve:
            print(f"[auto-fix] Fix output validation skipped (non-fatal): {_ve}")

        print(f"[auto-fix] Returning {len(files)} validated fix(es)")
        return result

    except Exception as e:
        print(f"[auto-fix] Error: {e}")
        return None
    finally:
        db.close()


def _resolve_model(user_id: str | None, db=None) -> dict:
    """Resolve model for auto-fix (reuses code_gen routing)."""
    if user_id:
        from model_resolver import resolve_model_for_task
        return resolve_model_for_task(user_id, "code_gen", db=db)
    return {
        "model": "anthropic/claude-sonnet-4-20250514",
        "api_key": None,
        "api_base": None,
        "provider_name": "Default",
    }
