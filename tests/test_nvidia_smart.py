import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "nvidia-test-secret")
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.core.auth import encrypt_gateway_secret
from app.routing.nvidia_smart import NvidiaSmartRouter, NvidiaUpstreamError
from app.db.models import Base, Provider, Model
from app.db.session import async_session_maker, engine
from app.db.migrations import cleanup_generic_nvidia_providers
import app.routing.nvidia_smart as smart


def account(identifier, model="model-a", status="healthy"):
    return SimpleNamespace(
        id=identifier,
        label=identifier,
        model_id=model,
        encrypted_api_key=encrypt_gateway_secret(f"key-{identifier}"),
        enabled=True,
        status=status,
        cooldown_until=None,
        consecutive_failures=0,
        success_count=0,
        failure_count=0,
        avg_latency_ms=0.0,
        last_status_code=None,
        last_error_code=None,
        last_error_at=None,
        last_used_at=None,
        updated_at=None,
    )


def config():
    return SimpleNamespace(id="cfg", public_model_id="nvidia-smart", base_url="https://integrate.api.nvidia.com/v1", enabled=True)


class FakeResponse:
    def __init__(self, status_code=200, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {"id": "ok", "choices": [], "usage": {}}

    def json(self):
        return self._payload


class FakeClient:
    responses = []
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers=None, json=None):
        self.calls.append((url, headers, json))
        return self.responses.pop(0)


async def no_persist(*args, **kwargs):
    return None


async def check_generic_nvidia_cleanup_preserves_dedicated_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        provider = Provider(id="legacy-nvidia", name="NVIDIA", provider_type="nvidia", base_url="https://integrate.api.nvidia.com/v1", models=["legacy-model"])
        session.add(provider)
        await session.flush()
        session.add(Model(id="legacy-model-row", name="legacy-model", provider_id=provider.id, model_id="legacy-model"))
        await session.commit()
    result = await cleanup_generic_nvidia_providers()
    assert result["deleted_providers"] == 1
    async with async_session_maker() as session:
        assert await session.get(Provider, "legacy-nvidia") is None
        assert await session.get(Model, "legacy-model-row") is None


async def run():
    original_client = smart.httpx.AsyncClient
    try:
        smart.httpx.AsyncClient = FakeClient

        first, second = account("a1"), account("a2")
        router = NvidiaSmartRouter(config(), [first, second], None)
        FakeClient.responses = [FakeResponse(200)]
        result = await router.chat("nvidia-smart", [{"role": "user", "content": "hi"}], temperature=0.2)
        assert result["model"] == "nvidia-smart"
        assert FakeClient.calls[-1][2]["model"] in {"model-a"}

        first, second = account("a1"), account("a2")
        router = NvidiaSmartRouter(config(), [first, second], None)
        FakeClient.responses = [FakeResponse(429, {"retry-after": "7"}), FakeResponse(200)]
        result = await router.chat("nvidia-smart", [{"role": "user", "content": "hi"}])
        assert result["model"] == "nvidia-smart"
        assert len(FakeClient.calls) >= 3

        assert NvidiaSmartRouter._retry_after("7") == 7
        assert NvidiaSmartRouter._retry_after("not-a-date") is None
        assert NvidiaSmartRouter._cooldown_seconds(429, 1, 7) == 7

        first = account("a1")
        first.status = "cooling_down"
        first.cooldown_until = datetime.utcnow() + timedelta(minutes=5)
        router = NvidiaSmartRouter(config(), [first], None)
        try:
            await router.chat("nvidia-smart", [])
        except NvidiaUpstreamError as exc:
            assert exc.status_code == 503
        else:
            raise AssertionError("cooling-down account should not be selected")

        await check_generic_nvidia_cleanup_preserves_dedicated_tables()
        print("nvidia smart router and provider-boundary checks: PASS")
    finally:
        smart.httpx.AsyncClient = original_client


if __name__ == "__main__":
    asyncio.run(run())
