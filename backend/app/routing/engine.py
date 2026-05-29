"""Intelligent routing engine — selects best provider per request."""
import asyncio
import random
from typing import Optional
from app.providers.adapters import ProviderAdapter


class RoutingEngine:
    STRATEGIES = {"fallback", "cost", "latency", "round_robin", "weighted", "priority"}

    def __init__(self, providers: list[dict], strategy: str = "fallback"):
        self.providers = [p for p in providers if p.get("enabled")]
        self.strategy = strategy
        self._round_robin_index = 0

    async def select(self, model: str, **kwargs) -> Optional[ProviderAdapter]:
        if not self.providers:
            return None

        if self.strategy == "fallback":
            return await self._fallback(model)
        elif self.strategy == "cost":
            return await self._cost_based(model)
        elif self.strategy == "latency":
            return await self._lowest_latency(model)
        elif self.strategy == "round_robin":
            return await self._round_robin(model)
        elif self.strategy == "weighted":
            return await self._weighted(model)
        elif self.strategy == "priority":
            return await self._priority_based(model)
        return await self._fallback(model)

    async def _fallback(self, model: str) -> Optional[ProviderAdapter]:
        for p in self.providers:
            adapter = ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
            health = await adapter.health_check()
            if health.get("ok"):
                return adapter
        return None

    async def _cost_based(self, model: str) -> Optional[ProviderAdapter]:
        sorted_providers = sorted(self.providers, key=lambda p: p.get("cost_per_1k_input", 999))
        return await self._fallback(model) # fallback ensures health first

    async def _lowest_latency(self, model: str) -> Optional[ProviderAdapter]:
        results = await asyncio.gather(*[
            self._check_latency(p) for p in self.providers
        ])
        valid = [r for r in results if r[0]]
        if valid:
            valid.sort(key=lambda r: r[1])
            p = valid[0][2]
            return ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
        return None

    async def _check_latency(self, p: dict):
        try:
            adapter = ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
            health = await adapter.health_check()
            return health.get("ok", False), health.get("latency_ms", 999999), p
        except Exception:
            return False, 999999, p

    async def _round_robin(self, model: str) -> Optional[ProviderAdapter]:
        for _ in range(len(self.providers)):
            p = self.providers[self._round_robin_index]
            self._round_robin_index = (self._round_robin_index + 1) % len(self.providers)
            adapter = ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
            health = await adapter.health_check()
            if health.get("ok"):
                return adapter
        return None

    async def _weighted(self, model: str) -> Optional[ProviderAdapter]:
        total = sum(p.get("priority", 1) for p in self.providers)
        r = random.uniform(0, total)
        cum = 0
        for p in self.providers:
            cum += p.get("priority", 1)
            if r <= cum:
                adapter = ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
                health = await adapter.health_check()
                if health.get("ok"):
                    return adapter
        return await self._fallback(model)

    async def _priority_based(self, model: str) -> Optional[ProviderAdapter]:
        sorted_providers = sorted(self.providers, key=lambda p: p.get("priority", 99))
        for p in sorted_providers:
            adapter = ProviderAdapter(p["base_url"], p["api_key"], p.get("timeout_seconds", 60), p.get("headers", {}))
            health = await adapter.health_check()
            if health.get("ok"):
                return adapter
        return None
