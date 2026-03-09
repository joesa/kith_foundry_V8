import json
import re
from models import Message, File
from prompts import ARCHITECT_PROMPT, SURGEON_PROMPT
import asyncio
from design_context import get_design_context, get_design_context_compact, get_design_contract_css
import litellm
import os

# Ensure litellm doesn't drop requests if local models are passed
litellm.drop_params = True


def _enforce_app_css_contract(css_content: str, contract_css: str) -> str:
    """Inject/overwrite :root CSS tokens from the design contract.

    Same concept as _transplant_root_vars in the mockup pipeline:
    deterministic enforcement that runs after the LLM has generated its output.
    Inserts the locked brand tokens at the start of the existing :root block,
    or prepends a new :root block when none exists yet.
    """
    prop_lines = re.findall(r'(--[^:]+:\s*[^;]+;)', contract_css)
    if not prop_lines:
        return css_content
    injection = (
        "\n  /* ═══ DESIGN CONTRACT — brand tokens locked by Kith Foundry ═══ */\n  "
        + "\n  ".join(p.strip() for p in prop_lines)
        + "\n"
    )
    if re.search(r':root\s*\{', css_content):
        return re.sub(r':root\s*\{', f':root {{{injection}', css_content, count=1)
    else:
        return f":root {{{injection}}}\n\n" + css_content


def _extract_json_block(text: str) -> str | None:
    """Find the outermost JSON object or array in text using bracket depth tracking."""
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


def collect_file_paths(tree_nodes: list, paths: list = None) -> list:
    """Recursively collect all file paths from the tree structure."""
    if paths is None:
        paths = []
    for node in tree_nodes:
        if node.get("type") == "file":
            paths.append(node["path"])
        elif node.get("children"):
            collect_file_paths(node["children"], paths)
    return paths


async def read_all_project_files(db, project_id: str) -> dict:
    """Read the content of all source files from Supabase Storage."""
    import storage_service

    source_extensions = {'.tsx', '.ts', '.jsx', '.js', '.css', '.json'}
    skip_files = {'package.json', 'tsconfig.json', 'vite.config.ts', 'package-lock.json'}

    stored_files = db.query(File).filter(File.project_id == project_id).all()

    # Filter to source files only (path-based filter, no content needed yet)
    candidate_paths = []
    db_fallback = {}
    for f in stored_files:
        ext = os.path.splitext(f.file_path)[1]
        basename = os.path.basename(f.file_path)
        if ext in source_extensions and basename not in skip_files:
            candidate_paths.append(f.file_path)
            if f.content:
                db_fallback[f.file_path] = f.content  # legacy content fallback

    if not candidate_paths:
        return {}

    # Download content from Supabase Storage (falls back to DB for legacy rows)
    contents = await storage_service.download_project_files(
        project_id, candidate_paths, db_fallback=db_fallback
    )

    # Only return files that actually have content
    return {fp: content for fp, content in contents.items() if content}


