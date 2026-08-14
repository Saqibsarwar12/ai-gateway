"""Cloudflare KV-backed rate limiting with a local in-memory fallback."""

import json
import os
import time
from typing import Optional
from urllib.parse import quote

import httpx

CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
CF_KV_NAMESPACE_ID = os.getenv("CF_KV_NAMESPACE_ID", "")
CF_EMAIL = os.getenv("CF_EMAIL", "")
CF_GLOBAL_KEY = os.getenv("Cloudflare_Global_API_Key", "")
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NAMESPACE_ID}"
_memory_store: dict[str, tuple[list[float], float]] = {}


def _configured() -> bool:
    return bool((CF_API_TOKEN or (CF_EMAIL and CF_GLOBAL_KEY)) and CF_ACCOUNT_ID and CF_KV_NAMESPACE_ID)


def _headers() -> dict[str, str]:
    if CF_GLOBAL_KEY and CF_EMAIL and not CF_API_TOKEN:
        return {"X-Auth-Email": CF_EMAIL, "X-Auth-Key": CF_GLOBAL_KEY}
    return {"Authorization": f"Bearer {CF_API_TOKEN}"}


def _key_url(key: str) -> str:
    return f"{KV_URL}/{quote(key, safe='')}"


async def _kv_get(key: str) -> Optional[list[float]]:
    if _configured():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(_key_url(key), headers=_headers())
            if response.status_code == 404:
                return None
            response.raise_for_status()
            value = response.json() if response.headers.get("content-type", "").startswith("application/json") else json.loads(response.text)
            return value if isinstance(value, list) else None
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    entry = _memory_store.get(key)
    if entry is None:
        return None
    timestamps, expires_at = entry
    if time.time() >= expires_at:
        _memory_store.pop(key, None)
        return None
    return timestamps


async def _kv_set(key: str, timestamps: list[float], ttl: float) -> None:
    if _configured():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.put(
                    _key_url(key),
                    headers={**_headers(), "Content-Type": "application/json"},
                    content=json.dumps(timestamps),
                    params={"expiration_ttl": max(60, int(ttl))},
                )
            response.raise_for_status()
            return
        except httpx.HTTPError:
            return
    _memory_store[key] = (timestamps, time.time() + ttl)


async def _kv_delete(key: str) -> None:
    if _configured():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.delete(_key_url(key), headers=_headers())
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()
            return
        except httpx.HTTPError:
            return
    _memory_store.pop(key, None)


async def check_rate_limit(key: str, window_seconds: int, max_attempts: int) -> tuple[bool, int]:
    now = time.time()
    original = await _kv_get(key) or []
    timestamps = [timestamp for timestamp in original if now - timestamp < window_seconds]
    remaining = max(0, max_attempts - len(timestamps))
    if timestamps != original:
        await _kv_set(key, timestamps, window_seconds + 60)
    return remaining > 0, remaining


async def record_attempt(key: str, window_seconds: int, ttl: Optional[float] = None) -> None:
    now = time.time()
    timestamps = await _kv_get(key) or []
    timestamps = [timestamp for timestamp in timestamps if now - timestamp < window_seconds]
    timestamps.append(now)
    await _kv_set(key, timestamps, ttl or window_seconds + 60)


async def reset_rate_limit(key: str) -> None:
    await _kv_delete(key)
