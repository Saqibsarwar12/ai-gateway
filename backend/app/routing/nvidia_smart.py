"""Adaptive NVIDIA Smart routing with per-account health and cooldown state."""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.core.auth import decrypt_gateway_secret

NVIDIA_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
AUTH_STATUS_CODES = {401, 403}
MAX_COOLDOWN_SECONDS = 900

_pool_locks: dict[str, asyncio.Lock] = {}
_pool_locks_guard = asyncio.Lock()
_inflight: dict[tuple[str, str], int] = {}


class NvidiaUpstreamError(Exception):
    def __init__(self, status_code: int | None, code: str, retry_after: int | None = None):
        self.status_code = status_code
        self.code = code
        self.retry_after = retry_after
        super().__init__(code)


async def _get_pool_lock(config_id: str) -> asyncio.Lock:
    async with _pool_locks_guard:
        return _pool_locks.setdefault(config_id, asyncio.Lock())


def _now() -> datetime:
    return datetime.utcnow()


def _retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return max(1, min(int(float(value)), MAX_COOLDOWN_SECONDS))
    except (TypeError, ValueError):
        pass
    try:
        target = parsedate_to_datetime(value)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        seconds = int((target - datetime.now(timezone.utc)).total_seconds())
        return max(1, min(seconds, MAX_COOLDOWN_SECONDS))
    except (TypeError, ValueError, OverflowError):
        return None


def _cooldown_seconds(status_code: int | None, failures: int, retry_after: int | None) -> int:
    if retry_after is not None:
        return retry_after
    if status_code in AUTH_STATUS_CODES:
        return 600
    exponent = min(max(failures - 1, 0), 4)
    return min(MAX_COOLDOWN_SECONDS, 15 * (2 ** exponent) if status_code == 429 else 5 * (2 ** exponent))


def _cooldown_active(value: datetime | None) -> bool:
    return bool(value and value > _now())


def _eligible(account: Any, now: datetime, attempted: set[str]) -> bool:
    return (
        account.id not in attempted
        and bool(account.enabled)
        and account.status != "disabled"
        and (not account.cooldown_until or account.cooldown_until <= now)
    )


