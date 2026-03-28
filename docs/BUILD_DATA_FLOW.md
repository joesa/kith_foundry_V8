# Build Workspace — End-to-End Data Flow

> **Purpose**: Document every actor, data source, API call, WebSocket message, LLM invocation, and file operation involved in the Build Workspace (Editor/Chat). Written to enable replication of this flow in other systems.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Actors & Components](#2-actors--components)
3. [Entry Point & Route](#3-entry-point--route)
4. [Frontend State Machine](#4-frontend-state-machine)
5. [WebSocket Connection Lifecycle](#5-websocket-connection-lifecycle)
6. [Auto-Build Trigger](#6-auto-build-trigger)
7. [Bootstrap Prompt Assembly](#7-bootstrap-prompt-assembly)
8. [Backend WebSocket Handler](#8-backend-websocket-handler)
9. [Intent Classification & Routing](#9-intent-classification--routing)
10. [Multi-Agent Pipeline](#10-multi-agent-pipeline)
11. [Design Context Assembly](#11-design-context-assembly)
12. [LLM Streaming & File Parsing](#12-llm-streaming--file-parsing)
13. [File Persistence & Sandbox Write](#13-file-persistence--sandbox-write)
14. [Sandbox Architecture](#14-sandbox-architecture)
15. [Auto-Save (Manual Edits)](#15-auto-save-manual-edits)
16. [Auto-Fix Error Loop](#16-auto-fix-error-loop)
17. [Complete Sequence Diagram](#17-complete-sequence-diagram)
18. [WebSocket Message Reference](#18-websocket-message-reference)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      BROWSER                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Workspace.tsx                        │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌───────────────┐   │  │
│  │  │ Chat │ │Editor│ │Files │ │ Live Preview  │   │  │
│  │  │ Pane │ │(Monaco)│ │ Tree │ │ (iframe)      │   │  │
│  │  └──┬───┘ └──┬───┘ └──────┘ └──────┬────────┘   │  │
│  │     │        │                      │            │  │
│  │     └────────┴──────────┬───────────┘            │  │
│  │                         │                        │  │
│  │              useFoundry.ts (WS hook)             │  │
│  └─────────────────────────┬────────────────────────┘  │
│                            │ WebSocket                  │
└────────────────────────────┼────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────┐
│              BACKEND (FastAPI on :8000)                  │
│                            │                            │
│  ┌─────────────────────────┴──────────────────────┐     │
│  │          WebSocket Handler (main.py)           │     │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────────┐  │     │
│  │  │  Intent  │ │  Router  │ │ Multi-Agent   │  │     │
│  │  │ Classify │ │  Prompt  │ │   Pipeline    │  │     │
│  │  └──────────┘ └──────────┘ └──────┬────────┘  │     │
│  └───────────────────────────────────┼────────────┘     │
│                                      │                  │
│  ┌──────────┐ ┌──────────────┐ ┌─────┴────────┐        │
│  │ Design   │ │   Brain      │ │  LLM (via    │        │
│  │ Context  │ │   Service    │ │  LiteLLM)    │        │
│  └──────────┘ └──────────────┘ └──────────────┘        │
│                                                         │
│  ┌──────────┐ ┌──────────────┐                          │
│  │ Storage  │ │  Sandbox     │                          │
│  │ (Nhost)  │ │  Worker      │                          │
│  └──────────┘ └──────┬───────┘                          │
└──────────────────────┼──────────────────────────────────┘
                       │ HTTPS (Bridge API)
┌──────────────────────┼──────────────────────────────────┐
│          FLY.IO SANDBOX MACHINE                         │
│  ┌───────────────────┴──────────────────────────┐       │
│  │             Bridge API (bridge.py)            │       │
│  │     ┌──────────┐  ┌──────────────────┐       │       │
│  │     │ Vite Dev │  │ /workspace/ dir  │       │       │
│  │     │ Server   │  │ (project files)  │       │       │
│  │     └──────────┘  └──────────────────┘       │       │
│  └──────────────────────────────────────────────┘       │
│  Preview URL: https://kith-sandbox-{8hex}.fly.dev       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Actors & Components

| Actor | Type | File(s) | Role |
|-------|------|---------|------|
| **Workspace** | React Component | `frontend/src/features/build/Workspace.tsx` | Main build page UI — chat, editor, file tree, preview |
| **useFoundry** | React Hook | `frontend/src/features/build/hooks/useFoundry.ts` | WebSocket connection + message dispatch |
| **useAutoSave** | React Hook | `frontend/src/features/build/hooks/useAutoSave.ts` | Debounced save of manual editor changes |
| **WS Handler** | Backend | `backend/main.py` (L1338–1800) | WebSocket endpoint — auth, sandbox boot, message loop |
| **Intent Classifier** | Backend | `backend/agent.py` (L200–260) | Heuristic + LLM classification of user prompt |
| **Multi-Agent Pipeline** | Backend | `backend/agent_pipeline.py` | 4-stage pipeline: Intent → Layout → Component → Code |
| **Conversation Agent** | Backend | `backend/agent.py` (L262–330) | Handles non-code conversation messages |
| **Code Agent** | Backend | `backend/agent.py` (L460–700) | Streaming JSON parser + design enforcement |
| **Design Context** | Backend | `backend/design_context.py` | Assembles design tokens/brief/spec from artifacts |
| **Brain Service** | Backend | `backend/brain_service.py` | Semantic memory of project decisions/patterns |
| **Error Resolver** | Backend | `backend/error_resolver.py` | Auto-fix Vite compilation errors |
| **Bootstrap Prompt** | Backend API | `backend/artifacts_api.py` (L365–496) | Assembles all artifacts into initial build prompt |
| **Storage Service** | Backend | `backend/storage_service.py` | File persistence to Nhost Storage |
| **Sandbox Worker** | Backend | `backend/fly_service.py` | Manages Fly.io Machine lifecycle |
| **Bridge API** | Sandbox | `backend/bridge.py` | REST API inside sandbox for file writes + Vite control |
| **Vite Dev Server** | Sandbox | (pre-installed in Docker image) | Compiles React/TS, serves preview |

---

## 3. Entry Point & Route

**Route**: `/app/projects/:projectId/build`

**Query Parameters**:
| Param | Effect |
|-------|--------|
| `?autobuild=1` | Auto-triggers initial build from bootstrap prompt |
| `?applydesign=1` | Same as autobuild but signals design studio context |

**Component mount**: `Workspace.tsx` renders the full IDE: Chat pane, Monaco editor, file explorer sidebar, and live preview iframe.

---

## 4. Frontend State Machine

### Key State Variables (Workspace.tsx)

```typescript
// Connection & sandbox
wsConnected: boolean          // WebSocket connected
status: string                // "idle" | "working" | "streaming" | "error"
previewUrl: string            // Fly.io sandbox preview URL
iframeSrc: string             // Current iframe URL (preview + path)

// Project files
hasExistingFiles: boolean     // Whether sandbox has files already
files: Record<string, string> // { "src/App.tsx": "content..." }
fileTree: FileNode[]          // Hierarchical tree for explorer
selectedFile: string          // Currently open file in editor

// Chat
messages: ChatMessage[]       // Chat history (user + assistant)
isStreaming: boolean          // Whether LLM is streaming
buildStage: string            // "planning" | "coding" | "writing" | etc.

// Model selection
selectedModel: string         // LLM model identifier

// Refs
bootstrapSentRef: boolean     // Prevents double-send of auto-build
```

### State Flow

```
mount → wsConnected=false
  ↓
WebSocket opens → wsConnected=true, status="idle"
  ↓
sandbox_ready received → previewUrl set, hasExistingFiles computed
  ↓
(if autobuild & !hasExistingFiles)
  → bootstrap prompt fetched → sendCommand() → status="working"
  → file_stream_start → isStreaming=true, status="streaming"
  → code_token (×N) → files[path] accumulates content
  → file_stream_end → file complete
  → (repeat for each file)
  → execution_complete → files fully populated
  → reload_preview → iframe refreshes
  → status="idle"
```

---

## 5. WebSocket Connection Lifecycle

**File**: `frontend/src/features/build/hooks/useFoundry.ts`

### Connection

```
URL: ws(s)://{host}/ws/chat?project_id={projectId}&token={jwt}
Protocol: native WebSocket (no Socket.IO)
Reconnect: automatic with backoff on disconnect
```

### Message Types Received (server → client)

| Type | Purpose | Key Data |
|------|---------|----------|
| `status` | Build state change | `{ status: "idle" \| "working" }` |
| `sandbox_ready` | Sandbox booted | `{ previewUrl, fileCount }` |
| `file_tree` | Project structure | `{ tree: FileNode[] }` |
| `file_stream_start` | Begin streaming a file | `{ file_path }` |
| `code_token` | One token of file content | `{ token }` |
| `file_stream_end` | File streaming complete | `{ file_path }` |
| `chat_token` | Conversation text token | `{ token }` |
| `chat_complete` | Conversation response done | `{}` |
| `build_stage` | Pipeline stage label | `{ stage: "planning" \| "coding" }` |
| `stream_end` | LLM stream finished | `{}` |
| `execution_complete` | All files generated | `{ edits: [{file_path, content}] }` |
| `file_written` | Single file persisted | `{ file_path }` |
| `reload_preview` | Refresh iframe | `{}` |
| `message_history` | Restored chat history | `{ messages: [] }` |
| `error` | Error message | `{ message }` |

### Message Types Sent (client → server)

| Type | Purpose | Key Data |
|------|---------|----------|
| (default) | User prompt | `{ prompt, model, images: [] }` |
| `preview_error` | Runtime error from preview | `{ errors: [string] }` |

---

## 6. Auto-Build Trigger

**File**: `Workspace.tsx` (L353–392)

### Trigger Conditions

All three must be true:
1. URL has `?autobuild=1` or `?applydesign=1`
2. WebSocket is connected AND `sandbox_ready` received
3. `hasExistingFiles === false` (fileCount === 0) AND `bootstrapSentRef.current === false`

### Sequence

```
1. useEffect detects conditions met
2. POST /api/v1/projects/{projectId}/bootstrap-prompt
   → Returns: { prompt: "Build the full product application..." }
3. sendCommand(prompt, selectedModel)
   → Sends over WebSocket: { prompt, model, images: [] }
4. bootstrapSentRef.current = true (prevent re-fire)
```

---

## 7. Bootstrap Prompt Assembly

**File**: `backend/artifacts_api.py` (L365–496)  
**Endpoint**: `POST /api/v1/projects/{project_id}/bootstrap-prompt`

### Data Sources Collected

| Source | How Retrieved | Content |
|--------|--------------|---------|
| **Project metadata** | `db.query(Project)` | Name, description, product_mode, style_mode |
| **PRD** | `Artifact(type=prd, status=completed)` | Full product requirements document |
| **Wireframes** | `Artifact(type=wireframes, status=completed)` | Page structure and layout specs |
| **User Flows** | `Artifact(type=user_flows, status=completed)` | Interaction flows and paths |
| **Tech Stack** | `Artifact(type=tech_stack, status=completed)` | Technology decisions |
| **Design System** | `Artifact(type=design_system, status=completed)` | Design tokens, typography, palette |
| **Site Map** | `Artifact(type=site_map, status=completed)` | Page hierarchy and navigation |
| **Design Mockups** | `Artifact(type=mockup_*, status=completed)` | Visual mockup descriptions |
| **Design Context** | `get_design_context(db, project_id)` | Compiled design spec + CSS tokens |
| **Brand Brief** | `Artifact(type=brand_brief)` | Brand identity and voice |

### Prompt Template Structure

```
"Build the full product application for '{project.name}'.

=== PRODUCT REQUIREMENTS ===
{prd_content}

=== DESIGN SYSTEM ===
{design_system_content}

=== WIREFRAMES ===
{wireframes_content}

=== USER FLOWS ===
{user_flows_content}

=== TECH STACK ===
{tech_stack_content}

=== SITE MAP ===
{site_map_content}

=== DESIGN CONTEXT ===
{design_context}

=== BUILD INSTRUCTIONS ===
Build a complete, production-ready React application..."
```

### Output

The assembled prompt is:
1. Persisted as `Artifact(type=bootstrap_prompt)` in the database
2. Returned as `{ prompt: "..." }` to the frontend

---

## 8. Backend WebSocket Handler

**File**: `backend/main.py` (L1338–1800)  
**Endpoint**: `GET /ws/chat`

### Connection Setup Sequence

```
1. Parse query params: project_id, token
2. Accept WebSocket connection
3. Authenticate: decode JWT, verify user owns project
4. Rate limit check
5. _ensure_sandbox_ready(project_id):
   ├── get_or_create_worker(project_id) → FlySandboxWorker
   ├── Health check existing sandbox (or boot new one)
   ├── Restore persisted files from Storage to sandbox
   ├── Start Vite → wait_vite_ready
   └── Return (worker, preview_url)
6. Send: sandbox_ready { previewUrl, fileCount }
7. Build file_tree from DB → Send: file_tree
8. _restore_project_state() → Send: message_history (past conversations)
9. Send: status { idle }
10. Enter message receive loop
```

### Message Receive Loop

```python
while True:
    data = await websocket.receive_json()
    prompt = data["prompt"]
    model = data.get("model", default_model)

    # Persist user message
    save_message(db, project_id, role="user", content=prompt)

    # Send: status { working }
    async for event in _step_stream(project_id, prompt, model, ...):
        await websocket.send_json(event)

    # Handle execution_complete specially (persist + sandbox write)
    # Send: status { idle }
```

---

## 9. Intent Classification & Routing

**File**: `backend/agent.py` (L200–260)

### Fast-Path Heuristics

Before calling the LLM, the classifier checks for keyword patterns:

| Pattern | Classification |
|---------|---------------|
| "build", "create", "add page", "implement" | `code` |
| "fix", "update", "change the", "modify" | `code` |
| "what is", "explain", "how does", "tell me" | `conversation` |

### LLM Classification (Fallback)

```
Prompt: ROUTER_PROMPT
Input: user message (truncated to 500 chars)
Output: "code" or "conversation" (max_tokens=10)
Default on ambiguity: "code"
```

### Routing

| Classification | Handler | Pipeline |
|---------------|---------|----------|
| `code` | `run_multi_agent_pipeline()` | Intent → Layout → Component → Code |
| `conversation` | `process_conversation()` | Single LLM call with file context |

---

## 10. Multi-Agent Pipeline

**File**: `backend/agent_pipeline.py`

### Stage 1 — Intent Agent (L130–170)

```
Input:
  - User prompt
  - Compressed project context (token budget ~5000)
  - Brain context (semantic memory)

Output (JSON):
  {
    intent_type: "initial_build" | "add_feature" | "fix_bug" | "style_change" | "refactor",
    scope: "full_app" | "single_page" | "single_component" | "style_only",
    description: "...",
    new_pages_needed: ["Dashboard", "Settings"]
  }

System Prompt: INTENT_AGENT_PROMPT
```

### Stage 2 — Layout Agent (L172–200)

**Runs only when**: `scope ∈ {full_app, single_page}` OR `intent_type === initial_build`

```
Input:
  - Intent JSON from Stage 1
  - Design reference (from design_context.py)

Output (JSON):
  {
    pages: [
      { name: "Landing", route: "/", layout: "hero-cta", sections: [...] },
      { name: "Dashboard", route: "/dashboard", layout: "sidebar-main", sections: [...] }
    ]
  }

System Prompt: LAYOUT_AGENT_PROMPT
```

### Stage 3 — Component Agent (L202–225)

**Runs only when**: Layout Agent succeeded AND `intent_type ∉ {style_only, fix_bug}`

```
Input:
  - Layout plan JSON from Stage 2
  - Design reference

Output (JSON):
  {
    components: [
      { name: "HeroSection", file_path: "src/components/HeroSection.tsx", purpose: "...", visual_spec: "..." }
    ],
    file_order: ["src/App.css", "src/components/HeroSection.tsx", "src/App.tsx", "src/main.tsx"],
    design_token_css: ":root { --color-primary: #...; }"
  }

System Prompt: COMPONENT_AGENT_PROMPT
```

### Stage 4 — Code Agent (L227–470)

**Always runs.** This is the stage that generates actual code.

```
Input (_build_code_agent_prompt concatenates):
  1. User's original request
  2. Design reference (full design context)
  3. Intent analysis summary (from Stage 1)
  4. Layout plan JSON (from Stage 2, if available)
  5. Component manifest + design token CSS + file order (from Stage 3, if available)
  6. Full file tree (all existing project files)
  7. Full project file contents (every file's code)

Output: Streaming JSON
  {
    "files": [
      { "file_path": "src/App.css", "content": "..." },
      { "file_path": "src/components/Hero.tsx", "content": "..." },
      ...
    ]
  }

System Prompt: SURGEON_PROMPT (prompts.py L5)
```

### Context Compression

- **Stages 1–3**: Use `compress_context()` with ~5000 token budget (summarizes file contents)
- **Stage 4 (Code Agent)**: Uses **full uncompressed file contents** — the LLM needs exact code to generate correct edits

---

## 11. Design Context Assembly

**File**: `backend/design_context.py`

### `get_design_context()` — Full Context (L135–310)

Used for bootstrap prompt and initial builds. Assembles a rich design reference block with a **three-layer priority system**:

#### Layer 1: Mandatory Design Contract (CSS `:root` Variables)

Priority order for sourcing CSS tokens:
1. **GPT Engine `design_tokens`** from `Artifact(type=design_system)` content JSON
2. **`:root` block** extracted from Design System Foundation artifact text
3. **Persisted `design_tokens`** artifact (prevents drift across builds)
4. **Vendor brief palette** → auto-generated synthetic CSS variables

```css
/* Example output */
:root {
  --color-primary: #2563eb;
  --color-secondary: #7c3aed;
  --color-background: #ffffff;
  --font-heading: 'Inter', sans-serif;
  --radius-md: 8px;
}
```

#### Layer 2: Compiled Design Spec

From `build_compiled_design_spec()`:
- Typography scale
- Spacing system
- Color palette with semantic names
- Component style patterns

#### Layer 3: Strategic Design Guidance

| Source | Content |
|--------|---------|
| Design Brief | `build_design_brief()` — Brand voice, visual direction |
| CDO Analysis | `CSuiteAnalysis(role=cdo)` — Recommendations, risks, strengths |
| Executive Strategy | `CSuiteAnalysis(role=synthesizer)` — Strategic direction, priorities |
| Design System Foundation | Full text from `Artifact(type=design_system)` |

### `get_design_context_compact()` — Light Context (L312–400)

Same data sources but **truncated** — used for follow-up requests (not initial build) to save tokens.

### `get_design_contract_css()` — CSS Only (L125–133)

Returns just the `:root {}` CSS block. Used for **post-generation enforcement** (injecting locked design tokens into generated CSS files).

---

## 12. LLM Streaming & File Parsing

### SURGEON_PROMPT (System Prompt)

**File**: `backend/prompts.py` (L5+)

Defines:
- **Output format**: `{ "files": [{ "file_path": "...", "content": "..." }] }`
- **Design System Preservation** ("Golden Rule") — never override design tokens
- **Design Contract Enforcement** — mandatory CSS token usage
- **Forbidden patterns**: AI-purple palettes, glassmorphism, emoji as icons, hardcoded hex colors
- **Required patterns**: `cursor:pointer` on clickables, `prefers-reduced-motion`, hover transitions, viewport meta
- **Available libraries**: `react-router-dom`, `framer-motion`, `lucide-react`, `tailwindcss`
- **File order**: `App.css` → components → `App.tsx` → `main.tsx`
- **Component rules**: Self-contained, no shared type files
- **Initial build page set**: Landing → Auth → Dashboard → All remaining pages

### Streaming State Machine

**File**: `backend/agent.py` (L460–590)

The LLM response is parsed **in-flight** as tokens arrive:

```
State Machine:

1. Accumulate tokens into full_response buffer
2. Scan unprocessed text for `"content": "` marker
3. When marker found:
   a. Look backward for `"file_path": "..."` → extract filename
   b. Yield: file_stream_start { file_path }
   c. Enter inside_content mode
4. In inside_content mode, process each character:
   - Regular char → accumulate + yield code_token { token }
   - Backslash → set escape_next = true
   - Escaped char → map (\n→newline, \t→tab, \"→quote, \\→backslash) + yield code_token
   - Unescaped closing quote → yield file_stream_end { file_path }, exit content mode
5. Repeat from step 2 for next file
6. After stream ends → yield stream_end
```

This approach means the frontend receives file content **character by character** as the LLM generates it, enabling real-time code display in the editor.

### Post-Stream Processing (L600–700)

```
1. Parse complete JSON response into files_list
2. Support multiple JSON key formats: file_path, filePath, path, filename, name
3. Support nested structures: parsed_data["files"], parsed_data["data"]
4. Fallback: if JSON parse fails, use streamed_files captured during streaming
5. Design contract enforcement: inject locked CSS tokens into App.css / index.css
6. Yield: execution_complete { edits: [{ file_path, content }] }
```

---

## 13. File Persistence & Sandbox Write

### On `execution_complete` (main.py L1620–1740)

```
Step 1: Sanitize edits
  ├── _sanitize_tsx_write_edits() — fix invalid lucide-react icon imports
  └── _sanitize_css_write_edits() — fix CSS syntax issues

Step 2: Persist to Storage (best-effort)
  └── storage_service.upload_files(project_id, edits)
      → Uploads to Nhost Storage bucket: projects/{project_id}/{file_path}

Step 3: Update DB metadata
  └── Upsert File rows: { project_id, file_path, updated_at }
      (content=None — source of truth is Storage, not DB)

Step 4: Send file_written events
  └── For each file: websocket.send_json({ type: "file_written", file_path })

Step 5: Update file_tree
  └── Rebuild from DB → websocket.send_json({ type: "file_tree", tree })

Step 6: Write to sandbox
  └── worker.execute("write_files", write_edits)
      → Bridge API: POST /write_files
      → Writes each file to /workspace/{file_path} on the Fly Machine

Step 7: Wait for Vite
  └── worker.execute("wait_vite_ready", None, timeout=45.0)
      → Polls Bridge health endpoint until Vite reports ready

Step 8: Reload preview
  └── websocket.send_json({ type: "reload_preview" })

Step 9: Check for compilation errors
  └── worker.execute("check_vite_errors")
      → Bridge API: POST /check_vite_errors
      → Probes each .tsx file through Vite HMR
      → If errors found: trigger auto-fix cycle (see §16)

Step 10: Populate Brain (non-blocking)
  └── populate_brain_from_edits(project_id, edits)
      → Indexes code patterns and decisions into brain service
```

---

## 14. Sandbox Architecture

### Fly.io Sandbox Worker

**File**: `backend/fly_service.py`

Each project gets a dedicated Fly.io Machine running a Docker container (`Dockerfile.sandbox`) with:
- Node.js + npm pre-installed
- Vite + React template pre-configured
- Bridge API (FastAPI) for file writes and commands
- Preview accessible at `https://kith-sandbox-{8hex}.fly.dev`

### Bridge API

**File**: `backend/bridge.py`  
Runs inside the sandbox container, protected by `X-Bridge-Secret` header.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET/POST | Returns `{ ok: true, vite_ready: bool }` |
| `/write_files` | POST | Writes `files[]` array to `/workspace/` |
| `/setup_vite` | POST | No-op (pre-installed) |
| `/start_vite` | POST | No-op (started on boot) |
| `/run_cmd` | POST | Execute arbitrary shell command |
| `/fetch?url=` | GET | HTTP GET from inside sandbox network |
| `/check_vite_errors` | POST | Probe each `.tsx` file through Vite, return errors |

### Sandbox Boot Sequence (`_ensure_sandbox_ready`)

**File**: `main.py` (L1090–1200)

```
1. get_or_create_worker(project_id) → FlySandboxWorker
2. If worker has existing preview_url:
   a. Health check → if alive: restore files from Storage → reuse
   b. If dead: release_worker → fall through to step 3
3. Create new Fly Machine:
   a. setup_vite() (no-op, pre-installed)
   b. Restore persisted files from Nhost Storage → write to sandbox
   c. start_vite() (no-op, started on boot)
   d. wait_vite_ready(timeout=45s)
4. Save preview_url to Project DB row
5. Return (worker, preview_url)
```

---

## 15. Auto-Save (Manual Edits)

**File**: `frontend/src/features/build/hooks/useAutoSave.ts`

When the user manually edits code in the Monaco editor:

```
1. Monitor files state changes (800ms debounce)
2. Compute dirty files (diff against lastSaved snapshot)
3. POST /api/v1/projects/{project_id}/save
   Body: { files: { "src/App.tsx": "new content...", ... } }
4. On success: update lastSaved, trigger preview reload via callback
```

**Backend save endpoint** (`main.py` L1208–1245):

```
1. Receive file edits
2. Sanitize edits (_sanitize_tsx_write_edits, _sanitize_css_write_edits)
3. Persist to Nhost Storage
4. Write to sandbox worker via Bridge API
5. Wait for Vite ready
```

---

## 16. Auto-Fix Error Loop

### Frontend Detection

**File**: `useFoundry.ts` (L85–130)

```
1. Listen for iframe postMessage events of type "preview-error"
2. Listen for window.onerror / unhandledrejection matching preview iframe URL patterns
3. Debounce collected errors (500ms)
4. Send over WebSocket: { type: "preview_error", errors: ["Error: ...", ...] }
```

### Backend Resolution

**File**: `main.py` (L1470–1540), `error_resolver.py`

```
1. Receive preview_error WebSocket message
2. Call attempt_fix(project_id, errors, user_id):
   a. Read current project files
   b. Send error context + file contents to LLM
   c. LLM returns corrected files
3. If fix files returned:
   a. Sanitize edits
   b. Persist to Storage
   c. Write to sandbox via Bridge API
   d. Send reload_preview to frontend
4. If fix fails: send error message to chat
```

### Vite Compilation Error Auto-Fix

Separate from runtime errors — triggered after every `execution_complete`:

```
1. check_vite_errors() → Bridge probes each .tsx through Vite
2. If compilation errors found:
   a. attempt_fix() with error details
   b. Write corrected files → reload preview
   c. Re-check (up to 3 cycles)
```

---

## 17. Complete Sequence Diagram

### Initial Build with `?applydesign=1`

```
User clicks "Build with Kith" in Design Studio
    │
    ▼
Browser navigates to /app/projects/{id}/build?applydesign=1
    │
    ▼
Workspace.tsx mounts → useFoundry(projectId) opens WebSocket
    │
    ▼
┌─── Backend WS Handler ──────────────────────────────────────┐
│  1. Authenticate user (JWT)                                  │
│  2. _ensure_sandbox_ready()                                  │
│     └── Boot Fly Machine → Start Vite → Health check         │
│  3. Send → sandbox_ready { previewUrl, fileCount: 0 }        │
│  4. Send → file_tree (empty)                                 │
│  5. _restore_project_state()                                 │
│     └── Send → message_history                               │
│  6. Send → status { idle }                                   │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌─── Frontend Auto-Build Trigger ──────────────────────────────┐
│  Conditions met: autobuild=1 + wsConnected + !hasExisting     │
│  1. POST /api/v1/projects/{id}/bootstrap-prompt               │
│     └── Assembles: PRD + Design + Wireframes + Flows + ...    │
│     └── Returns: { prompt: "Build the full product..." }      │
│  2. sendCommand(prompt, selectedModel)                        │
│     └── WS sends: { prompt, model, images: [] }              │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌─── Backend Multi-Agent Pipeline ─────────────────────────────┐
│  1. Persist user message to DB                                │
│  2. Send → status { working }                                 │
│  3. Resolve LLM credentials (user keys or platform keys)      │
│  4. classify_intent(prompt) → "code"                          │
│  5. run_multi_agent_pipeline():                               │
│     ├── Read all project files (empty for initial build)      │
│     ├── compress_context() for planning agents                │
│     ├── Load design context (get_design_context)              │
│     ├── Load brain context                                    │
│     ├── Send → build_stage { "planning" }                     │
│     │                                                         │
│     ├── Stage 1: Intent Agent                                 │
│     │   └── → { type: initial_build, scope: full_app }        │
│     │                                                         │
│     ├── Stage 2: Layout Agent                                 │
│     │   └── → { pages: [Landing, Auth, Dashboard, ...] }      │
│     │                                                         │
│     ├── Stage 3: Component Agent                              │
│     │   └── → { components: [...], file_order: [...] }        │
│     │                                                         │
│     ├── Send → build_stage { "coding" }                       │
│     │                                                         │
│     └── Stage 4: Code Agent (SURGEON_PROMPT)                  │
│         ├── Streams JSON { files: [{file_path, content}] }    │
│         ├── In-flight parser yields per file:                 │
│         │   ├── Send → file_stream_start { file_path }        │
│         │   ├── Send → code_token { token } (×N chars)        │
│         │   └── Send → file_stream_end { file_path }          │
│         ├── Send → stream_end                                 │
│         ├── Design contract enforcement (inject CSS tokens)   │
│         └── Send → execution_complete { edits: [...] }        │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌─── Post-Generation Processing ───────────────────────────────┐
│  1. Sanitize edits (lucide icons, CSS syntax)                 │
│  2. _persist_files() → Nhost Storage + DB metadata            │
│  3. Send → file_written { file_path } (×N files)             │
│  4. Send → file_tree { tree: [...] }                         │
│  5. worker.execute("write_files") → Bridge → /workspace/      │
│  6. worker.execute("wait_vite_ready") → poll health           │
│  7. Send → reload_preview                                     │
│  8. worker.execute("check_vite_errors")                       │
│     └── If errors: auto-fix cycle (up to 3 attempts)          │
│  9. populate_brain_from_edits() (async, non-blocking)         │
│ 10. Send → status { idle }                                    │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌─── Frontend Final State ─────────────────────────────────────┐
│  • files{} populated with all generated code                  │
│  • fileTree updated with full project structure               │
│  • Monaco editor shows code (now editable)                    │
│  • Chat shows ✓ messages for each generated file              │
│  • iframe loads preview URL → user sees live app              │
│  • hasGenerated=true → explorer/editor/chat toggles visible   │
└──────────────────────────────────────────────────────────────┘
```

### Follow-Up User Request (e.g., "Add a settings page")

```
User types in chat → sendCommand(prompt, model)
    │
    ▼
Backend:
  1. classify_intent → "code"
  2. run_multi_agent_pipeline():
     ├── Reads ALL existing project files (full contents)
     ├── get_design_context_compact() (truncated, save tokens)
     ├── Intent Agent → { type: add_feature, scope: single_page }
     ├── Layout Agent → { pages: [Settings] }
     ├── Component Agent → { new components for Settings }
     └── Code Agent → generates new + modified files
  3. Same post-generation flow: persist → sandbox write → reload
```

---

## 18. WebSocket Message Reference

### Complete Message Flow (Chronological)

```
── Connection ─────────────────────────────
  S→C  sandbox_ready    { previewUrl, fileCount }
  S→C  file_tree        { tree: FileNode[] }
  S→C  message_history  { messages: ChatMessage[] }
  S→C  status           { status: "idle" }

── Build Request ──────────────────────────
  C→S  (prompt)         { prompt, model, images }
  S→C  status           { status: "working" }
  S→C  build_stage      { stage: "planning" }
  S→C  build_stage      { stage: "coding" }

── File Streaming (per file) ──────────────
  S→C  file_stream_start  { file_path: "src/App.css" }
  S→C  code_token         { token: ":" }         ×N
  S→C  file_stream_end    { file_path: "src/App.css" }

── Stream Complete ────────────────────────
  S→C  stream_end        {}
  S→C  execution_complete { edits: [{file_path, content}] }

── Post-Processing ────────────────────────
  S→C  file_written      { file_path }           ×N
  S→C  file_tree         { tree: FileNode[] }
  S→C  reload_preview    {}
  S→C  status            { status: "idle" }

── Error Auto-Fix (if needed) ─────────────
  C→S  preview_error     { errors: [string] }
  S→C  status            { status: "working" }
  S→C  file_stream_start → code_token → file_stream_end  (fixed files)
  S→C  execution_complete { edits: [...] }
  S→C  reload_preview    {}
  S→C  status            { status: "idle" }

── Conversation (non-code) ────────────────
  C→S  (prompt)          { prompt, model, images }
  S→C  chat_token        { token: "The " }       ×N
  S→C  chat_complete     {}
  S→C  status            { status: "idle" }
```

---

## Key Implementation Notes for Replication

1. **WebSocket is the backbone** — all real-time communication uses a single persistent WebSocket, not REST polling.

2. **Bootstrap prompt is the critical handoff** — the entire upstream pipeline (C-Suite analysis, PRD, design system, mockups) is compressed into a single mega-prompt that seeds the build.

3. **Multi-agent pipeline is sequential** — Intent → Layout → Component → Code. Each stage's output feeds the next. Only Code Agent generates actual files.

4. **In-flight streaming parser** — the LLM generates JSON, but the system parses `file_path` and `content` values as they stream, sending individual characters to the frontend in real-time. This creates the "live coding" effect.

5. **Design contract enforcement is post-hoc** — after the LLM generates all files, the system injects locked CSS `:root` variables into `App.css`/`index.css` to prevent design drift.

6. **Sandbox is stateless** — files are persisted to Nhost Storage and restored on sandbox boot. The Fly Machine can be destroyed and recreated without data loss.

7. **Error auto-fix is a closed loop** — runtime errors from the preview iframe and Vite compilation errors are both captured and automatically fed back to the LLM for correction, up to 3 attempts.

8. **Context compression is selective** — planning agents (Intent, Layout, Component) get compressed context (~5000 tokens) while the Code Agent gets full uncompressed file contents for accurate code generation.
