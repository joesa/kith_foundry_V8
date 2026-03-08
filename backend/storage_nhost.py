"""
Nhost Storage service for project code files.
Uses Nhost Storage REST API (S3-compatible backend).

Set USE_NHOST=1 in .env to use Nhost instead of Supabase.
"""
import os
import asyncio
import mimetypes
from typing import Optional

import requests
import httpx
from dotenv import load_dotenv

load_dotenv()

BUCKET = "default"

NHOST_STORAGE_URL = os.getenv("NHOST_STORAGE_URL", "").rstrip("/")
NHOST_ADMIN_SECRET = os.getenv("NHOST_ADMIN_SECRET", "")

_MIME_OVERRIDES = {
    ".tsx": "text/plain", ".ts": "text/plain", ".jsx": "text/plain",
    ".css": "text/css", ".html": "text/html", ".json": "application/json",
    ".js": "application/javascript", ".md": "text/markdown", ".txt": "text/plain",
}


def _content_type_for(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[ext]
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "text/plain"


def _storage_path(project_id: str, file_path: str) -> str:
    return f"{project_id}/{file_path.lstrip('/')}"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {NHOST_ADMIN_SECRET}"}


def ensure_bucket_exists() -> None:
    """Nhost creates buckets via dashboard; no-op here."""
    pass


def upload_file_sync(project_id: str, file_path: str, content: str) -> None:
    """Upload a single file (sync)."""
    path = _storage_path(project_id, file_path)
    url = f"{NHOST_STORAGE_URL}/files"
    headers = _auth_headers()
    files = {"file[]": (file_path, (content or "").encode("utf-8"), _content_type_for(file_path))}
    data = {"name": path, "bucketId": BUCKET}
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Storage upload failed for {file_path}: HTTP {resp.status_code} - {resp.text[:300]}")


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
    path = _storage_path(project_id, file_path)
    url = f"{NHOST_STORAGE_URL}/files/{BUCKET}/{path}"
    resp = requests.get(url, headers=_auth_headers(), timeout=30)
    if resp.status_code == 200:
        return resp.text
    if resp.status_code == 404:
        return None
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
    path = _storage_path(project_id, file_path)
    url = f"{NHOST_STORAGE_URL}/files/{BUCKET}/{path}"
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


async def upload_files(project_id: str, files: list[dict]) -> None:
    """Upload files to Nhost Storage."""
    if not NHOST_STORAGE_URL or not NHOST_ADMIN_SECRET:
        raise RuntimeError("NHOST_STORAGE_URL and NHOST_ADMIN_SECRET required")
    url = f"{NHOST_STORAGE_URL}/files"
    errors = []
    for f in files:
        fp = f.get("file_path", "")
        content = f.get("content", "")
        if not fp:
            continue
        path = _storage_path(project_id, fp)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers=_auth_headers(),
                    files={"file[]": (fp, content.encode("utf-8"), _content_type_for(fp))},
                    data={"name": path, "bucketId": BUCKET},
                    timeout=30,
                )
                if resp.status_code not in (200, 201):
                    errors.append(f"{fp}: HTTP {resp.status_code}")
        except Exception as e:
            errors.append(f"{fp}: {e}")
    if errors:
        raise RuntimeError(f"Storage upload failed: {'; '.join(errors[:5])}")


async def download_project_files(
    project_id: str,
    file_paths: list[str],
    db_fallback: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Download files from Nhost Storage."""
    results = {}
    for fp in file_paths:
        path = _storage_path(project_id, fp)
        url = f"{NHOST_STORAGE_URL}/files/{BUCKET}/{path}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=_auth_headers(), timeout=30)
                if resp.status_code == 200:
                    results[fp] = resp.text
                elif db_fallback and fp in db_fallback:
                    results[fp] = db_fallback[fp]
                else:
                    results[fp] = ""
        except Exception:
            if db_fallback and fp in db_fallback:
                results[fp] = db_fallback[fp]
            else:
                results[fp] = ""
    return results
