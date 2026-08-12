"""NVIDIA Smart configuration cache and admin-facing helpers."""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select

from app.core.auth import decrypt_gateway_secret, encrypt_gateway_secret
from app.db.models import NvidiaSmartAccount, NvidiaSmartConfig
from app.db.session import async_session_maker

NVIDIA_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

NVIDIA_CONFIG_ID = "nvidia-smart-default"
MAX_ACCOUNTS = 50
CONFIG_CACHE_SECONDS = 5

_snapshot: tuple[float, NvidiaSmartConfig | None, list[NvidiaSmartAccount]] | None = None
_snapshot_lock = asyncio.Lock()


def public_account_view(account: NvidiaSmartAccount) -> dict[str, Any]:
    cooldown_until = account.cooldown_until
    status = account.status or "healthy"
    if cooldown_until and cooldown_until > datetime.utcnow():
        status = "cooling_down"
    return {
        "id": account.id,
        "label": account.label,
        "model_id": account.model_id,
        "enabled": bool(account.enabled),
        "status": status,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
        "consecutive_failures": account.consecutive_failures or 0,
        "success_count": account.success_count or 0,
        "failure_count": account.failure_count or 0,
        "avg_latency_ms": round(account.avg_latency_ms or 0, 2),
        "last_status_code": account.last_status_code,
        "last_error_code": account.last_error_code,
        "last_error_at": account.last_error_at.isoformat() if account.last_error_at else None,
        "last_used_at": account.last_used_at.isoformat() if account.last_used_at else None,
        "has_api_key": bool(account.encrypted_api_key),
    }


def public_config_view(config: NvidiaSmartConfig | None, accounts: list[NvidiaSmartAccount]) -> dict[str, Any]:
    if not config:
        return {
            "configured": False,
            "display_name": "NVIDIA Smart",
            "public_model_id": "nvidia-smart",
            "base_url": NVIDIA_DEFAULT_BASE_URL,
            "enabled": False,
            "accounts": [],
        }
    return {
        "configured": True,
        "id": config.id,
        "display_name": config.display_name,
        "public_model_id": config.public_model_id,
        "base_url": NVIDIA_DEFAULT_BASE_URL,
        "enabled": bool(config.enabled),
        "accounts": [public_account_view(account) for account in accounts],
    }


async def invalidate_cache() -> None:
    global _snapshot
    async with _snapshot_lock:
        _snapshot = None


async def get_snapshot(include_disabled: bool = False) -> tuple[NvidiaSmartConfig | None, list[NvidiaSmartAccount]]:
    global _snapshot
    now = time.monotonic()
    if _snapshot and now - _snapshot[0] < CONFIG_CACHE_SECONDS:
        config, accounts = _snapshot[1], _snapshot[2]
        if include_disabled or (config and config.enabled):
            return config, accounts
    async with _snapshot_lock:
        now = time.monotonic()
        if _snapshot and now - _snapshot[0] < CONFIG_CACHE_SECONDS:
            config, accounts = _snapshot[1], _snapshot[2]
            if include_disabled or (config and config.enabled):
                return config, accounts
        async with async_session_maker() as session:
            result = await session.execute(select(NvidiaSmartConfig).where(NvidiaSmartConfig.id == NVIDIA_CONFIG_ID))
            config = result.scalar_one_or_none()
            accounts: list[NvidiaSmartAccount] = []
            if config:
                account_result = await session.execute(
                    select(NvidiaSmartAccount)
                    .where(NvidiaSmartAccount.config_id == config.id)
                    .order_by(NvidiaSmartAccount.created_at.asc())
                )
                accounts = account_result.scalars().all()
        _snapshot = (time.monotonic(), config, accounts)
        if include_disabled or (config and config.enabled):
            return config, accounts
        return None, accounts


async def _persist_test_state(account: NvidiaSmartAccount, ok: bool, status_code: int | None, error: str | None) -> None:
    now = datetime.utcnow()
    async with async_session_maker() as session:
        result = await session.execute(select(NvidiaSmartAccount).where(NvidiaSmartAccount.id == account.id))
        stored = result.scalar_one_or_none()
        if not stored:
            return
        stored.last_used_at = now
        stored.updated_at = now
        stored.last_status_code = status_code
        if ok:
            stored.status = "healthy"
            stored.cooldown_until = None
            stored.consecutive_failures = 0
            stored.success_count = (stored.success_count or 0) + 1
            stored.last_error_code = None
            stored.last_error_at = None
        else:
            stored.failure_count = (stored.failure_count or 0) + 1
            stored.consecutive_failures = (stored.consecutive_failures or 0) + 1
            stored.last_error_code = error or "upstream_unavailable"
            stored.last_error_at = now
            stored.status = "auth_failed" if status_code in {401, 403} else "cooling_down"
            stored.cooldown_until = None if status_code in {401, 403} else now + timedelta(seconds=300)
        await session.commit()


async def test_account(account_id: str) -> dict[str, Any]:
    config, accounts = await get_snapshot(include_disabled=True)
    account = next((item for item in accounts if item.id == account_id), None)
    if not config or not account:
        raise ValueError("NVIDIA Smart account not found")
    try:
        api_key = decrypt_gateway_secret(account.encrypted_api_key)
    except Exception as exc:
        raise ValueError("NVIDIA credential is unavailable") from exc
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{NVIDIA_DEFAULT_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        retry_after = response.headers.get("retry-after")
        ok = response.status_code == 200
        error = None if ok else f"upstream_http_{response.status_code}"
        await _persist_test_state(account, ok, response.status_code, error)
        return {
            "ok": ok,
            "status_code": response.status_code,
            "retry_after": retry_after,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "account_id": account.id,
            "error": error,
        }
    except httpx.TimeoutException:
        await _persist_test_state(account, False, None, "timeout")
        return {
            "ok": False,
            "status_code": None,
            "retry_after": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "account_id": account.id,
            "error": "timeout",
        }
    except httpx.NetworkError:
        await _persist_test_state(account, False, None, "network_error")
        return {
            "ok": False,
            "status_code": None,
            "retry_after": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "account_id": account.id,
            "error": "network_error",
        }


async def test_all_accounts() -> dict[str, Any]:
    config, accounts = await get_snapshot(include_disabled=True)
    if not config:
        return {"ok": False, "tested": 0, "results": [], "error": "NVIDIA Smart is not configured"}
    results = await asyncio.gather(*(test_account(account.id) for account in accounts if account.enabled))
    return {
        "ok": bool(results) and all(item["ok"] for item in results),
        "tested": len(results),
        "results": results,
    }


def encrypt_api_key(value: str) -> str:
    return encrypt_gateway_secret(value)
