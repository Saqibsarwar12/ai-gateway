"""Provider adapters — OpenAI-compatible + Anthropic + custom."""

import httpx
import json
import time
import asyncio
from typing import Optional, AsyncIterator, Any


class ProviderAdapter:
    """Universal OpenAI-compatible provider adapter."""

    def __init__(
        self,
        name: str = "unknown",
        base_url: str = "",
        api_key: str = "",
        models: list = None,
        requires_proxy: bool = False,
        proxy_url: Optional[str] = None,
        timeout: int = 60,
        headers: dict = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key or ""
        self.models = models or []
        self.requires_proxy = requires_proxy
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.headers = headers or {}

    def _client(self) -> httpx.AsyncClient:
        kwargs = {"timeout": self.timeout}
        if self.requires_proxy and self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.headers,
        }

    async def chat(self, model: str, messages: list, **kwargs) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": model, "messages": messages, **{k: v for k, v in kwargs.items() if v is not None}},
            )
            r.raise_for_status()
            return r.json()

    async def chat_stream(self, model: str, messages: list, **kwargs) -> AsyncIterator[str]:
        async with self._client() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": model, "messages": messages, "stream": True, **{k: v for k, v in kwargs.items() if v is not None}},
            ) as r:
                async for line in r.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]
                    if line == "data: [DONE]":
                        break

    async def list_models(self) -> list:
        try:
            async with self._client() as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers())
                if r.status_code == 200:
                    return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            pass
        return []

    async def health_check(self) -> dict:
        start = time.time()
        try:
            async with self._client() as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers())
                return {
                    "ok": r.status_code == 200,
                    "latency_ms": int((time.time() - start) * 1000),
                    "status_code": r.status_code,
                    "provider": self.name,
                }
        except Exception as e:
            return {"ok": False, "latency_ms": 0, "error": str(e), "provider": self.name}


class AnthropicAdapter(ProviderAdapter):
    """Anthropic-specific adapter (converts OpenAI-format messages to Anthropic format)."""

    async def chat(self, model: str, messages: list, **kwargs) -> dict:
        system = None
        converted = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                converted.append(m)

        body = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": converted,
        }
        if system:
            body["system"] = system
        if "temperature" in kwargs:
            body["temperature"] = kwargs["temperature"]

        async with self._client() as client:
            r = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "id": data.get("id", ""),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": data["content"][0]["text"]},
                        "finish_reason": data.get("stop_reason", "stop"),
                    }
                ],
                "usage": {
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        data.get("usage", {}).get("input_tokens", 0)
                        + data.get("usage", {}).get("output_tokens", 0)
                    ),
                },
            }


def make_adapter(provider: dict) -> ProviderAdapter:
    """Factory: build the right adapter for a provider config."""
    ptype = provider.get("provider_type", "openai")
    if ptype == "anthropic":
        return AnthropicAdapter(
            name=provider.get("id") or provider.get("name"),
            base_url=provider.get("base_url", "https://api.anthropic.com/v1"),
            api_key=provider.get("api_key", ""),
            models=provider.get("models", []),
            requires_proxy=provider.get("requires_proxy", False),
            proxy_url=provider.get("proxy_url"),
        )
    return ProviderAdapter(
        name=provider.get("id") or provider.get("name"),
        base_url=provider.get("base_url", ""),
        api_key=provider.get("api_key", ""),
        models=provider.get("models", []),
        requires_proxy=provider.get("requires_proxy", False),
        proxy_url=provider.get("proxy_url"),
    )


OpenAIAdapter = ProviderAdapter
