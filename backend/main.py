from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()
import uuid
from datetime import datetime
import requests as http_requests
from fly_service import create_and_boot_sandbox, get_file_tree, write_batch_to_machine, wake_sandbox_if_needed
from agent import process_user_request
from models import Base, engine, SessionLocal, Project, File, Message
from auth import get_current_user_ws
import models_api
import provider_api
import projects_api
import ideation_api
import csuite_api
import artifacts_api
import design_api

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing routers
app.include_router(models_api.router)
app.include_router(provider_api.router)

# New API routers
app.include_router(projects_api.router)
app.include_router(ideation_api.router)
app.include_router(csuite_api.router)
app.include_router(artifacts_api.router)
app.include_router(design_api.router)
import routing_api
app.include_router(routing_api.router)

# Mock in-memory state for project -> machine mapping
projects = {}


def _app_name_from_preview_url(preview_url: str | None) -> str | None:
    if not preview_url:
        return None
    try:
        return preview_url.split("//")[1].split(".")[0]
    except Exception:
        return None


def _poll_sandbox_health(url: str, retries: int = 30, interval: float = 2.0) -> bool:
    """Synchronous poll – run via asyncio.to_thread.
    Waits until the sandbox returns a real page (not the nginx 'Building preview' fallback).
    Allows up to retries * interval seconds (default 60s) for Vite cold-boot.
    """
    import time
    import socket
    from urllib.parse import urlparse

    # Quick DNS check — if the hostname doesn't resolve, the sandbox was destroyed
    hostname = urlparse(url).hostname
    if hostname:
        try:
            socket.getaddrinfo(hostname, 443)
        except socket.gaierror:
            print(f"[sandbox] DNS resolution failed for {hostname} — sandbox was likely destroyed")
            return False

    # Give the machine a moment to finish starting services
    time.sleep(3)

    for i in range(retries):
        try:
            r = http_requests.get(url, timeout=5, allow_redirects=True)
            # nginx @vite_loading returns 200/503 with 'Building preview' while Vite boots.
            # Only treat as ready when response is non-5xx AND not the loading placeholder.
            if r.status_code < 500 and "Building preview" not in r.text[:500]:
                print(f"[sandbox] Health check passed on attempt {i+1} (status={r.status_code})")
                return True
            else:
                if i % 5 == 0:  # log every 5th attempt to reduce noise
                    print(f"[sandbox] Not ready yet (attempt {i+1}/{retries}, status={r.status_code})")
        except http_requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e) or "getaddrinfo" in str(e):
                print(f"[sandbox] DNS resolution failed — sandbox was likely destroyed")
                return False
            if i % 5 == 0:
                print(f"[sandbox] Health check error (attempt {i+1}/{retries}): {e}")
        except Exception as e:
            if i % 5 == 0:
                print(f"[sandbox] Health check error (attempt {i+1}/{retries}): {e}")
        if i < retries - 1:
            time.sleep(interval)
    print(f"[sandbox] Health check exhausted {retries} retries ({retries * interval:.0f}s)")
    return False


def _persist_message(db, project_id: str, role: str, content: str):
    if not content:
        return
    db.add(Message(
        id=str(uuid.uuid4()),
        project_id=project_id,
        role=role,
        content=content,
        created_at=datetime.utcnow(),
    ))
    db.commit()


def _persist_files(db, project_id: str, write_edits: list[dict]):
    for edit in write_edits:
        file_path = edit.get("file_path")
        content = edit.get("content")
        if not file_path:
            continue

        existing = db.query(File).filter(
            File.project_id == project_id,
            File.file_path == file_path,
        ).first()

        if existing:
            existing.content = content
            existing.updated_at = datetime.utcnow()
        else:
            db.add(File(
                id=str(uuid.uuid4()),
                project_id=project_id,
                file_path=file_path,
                content=content,
                updated_at=datetime.utcnow(),
            ))
    db.commit()


async def _send_json(websocket: WebSocket, payload: dict):
    await websocket.send_text(json.dumps(payload))


