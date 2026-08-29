"""Provider adapters — OpenAI-compatible + Anthropic + custom."""

import httpx
import json
import time
import asyncio
from typing import Optional, AsyncIterator, Any


class UpstreamError(Exception):
    """Typed upstream provider failure, parsed from the provider's response.

    Carries the HTTP status the provider returned, a machine-readable code
    (e.g. "invalid_api_key", "model_not_found") and the provider's own
    message, so the gateway can surface the REAL cause to clients instead of
    a generic 500 "All providers failed".
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
        provider_id: Optional[str] = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.provider_id = provider_id
        super().__init__(f"{status_code} {code}: {message or code}")


def parse_upstream_error(response: httpx.Response, provider_id: Optional[str] = None) -> UpstreamError:
    """Build an UpstreamError from an httpx >=400 response, keeping the body."""
    status = response.status_code
    code = f"http_{status}"
    message = None
    retry_after = None
    raw_retry = response.headers.get("retry-after")
    if raw_retry:
        try:
            retry_after = max(1, min(int(float(raw_retry)), 900))
        except (TypeError, ValueError):
            retry_after = None
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            candidate = err.get("code") or err.get("type")
            if isinstance(candidate, str) and candidate:
                code = candidate[:80]
            msg = err.get("message")
            if isinstance(msg, str):
                message = msg[:300]
        elif isinstance(err, str):
            message = err[:300]
        if message is None:
            for key in ("message", "detail", "title"):
                val = payload.get(key)
                if isinstance(val, str) and val:
                    message = val[:300]
                    break
    if message is None:
        try:
            message = response.text[:300]
        except Exception:
            message = None
    return UpstreamError(status, code, message, retry_after, provider_id)


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
            if r.status_code >= 400:
                raise parse_upstream_error(r, provider_id=self.name)
            return r.json()

    async def chat_stream(self, model: str, messages: list, **kwargs) -> AsyncIterator[str]:
        async with self._client() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": model, "messages": messages, "stream": True, **{k: v for k, v in kwargs.items() if v is not None}},
            ) as r:
                if r.status_code >= 400:
                    body = (await r.aread()).decode("utf-8", "replace")

                    class _ShimResponse:
                        status_code = r.status_code
                        headers = r.headers
                        text = body

                        def json(self):
                            return json.loads(body)

                    raise parse_upstream_error(_ShimResponse(), provider_id=self.name)
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
                result = {
                    "ok": r.status_code == 200,
                    "latency_ms": int((time.time() - start) * 1000),
                    "status_code": r.status_code,
                    "provider": self.name,
                }
                if r.status_code >= 400:
                    parsed = parse_upstream_error(r, provider_id=self.name)
                    result["code"] = parsed.code
                    result["message"] = parsed.message
                    result["error"] = f"{parsed.code}: {parsed.message or parsed.code}"
                return result
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
            if r.status_code >= 400:
                raise parse_upstream_error(r, provider_id=self.name)
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
