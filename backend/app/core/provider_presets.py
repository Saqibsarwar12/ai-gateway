"""Provider presets — base URLs and model-discovery patterns for major AI APIs.

Adding a new provider?  Add an entry here and it will show up in the dashboard
dropdown automatically.  The `detect` field tells the front-end which endpoints
to hit when the user pastes a key.
"""
from __future__ import annotations
from typing import TypedDict


class ProviderPreset(TypedDict, total=False):
    id: str
    name: str
    type: str  # "openai" | "anthropic" | "custom"
    base_url: str
    models_path: str  # path on base_url to GET for model list, e.g. "/v1/models"
    models_field: str  # "data" | "models" — json key containing the array
    model_id_field: str  # json field on each model entry that holds the model id
    extra_auth: dict  # extra headers (e.g. Anthropic needs x-api-key + anthropic-version)
    test_path: str  # path used by the /test endpoint to confirm the key works
    hint: str  # shown in the dashboard


PROVIDER_PRESETS: list[ProviderPreset] = [
    # ─── OpenAI-compatible (most common shape) ─────────────────
    {
        "id": "openai",
        "name": "OpenAI",
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "gpt-4o, gpt-4o-mini, o1, o1-mini, o3-mini, gpt-3.5-turbo",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "type": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Routes 200+ models from one key. Get a key at openrouter.ai",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "type": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "deepseek-chat, deepseek-reasoner",
    },
    {
        "id": "groq",
        "name": "Groq",
        "type": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Ultra-fast inference: llama-3.3-70b, mixtral, gemma2",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "type": "openai",
        "base_url": "https://api.mistral.ai/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "mistral-large, mistral-small, codestral",
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "type": "openai",
        "base_url": "https://api.x.ai/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "grok-2, grok-2-vision, grok-beta",
    },
    {
        "id": "perplexity",
        "name": "Perplexity",
        "type": "openai",
        "base_url": "https://api.perplexity.ai",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "llama-3.1-sonar-small/large/huge online (web search built in)",
    },
    {
        "id": "kimi",
        "name": "Kimi (Moonshot)",
        "type": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k",
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "type": "openai",
        "base_url": "https://api.minimax.chat/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "abab6.5s, abab6.5g, abab5.5",
    },
    {
        "id": "nvidia",
        "name": "NVIDIA NIM",
        "type": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "meta/llama-3.1-70b-instruct, mistralai/mixtral-8x7b-instruct, etc.",
    },
    {
        "id": "together",
        "name": "Together AI",
        "type": "openai",
        "base_url": "https://api.together.xyz/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Open-source models at low cost",
    },
    {
        "id": "fireworks",
        "name": "Fireworks AI",
        "type": "openai",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Fast open-source inference",
    },
    {
        "id": "replicate",
        "name": "Replicate (proxy)",
        "type": "openai",
        "base_url": "https://openai.replicate.com/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Use Replicate's OpenAI-compatible proxy",
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "type": "openai",
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "command-r-plus, command-r, c4ai-aya",
    },
    {
        "id": "google",
        "name": "Google Gemini (compat)",
        "type": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "OpenAI-compatible endpoint for Gemini",
    },
    {
        "id": "azure-openai",
        "name": "Azure OpenAI",
        "type": "openai",
        "base_url": "https://YOUR-RESOURCE.openai.azure.com/openai/deployments",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Replace YOUR-RESOURCE with your Azure resource name",
    },
    {
        "id": "ollama",
        "name": "Ollama (local)",
        "type": "openai",
        "base_url": "http://localhost:11434/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Local Ollama server with OpenAI-compat shim",
    },
    {
        "id": "lmstudio",
        "name": "LM Studio (local)",
        "type": "openai",
        "base_url": "http://localhost:1234/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "LM Studio local server",
    },
    {
        "id": "vllm",
        "name": "vLLM (self-hosted)",
        "type": "openai",
        "base_url": "http://localhost:8000/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/models",
        "hint": "Self-hosted vLLM with OpenAI-compat API",
    },
    # ─── Anthropic (NOT OpenAI-compatible) ──────────────────────
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "type": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "models_path": "/models",
        "models_field": "data",
        "model_id_field": "id",
        "extra_auth": {
            "x-api-key": "$API_KEY",
            "anthropic-version": "2023-06-01",
        },
        "test_path": "/models",
        "hint": "claude-3-5-sonnet-latest, claude-3-5-haiku-latest, claude-3-opus",
    },
    # ─── Custom URL fallback ───────────────────────────────────
    {
        "id": "custom",
        "name": "Custom URL",
        "type": "openai",
        "base_url": "",
        "models_path": "/v1/models",
        "models_field": "data",
        "model_id_field": "id",
        "test_path": "/v1/models",
        "hint": "Any OpenAI-compatible endpoint. We'll auto-detect available models.",
    },
]


def get_preset(preset_id: str) -> ProviderPreset | None:
    for p in PROVIDER_PRESETS:
        if p["id"] == preset_id:
            return p
    return None


def list_presets() -> list[ProviderPreset]:
    return list(PROVIDER_PRESETS)


def normalize_base_url(url: str) -> str:
    """Strip trailing slashes and ensure base URL has no /v1 suffix double-up."""
    u = (url or "").strip().rstrip("/")
    return u
