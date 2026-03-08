"""
Nhost Storage service for project code files.
Uses Nhost Storage REST API (S3-compatible backend).

Set USE_NHOST=1 in .env to use Nhost instead of Supabase.
"""
import os
import asyncio
import json
import logging
import mimetypes
import time
import uuid
from typing import Optional

import requests
import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

BUCKET = "default"

# Nhost Storage base URL — ensure it ends with /v1
_RAW_STORAGE_URL = os.getenv("NHOST_STORAGE_URL", "").rstrip("/")
NHOST_STORAGE_URL = _RAW_STORAGE_URL if _RAW_STORAGE_URL.endswith("/v1") else f"{_RAW_STORAGE_URL}/v1"
NHOST_ADMIN_SECRET = os.getenv("NHOST_ADMIN_SECRET", "")

_MIME_OVERRIDES = {
    ".tsx": "text/plain", ".ts": "text/plain", ".jsx": "text/plain",
    ".css": "text/css", ".html": "text/html", ".json": "application/json",
    ".js": "application/javascript", ".md": "text/markdown", ".txt": "text/plain",
}

MAX_RETRIES = 3
RETRY_BACKOFF = 0.5
# 502/503/504 are transient; use longer backoff so Nhost/nginx can recover
TRANSIENT_CODES = (502, 503, 504)
TRANSIENT_BACKOFF_BASE = 2.0  # seconds
# Limit concurrent uploads to avoid overwhelming Nhost (reduces 503 rate limiting)
UPLOAD_SEMAPHORE = asyncio.Semaphore(2)


