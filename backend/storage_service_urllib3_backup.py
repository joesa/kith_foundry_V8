"""
Supabase Storage service for project code files.

Files are stored in the 'project-files' bucket at:
    {project_id}/{file_path}   e.g.  abc-123/src/App.tsx

The 'files' DB table keeps only metadata (file_path, updated_at).
Content is stored exclusively in Supabase Storage.

Backward compat: if a file doesn't exist in Storage yet (legacy rows),
callers fall back to the DB `content` column automatically.

Upload strategy
---------------
ALL HTTP calls use urllib3 directly (HTTP/1.1 only).  The Supabase Python
SDK is NOT used for any HTTP operation.  The SDK internally uses httpx
which negotiates HTTP/2 via TLS ALPN (through the h2 library).  HTTP/2
multiplexes all requests onto one TCP connection; when many files are
uploaded quickly, the server's stream limit is exhausted and it sends
GOAWAY with error_code:9 (ConnectionTerminated).

urllib3 has ZERO HTTP/2 support -- the error is physically impossible.
"""
import os
import json
import ssl
import zlib
import asyncio
import random
import time
from typing import Optional

import urllib3
from dotenv import load_dotenv

load_dotenv()

BUCKET = "project-files"

# -- urllib3 pool (HTTP/1.1 only, no HTTP/2, ever) -------------------------
# urllib3 >=2 negotiates HTTP/2 via TLS ALPN when the `h2` package is
# installed (pulled in by httpx / supabase SDK).  Force HTTP/1.1 by
# creating an SSL context that only advertises "http/1.1" in ALPN.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.set_alpn_protocols(["http/1.1"])

_http = urllib3.PoolManager(
    num_pools=4,
    maxsize=4,
    retries=urllib3.Retry(total=0),   # we handle retries ourselves
    timeout=urllib3.Timeout(connect=10.0, read=30.0),
    ssl_context=_ssl_ctx,
)

_SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {_SERVICE_KEY}",
        "apikey": _SERVICE_KEY,
    }


def _storage_path(project_id: str, file_path: str) -> str:
    """Normalise to '{project_id}/{file_path}' with no leading slash."""
    return f"{project_id}/{file_path.lstrip('/')}"


# -- Bucket setup ----------------------------------------------------------

def ensure_bucket_exists() -> None:
    """Create the storage bucket if it doesn't already exist (idempotent)."""
    url = f"{_SUPABASE_URL}/storage/v1/bucket"
    hdrs = {**_auth_headers(), "Content-Type": "application/json"}
    try:
        # List buckets
        resp = _http.request("GET", url, headers=hdrs)
        if resp.status == 200:
            buckets = json.loads(resp.data.decode("utf-8"))
            names = [b.get("name") for b in buckets if isinstance(b, dict)]
            if BUCKET in names:
                print(f"[storage] Bucket '{BUCKET}' already exists")
                return
        # Create bucket
        body = json.dumps({
            "id": BUCKET,
            "name": BUCKET,
            "public": False,
        }).encode("utf-8")
        resp2 = _http.request("POST", url, body=body, headers=hdrs)
        if resp2.status in (200, 201):
            print(f"[storage] Created bucket '{BUCKET}'")
        else:
            msg = resp2.data.decode("utf-8", errors="replace")[:200]
            if "already exists" in msg.lower() or "duplicate" in msg.lower():
                print(f"[storage] Bucket '{BUCKET}' already exists")
            else:
                print(f"[storage] Warning: bucket create returned {resp2.status}: {msg}")
    except Exception as e:
        print(f"[storage] Warning: could not ensure bucket exists: {e}")


# -- Upload (urllib3 HTTP/1.1 only) ----------------------------------------

def upload_file_sync(
    project_id: str,
    file_path: str,
    content: str,
    _retries: int = 5,
) -> None:
    """Upload / overwrite a single file in Supabase Storage (zlib-compressed).

    Uses urllib3 (pure HTTP/1.1) so ConnectionTerminated / error_code:9
    stream exhaustion is physically impossible.
    """
    path = _storage_path(project_id, file_path)
    data = zlib.compress((content or "").encode("utf-8"), level=6)
    url = f"{_SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"
    hdrs = {
        **_auth_headers(),
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",
    }

    for attempt in range(1, _retries + 1):
        try:
            resp = _http.request("POST", url, body=data, headers=hdrs)

            if resp.status in (200, 201):
                return  # success

            # Server error -> retry with backoff
            if resp.status >= 500 and attempt < _retries:
                wait = min(10.0, (1.2 ** attempt) + attempt + random.uniform(0.0, 0.8))
                print(
                    f"[storage] Server {resp.status} uploading {file_path} "
                    f"(attempt {attempt}/{_retries}) - retrying in {wait:.1f}s"
                )
                time.sleep(wait)
                continue

            # Client error -> don't retry
            body_text = resp.data.decode("utf-8", errors="replace")[:300]
            raise RuntimeError(
                f"Storage upload failed for {file_path}: HTTP {resp.status} - {body_text}"
            )

        except RuntimeError:
            raise
        except Exception as e:
            if attempt < _retries:
                wait = min(10.0, (1.2 ** attempt) + attempt + random.uniform(0.0, 0.8))
                print(
                    f"[storage] Transient error uploading {file_path} "
                    f"(attempt {attempt}/{_retries}): {e} - retrying in {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"Storage upload failed for {file_path}: {e}"
                ) from e


