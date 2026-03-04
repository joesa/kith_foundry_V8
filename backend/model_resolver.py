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
    "cohere": "cohere/",
    "huggingface": "huggingface/",
}

DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"


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
            # No provider configured at all — return default
            return {
                "model": DEFAULT_MODEL,
                "api_key": None,
                "api_base": None,
                "provider_name": "Default",
            }

        # Decrypt the API key
        from provider_api import decrypt_key
        api_key = decrypt_key(provider_key.api_key_encrypted)
        base_url = provider_key.base_url

        # Determine the model ID
        if routing and routing.model_id:
            model_id = routing.model_id
        else:
            # No specific model configured — use a sensible default per provider
            model_id = _default_model_for_provider(provider_key.provider)

        # Build the litellm-compatible model string
        prefix = PROVIDER_PREFIXES.get(provider_key.provider, "")
        if model_id.startswith(prefix) or "/" in model_id:
            # Already prefixed or has a provider prefix
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
        "cohere": "command-r-plus",
    }
    return defaults.get(provider, "gpt-4o")