def _content_type_for(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[ext]
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "text/plain"


def _storage_path(project_id: str, file_path: str) -> str:
    return f"{project_id}/{file_path.lstrip('/')}"


def _auth_headers() -> dict:
    return {"x-hasura-admin-secret": NHOST_ADMIN_SECRET}


def ensure_bucket_exists() -> None:
    """Nhost creates buckets via dashboard; no-op here."""
    pass


def _file_id(project_id: str, file_path: str) -> str:
    """Generate a deterministic UUID for a project file.

    Using a stable UUID5 means we always know the Nhost file ID without any
    network lookup. PUT updates existing, POST with same id creates new.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nhost-kith/{project_id}/{file_path.lstrip('/')}"))


def _post_file(headers: dict, basename: str, content_bytes: bytes,
               content_type: str, fid: str, storage_name: str) -> requests.Response:
    """POST /files — create a new file with deterministic ID via metadata[]."""
    return requests.post(
        f"{NHOST_STORAGE_URL}/files",
        headers=headers,
        files={"file[]": (basename, content_bytes, content_type)},
        data=[
            ("bucket-id", BUCKET),
            ("metadata[]", json.dumps({"id": fid, "name": storage_name})),
        ],
        timeout=30,
    )


def upload_file_sync(project_id: str, file_path: str, content: str) -> None:
    """Upload (or replace) a single file (sync) using deterministic file IDs.

    Strategy:
      1. PUT /files/{id} with field ``file`` — replaces content if file exists.
      2. On non-success, POST /files with ``metadata[]`` JSON to create.
      3. On POST 500 (stale/broken metadata), delete the old record and retry.
    """
    fid = _file_id(project_id, file_path)
    storage_name = _storage_path(project_id, file_path)
    headers = _auth_headers()
    content_bytes = (content or "").encode("utf-8")
    content_type = _content_type_for(file_path)
    basename = os.path.basename(file_path)

    last_put, last_post = None, None
    for attempt in range(MAX_RETRIES):
        # --- PUT (update existing) ---
        put_resp = requests.put(
            f"{NHOST_STORAGE_URL}/files/{fid}",
            headers=headers,
            files={"file": (basename, content_bytes, content_type)},
            timeout=30,
        )
        if put_resp.status_code in (200, 201, 204):
            return

        # --- POST (create new) ---
        post_resp = _post_file(headers, basename, content_bytes,
                               content_type, fid, storage_name)
        if post_resp.status_code in (200, 201):
            return

        last_put, last_post = put_resp.status_code, post_resp.status_code

        # Transient 502/503/504 — wait and retry (Nhost/nginx overloaded)
        if put_resp.status_code in TRANSIENT_CODES or post_resp.status_code in TRANSIENT_CODES:
            if attempt < MAX_RETRIES - 1:
                wait = TRANSIENT_BACKOFF_BASE * (2 ** attempt)
                log.warning("[storage] %s returned 5xx (PUT %s, POST %s) — retrying in %.1fs (attempt %d)",
                            file_path, put_resp.status_code, post_resp.status_code, wait, attempt + 1)
                time.sleep(wait)
                continue
        # 409/500 — stale metadata; delete and retry
        elif post_resp.status_code in (409, 500) and attempt < MAX_RETRIES - 1:
            log.warning("[storage] POST %s returned %s — deleting stale record and retrying (attempt %d)",
                        file_path, post_resp.status_code, attempt + 1)
            try:
                requests.delete(
                    f"{NHOST_STORAGE_URL}/files/{fid}",
                    headers=headers,
                    timeout=15,
                )
            except Exception:
                pass
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue

        break

    raise RuntimeError(
        f"Storage upload failed for {file_path}: "
        f"PUT {last_put}, POST {last_post} - (after {MAX_RETRIES} attempts)"
    )


def upload_files_sync(project_id: str, files: list[dict]) -> None:
    """Upload a batch of files (sync)."""
    errors = []
    for f in files:
        fp = f.get("file_path", "")
        content = f.get("content", "")
        if not fp:
            continue
        try:
            upload_file_sync(project_id, fp, content)
        except Exception as e:
            errors.append(f"{fp}: {e}")
    if errors:
        raise RuntimeError(f"Storage upload failed for {len(errors)} file(s): {'; '.join(errors[:5])}")


def download_file_sync(project_id: str, file_path: str) -> Optional[str]:
    """Download a single file (sync). Returns None if not found."""
    fid = _file_id(project_id, file_path)
    url = f"{NHOST_STORAGE_URL}/files/{fid}"
    resp = requests.get(url, headers=_auth_headers(), timeout=30)
    if resp.status_code == 200:
        return resp.text
    return None


def download_project_files_sync(
    project_id: str,
    file_paths: list[str],
    db_fallback: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Download all files (sync)."""
    results = {}
    for fp in file_paths:
        content = download_file_sync(project_id, fp)
        if content is None and db_fallback and fp in db_fallback:
            content = db_fallback[fp]
        results[fp] = content or ""
    return results


def delete_file_sync(project_id: str, file_path: str) -> None:
    fid = _file_id(project_id, file_path)
    url = f"{NHOST_STORAGE_URL}/files/{fid}"
    requests.delete(url, headers=_auth_headers(), timeout=15)


def delete_project_files_sync(project_id: str, file_paths: list[str]) -> None:
    for fp in file_paths:
        try:
            delete_file_sync(project_id, fp)
        except Exception:
            pass


def delete_all_project_files_sync(project_id: str) -> int:
    """Nhost: list + delete. Returns count deleted."""
    list_url = f"{NHOST_STORAGE_URL}/files"
    resp = requests.get(list_url, headers=_auth_headers(), params={"bucketId": BUCKET, "prefix": f"{project_id}/"}, timeout=15)
    if resp.status_code != 200:
        return 0
    data = resp.json()
    items = data if isinstance(data, list) else (data.get("files") or [])
    count = 0
    for item in (items if isinstance(items, list) else []):
        fid = item.get("id") if isinstance(item, dict) else None
        if fid:
            try:
                requests.delete(f"{NHOST_STORAGE_URL}/files/{fid}", headers=_auth_headers(), timeout=15)
                count += 1
            except Exception:
                pass
    return count


async def _upload_one(project_id: str, file_path: str, content: str) -> Optional[str]:
    """Upload a single file in a thread; returns error string or None."""
    async with UPLOAD_SEMAPHORE:
        try:
            await asyncio.to_thread(upload_file_sync, project_id, file_path, content)
            return None
        except Exception as e:
            return f"{file_path}: {e}"


async def upload_files(project_id: str, files: list[dict]) -> None:
    """Upload (or replace) files to Nhost Storage concurrently."""
    if not NHOST_STORAGE_URL or not NHOST_ADMIN_SECRET:
        raise RuntimeError("NHOST_STORAGE_URL and NHOST_ADMIN_SECRET required")

    tasks = []
    for f in files:
        fp = f.get("file_path", "")
        content = f.get("content", "")
        if not fp:
            continue
        tasks.append(_upload_one(project_id, fp, content))

    results = await asyncio.gather(*tasks)
    errors = [e for e in results if e is not None]
    if errors:
        raise RuntimeError(f"Storage upload failed: {'; '.join(errors[:5])}")


async def download_project_files(
    project_id: str,
    file_paths: list[str],
    db_fallback: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Download files from Nhost Storage using deterministic file IDs."""
    async def _dl(fp: str) -> tuple[str, str]:
        fid = _file_id(project_id, fp)
        url = f"{NHOST_STORAGE_URL}/files/{fid}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=_auth_headers(), timeout=30)
                if resp.status_code == 200:
                    return fp, resp.text
        except Exception:
            pass
        if db_fallback and fp in db_fallback:
            return fp, db_fallback[fp]
        return fp, ""

    pairs = await asyncio.gather(*[_dl(fp) for fp in file_paths])
    return dict(pairs)
