"""Provider adapter — calls any OpenAI-compatible API."""
import httpx
import json
from typing import Optional


class ProviderAdapter:
    def __init__(self, base_url: str, api_key: str, timeout: int = 60, headers: dict = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = headers or {}

    async def chat(self, model: str, messages: list[dict], **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    **self.headers,
                },
                json={
                    "model": model,
                    "messages": messages,
                    **{k: v for k, v in kwargs.items() if v is not None},
                },
            )
            response.raise_for_status()
            return response.json()

    async def chat_stream(self, model: str, messages: list[dict], **kwargs):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    **self.headers,
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    **{k: v for k, v in kwargs.items() if v is not None},
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]
                    elif line == "data: [DONE]":
                        break

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return []

    async def health_check(self) -> dict:
        import time
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/models", headers={"Authorization": f"Bearer {self.api_key}"})
                latency = int((time.time() - start) * 1000)
                return {"ok": r.status_code == 200, "latency_ms": latency, "status_code": r.status_code}
        except Exception as e:
            return {"ok": False, "latency_ms": 0, "error": str(e)}
