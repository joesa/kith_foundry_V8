import os
import base64
import aiohttp
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from models import ProviderKey, engine, Base, User
from auth import get_current_user, get_optional_user
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

router = APIRouter()

# ── AES-256-GCM Encryption ────────────────────────────────────────────────────
# Key must be 32 raw bytes, stored base64-urlsafe in PROVIDER_ENCRYPTION_KEY.
# Encrypted values are stored as "gcm:<base64(nonce[12] + ciphertext + tag[16])>".

_aes_key_cache: bytes | None = None


def _lm_studio_openai_base(base_url: str | None) -> str:
    """Return LM Studio base URL normalized for OpenAI-compatible endpoints."""
    base = (base_url or "http://localhost:1234").rstrip("/")
    if base.endswith("/api/v1"):
        base = base[:-7] + "/v1"
    elif not base.endswith("/v1"):
        base = base + "/v1"
    return base


def _lm_studio_rest_base(base_url: str | None) -> str:
    """Return LM Studio base URL normalized for REST API v1 endpoints."""
    base = (base_url or "http://localhost:1234").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3] + "/api/v1"
    elif not base.endswith("/api/v1"):
        base = base + "/api/v1"
    return base


def _get_aes_key() -> bytes:
    global _aes_key_cache
    if _aes_key_cache is None:
        raw = os.getenv("PROVIDER_ENCRYPTION_KEY", "")
        if not raw:
            raw = base64.urlsafe_b64encode(os.urandom(32)).decode()
            print(f"⚠️  No PROVIDER_ENCRYPTION_KEY in .env. Generated temporary: {raw}")
            print(f"   Add PROVIDER_ENCRYPTION_KEY={raw} to .env to persist across restarts.")
        # Decode — pad to multiple of 4 for safety
        key_bytes = base64.urlsafe_b64decode(raw + "==")
        if len(key_bytes) < 32:
            raise ValueError(f"PROVIDER_ENCRYPTION_KEY decodes to {len(key_bytes)} bytes; need 32.")
        _aes_key_cache = key_bytes[:32]
    return _aes_key_cache


def encrypt_key(api_key: str) -> str:
    """AES-256-GCM encrypt. Returns 'gcm:<base64url(nonce+ciphertext+tag)>'."""
    nonce = os.urandom(12)          # 96-bit nonce (GCM spec recommendation)
    ct = AESGCM(_get_aes_key()).encrypt(nonce, api_key.encode("utf-8"), None)
    return "gcm:" + base64.urlsafe_b64encode(nonce + ct).decode()


def decrypt_key(encrypted: str) -> str:
    """Decrypt AES-256-GCM (gcm: prefix). Falls back to Fernet for legacy rows."""
    if encrypted.startswith("gcm:"):
        data = base64.urlsafe_b64decode(encrypted[4:] + "==")
        nonce, ct = data[:12], data[12:]
        return AESGCM(_get_aes_key()).decrypt(nonce, ct, None).decode("utf-8")
    # Legacy Fernet fallback (rows encrypted before AES-256-GCM upgrade)
    try:
        from cryptography.fernet import Fernet
        fernet_key = os.getenv("PROVIDER_ENCRYPTION_KEY", "")
        return Fernet(fernet_key.encode()).decrypt(encrypted.encode()).decode()
    except Exception:
        raise ValueError("Cannot decrypt provider key — unsupported format or wrong key.")


def mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "••••••••"
    return api_key[:4] + "••••••••" + api_key[-4:]


# --- Pydantic models ---
class ProviderCreate(BaseModel):
    name: str
    provider: str
    api_key: str
    base_url: Optional[str] = None
    is_default: bool = False


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# Tables are created by main.py at startup — no need to call create_all here.


def get_db():
    from sqlalchemy.orm import Session as SQLSession
    return SQLSession(bind=engine)


# --- Routes ---
@router.get("/api/v1/providers")
def list_providers(user: User = Depends(get_current_user)):
    db = get_db()
    try:
        keys = db.query(ProviderKey).filter(
            ProviderKey.user_id == user.id
        ).order_by(ProviderKey.created_at.desc()).all()
        result = []
        for k in keys:
            try:
                masked = mask_key(decrypt_key(k.api_key_encrypted))
            except Exception:
                masked = "••••••••(key error)"
            result.append({
                "id": k.id,
                "name": k.name,
                "provider": k.provider,
                "api_key_masked": masked,
                "base_url": k.base_url,
                "is_default": k.is_default,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            })
        return {"providers": result}
    finally:
        db.close()