def upload_files_sync(project_id: str, files: list[dict]) -> None:
    """Upload a batch of files.  Each dict: {file_path, content}.

    Continues uploading remaining files if one fails; collects errors and
    raises after all files have been attempted.
    """
    errors: list[str] = []

    for f in files:
        fp = f.get("file_path", "")
        content = f.get("content", "")
        if not fp:
            continue
        try:
            upload_file_sync(project_id, fp, content)
        except Exception as e:
            print(f"[storage] Upload error for {fp}: {e}")
            errors.append(f"{fp}: {e}")

    if errors:
        raise RuntimeError(
            f"Storage upload failed for {len(errors)} file(s): "
            + "; ".join(errors[:5])
        )


# -- Download (urllib3 HTTP/1.1 only) --------------------------------------

def download_file_sync(project_id: str, file_path: str) -> Optional[str]:
    """Download a single file.  Returns content string, or None if not found."""
    path = _storage_path(project_id, file_path)
    url = f"{_SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"
    hdrs = _auth_headers()
    try:
        resp = _http.request("GET", url, headers=hdrs)
        if resp.status == 200:
            raw = resp.data
            if not raw:
                return ""
            # Try decompressing - falls back to raw UTF-8 for legacy uncompressed files
            try:
                return zlib.decompress(raw).decode("utf-8")
            except (zlib.error, Exception):
                return raw.decode("utf-8", errors="replace")
        if resp.status == 404:
            return None
        # Other error
        return None
    except Exception as e:
        print(f"[storage] Download error for {file_path}: {e}")
        return None


def download_project_files_sync(
    project_id: str,
    file_paths: list[str],
    db_fallback: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Download all files for a project.  Returns {file_path: content}.

    db_fallback: optional {file_path: content} from DB used when a file
    doesn't exist in Storage yet (backward compat).
    """
    results: dict[str, str] = {}
    for fp in file_paths:
        content = download_file_sync(project_id, fp)
        if content is None and db_fallback:
            content = db_fallback.get(fp, "")
            if content:
                print(f"[storage] Using DB fallback for legacy file: {fp}")
        results[fp] = content or ""
    return results


# -- Delete (urllib3 HTTP/1.1 only) ----------------------------------------

def delete_file_sync(project_id: str, file_path: str) -> None:
    path = _storage_path(project_id, file_path)
    url = f"{_SUPABASE_URL}/storage/v1/object/{BUCKET}"
    hdrs = {**_auth_headers(), "Content-Type": "application/json"}
    body = json.dumps({"prefixes": [path]}).encode("utf-8")
    _http.request("DELETE", url, body=body, headers=hdrs)


def delete_project_files_sync(project_id: str, file_paths: list[str]) -> None:
    """Delete all listed files for a project from Storage."""
    if not file_paths:
        return
    paths = [_storage_path(project_id, fp) for fp in file_paths]
    url = f"{_SUPABASE_URL}/storage/v1/object/{BUCKET}"
    hdrs = {**_auth_headers(), "Content-Type": "application/json"}
    body = json.dumps({"prefixes": paths}).encode("utf-8")
    _http.request("DELETE", url, body=body, headers=hdrs)


def delete_all_project_files_sync(project_id: str) -> int:
    """List and delete every file stored under {project_id}/ in the bucket.

    Supabase Storage lists up to 100 items per call, so we page until empty.
    Returns the total number of files deleted.
    """
    all_paths: list[str] = []
    offset = 0
    limit = 100
    list_url = f"{_SUPABASE_URL}/storage/v1/object/list/{BUCKET}"
    hdrs = {**_auth_headers(), "Content-Type": "application/json"}

    while True:
        try:
            body = json.dumps({
                "prefix": f"{project_id}/",
                "limit": limit,
                "offset": offset,
            }).encode("utf-8")
            resp = _http.request("POST", list_url, body=body, headers=hdrs)
            if resp.status != 200:
                print(f"[storage] Warning: listing files returned {resp.status}")
                break
            items = json.loads(resp.data.decode("utf-8"))
            if not items:
                break
            for item in items:
                name = item.get("name") if isinstance(item, dict) else None
                if name:
                    all_paths.append(f"{project_id}/{name}")
            if len(items) < limit:
                break
            offset += limit
        except Exception as e:
            print(f"[storage] Warning: could not list files for project {project_id}: {e}")
            break

    if all_paths:
        try:
            del_url = f"{_SUPABASE_URL}/storage/v1/object/{BUCKET}"
            body = json.dumps({"prefixes": all_paths}).encode("utf-8")
            resp = _http.request("DELETE", del_url, body=body, headers=hdrs)
            if resp.status in (200, 201):
                print(f"[storage] Deleted {len(all_paths)} file(s) for project {project_id}")
            else:
                print(f"[storage] Warning: delete returned {resp.status}")
        except Exception as e:
            print(f"[storage] Warning: could not delete files for project {project_id}: {e}")
    return len(all_paths)


# -- Async wrappers --------------------------------------------------------

async def upload_files(project_id: str, files: list[dict]) -> None:
    await asyncio.to_thread(upload_files_sync, project_id, files)


async def download_project_files(
    project_id: str,
    file_paths: list[str],
    db_fallback: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    return await asyncio.to_thread(
        download_project_files_sync, project_id, file_paths, db_fallback,
    )


