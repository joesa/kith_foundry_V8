"""
Auto Error Resolver — silently captures and repairs errors from the user's sandbox app.

Receives error context (browser console errors, Vite build errors),
reads the relevant source files, calls the AI with a targeted FIX_PROMPT,
and returns corrected files for the sandbox to apply.
"""
import json
import time
import asyncio
from datetime import datetime

import litellm

from prompts import FIX_PROMPT

litellm.drop_params = True

# ── Rate limiting / loop prevention ──────────────────────────────────────────

# Per-project state to prevent infinite fix loops
_fix_state: dict[str, dict] = {}


def _get_state(project_id: str) -> dict:
    if project_id not in _fix_state:
        _fix_state[project_id] = {
            "attempt_count": 0,
            "last_attempt_at": 0.0,
            "last_error_hash": None,
            "cycle_start": 0.0,
        }
    return _fix_state[project_id]


def reset_fix_cycle(project_id: str):
    """Call after a user-initiated edit to reset the fix attempt counter."""
    _fix_state.pop(project_id, None)


def can_attempt_fix(project_id: str, error_hash: str) -> tuple[bool, str]:
    """Check if we should attempt an auto-fix. Returns (allowed, reason)."""
    state = _get_state(project_id)

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

    state = _get_state(project_id)
    state["attempt_count"] += 1
    state["last_attempt_at"] = time.time()
    state["last_error_hash"] = error_hash

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

        # Build file context
        file_context = ""
        for f in sorted(stored_files, key=lambda x: x.file_path):
            ext = f.file_path.rsplit('.', 1)[-1] if '.' in f.file_path else 'txt'
            lang_map = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css', 'jsx': 'jsx', 'js': 'javascript'}
            lang = lang_map.get(ext, ext)
            file_context += f"\n--- {f.file_path} ---\n```{lang}\n{contents.get(f.file_path, '')}\n```\n"

        # Build error context
        error_text = "\n".join(
            f"[{e.get('source', 'unknown')}] {e.get('message', 'Unknown error')}"
            + (f"\n  Stack: {e['stack'][:300]}" if e.get('stack') else "")
            for e in errors
        )

        user_prompt = f"""The following errors occurred in the user's app:

{error_text}

Current project files:
{file_context}

Fix ONLY the files needed to resolve these errors. Output JSON only."""

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

        import re
        match = re.search(r'\{[\s\S]*\}', text)
        result = json.loads(match.group() if match else text)

        files = result.get("files", [])
        if not files:
            print("[auto-fix] AI returned no files to fix")
            return None

        print(f"[auto-fix] AI generated fixes for {len(files)} file(s)")
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
