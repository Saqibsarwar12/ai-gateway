"""Intelligent routing engine for provider selection."""
import asyncio
import random
from typing import Optional
from dataclasses import dataclass
from app.db.models import RoutingStrategy, ProviderModel
from app.providers.adapters import get_provider_adapter, ProviderConfig, BaseProviderAdapter, ProviderResponse
import time


@dataclass
class RoutingDecision:
    provider_id: str
    provider_name: str
    strategy: str
    latency_ms: float = 0.0
    cost: float = 0.0


class RoutingEngine:
    """
    Routes requests to the best provider based on strategy.
    Strategies: latency | cost | weighted | failover | priority
    """

    def __init__(self, providers: list[ProviderModel], default_strategy: str = "latency"):
        self.providers = providers
        self.default_strategy = default_strategy
        # Sort providers by priority (highest first)
        self.providers.sort(key=lambda p: getattr(p, "priority", 50), reverse=True)

    async def route(self, model: str, strategy: str, user_id: Optional[str] = None) -> RoutingDecision:
        """Pick the best provider for a given model using specified strategy."""
        strat = strategy or self.default_strategy

        if strat == "latency":
            return await self._route_by_latency(model)
        elif strat == "cost":
            return await self._route_by_cost(model)
        elif strat == "weighted":
            return await self._route_by_weight(model)
        elif strat == "failover":
            return await self._route_by_failover(model)
        elif strat == "priority":
            return await self._route_by_priority(model)
        else:
            return await self._route_by_latency(model)

    async def _route_by_latency(self, model: str) -> RoutingDecision:
        """Pick the provider with lowest average latency for this model."""
        available = [p for p in self.providers if p.status.value == "active" and p.avg_latency_ms > 0]
        if not available:
            # Fall back to first active provider
            available = [p for p in self.providers if p.status.value == "active"]
        if not available:
            raise ValueError("No active providers available")

        best = min(available, key=lambda p: p.avg_latency_ms)
        return RoutingDecision(
            provider_id=best.id, provider_name=best.name, strategy="latency",
            latency_ms=best.avg_latency_ms, cost=best.avg_cost_per_1k or 0.0
        )

    async def _route_by_cost(self, model: str) -> RoutingDecision:
        """Pick the cheapest provider for this model."""
        available = [p for p in self.providers if p.status.value == "active"]
        if not available:
            raise ValueError("No active providers available")
        best = min(available, key=lambda p: p.avg_cost_per_1k or float("inf"))
        return RoutingDecision(
            provider_id=best.id, provider_name=best.name, strategy="cost",
            latency_ms=best.avg_latency_ms or 0.0, cost=best.avg_cost_per_1k or 0.0
        )

    async def _route_by_weight(self, model: str) -> RoutingDecision:
        """Weighted round-robin — higher weight = more likely to be selected."""
        available = [p for p in self.providers if p.status.value == "active"]
        if not available:
            raise ValueError("No active providers available")

        weights = [p.weight or 1 for p in available]
        chosen = random.choices(available, weights=weights, k=1)[0]
        return RoutingDecision(
            provider_id=chosen.id, provider_name=chosen.name, strategy="weighted",
            latency_ms=chosen.avg_latency_ms or 0.0, cost=chosen.avg_cost_per_1k or 0.0
        )

    async def _route_by_failover(self, model: str) -> RoutingDecision:
        """Always use first healthy provider, fall back on failure."""
        available = [p for p in self.providers if p.status.value == "active"]
        if not available:
            raise ValueError("No active providers available")
        # Primary = first in list (by priority)
        return RoutingDecision(
            provider_id=available[0].id, provider_name=available[0].name, strategy="failover",
            latency_ms=available[0].avg_latency_ms or 0.0,
            cost=available[0].avg_cost_per_1k or 0.0
        )

    async def _route_by_priority(self, model: str) -> RoutingDecision:
        """Use highest priority active provider."""
        available = [p for p in self.providers if p.status.value == "active"]
        if not available:
            raise ValueError("No active providers available")
        # Already sorted by priority
        primary = available[0]
        return RoutingDecision(
            provider_id=primary.id, provider_name=primary.name, strategy="priority",
            latency_ms=primary.avg_latency_ms or 0.0,
            cost=primary.avg_cost_per_1k or 0.0
        )

    async def execute_with_failover(
        self,
        model: str,
        request_payload: dict,
        user_id: Optional[str] = None
    ) -> ProviderResponse:
        """Try primary provider, fall back to next on failure."""
        from tenacity import retry, stop_after_attempt, wait_exponential

        available = [p for p in self.providers if p.status.value == "active"]
        errors = []

        for provider in available:
            try:
                config = ProviderConfig(
                    id=provider.id,
                    name=provider.name,
                    provider_type=provider.provider_type,
                    base_url=provider.base_url,
                    api_key=provider.api_key,
                    headers=provider.headers or {},
                    models=provider.models or [],
                    timeout=provider.timeout,
                    retry_policy=provider.retry_policy or {},
                    weight=provider.weight,
                    region=provider.region,
                    extra=provider.extra or {},
                )
                adapter = get_provider_adapter(config)
                resp = await adapter.chat_completion(request_payload)
                if resp.status_code < 500:
                    return resp
                errors.append(f"{provider.name}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{provider.name}: {str(e)}")

        # All providers failed
        return ProviderResponse(
            status_code=503,
            content=None,
            error=f"All providers failed. Errors: {'; '.join(errors)}"
        )


