import os
import aiohttp
import asyncio
from fastapi import APIRouter

router = APIRouter()

async def fetch_openai_models():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Filter for gpt models, or just return all
                    models = [m["id"] for m in data.get("data", []) if "gpt" in m["id"] or "o1" in m["id"] or "o3" in m["id"]]
                    return [{"id": m, "provider": "OpenAI"} for m in models]
    except Exception as e:
        print(f"Error fetching OpenAI models: {e}")
    return []

async def fetch_anthropic_models():
    # Per user instructions, hardcode requested Anthropic models and specifically exclude 
    # Sonnet 3.5 - 3.7. Also adding claude-sonnet-4-6 for the requested test.
    return [
        {"id": "anthropic/claude-3-opus-20240229", "provider": "Anthropic"},
        {"id": "anthropic/claude-3-5-haiku-20241022", "provider": "Anthropic"},
        {"id": "anthropic/claude-sonnet-4-6", "provider": "Anthropic"}
    ]

async def fetch_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"].replace("models/", "") for m in data.get("models", []) if "gemini" in m["name"]]
                    return [{"id": m, "provider": "Gemini"} for m in models]
    except Exception as e:
        print(f"Error fetching Gemini models: {e}")
    return []

async def fetch_openrouter_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return [{"id": m, "provider": "OpenRouter"} for m in models]
    except Exception as e:
        print(f"Error fetching OpenRouter models: {e}")
    return []

@router.get("/api/v1/models")
async def get_models():
    # Fetch all models concurrently
    results = await asyncio.gather(
        fetch_openai_models(),
        fetch_anthropic_models(),
        fetch_gemini_models(),
        fetch_openrouter_models()
    )
    
    available_models = []
    for r in results:
        if r:
            available_models.extend(r)
            
    # Add Local Models
    local_models = [
        {"id": "ollama/llama3", "provider": "Local (Ollama)"},
        {"id": "ollama/mistral", "provider": "Local (Ollama)"},
        {"id": "lm_studio/local-model", "provider": "Local (LM Studio)"}
    ]
    available_models.extend(local_models)
    
    return {"models": available_models}
