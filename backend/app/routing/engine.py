"""Intelligent routing engine for provider selection.

Key behaviours:
- Model IDs may be passed as either a bare name (e.g. "gpt-4o") or as
  "<provider_id>/<model>" (the form advertised by /v{n}/models). The engine
  strips the provider prefix before calling upstream, and uses the prefix
  (when present) to target the matching provider.
- The correct adapter (OpenAI-compatible vs Anthropic) is selected per
  provider via make_adapter, so Anthropic providers work too.
- Fallback only tries providers that actually serve the requested model
  (when that information is available), then any remaining providers.
"""
import asyncio
import random
from typing import Optional

from app.providers.adapters import make_adapter, ProviderAdapter


def _split_model(model: str) -> tuple[Optional[str], str]:
    """Split a model id into (provider_id, bare_model).

    "openai-main/gpt-4o" -> ("openai-main", "gpt-4o")
    "gpt-4o"             -> (None, "gpt-4o")
    "auto"              -> (None, "auto")
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
    # models may be stored as bare names or prefixed; compare on the tail
    for m in models:
        m_tail = m.split("/")[-1] if isinstance(m, str) else m
        if m_tail == bare_model:
            return True
    return False


class RoutingEngine:
    """Routes requests to the best available provider.

    Strategies: fallback | cost | latency | round_robin | weighted | priority
    """

    def __init__(self, providers: list[dict], strategy: str = "fallback"):
        self.providers = providers
        self.strategy = strategy
        self._rr_index = 0
        self.last_provider = None

    def _ordered_providers(self, model: str) -> tuple[str, list[dict]]:
        """Return (bare_model, providers ordered by suitability for the model).

    1. If model is prefixed with a provider id, that provider goes first.
    2. Providers that list the bare model come next.
    3. All remaining providers follow (so fallback still works).
        """
        target_provider_id, bare_model = _split_model(model)

        targeted = [p for p in self.providers if target_provider_id and p["id"] == target_provider_id]
        has_model = [
            p for p in self.providers
            if p not in targeted and _provider_has_model(p, bare_model)
        ]
        rest = [p for p in self.providers if p not in targeted and p not in has_model]
        ordered = targeted + has_model + rest
        return bare_model, (ordered or list(self.providers))

    async def chat(self, model: str, messages: list[dict], **kwargs):
        if not self.providers:
            raise Exception("No providers configured")

        if self.strategy == "round_robin":
            return await self._round_robin(model, messages, **kwargs)
        if self.strategy == "weighted":
            return await self._weighted(model, messages, **kwargs)
        # cost / latency currently fall through to ordered fallback
        return await self._fallback(model, messages, **kwargs)

    def _get_adapter(self, provider: dict) -> ProviderAdapter:
        return make_adapter(provider)

    async def _call_provider(self, adapter: ProviderAdapter, model: str, messages: list[dict], **kwargs):
        return await asyncio.wait_for(
            adapter.chat(model, messages, **kwargs),
            timeout=kwargs.get("timeout", 60),
        )

    async def _fallback(self, model: str, messages: list[dict], **kwargs):
        """Try suitable providers in order until one succeeds."""
        bare_model, providers = self._ordered_providers(model)
        errors = []
        for provider in providers:
            try:
                adapter = self._get_adapter(provider)
                result = await self._call_provider(adapter, bare_model, messages, **kwargs)
                self.last_provider = provider["id"]
                return result
            except Exception as e:
                errors.append(f"{provider['id']}: {str(e)}")
                continue
        raise Exception(f"All providers failed: {'; '.join(errors[-3:])}")

    async def _round_robin(self, model: str, messages: list[dict], **kwargs):
        bare_model, providers = self._ordered_providers(model)
        provider = providers[self._rr_index % len(providers)]
        self._rr_index += 1
        adapter = self._get_adapter(provider)
        try:
            result = await self._call_provider(adapter, bare_model, messages, **kwargs)
            self.last_provider = provider["id"]
            return result
        except Exception:
            # On failure, fall back to trying the rest
            return await self._fallback(model, messages, **kwargs)

    async def _weighted(self, model: str, messages: list[dict], **kwargs):
        bare_model, providers = self._ordered_providers(model)
        weights = kwargs.get("weights", {})
        rand = random.random()
        cumulative = 0.0
        for provider in providers:
            cumulative += weights.get(provider["id"], 1.0 / len(providers))
            if rand <= cumulative:
                adapter = self._get_adapter(provider)
                try:
                    result = await self._call_provider(adapter, bare_model, messages, **kwargs)
                    self.last_provider = provider["id"]
                    return result
                except Exception:
                    break
        return await self._fallback(model, messages, **kwargs)
