"""Intelligent routing engine for provider selection."""
import httpx
import asyncio
import random
from typing import Optional

from app.providers.adapters import OpenAIAdapter


class RoutingEngine:
    """
    Routes requests to the best available provider.
    Strategies: fallback | cost | latency | round_robin | weighted | priority
    """

    def __init__(self, providers: list[dict], strategy: str = "fallback"):
        self.providers = providers
        self.strategy = strategy
        self._rr_index = 0
        self.last_provider = None

    async def chat(self, model: str, messages: list[dict], **kwargs):
        """Send a chat completion request through the routing strategy."""
        if not self.providers:
            raise Exception("No providers configured")

        if self.strategy == "fallback":
            return await self._fallback(model, messages, **kwargs)
        elif self.strategy == "cost":
            return await self._cost_based(model, messages, **kwargs)
        elif self.strategy == "latency":
            return await self._latency_based(model, messages, **kwargs)
        elif self.strategy == "round_robin":
            return await self._round_robin(model, messages, **kwargs)
        elif self.strategy == "weighted":
            return await self._weighted(model, messages, **kwargs)
        else:
            return await self._fallback(model, messages, **kwargs)

    async def _get_adapter(self, provider: dict) -> OpenAIAdapter:
        return OpenAIAdapter(
            name=provider["id"],
            base_url=provider["base_url"],
            api_key=provider.get("api_key", ""),
            models=provider.get("models", []),
            requires_proxy=provider.get("requires_proxy", False),
            proxy_url=provider.get("proxy_url"),
        )

    async def _call_provider(self, adapter: OpenAIAdapter, model: str, messages: list[dict], **kwargs):
        """Call a provider with timeout."""
        return await asyncio.wait_for(
            adapter.chat(model, messages, **kwargs),
            timeout=kwargs.get("timeout", 60),
        )

    async def _fallback(self, model: str, messages: list[dict], **kwargs):
        """Try providers in order until one succeeds."""
        errors = []
        for provider in self.providers:
            try:
                adapter = await self._get_adapter(provider)
                result = await self._call_provider(adapter, model, messages, **kwargs)
                self.last_provider = provider["id"]
                return result
            except Exception as e:
                errors.append(f"{provider['id']}: {str(e)}")
                continue
        raise Exception(f"All providers failed: {'; '.join(errors[-3:])}")

    async def _cost_based(self, model: str, messages: list[dict], **kwargs):
        """Route to cheapest available provider."""
        sorted_providers = sorted(self.providers, key=lambda p: p.get("cost_per_1k_input", 999))
        return await self._fallback(model, messages, **kwargs)

    async def _latency_based(self, model: str, messages: list[dict], **kwargs):
        """Route to fastest provider (by historical latency)."""
        sorted_providers = sorted(self.providers, key=lambda p: p.get("avg_latency_ms", 99999))
        return await self._fallback(model, messages, **kwargs)

    async def _round_robin(self, model: str, messages: list[dict], **kwargs):
        """Rotate through providers evenly."""
        provider = self.providers[self._rr_index % len(self.providers)]
        self._rr_index += 1
        self.last_provider = provider["id"]
        adapter = await self._get_adapter(provider)
        return await self._call_provider(adapter, model, messages, **kwargs)

    async def _weighted(self, model: str, messages: list[dict], **kwargs):
        """Route based on weight percentages."""
        weights = kwargs.get("weights", {})
        rand = random.random()
        cumulative = 0.0
        for provider in self.providers:
            cumulative += weights.get(provider["id"], 1.0 / len(self.providers))
            if rand <= cumulative:
                self.last_provider = provider["id"]
                adapter = await self._get_adapter(provider)
                return await self._call_provider(adapter, model, messages, **kwargs)
        return await self._fallback(model, messages, **kwargs)
