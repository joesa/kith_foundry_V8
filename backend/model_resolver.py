"""
Central model resolver — resolves which provider + model to use for a given task type.
"""
from models import ModelRouting, ProviderKey, SessionLocal

# Provider ID → litellm model prefix mapping
PROVIDER_PREFIXES = {
    "openai": "",            # litellm uses model ID directly for OpenAI
    "anthropic": "anthropic/",
    "google_ai": "gemini/",
    "gemini": "gemini/",
    "openrouter": "openrouter/",
    "ollama": "ollama/",
    "lm_studio": "openai/",  # LM Studio uses OpenAI-compatible API
    "openai_compatible": "openai/",  # Generic OpenAI-compatible endpoints
    "cohere": "cohere/",
    "huggingface": "huggingface/",
}

DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"


def _normalize_base_url(provider: str, base_url: str | None) -> str | None:
    """Normalize provider base URLs for LiteLLM expectations."""
    if not base_url:
        if provider == "lm_studio":
            return "http://localhost:1234/v1"
        return None

    normalized = base_url.rstrip("/")

    if provider == "lm_studio":
        # LM Studio in this app is routed through LiteLLM's OpenAI-compatible path,
        # which expects api_base ending in /v1.
        if normalized.endswith("/api/v1"):
            normalized = normalized[:-7] + "/v1"
        elif not normalized.endswith("/v1"):
            normalized = normalized + "/v1"

    return normalized


def resolve_model_for_task(user_id: str, task_type: str, db=None) -> dict:
    """
    Resolve the model config for a given user + task type.

    Returns dict with:
      - model: litellm-compatible model string
      - api_key: decrypted API key (or None)
      - api_base: custom base URL (or None)
      - provider_name: human-readable provider name
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Check for a user-specific task routing
        routing = (
            db.query(ModelRouting)
            .filter(ModelRouting.user_id == user_id, ModelRouting.task_type == task_type)
            .first()
        )

        provider_key = None
        if routing and routing.provider_id:
            provider_key = (
                db.query(ProviderKey)
                .filter(ProviderKey.id == routing.provider_id, ProviderKey.is_active == True)
                .first()
            )

        # 2. Fall back to user's default provider if no routing or provider not found
        if not provider_key:
            provider_key = (
                db.query(ProviderKey)
                .filter(
                    ProviderKey.user_id == user_id,
                    ProviderKey.is_default == True,
                    ProviderKey.is_active == True,
                )
                .first()
            )

        # 3. Fall back to any active provider
        if not provider_key:
            provider_key = (
                db.query(ProviderKey)
                .filter(
                    ProviderKey.user_id == user_id,
                    ProviderKey.is_active == True,
                )
                .first()
            )

        if not provider_key:
            # No user provider configured — fall back to server env API keys
            return _env_fallback()

        # Decrypt the API key
        from provider_api import decrypt_key
        api_key = decrypt_key(provider_key.api_key_encrypted)
        base_url = _normalize_base_url(provider_key.provider, provider_key.base_url)

        # Determine the model ID
        if routing and routing.model_id:
            model_id = routing.model_id
        else:
            # No specific model configured — use a sensible default per provider
            model_id = _default_model_for_provider(provider_key.provider)

        # Build the litellm-compatible model string
        prefix = PROVIDER_PREFIXES.get(provider_key.provider, "")
        if prefix and model_id.startswith(prefix):
            # Already has this provider's prefix
            litellm_model = model_id
        else:
            litellm_model = f"{prefix}{model_id}"

        return {
            "model": litellm_model,
            "api_key": api_key,
            "api_base": base_url,
            "provider_name": provider_key.name,
        }

    finally:
        if close_db:
            db.close()


def _env_fallback() -> dict:
    """Fall back to server env API keys when no user provider is configured."""
    import os
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if openai_key:
        return {"model": "gpt-4o", "api_key": openai_key, "api_base": None, "provider_name": "Server (OpenAI)"}
    if anthropic_key:
        return {"model": "anthropic/claude-sonnet-4-20250514", "api_key": anthropic_key, "api_base": None, "provider_name": "Server (Anthropic)"}
    if gemini_key:
        return {"model": "gemini/gemini-2.5-flash", "api_key": gemini_key, "api_base": None, "provider_name": "Server (Google AI)"}
    return {"model": None, "api_key": None, "api_base": None, "provider_name": None,
            "error": "No API provider configured. Add your API key in Profile → Settings."}


def _default_model_for_provider(provider: str) -> str:
    """Return a sensible default model ID for a given provider."""
    defaults = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "google_ai": "gemini-2.5-flash",
        "gemini": "gemini-2.5-flash",
        "openrouter": "anthropic/claude-sonnet-4-20250514",
        "ollama": "llama3",
        "lm_studio": "local-model",
        "openai_compatible": "local-model",
        "cohere": "command-r-plus",
    }
    return defaults.get(provider, "gpt-4o")