class NvidiaSmartRouter:
    def __init__(self, config: Any, accounts: list[Any], session_factory=None):
        self.config = config
        self.accounts = accounts
        self.session_factory = session_factory

    @staticmethod
    def _retry_after(value: str | None) -> int | None:
        return _retry_after(value)

    @staticmethod
    def _cooldown_seconds(status_code: int | None, failures: int, retry_after: int | None) -> int:
        return _cooldown_seconds(status_code, failures, retry_after)

    async def _select_account(self, attempted: set[str]) -> Any | None:
        lock = await _get_pool_lock(self.config.id)
        async with lock:
            now = _now()
            eligible = [account for account in self.accounts if _eligible(account, now, attempted)]
            if not eligible:
                return None
            eligible.sort(
                key=lambda account: (
                    _inflight.get((self.config.id, account.id), 0),
                    account.consecutive_failures or 0,
                    account.avg_latency_ms or 0,
                    account.last_used_at or datetime.min,
                    random.random(),
                )
            )
            candidates = eligible[: min(2, len(eligible))]
            account = random.choice(candidates)
            key = (self.config.id, account.id)
            _inflight[key] = _inflight.get(key, 0) + 1
            account.last_used_at = now
            return account

    async def _release_account(self, account: Any) -> None:
        lock = await _get_pool_lock(self.config.id)
        async with lock:
            key = (self.config.id, account.id)
            _inflight[key] = max(0, _inflight.get(key, 1) - 1)

    async def _persist_state(
        self,
        account: Any,
        success: bool,
        status_code: int | None = None,
        error_code: str | None = None,
        retry_after: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        if self.session_factory is None:
            return
        lock = await _get_pool_lock(self.config.id)
        async with lock:
            from sqlalchemy import select
            from app.db.models import NvidiaSmartAccount

            async with self.session_factory() as session:
                result = await session.execute(select(NvidiaSmartAccount).where(NvidiaSmartAccount.id == account.id))
                stored = result.scalar_one_or_none()
                if not stored:
                    return
                now = _now()
                stored.last_used_at = now
                stored.updated_at = now
                if success:
                    previous = stored.success_count or 0
                    stored.status = "healthy"
                    stored.cooldown_until = None
                    stored.consecutive_failures = 0
                    stored.success_count = previous + 1
                    stored.last_status_code = 200
                    stored.last_error_code = None
                    stored.last_error_at = None
                    if latency_ms is not None:
                        stored.avg_latency_ms = round(((stored.avg_latency_ms or 0) * previous + latency_ms) / (previous + 1), 2)
                else:
                    stored.failure_count = (stored.failure_count or 0) + 1
                    stored.consecutive_failures = (stored.consecutive_failures or 0) + 1
                    stored.last_status_code = status_code
                    stored.last_error_code = error_code or "upstream_failure"
                    stored.last_error_at = now
                    stored.status = "cooling_down" if status_code in TRANSIENT_STATUS_CODES or status_code is None else ("auth_failed" if status_code in AUTH_STATUS_CODES else "failing")
                    stored.cooldown_until = now + timedelta(seconds=_cooldown_seconds(status_code, stored.consecutive_failures, retry_after)) if stored.status != "failing" else None
                await session.commit()
                account.status = stored.status
                account.cooldown_until = stored.cooldown_until
                account.consecutive_failures = stored.consecutive_failures
                account.success_count = stored.success_count
                account.failure_count = stored.failure_count
                account.avg_latency_ms = stored.avg_latency_ms
                account.last_status_code = stored.last_status_code
                account.last_error_code = stored.last_error_code
                account.last_error_at = stored.last_error_at
                account.last_used_at = stored.last_used_at

    async def _request(self, account: Any, messages: list[dict], **kwargs) -> dict:
        try:
            api_key = decrypt_gateway_secret(account.encrypted_api_key)
        except Exception as exc:
            raise NvidiaUpstreamError(500, "credential_unavailable") from exc
        body = {"model": account.model_id, "messages": messages}
        body.update({key: value for key, value in kwargs.items() if value is not None})
        timeout = kwargs.pop("timeout", 60)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{(self.config.base_url or NVIDIA_DEFAULT_BASE_URL).rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise NvidiaUpstreamError(None, "timeout") from exc
        except httpx.NetworkError as exc:
            raise NvidiaUpstreamError(None, "network_error") from exc
        if response.status_code >= 400:
            raise NvidiaUpstreamError(response.status_code, f"http_{response.status_code}", _retry_after(response.headers.get("retry-after")))
        try:
            payload = response.json()
        except ValueError as exc:
            raise NvidiaUpstreamError(502, "invalid_json_response") from exc
        if not isinstance(payload, dict):
            raise NvidiaUpstreamError(502, "invalid_json_response")
        return payload

    async def chat(self, public_model_id: str, messages: list[dict], **kwargs) -> dict:
        if not self.config.enabled:
            raise NvidiaUpstreamError(503, "nvidia_smart_disabled")
        attempted: set[str] = set()
        for _ in range(len(self.accounts)):
            account = await self._select_account(attempted)
            if not account:
                break
            attempted.add(account.id)
            started = _now()
            try:
                result = await self._request(account, messages, **kwargs)
                await self._persist_state(account, True, latency_ms=max(0, int((_now() - started).total_seconds() * 1000)))
                result["model"] = public_model_id
                return result
            except NvidiaUpstreamError as exc:
                await self._persist_state(account, False, exc.status_code, exc.code, exc.retry_after)
                if exc.status_code not in TRANSIENT_STATUS_CODES and exc.status_code not in AUTH_STATUS_CODES:
                    break
            finally:
                await self._release_account(account)
        raise NvidiaUpstreamError(503, "nvidia_accounts_unavailable")

    async def health_check(self, account: Any) -> dict:
        try:
            api_key = decrypt_gateway_secret(account.encrypted_api_key)
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"{(self.config.base_url or NVIDIA_DEFAULT_BASE_URL).rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            return {"ok": response.status_code == 200, "status_code": response.status_code}
        except (httpx.TimeoutException, httpx.NetworkError):
            return {"ok": False, "status_code": None}