class RequestRouter:
    """
    High-level request router that:
    1. Authenticates the request
    2. Applies routing rules (global + user-level)
    3. Selects provider
    4. Forwards request
    5. Logs result
    6. Returns response (streaming or regular)
    """

    def __init__(self, engine: RoutingEngine):
        self.engine = engine

    async def route_and_forward(
        self,
        payload: dict,
        model: str,
        user_id: Optional[str],
        api_key_hash: Optional[str],
        request_id: str,
    ) -> ProviderResponse:
        """Main entry point for routing + forwarding a chat completion."""
        from app.db.session import get_redis
        import json

        redis = await get_redis()
        cache_key = f"cache:completion:{hash(json.dumps(payload, sort_keys=True))}"

        # Check cache
        cached = await redis.get(cache_key)
        if cached:
            return ProviderResponse(status_code=200, content=json.loads(cached), cached=True)

        # Route
        strategy = "latency"  # TODO: look up user's routing preference
        decision = await self.engine.route(model, strategy, user_id)

        # Find provider config
        from app.db.session import async_session
        from sqlalchemy import select
        async with async_session() as session:
            from app.db.models import ProviderModel
            result = await session.execute(
                select(ProviderModel).where(ProviderModel.id == decision.provider_id)
            )
            provider = result.scalar_one_or_none()

        if not provider:
            return ProviderResponse(status_code=503, content=None, error="Provider not found")

        config = ProviderConfig(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            api_key=provider.api_key,
            headers=provider.headers or {},
            models=provider.models or [],
            timeout=provider.timeout,
            retry_policy=provider.retry_policy or {},
            weight=provider.weight,
            region=provider.region,
            extra=provider.extra or {},
        )
        adapter = get_provider_adapter(config)
        response = await adapter.chat_completion(payload)

        # Log request
        await self._log_request(request_id, user_id, api_key_hash, model, provider.id, response)

        # Cache result (short TTL, only successful responses)
        if response.status_code == 200 and not response.cached:
            await redis.setex(cache_key, 60, json.dumps(response.content))

        return response

    async def _log_request(
        self,
        request_id: str,
        user_id: Optional[str],
        api_key_hash: Optional[str],
        model: str,
        provider_id: str,
        response: ProviderResponse,
    ):
        """Log request to database for analytics."""
        from app.db.session import async_session
        from app.db.models import RequestLog
        from sqlalchemy import select
        import shortuuid

        async with async_session() as session:
            log = RequestLog(
                id=request_id or shortuuid.uuid(),
                user_id=user_id,
                api_key_id=api_key_hash,
                model=model,
                provider_id=provider_id,
                latency_ms=response.latency_ms,
                status_code=response.status_code,
                error=response.error,
                cache_hit=response.cached,
            )
            session.add(log)
            await session.commit()