_TRANSIENT_MESSAGES = {
    "Analyzing request",
    "Reading current project files",
    "Generating code",
    "Waiting for input",
    "Writing ",
    "Agent is working",
}

def _is_transient(content: str) -> bool:
    return any(content.startswith(t) for t in _TRANSIENT_MESSAGES)


async def _restore_project_state(websocket: WebSocket, db, project_id: str):
    stored_files = db.query(File).filter(File.project_id == project_id).order_by(File.file_path.asc()).all()
    for file_row in stored_files:
        await _send_json(websocket, {
            "type": "file_written",
            "file": file_row.file_path,
            "content": file_row.content or "",
        })

    # Purge stale transient messages from DB so they never come back
    all_messages = db.query(Message).filter(Message.project_id == project_id).order_by(Message.created_at.asc()).all()
    clean_history = []
    for m in all_messages:
        if m.role == "system" and _is_transient(m.content or ""):
            db.delete(m)
        else:
            clean_history.append({"role": m.role, "content": m.content})
    db.commit()

    await _send_json(websocket, {
        "type": "message_history",
        "messages": clean_history,
    })


def _load_project_files(db, project_id: str):
    return db.query(File).filter(File.project_id == project_id).order_by(File.file_path.asc()).all()


async def _replay_project_files_to_sandbox(db, project_id: str, preview_url: str | None):
    app_name = _app_name_from_preview_url(preview_url)
    if not app_name:
        return

    stored_files = _load_project_files(db, project_id)
    if not stored_files:
        return

    batch_files = [
        {"file_path": f.file_path, "content": f.content or ""}
        for f in stored_files
    ]
    await asyncio.to_thread(write_batch_to_machine, app_name, batch_files)


