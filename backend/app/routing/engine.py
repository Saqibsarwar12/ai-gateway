"""Intelligent routing engine with typed error propagation.

Key behaviours:
- Model IDs may be passed as either a bare name (e.g. "gpt-4o") or as
  "<provider_id>/<model>" (the form advertised by /v{n}/models). The engine
  strips the provider prefix before calling upstream, and uses the prefix
  (when present) to target the matching provider.
- The correct adapter (OpenAI-compatible vs Anthropic) is selected per
  provider via make_adapter, so Anthropic providers work too.
- Fallback only tries providers that actually serve the requested model
  (when that information is available), then any remaining providers.
- Every upstream failure raises a typed UpstreamError; when all providers
  fail, AllProvidersFailed carries the last typed error so the gateway can
  surface the REAL cause (bad key / missing model / rate limit / outage)
  instead of a blanket 500.
"""
import asyncio
import logging
import random
import time
from typing import Optional, List, AsyncIterator

from app.providers.adapters import make_adapter, ProviderAdapter, UpstreamError

logger = logging.getLogger(__name__)


def _split_model(model: str) -> tuple[Optional[str], str]:
    """Split a model id into (provider_id, bare_model).

    "openai-main/gpt-4o" -> ("openai-main", "gpt-4o")
    "gpt-4o"             -> (None, "gpt-4o")
    "auto"               -> (None, "auto")
    """
    if "/" in model:
        prefix, _, rest = model.partition("/")
        if prefix and rest:
            return prefix, rest
    return None, model


def _provider_has_model(provider: dict, bare_model: str) -> bool:
    models = provider.get("models") or []
    if not models:
        return True  # unknown model list -> assume it can serve it
    for m in models:
        m_tail = m.split("/")[-1] if isinstance(m, str) else m
        if m_tail == bare_model:
            return True
    return False


class AllProvidersFailed(Exception):
    """Every candidate provider failed.

    Carries per-provider error strings plus the last typed UpstreamError
    (if any) so the gateway can map the real cause to the correct
    client-facing HTTP status.
    """

    def __init__(self, errors: List[str], last_error: Optional[UpstreamError] = None, tried: Optional[List[str]] = None):
        self.errors = errors
        self.last_error = last_error
        self.tried = tried or []
        summary = "; ".join(errors[-3:]) if errors else "no providers configured"
        super().__init__(f"All providers failed: {summary}")