@router.post("/api/v1/providers")
def create_provider(data: ProviderCreate, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        # If setting as default, clear existing defaults for this user+provider
        if data.is_default:
            db.query(ProviderKey).filter(
                ProviderKey.user_id == user.id,
                ProviderKey.provider == data.provider,
                ProviderKey.is_default == True
            ).update({"is_default": False})

        key = ProviderKey(
            user_id=user.id,
            name=data.name,
            provider=data.provider,
            api_key_encrypted=encrypt_key(data.api_key),
            base_url=data.base_url,
            is_default=data.is_default,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(key)
        db.commit()
        db.refresh(key)
        return {
            "id": key.id,
            "name": key.name,
            "provider": key.provider,
            "message": "Provider connected successfully"
        }
    finally:
        db.close()


@router.put("/api/v1/providers/{provider_id}")
def update_provider(provider_id: int, data: ProviderUpdate, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")

        if data.name is not None:
            key.name = data.name
        if data.api_key is not None:
            key.api_key_encrypted = encrypt_key(data.api_key)
        if data.base_url is not None:
            key.base_url = data.base_url

        db.commit()
        return {"message": "Provider updated successfully"}
    finally:
        db.close()


@router.delete("/api/v1/providers/{provider_id}")
def delete_provider(provider_id: int, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")
        db.delete(key)
        db.commit()
        return {"message": "Provider deleted successfully"}
    finally:
        db.close()


@router.patch("/api/v1/providers/{provider_id}/default")
def set_default_provider(provider_id: int, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")

        # Clear all existing defaults for this user
        db.query(ProviderKey).filter(ProviderKey.user_id == user.id, ProviderKey.is_default == True).update({"is_default": False})
        key.is_default = True
        db.commit()
        return {"message": f"{key.name} set as default for all generations"}
    finally:
        db.close()


@router.patch("/api/v1/providers/{provider_id}/toggle")
def toggle_provider(provider_id: int, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")

        key.is_active = not key.is_active
        db.commit()
        return {
            "is_active": key.is_active,
            "message": f"{key.name} {'activated' if key.is_active else 'deactivated'}"
        }
    finally:
        db.close()


@router.post("/api/v1/providers/{provider_id}/test")
async def test_provider(provider_id: int, user: User = Depends(get_current_user)):
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")

        api_key = decrypt_key(key.api_key_encrypted)
        provider = key.provider.lower()
        base_url = key.base_url

        try:
            async with aiohttp.ClientSession() as session:
                if provider == "openai":
                    url = (base_url or "https://api.openai.com") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            return {"success": True, "message": "Connection successful — OpenAI API is reachable."}
                        else:
                            body = await resp.text()
                            return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

                elif provider == "anthropic":
                    url = (base_url or "https://api.anthropic.com") + "/v1/messages"
                    async with session.post(url,
                        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status in (200, 201):
                            return {"success": True, "message": "Connection successful — Anthropic API is reachable."}
                        else:
                            body = await resp.text()
                            return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

                elif provider == "google_ai":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            return {"success": True, "message": "Connection successful — Google AI API is reachable."}
                        else:
                            body = await resp.text()
                            return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

                elif provider in ("openrouter", "openai_compatible", "azure_openai"):
                    url = (base_url or "https://openrouter.ai/api") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            return {"success": True, "message": f"Connection successful — {key.provider} is reachable."}
                        else:
                            body = await resp.text()
                            return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

                elif provider == "ollama":
                    url = (base_url or "http://localhost:11434") + "/api/tags"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            return {"success": True, "message": "Connection successful — Ollama is reachable."}
                        else:
                            return {"success": False, "message": f"HTTP {resp.status}"}

                elif provider == "lm_studio":
                    # Prefer OpenAI-compatible API used by LiteLLM, then fall back to
                    # LM Studio REST API v1 for instances configured in that mode.
                    openai_url = _lm_studio_openai_base(base_url) + "/models"
                    rest_url = _lm_studio_rest_base(base_url) + "/models"
                    for url in (openai_url, rest_url):
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                return {"success": True, "message": "Connection successful — LM Studio is reachable."}
                    return {"success": False, "message": "LM Studio unreachable on both /v1/models and /api/v1/models"}

                else:
                    # Generic OpenAI-compatible test
                    url = (base_url or "https://api.example.com") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            return {"success": True, "message": "Connection successful."}
                        else:
                            body = await resp.text()
                            return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

        except aiohttp.ClientError as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Test failed: {str(e)}"}

    finally:
        # Update last_used_at
        key.last_used_at = datetime.utcnow()
        db.commit()
        db.close()


@router.get("/api/v1/providers/{provider_id}/models")
async def fetch_provider_models(provider_id: int, user: User = Depends(get_current_user)):
    """Fetch available models from a configured provider."""
    db = get_db()
    try:
        key = db.query(ProviderKey).filter(ProviderKey.id == provider_id, ProviderKey.user_id == user.id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Provider not found")

        api_key = decrypt_key(key.api_key_encrypted)
        provider = key.provider.lower()
        base_url = key.base_url

        try:
            async with aiohttp.ClientSession() as session:
                if provider == "openai":
                    url = (base_url or "https://api.openai.com") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["id"] for m in data.get("data", [])
                                            if any(k in m["id"] for k in ("gpt", "o1", "o3", "o4"))])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

                elif provider == "anthropic":
                    # Anthropic doesn't have a /models endpoint, return known models
                    return {
                        "models": [
                            "claude-sonnet-4-20250514",
                            "claude-3-5-haiku-20241022",
                            "claude-3-opus-20240229",
                            "claude-3-haiku-20240307",
                        ],
                        "provider": key.name
                    }

                elif provider == "google_ai":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["name"].replace("models/", "") for m in data.get("models", [])
                                            if "gemini" in m.get("name", "")])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

                elif provider in ("openrouter", "openai_compatible", "azure_openai"):
                    url = (base_url or "https://openrouter.ai/api") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["id"] for m in data.get("data", [])])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

                elif provider == "ollama":
                    url = (base_url or "http://localhost:11434") + "/api/tags"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["name"] for m in data.get("models", [])])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

                elif provider == "lm_studio":
                    openai_url = _lm_studio_openai_base(base_url) + "/models"
                    rest_url = _lm_studio_rest_base(base_url) + "/models"

                    # OpenAI-compatible shape: { data: [{ id: "..." }] }
                    async with session.get(openai_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["id"] for m in data.get("data", []) if m.get("id")])
                            return {"models": models, "provider": key.name}

                    # LM Studio REST API v1 shape can differ; normalize to string IDs.
                    async with session.get(rest_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_models = data.get("data") or data.get("models") or []
                            models: list[str] = []
                            for m in raw_models:
                                if isinstance(m, dict):
                                    mid = m.get("id") or m.get("model") or m.get("name")
                                    if mid:
                                        models.append(str(mid))
                                elif isinstance(m, str):
                                    models.append(m)
                            return {"models": sorted(set(models)), "provider": key.name}

                    return {"models": [], "error": "LM Studio model endpoint unavailable on /v1/models and /api/v1/models"}

                elif provider == "cohere":
                    url = (base_url or "https://api.cohere.ai") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m.get("name", m.get("id", "")) for m in data.get("models", data.get("data", []))])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

                elif provider == "huggingface":
                    # HuggingFace Inference API — return commonly used models
                    return {
                        "models": [
                            "meta-llama/Meta-Llama-3-70B-Instruct",
                            "mistralai/Mixtral-8x7B-Instruct-v0.1",
                            "microsoft/Phi-3-mini-4k-instruct",
                        ],
                        "provider": key.name
                    }

                else:
                    # Generic: try /v1/models
                    url = (base_url or "https://api.example.com") + "/v1/models"
                    async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = sorted([m["id"] for m in data.get("data", [])])
                            return {"models": models, "provider": key.name}
                        return {"models": [], "error": f"HTTP {resp.status}"}

        except Exception as e:
            return {"models": [], "error": str(e)}

    finally:
        db.close()