async def process_user_request(prompt: str, project_id: int, model_id: str, db=None, images: list = None, user_id: str = None):
    """
    Executes a streaming LLM call to generate multi-file modifications.
    Parses the JSON in-flight to stream individual file contents to the editor.
    Reads project state from the database — no sandbox needed.
    """
    # Resolve model via user's routing config if no specific model requested
    api_key = None
    api_base = None
    if user_id and (not model_id or model_id == "default"):
        from model_resolver import resolve_model_for_task
        mc = resolve_model_for_task(user_id, "code_gen")
        if mc.get("error"):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=mc["error"])
        model_id = mc["model"]
        api_key = mc.get("api_key")
        api_base = mc.get("api_base")
        print(f"\U0001f4bb Code Gen using: {model_id} via {mc['provider_name']}")

    yield {"status": "analyzing", "message": f"Analyzing request using {model_id}..."}
    
    # 1. Read the FULL project state from DB
    all_files = {}
    file_tree_str = ""
    
    if db:
        yield {"status": "reading", "message": "Reading current project files..."}
        all_files = await read_all_project_files(db, project_id)
        # Build a simple tree from the file paths for context
        tree_nodes = [{"name": os.path.basename(p), "path": p, "type": "file"} for p in sorted(all_files.keys())]
        file_tree_str = json.dumps(tree_nodes, indent=2)
    
    if not file_tree_str:
        file_tree_str = '[{"name": "App.tsx", "path": "src/App.tsx", "type": "file"}]'
    
    # 2. Build the full project context string
    project_context = ""
    if all_files:
        for path, content in sorted(all_files.items()):
            ext = path.rsplit('.', 1)[-1] if '.' in path else 'txt'
            lang = {'tsx': 'tsx', 'ts': 'typescript', 'css': 'css', 'jsx': 'jsx', 'js': 'javascript'}.get(ext, ext)
            project_context += f"\n--- {path} ---\n```{lang}\n{content}\n```\n"
    else:
        project_context = "\n(No existing files — this is a fresh project)\n"
    
    # 2b. Fetch design context (CDO design system + screen inventory)
    # Use compact by default to keep prompt within model context limits.
    # Only pull full HTML mockups when the prompt explicitly references
    # design / visual / mockup work — those tokens easily exceed 10k chars.
    design_ref = ""
    try:
        _design_keywords = ("design", "mockup", "visual", "style", "color", "layout",
                            "theme", "ui", "ux", "brand", "font", "typography",
                            "foundational", "foundation", "cdo")
        _use_full = any(kw in prompt.lower() for kw in _design_keywords)
        if _use_full:
            design_ref = await asyncio.to_thread(get_design_context, project_id)
        if not design_ref:
            design_ref = await asyncio.to_thread(get_design_context_compact, project_id)
        # Safety cap: if the combined prompt would be huge, fall back to compact
        if design_ref and len(design_ref) > 12_000:
            compact = await asyncio.to_thread(get_design_context_compact, project_id)
            design_ref = compact or design_ref[:12_000]
    except Exception as e:
        print(f"Design context fetch skipped: {e}")

    # 3. Construct LLM payload
    system_prompt = SURGEON_PROMPT
    user_prompt = f"""User Request: {prompt}
{design_ref}
Current project file tree:
```json
{file_tree_str}
```

Current project files:{project_context}

Output a JSON object with a "files" array. Each entry has "file_path" and "content". Output ONLY valid JSON."""

    yield {"status": "generating", "message": "Generating code..."}

    # Pre-initialize streaming state so the except block can always reference them
    # even if an exception fires before we reach the state machine setup below.
    current_file: str | None = None
    content_accumulator: str = ""
    streamed_files: dict = {}
    edits: list = []

    try:
        # 4. Look up configured provider credentials
        llm_kwargs = {}
        effective_model = model_id
        try:
            from provider_api import get_db, decrypt_key
            from models import ProviderKey
            db = get_db()
            # Find the default active provider, or first active one
            provider_key = db.query(ProviderKey).filter(
                ProviderKey.is_active == True,
                ProviderKey.is_default == True
            ).first()
            if not provider_key:
                provider_key = db.query(ProviderKey).filter(
                    ProviderKey.is_active == True
                ).first()
            if provider_key:
                api_key = decrypt_key(provider_key.api_key_encrypted)
                llm_kwargs["api_key"] = api_key
                if provider_key.base_url:
                    llm_kwargs["api_base"] = provider_key.base_url
                
                # Auto-prefix model ID for litellm routing based on provider type
                ptype = provider_key.provider.lower()
                if ptype == "lm_studio":
                    # LM Studio expects /v1/chat/completions; litellm appends /chat/completions
                    # so we need api_base to end with /v1
                    base = llm_kwargs.get("api_base", "http://localhost:1234")
                    if not base.rstrip("/").endswith("/v1"):
                        llm_kwargs["api_base"] = base.rstrip("/") + "/v1"
                    if not effective_model.startswith("openai/"):
                        effective_model = f"openai/{effective_model}"
                elif ptype in ("openai_compatible", "azure_openai"):
                    if not effective_model.startswith("openai/"):
                        effective_model = f"openai/{effective_model}"
                elif ptype == "ollama":
                    if not effective_model.startswith("ollama/"):
                        effective_model = f"ollama/{effective_model}"
                elif ptype == "anthropic":
                    if not effective_model.startswith("anthropic/"):
                        effective_model = f"anthropic/{effective_model}"
                elif ptype == "google_ai":
                    if not effective_model.startswith("gemini/"):
                        effective_model = f"gemini/{effective_model}"
                elif ptype == "cohere":
                    if not effective_model.startswith("cohere/"):
                        effective_model = f"cohere/{effective_model}"

                # Update last_used_at
                from datetime import datetime
                provider_key.last_used_at = datetime.utcnow()
                db.commit()
                print(f"🔑 Using provider: {provider_key.name} ({ptype}), model: {effective_model}, base: {provider_key.base_url}")
            db.close()
        except Exception as e:
            print(f"Provider lookup failed, falling back to env vars: {e}")

        print(f"🚀 LiteLLM call: model={effective_model}, api_base={llm_kwargs.get('api_base', 'default')}")

        # 5. Call LiteLLM with streaming
        # Build user message — include images as vision blocks if provided
        if images:
            user_content: list = []
            for data_url in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url}
                })
            if user_prompt:
                user_content.append({"type": "text", "text": user_prompt})
        else:
            user_content = user_prompt

        response = await litellm.acompletion(
            model=effective_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            stream=True,
            **llm_kwargs
        )
        
        # 5. Stream and parse in-flight using a state machine
        full_response = ""
        
        # State machine for in-flight JSON parsing
        current_file = None        # The file_path we're currently inside
        inside_content = False     # Are we inside a "content" string value?
        content_accumulator = ""   # Buffer for the current file's content
        escape_next = False        # Next char is escaped
        streamed_files = {}        # Fallback: files captured during streaming
        last_processed_index = 0   # Track how far in full_response we've searched for markers
        
        async for chunk in response:
            delta = chunk.choices[0].delta
            if not delta.content:
                continue
                
            token = delta.content
            full_response += token
            
            # Process token chars if we are actively reading a file's content
            if inside_content:
                for char in token:
                    if escape_next:
                        # Handle escape sequences
                        escape_map = {'n': '\n', 't': '\t', '"': '"', '\\': '\\', '/': '/'}
                        actual_char = escape_map.get(char, char)
                        content_accumulator += actual_char
                        yield {"status": "code_token", "file": current_file, "token": actual_char}
                        escape_next = False
                    elif char == '\\':
                        escape_next = True
                    elif char == '"':
                        # End of content string — file is complete
                        inside_content = False
                        streamed_files[current_file] = content_accumulator
                        yield {"status": "file_stream_end", "file": current_file, "content": content_accumulator}
                        # Advance last_processed_index past this file's content so we don't re-trigger
                        last_processed_index = len(full_response)
                        current_file = None
                        content_accumulator = ""
                        break # Stop processing this token's chars, wait for next file marker
                    else:
                        content_accumulator += char
                        yield {"status": "code_token", "file": current_file, "token": char}
            
            # If we are NOT inside content, search the unprocessed portion of full_response for the next file
            if not inside_content:
                unprocessed = full_response[last_processed_index:]
                
                content_marker_re = r'"content"\s*:\s*"'
                # Support common path keys: file_path, filePath, path, filename, name
                file_path_re = r'"(?:file_path|filePath|path|filename|name)"\s*:\s*"([^"]*)"'
                
                # Search for the *first* content marker in the unprocessed text
                marker_match = re.search(content_marker_re, unprocessed)
                
                if marker_match:
                    marker_end_local = marker_match.end()
                    marker_start_global = last_processed_index + marker_match.start()
                    
                    # Look for the file_path preceding this content marker.
                    # First try the window since last_processed_index; if that
                    # fails, widen to the entire response up to this point
                    # (handles cases where tokenisation splits the JSON object
                    # across chunk boundaries).
                    preceding = full_response[last_processed_index:marker_start_global]
                    file_paths = list(re.finditer(file_path_re, preceding))
                    
                    if not file_paths:
                        broader = full_response[:marker_start_global]
                        file_paths = list(re.finditer(file_path_re, broader))

                    if file_paths:
                        candidate = file_paths[-1].group(1)
                        # Guard against re-using a file_path that was already
                        # fully streamed (its content marker already consumed).
                        if candidate in streamed_files:
                            all_fps = [m.group(1) for m in file_paths if m.group(1) not in streamed_files]
                            current_file = all_fps[-1] if all_fps else None
                        else:
                            current_file = candidate
                    else:
                        current_file = None

                    if current_file is None:
                        # No valid file_path found — skip this content block
                        last_processed_index += marker_end_local
                        continue
                    
                    inside_content = True
                    escape_next = False
                    content_accumulator = ""
                    
                    yield {"status": "file_stream_start", "file": current_file}
                    
                    # Advance last_processed_index to just after the `"content": "` marker
                    last_processed_index += marker_end_local
                    
                    # The rest of the `unprocessed` text (after the marker) is actual file content!
                    remaining_content = unprocessed[marker_end_local:]
                    
                    # Feed the remaining chars directly into the state machine logic
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
                            # Update last_processed_index to where we found the closing quote
                            # (This requires calculating the exact index, but simply setting it to len(full_response) works since token ends here or shortly after)
                            last_processed_index = len(full_response) - len(remaining_content) + remaining_content.find('"') + 1
                            current_file = None
                            content_accumulator = ""
                            break
                        else:
                            content_accumulator += char
                            yield {"status": "code_token", "file": current_file, "token": char}

        # 6. Parse the complete JSON to get final verified content
        yield {"status": "stream_end"}
        
        edits = []
        try:
            clean = full_response.strip()
            # Strip markdown fences
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            
            # Find outermost JSON block ({...} or [...]) via bracket matching
            json_str = _extract_json_block(clean)
            if json_str:
                clean = json_str
            
            parsed_data = json.loads(clean)
            
            if isinstance(parsed_data, dict) and "files" in parsed_data:
                files_list = parsed_data["files"]
            elif isinstance(parsed_data, dict) and "content" in parsed_data:
                files_list = [parsed_data]
            elif isinstance(parsed_data, list):
                files_list = parsed_data
            elif isinstance(parsed_data, dict):
                # Some models nest under "data", "output", "result", etc.
                files_list = []
                for key in ("data", "output", "result", "edits"):
                    if key in parsed_data and isinstance(parsed_data[key], list):
                        files_list = parsed_data[key]
                        break
            else:
                files_list = []

            for file_entry in files_list:
                file_path = (
                    file_entry.get("file_path")
                    or file_entry.get("filePath")
                    or file_entry.get("path")
                    or file_entry.get("filename")
                    or file_entry.get("name")
                    or "src/App.tsx"
                )
                content = file_entry.get("content", "")
                if content:
                    edits.append({
                        "file_path": file_path,
                        "action": "write",
                        "content": content
                    })
        except (json.JSONDecodeError, Exception) as e:
            print(f"JSON parse error (falling back to streamed files): {e}")
            print(f"Raw response (first 500 chars): {full_response[:500]}")
        
        # Fallback: if JSON parsing failed or produced no edits, use streamed files
        if not edits and streamed_files:
            print(f"Using {len(streamed_files)} files captured during streaming as fallback")
            for file_path, content in streamed_files.items():
                if content:
                    edits.append({
                        "file_path": file_path,
                        "action": "write",
                        "content": content
                    })
        
        if edits:
            # ── Deterministic design contract enforcement ──────────────────
            # Locks :root CSS tokens in App.css after the LLM finishes — the same
            # concept as _transplant_root_vars in the mockup pipeline. This ensures
            # users who skip Design Studio still get product-branded output, not
            # generic AI clichés. Runs silently; failures are logged, not fatal.
            try:
                _contract = await asyncio.to_thread(get_design_contract_css, project_id)
                if _contract:
                    for _edit in edits:
                        _fp = _edit.get("file_path", "")
                        if _fp.endswith("App.css") or _fp in ("src/index.css", "index.css"):
                            _edit["content"] = _enforce_app_css_contract(
                                _edit["content"], _contract
                            )
                            break
            except Exception as _ce:
                print(f"Design contract enforcement skipped: {_ce}")

            yield {"status": "execution_complete", "edits": edits}
        else:
            # Debug: log snippet when parsing fails (helps diagnose model output format)
            snippet = full_response[:800].replace("\n", " ") if full_response else "(empty)"
            print(f"No valid file outputs. Response snippet: {snippet}...")
            yield {"status": "error", "message": "No valid file outputs found in LLM response"}
                
    except Exception as e:
        # Last resort: if streaming itself crashed, still try to use any files we captured
        print(f"Agent Execution Error: {e}")
        # Save any partially-streamed file that was in progress when the crash happened
        if current_file and content_accumulator:
            streamed_files[current_file] = content_accumulator
            print(f"Saved partial file: {current_file} ({len(content_accumulator)} chars)")
        if streamed_files:
            print(f"Agent crashed but recovered {len(streamed_files)} streamed files")
            edits = [{"file_path": fp, "action": "write", "content": c} for fp, c in streamed_files.items() if c]
            if edits:
                yield {"status": "stream_end"}
                yield {"status": "execution_complete", "edits": edits}
                return
        yield {"status": "error", "message": f"LLM Generation failed: {str(e)}"}