async def _ensure_project_sandbox(websocket: WebSocket, db, project: Project, project_id: str):
    project_state = projects.get(project_id, {})

    if not project_state.get("preview_url") and project.preview_url:
        project_state["preview_url"] = project.preview_url
    if not project_state.get("ipv6") and project.fly_machine_ipv6:
        project_state["ipv6"] = project.fly_machine_ipv6

    app_name = _app_name_from_preview_url(project_state.get("preview_url"))
    can_reuse = False
    if app_name:
        try:
            await asyncio.to_thread(get_file_tree, app_name)
            can_reuse = True
        except Exception:
            can_reuse = False

    # If app exists but is sleeping/suspended, try waking before provisioning new
    if app_name and not can_reuse:
        woke = await asyncio.to_thread(wake_sandbox_if_needed, app_name)
        if woke:
            try:
                await asyncio.to_thread(get_file_tree, app_name)
                can_reuse = True
            except Exception:
                can_reuse = False

    if not can_reuse:
        await _send_json(websocket, {
            "type": "status",
            "status": "booting_sandbox",
            "message": "Booting secure Fly.io Sandbox..."
        })
        preview_url, ipv6 = await asyncio.to_thread(create_and_boot_sandbox)
        project_state["preview_url"] = preview_url
        project_state["ipv6"] = ipv6

        project.preview_url = preview_url
        project.fly_machine_ipv6 = ipv6
        project.fly_app_name = _app_name_from_preview_url(preview_url)
        project.updated_at = datetime.utcnow()
        db.commit()

        # New sandbox was provisioned: restore persisted files into it.
        await _replay_project_files_to_sandbox(db, project_id, preview_url)

    projects[project_id] = project_state
    return project_state

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    db = SessionLocal()
    project_id = websocket.query_params.get("project_id")

    if not project_id:
        await _send_json(websocket, {"type": "error", "message": "Missing project_id in WebSocket query"})
        await websocket.close(code=4400)
        db.close()
        return

    user = await get_current_user_ws(websocket, db)
    if not user:
        await _send_json(websocket, {"type": "error", "message": "Authentication failed"})
        await websocket.close(code=4401)
        db.close()
        return

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        await _send_json(websocket, {"type": "error", "message": "Project not found"})
        await websocket.close(code=4404)
        db.close()
        return

    try:
        project_state = await _ensure_project_sandbox(websocket, db, project, project_id)

        # Poll until Vite is actually serving before telling the frontend
        preview_url = project_state.get("preview_url", "")
        if preview_url:
            await _send_json(websocket, {
                "type": "status",
                "status": "waiting_for_vite",
                "message": "Waiting for preview to become ready..."
            })
            health_ok = await asyncio.to_thread(_poll_sandbox_health, preview_url)
            if not health_ok:
                await _send_json(websocket, {
                    "type": "status",
                    "status": "warning",
                    "message": "Preview may be slow to load — sandbox is still booting."
                })

        file_count = db.query(File).filter(File.project_id == project_id).count()

        await _send_json(websocket, {
            "type": "sandbox_ready",
            "previewUrl": project_state["preview_url"],
            "fileCount": file_count,
        })

        app_name = _app_name_from_preview_url(project_state.get("preview_url"))
        if app_name:
            try:
                tree_data = await asyncio.to_thread(get_file_tree, app_name)
                await _send_json(websocket, {
                    "type": "file_tree",
                    "tree": tree_data.get("tree", [])
                })
            except Exception as tree_err:
                print(f"[sandbox] Failed to get file tree: {tree_err}")

        await _restore_project_state(websocket, db, project_id)
        # Signal idle so the spinner clears after restore
        await _send_json(websocket, {"type": "status", "status": "idle"})

    except Exception as init_err:
        print(f"[sandbox] Init error (non-fatal): {init_err}")
        await _send_json(websocket, {"type": "status", "status": "idle", "message": f"Sandbox init issue: {str(init_err)}. You can still use the editor."})
        # DON'T close the WS or return — let the user continue chatting
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_prompt = payload.get("prompt")
            model_id = payload.get("model", "claude-3-5-sonnet-latest")
            images = payload.get("images", [])  # list of base64 data URLs

            if not user_prompt and not images:
                continue

            try:
                _persist_message(db, project_id, "user", user_prompt or f"[{len(images)} image(s)]")

                # Always refresh project_state from DB to avoid stale sandbox URLs
                project = db.query(Project).filter(Project.id == project_id).first()
                project_state = projects.get(project_id, {})
                if project and project.preview_url:
                    project_state["preview_url"] = project.preview_url
                projects[project_id] = project_state

                preview_url = project_state.get("preview_url")
                app_name = _app_name_from_preview_url(preview_url)

                # Verify sandbox is actually reachable before using it
                if app_name:
                    try:
                        await asyncio.to_thread(get_file_tree, app_name)
                    except Exception:
                        print(f"[sandbox] {app_name} unreachable, provisioning new sandbox...")
                        await _send_json(websocket, {
                            "type": "status",
                            "status": "booting_sandbox",
                            "message": "Previous sandbox expired. Booting a new one..."
                        })
                        new_preview_url, new_ipv6 = await asyncio.to_thread(create_and_boot_sandbox)
                        project_state["preview_url"] = new_preview_url
                        project_state["ipv6"] = new_ipv6
                        projects[project_id] = project_state
                        if project:
                            project.preview_url = new_preview_url
                            project.fly_machine_ipv6 = new_ipv6
                            project.fly_app_name = _app_name_from_preview_url(new_preview_url)
                            project.updated_at = datetime.utcnow()
                            db.commit()
                        preview_url = new_preview_url
                        app_name = _app_name_from_preview_url(new_preview_url)

                        # Wait for new sandbox to boot
                        if preview_url:
                            await asyncio.to_thread(_poll_sandbox_health, preview_url)

                        # Replay stored files into new sandbox
                        await _replay_project_files_to_sandbox(db, project_id, preview_url)

                await _send_json(websocket, {
                    "type": "sandbox_ready",
                    "previewUrl": preview_url
                })

                if app_name:
                    try:
                        tree_data = await asyncio.to_thread(get_file_tree, app_name)
                        await _send_json(websocket, {
                            "type": "file_tree",
                            "tree": tree_data.get("tree", [])
                        })
                    except Exception:
                        pass
                async for step in process_user_request(user_prompt, project_id, model_id, app_name, images=images, user_id=user.id):
                    if step["status"] == "file_stream_start":
                        await _send_json(websocket, {
                            "type": "file_stream_start",
                            "file": step["file"]
                        })
                    elif step["status"] == "code_token":
                        await _send_json(websocket, {
                            "type": "code_token",
                            "file": step["file"],
                            "token": step["token"]
                        })
                    elif step["status"] == "file_stream_end":
                        await _send_json(websocket, {
                            "type": "file_stream_end",
                            "file": step["file"],
                            "content": step["content"]
                        })
                    elif step["status"] == "stream_end":
                        await _send_json(websocket, {
                            "type": "stream_end"
                        })
                    elif step["status"] == "execution_complete":
                        edits = step.get("edits", [])
                        write_edits = [e for e in edits if e.get("action") == "write"]

                        if write_edits:
                            await _send_json(websocket, {
                                "type": "status",
                                "status": "applying_edits",
                                "message": f"Writing {len(write_edits)} files to sandbox..."
                            })

                            try:
                                if not app_name:
                                    raise RuntimeError("Missing sandbox app name")

                                # Ensure sandbox is alive before writing
                                woke = await asyncio.to_thread(wake_sandbox_if_needed, app_name)
                                if not woke:
                                    print(f"[sandbox] Wake returned False for {app_name}, attempting write anyway...")

                                # Poll health before writing to avoid 502s
                                preview_url = project_state.get("preview_url", "")
                                if preview_url:
                                    await asyncio.to_thread(_poll_sandbox_health, preview_url, 10, 2.0)

                                batch_files = [{"file_path": e["file_path"], "content": e["content"]} for e in write_edits]
                                await asyncio.to_thread(
                                    write_batch_to_machine,
                                    app_name,
                                    batch_files
                                )

                                _persist_files(db, project_id, write_edits)

                                for edit in write_edits:
                                    await _send_json(websocket, {
                                        "type": "file_written",
                                        "file": edit["file_path"],
                                        "content": edit["content"]
                                    })

                                tree_data = await asyncio.to_thread(get_file_tree, app_name)
                                await _send_json(websocket, {
                                    "type": "file_tree",
                                    "tree": tree_data.get("tree", [])
                                })

                                # Poll sandbox until Vite is ready (server-side, no CORS issues)
                                preview_url = project_state.get("preview_url", "")
                                if preview_url:
                                    await asyncio.to_thread(_poll_sandbox_health, preview_url)
                                else:
                                    await asyncio.sleep(5)

                                await _send_json(websocket, {
                                    "type": "reload_preview"
                                })

                            except Exception as e:
                                await _send_json(websocket, {
                                    "type": "error",
                                    "message": f"Failed to batch write files: {str(e)}"
                                })
                                _persist_message(db, project_id, "system", f"Error: Failed to batch write files: {str(e)}")
                    else:
                        await _send_json(websocket, {
                            "type": "agent_status",
                            "data": step
                        })
                        # Only persist meaningful messages, not transient progress indicators
                        _TRANSIENT = {"analyzing", "reading", "generating"}
                        if step.get("message") and step.get("status") not in _TRANSIENT:
                            _persist_message(db, project_id, "system", step["message"])

                await _send_json(websocket, {
                    "type": "status",
                    "status": "idle"
                })
            except Exception as loop_err:
                await _send_json(websocket, {
                    "type": "error",
                    "message": f"Request processing failed: {str(loop_err)}"
                })
                _persist_message(db, project_id, "system", f"Error: Request processing failed: {str(loop_err)}")
                await _send_json(websocket, {
                    "type": "status",
                    "status": "idle",
                    "message": "Waiting for input..."
                })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        db.close()