class RoutingEngine:
    """Routes requests to the best available provider.

    Strategies: fallback | cost | latency | round_robin | weighted | priority
    """

    def __init__(self, providers: List[dict], strategy: str = "fallback"):
        self.providers = providers
        self.strategy = strategy or "fallback"
        self._rr_index = 0
        self.last_provider: Optional[str] = None

    def _ordered_providers(self, model: str) -> tuple[Optional[str], str, List[dict]]:
        """Return (target_provider_id, bare_model, providers ordered by suitability).

        1. If model is prefixed with a provider id, that provider goes first.
        2. Providers that list the bare model come next.
        3. All remaining providers follow (so fallback still works).
        """
        target_provider_id, bare_model = _split_model(model)
        targeted = [p for p in self.providers if target_provider_id and p.get("id") == target_provider_id]
        has_model = [
            p for p in self.providers
            if p not in targeted and p.get("enabled", True) and _provider_has_model(p, bare_model)
        ]
        rest = [p for p in self.providers if p not in targeted and p not in has_model and p.get("enabled", True)]
        ordered = targeted + has_model + rest
        return target_provider_id, bare_model, ordered

    def _get_adapter(self, provider: dict) -> ProviderAdapter:
        return make_adapter(provider)

    async def _with_retry(self, adapter: ProviderAdapter, model: str, messages: list, attempts: int = 2, **kwargs) -> dict:
        """Retry transient upstream failures on one provider.

        4xx client errors (bad key, missing model, bad request) are
        deterministic — they are NOT retried.
        """
        last_exc: Optional[UpstreamError] = None
        for i in range(attempts):
            try:
                return await adapter.chat(model, messages, **kwargs)
            except UpstreamError as exc:
                last_exc = exc
                if exc.status_code < 500:
                    raise
                if i < attempts - 1:
                    await asyncio.sleep(1.5 * (i + 1))
            except Exception:
                raise
        raise last_exc  # pragma: no cover - unreachable when attempts >= 1

    async def chat(self, model: str, messages: list, **kwargs) -> dict:
        if not self.providers:
            raise AllProvidersFailed(["no providers configured"], tried=[])

        if self.strategy == "round_robin":
            return await self._round_robin(model, messages, **kwargs)
        if self.strategy == "weighted":
            return await self._weighted(model, messages, **kwargs)
        # cost / latency / priority currently fall through to ordered fallback
        return await self._fallback(model, messages, **kwargs)

    async def chat_stream(self, model: str, messages: list, **kwargs) -> AsyncIterator[str]:
        target_id, bare_model, providers = self._ordered_providers(model)
        errors: List[str] = []
        last_error: Optional[UpstreamError] = None
        for provider in providers:
            try:
                adapter = self._get_adapter(provider)
                got_any = False
                async for chunk in adapter.chat_stream(bare_model, messages, **kwargs):
                    got_any = True
                    yield chunk
                self.last_provider = provider.get("id")
                return
            except UpstreamError as exc:
                last_error = exc
                errors.append(f"{provider.get('id')}: {exc.status_code} {exc.code}: {exc.message or exc.code}")
                logger.warning(f"[engine] stream {provider.get('id')} failed for {model}: {exc}")
                if exc.status_code < 500:
                    raise
            except Exception as exc:
                errors.append(f"{provider.get('id')}: {type(exc).__name__}: {exc}")
                logger.warning(f"[engine] stream {provider.get('id')} unexpected error for {model}: {exc}")
        raise AllProvidersFailed(errors, last_error, [e.split(":", 1)[0] for e in errors])

    async def _fallback(self, model: str, messages: list, **kwargs) -> dict:
        """Try suitable providers in order until one succeeds."""
        target_id, bare_model, providers = self._ordered_providers(model)
        errors: List[str] = []
        tried: List[str] = []
        last_error: Optional[UpstreamError] = None
        for provider in providers:
            try:
                adapter = self._get_adapter(provider)
                started = time.time()
                result = await self._with_retry(adapter, bare_model, messages, **kwargs)
                elapsed = int((time.time() - started) * 1000)
                self.last_provider = provider.get("id")
                logger.info(f"[engine] {provider.get('id')} served {bare_model} in {elapsed}ms")
                result.setdefault("model", model)
                result["_provider"] = provider.get("id")
                result["_latency_ms"] = elapsed
                return result
            except UpstreamError as exc:
                last_error = exc
                tried.append(str(provider.get("id")))
                errors.append(f"{provider.get('id')}: {exc.status_code} {exc.code}: {exc.message or exc.code}")
                logger.warning(f"[engine] {provider.get('id')} failed for {bare_model}: {exc}")
            except asyncio.TimeoutError:
                tried.append(str(provider.get("id")))
                errors.append(f"{provider.get('id')}: timeout")
                logger.warning(f"[engine] {provider.get('id')} timed out for {bare_model}")
            except Exception as exc:
                tried.append(str(provider.get("id")))
                errors.append(f"{provider.get('id')}: {type(exc).__name__}: {exc}")
                logger.warning(f"[engine] {provider.get('id')} unexpected error for {bare_model}: {exc}")
        raise AllProvidersFailed(errors, last_error, tried)

    async def _round_robin(self, model: str, messages: list, **kwargs) -> dict:
        target_id, bare_model, providers = self._ordered_providers(model)
        provider = providers[self._rr_index % len(providers)]
        self._rr_index += 1
        try:
            adapter = self._get_adapter(provider)
            result = await self._with_retry(adapter, bare_model, messages, **kwargs)
            self.last_provider = provider.get("id")
            result.setdefault("model", model)
            result["_provider"] = provider.get("id")
            return result
        except Exception:
            # On failure, fall back to trying the rest
            return await self._fallback(model, messages, **kwargs)

    async def _weighted(self, model: str, messages: list, **kwargs) -> dict:
        target_id, bare_model, providers = self._ordered_providers(model)
        weights = kwargs.pop("weights", {}) or {}
        rand = random.random()
        cumulative = 0.0
        for provider in providers:
            cumulative += weights.get(provider.get("id"), 1.0 / max(1, len(providers)))
            if rand <= cumulative:
                try:
                    adapter = self._get_adapter(provider)
                    result = await self._with_retry(adapter, bare_model, messages, **kwargs)
                    self.last_provider = provider.get("id")
                    result.setdefault("model", model)
                    result["_provider"] = provider.get("id")
                    return result
                except Exception:
                    break
        return await self._fallback(model, messages, **kwargs)
