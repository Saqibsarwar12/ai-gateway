"""Provider adapter base class + OpenAI-compatible adapter."""
import httpx
import json
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional
from dataclasses import dataclass, field
from app.core.config import settings


@dataclass
class ProviderConfig:
    id: str
    name: str
    provider_type: str
    base_url: str
    api_key: str
    headers: dict = field(default_factory=dict)
    models: list = field(default_factory=list)
    timeout: int = 60
    retry_policy: dict = field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 1.5})
    weight: int = 100
    region: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class ProviderResponse:
    status_code: int
    content: Any
    headers: dict = field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: float = 0.0
    cached: bool = False


@dataclass
class StreamingResponse:
    event: str  # content | done | error
    data: Any


class BaseProviderAdapter(ABC):
    """Abstract base for all provider adapters."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={"Authorization": f"Bearer {config.api_key}", **config.headers}
        )

    @abstractmethod
    async def chat_completion(self, payload: dict) -> ProviderResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def completion(self, payload: dict) -> ProviderResponse:
        ...

    @abstractmethod
    async def embeddings(self, payload: dict) -> ProviderResponse:
        ...

    @abstractmethod
    async def list_models(self) -> ProviderResponse:
        ...

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class OpenAIProviderAdapter(BaseProviderAdapter):
    """OpenAI-compatible provider adapter."""

    API_PATH = {
        "chat": "/v1/chat/completions",
        "completion": "/v1/completions",
        "embeddings": "/v1/embeddings",
        "models": "/v1/models",
        "images": "/v1/images/generations",
        "audio": "/v1/audio/transcriptions",
    }

    async def chat_completion(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        try:
            resp = await self.client.post(self.API_PATH["chat"], json=payload)
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                status_code=resp.status_code,
                content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                headers=dict(resp.headers),
                latency_ms=latency
            )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def completion(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        try:
            resp = await self.client.post(self.API_PATH["completion"], json=payload)
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                status_code=resp.status_code,
                content=resp.json(),
                latency_ms=latency
            )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def embeddings(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        try:
            resp = await self.client.post(self.API_PATH["embeddings"], json=payload)
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                status_code=resp.status_code,
                content=resp.json(),
                latency_ms=latency
            )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def list_models(self) -> ProviderResponse:
        import time
        start = time.perf_counter()
        try:
            resp = await self.client.get(self.API_PATH["models"])
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                status_code=resp.status_code,
                content=resp.json(),
                latency_ms=latency
            )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def stream_chat_completion(self, payload: dict) -> AsyncGenerator[StreamingResponse, None]:
        """Handle SSE streaming for chat completions."""
        import time
        start = time.perf_counter()
        try:
            async with self.client.stream("POST", self.API_PATH["chat"], json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield StreamingResponse(event="done", data=None)
                        else:
                            yield StreamingResponse(event="content", data=json.loads(data))
                latency = (time.perf_counter() - start) * 1000
                yield StreamingResponse(event="done", data={"latency_ms": latency})
        except Exception as e:
            yield StreamingResponse(event="error", data=str(e))


class AnthropicProviderAdapter(BaseProviderAdapter):
    """Anthropic Claude adapter."""

    async def chat_completion(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        try:
            # Anthropic uses /v1/messages
            resp = await self.client.post(
                "/v1/messages",
                json=payload,
                headers={"anthropic-version": "2023-06-01"}
            )
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                status_code=resp.status_code,
                content=resp.json(),
                latency_ms=latency
            )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def completion(self, payload: dict) -> ProviderResponse:
        return ProviderResponse(status_code=400, content=None, error="Anthropic does not support /v1/completions")

    async def embeddings(self, payload: dict) -> ProviderResponse:
        return ProviderResponse(status_code=400, content=None, error="Anthropic does not support embeddings")

    async def list_models(self) -> ProviderResponse:
        return ProviderResponse(
            status_code=200,
            content={"data": [{"id": "claude-3-5-sonnet-20241022"}]}
        )


class AzureOpenAIProviderAdapter(BaseProviderAdapter):
    """Azure OpenAI Service adapter — uses api-version header and different auth."""

    async def chat_completion(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        api_version = self.config.extra.get("api_version", "2024-02-01")
        try:
            async with self.client.stream(
                "POST",
                f"/chat/completions?api-version={api_version}",
                json=payload
            ) as resp:
                latency = (time.perf_counter() - start) * 1000
                if resp.headers.get("content-type", "").startswith("text/event-stream"):
                    chunks = []
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            chunks.append(json.loads(line[6:]))
                    return ProviderResponse(status_code=200, content=chunks, latency_ms=latency)
                else:
                    return ProviderResponse(
                        status_code=resp.status_code,
                        content=await resp.json(),
                        latency_ms=latency
                    )
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def completion(self, payload: dict) -> ProviderResponse:
        return ProviderResponse(status_code=501, content=None, error="Not implemented")

    async def embeddings(self, payload: dict) -> ProviderResponse:
        import time
        start = time.perf_counter()
        api_version = self.config.extra.get("api_version", "2024-02-01")
        try:
            resp = await self.client.post(
                f"/embeddings?api-version={api_version}",
                json=payload
            )
            latency = (time.perf_counter() - start) * 1000
            return ProviderResponse(status_code=resp.status_code, content=await resp.json(), latency_ms=latency)
        except Exception as e:
            return ProviderResponse(status_code=500, content=None, error=str(e))

    async def list_models(self) -> ProviderResponse:
        return ProviderResponse(status_code=200, content={"data": []})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
PROVIDER_ADAPTERS: dict[str, type[BaseProviderAdapter]] = {
    "openai": OpenAIProviderAdapter,
    "anthropic": AnthropicProviderAdapter,
    "azure": AzureOpenAIProviderAdapter,
    "custom": OpenAIProviderAdapter,  # custom uses OpenAI-compatible format
    "groq": OpenAIProviderAdapter,
    "deepseek": OpenAIProviderAdapter,
    "openrouter": OpenAIProviderAdapter,
    "ollama": OpenAIProviderAdapter,
    "nvidia": OpenAIProviderAdapter,
    "lmstudio": OpenAIProviderAdapter,
    "vllm": OpenAIProviderAdapter,
    "together": OpenAIProviderAdapter,
    "fireworks": OpenAIProviderAdapter,
    "mistral": OpenAIProviderAdapter,
    "cohere": OpenAIProviderAdapter,
    "google": OpenAIProviderAdapter,
    "custom_llm": OpenAIProviderAdapter,
}


def get_provider_adapter(config: ProviderConfig) -> BaseProviderAdapter:
    """Factory to get the right adapter for a provider type."""
    adapter_cls = PROVIDER_ADAPTERS.get(config.provider_type, OpenAIProviderAdapter)
    return adapter_cls(config)
