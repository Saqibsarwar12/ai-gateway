"""Admin API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Security
from app.core.auth import get_current_user_api_key, require_role
from app.db.session import async_session
from sqlalchemy import select, func, update, delete
from app.db.models import ProviderModel, GatewayModel, User, RoutingRuleModel, RequestLog, FeatureFlag, SystemConfig
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderTestResult,
    GatewayModelCreate, GatewayModelUpdate, GatewayModelResponse,
    UserCreate, UserUpdate, UserResponse,
    RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse,
    FeatureFlagCreate, SystemConfigUpdate, SystemConfigResponse,
    AnalyticsOverview,
)
from app.providers.adapters import get_provider_adapter, ProviderConfig
from app.core.config import settings
import shortuuid
import bcrypt
import json
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
@router.get("/providers")
async def list_providers(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(ProviderModel))
        providers = result.scalars().all()
    return [p.__dict__ for p in providers]


@router.post("/providers")
async def create_provider(data: ProviderCreate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        provider = ProviderModel(
            id=f"prov-{shortuuid.uuid()[:12]}",
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            api_key=data.api_key,
            headers=data.headers,
            models=data.models,
            timeout=data.timeout,
            retry_policy=data.retry_policy,
            weight=data.weight,
            region=data.region,
            is_default=data.is_default,
            extra=data.extra,
        )
        if data.is_default:
            await session.execute(update(ProviderModel).where(ProviderModel.is_default == True).values(is_default=False))
        session.add(provider)
        await session.commit()
        await session.refresh(provider)
    return {"id": provider.id, "status": "created"}


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str, _: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(ProviderModel).where(ProviderModel.id == provider_id))
        p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return p.__dict__


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, data: ProviderUpdate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        result = await session.execute(select(ProviderModel).where(ProviderModel.id == provider_id))
        p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = data.model_dump(exclude_none=True)
    if "is_default" in update_data and update_data["is_default"]:
        await session.execute(update(ProviderModel).where(ProviderModel.is_default == True).values(is_default=False))

    async with async_session() as session:
        await session.execute(update(ProviderModel).where(ProviderModel.id == provider_id).values(**update_data))
        await session.commit()
    return {"status": "updated"}


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        await session.execute(delete(ProviderModel).where(ProviderModel.id == provider_id))
        await session.commit()
    return {"status": "deleted"}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str, _: User = Security(require_role("staff"))) -> ProviderTestResult:
    """Actually test the provider by hitting its endpoint in real-time."""
    import time

    async with async_session() as session:
        result = await session.execute(select(ProviderModel).where(ProviderModel.id == provider_id))
        p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")

    config = ProviderConfig(
        id=p.id, name=p.name, provider_type=p.provider_type,
        base_url=p.base_url, api_key=p.api_key,
        headers=p.headers or {}, models=p.models or [],
        timeout=p.timeout, region=p.region, extra=p.extra or {},
    )
    adapter = get_provider_adapter(config)

    try:
        start = time.perf_counter()
        models_resp = await adapter.list_models()
        latency = (time.perf_counter() - start) * 1000

        models_detected = []
        if models_resp.status_code == 200 and isinstance(models_resp.content, dict):
            models_detected = [m.get("id", "") for m in models_resp.content.get("data", [])]

        # Test chat completion with a minimal payload
        test_payload = {
            "model": (p.models or ["gpt-4o"])[0] if p.models else "gpt-4o",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }
        chat_start = time.perf_counter()
        chat_resp = await adapter.chat_completion(test_payload)
        chat_latency = (time.perf_counter() - chat_start) * 1000

        return ProviderTestResult(
            success=200 <= models_resp.status_code < 300,
            latency_ms=latency,
            status_code=chat_resp.status_code,
            models_detected=models_detected,
            streaming_supported=False,
            message=f"Provider reachable. Chat latency: {chat_latency:.0f}ms"
        )
    except Exception as e:
        return ProviderTestResult(success=False, latency_ms=0, error=str(e), message="Connection failed")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@router.get("/users")
async def list_users(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
    return [u.__dict__ for u in users]


@router.post("/users")
async def create_user(data: UserCreate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode() if data.password else ""
        user = User(
            id=f"usr-{shortuuid.uuid()[:12]}",
            email=data.email,
            hashed_password=hashed,
            name=data.name,
            role=data.role,
            rate_limit=data.rate_limit,
            burst_limit=data.burst_limit,
            max_tokens=data.max_tokens,
            credits=data.credits or 0.0,
            allowed_ips=data.allowed_ips,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return {"id": user.id, "email": user.email}


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        update_data = data.model_dump(exclude_none=True)
        if "hashed_password" in update_data and update_data["hashed_password"]:
            update_data["hashed_password"] = bcrypt.hashpw(update_data["hashed_password"].encode(), bcrypt.gensalt()).decode()
        await session.execute(update(User).where(User.id == user_id).values(**update_data))
        await session.commit()
    return {"status": "updated"}


@router.post("/users/{user_id}/api-keys")
async def create_api_key(user_id: str, name: str = "", _: User = Security(require_role("admin"))):
    from app.core.auth import generate_api_key
    async with async_session() as session:
        raw, hash_ = generate_api_key()
        api_key = ProviderModel.__table__.c  # reuse model — but let's use ApiKey model
        from app.db.models import ApiKey
        ak = ApiKey(id=f"key-{shortuuid.uuid()[:12]}", user_id=user_id, key_hash=hash_, key_prefix=raw[:12], name=name)
        session.add(ak)
        await session.commit()
    return {"api_key": raw, "key_prefix": raw[:12], "id": ak.id}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
@router.get("/routing")
async def list_routing_rules(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(RoutingRuleModel))
        rules = result.scalars().all()
    return [r.__dict__ for r in rules]


@router.post("/routing")
async def create_routing_rule(data: RoutingRuleCreate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        rule = RoutingRuleModel(
            id=f"rout-{shortuuid.uuid()[:12]}",
            name=data.name, strategy=data.strategy,
            provider_id=data.provider_id, models=data.models,
            priority=data.priority, is_active=data.is_active,
            conditions=data.conditions,
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
    return {"id": rule.id, "status": "created"}


@router.put("/routing/{rule_id}")
async def update_routing_rule(rule_id: str, data: RoutingRuleUpdate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        await session.execute(update(RoutingRuleModel).where(RoutingRuleModel.id == rule_id).values(**data.model_dump(exclude_none=True)))
        await session.commit()
    return {"status": "updated"}


@router.delete("/routing/{rule_id}")
async def delete_routing_rule(rule_id: str, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        await session.execute(delete(RoutingRuleModel).where(RoutingRuleModel.id == rule_id))
        await session.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
@router.get("/models")
async def list_models(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(GatewayModel))
        models = result.scalars().all()
    return [m.__dict__ for m in models]


@router.post("/models")
async def create_model(data: GatewayModelCreate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        model = GatewayModel(
            id=data.id, name=data.name, provider_id=data.provider_id,
            model_type=data.model_type, enabled=data.enabled, hidden=data.hidden,
            extra_params=data.extra_params, cost_per_1k_input=data.cost_per_1k_input,
            cost_per_1k_output=data.cost_per_1k_output, context_window=data.context_window,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
    return {"id": model.id}


@router.put("/models/{model_id}")
async def update_model(model_id: str, data: GatewayModelUpdate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        await session.execute(update(GatewayModel).where(GatewayModel.id == model_id).values(**data.model_dump(exclude_none=True)))
        await session.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@router.get("/analytics/overview")
async def analytics_overview(_: User = Security(require_role("staff"))) -> AnalyticsOverview:
    async with async_session() as session:
        # Total requests (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        r_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.created_at >= thirty_days_ago)
        )
        total_requests = r_result.scalar() or 0

        # Total users
        u_result = await session.execute(select(func.count(User.id)))
        total_users = u_result.scalar() or 0

        # Total providers
        p_result = await session.execute(select(func.count(ProviderModel.id)))
        total_providers = p_result.scalar() or 0

        # Total tokens
        t_result = await session.execute(
            select(func.sum(RequestLog.input_tokens + RequestLog.output_tokens)).where(RequestLog.created_at >= thirty_days_ago)
        )
        total_tokens = t_result.scalar() or 0

        # Total cost (sum of provider costs = estimate)
        total_cost = total_tokens / 1000 * 0.01  # rough estimate

        # Avg latency
        l_result = await session.execute(
            select(func.avg(RequestLog.latency_ms)).where(RequestLog.created_at >= thirty_days_ago)
        )
        avg_latency = l_result.scalar() or 0.0

        # Cache hit rate
        c_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.cache_hit == True, RequestLog.created_at >= thirty_days_ago)
        )
        cache_hits = c_result.scalar() or 0
        cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        # Error rate
        e_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.status_code >= 400, RequestLog.created_at >= thirty_days_ago)
        )
        errors = e_result.scalar() or 0
        error_rate = (errors / total_requests * 100) if total_requests > 0 else 0.0

        return AnalyticsOverview(
            total_requests=total_requests,
            total_users=total_users,
            total_providers=total_providers,
            total_tokens_used=total_tokens,
            total_cost=total_cost,
            avg_latency_ms=avg_latency,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate,
            requests_by_model={},
            requests_by_provider={},
            requests_today=0,  # Can be refined with date filters
            requests_this_week=0,
        )


@router.get("/logs")
async def get_logs(limit: int = 100, offset: int = 0, _: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(
            select(RequestLog).order_by(RequestLog.created_at.desc()).offset(offset).limit(limit)
        )
        logs = result.scalars().all()
    return [{"id": log.id, "model": log.model, "latency_ms": log.latency_ms,
             "status_code": log.status_code, "error": log.error,
             "created_at": log.created_at.isoformat()} for log in logs]


# ---------------------------------------------------------------------------
# Feature Flags & Config
# ---------------------------------------------------------------------------
@router.get("/feature-flags")
async def list_feature_flags(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(FeatureFlag))
        flags = result.scalars().all()
    return [{"key": f.key, "description": f.description, "is_enabled": f.is_enabled} for f in flags]


@router.post("/feature-flags")
async def create_feature_flag(data: FeatureFlagCreate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        ff = FeatureFlag(
            id=f"ff-{shortuuid.uuid()[:12]}", key=data.key,
            description=data.description, is_enabled=data.is_enabled
        )
        session.add(ff)
        await session.commit()
    return {"status": "created"}


@router.put("/feature-flags/{flag_key}")
async def toggle_feature_flag(flag_key: str, is_enabled: bool, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        await session.execute(update(FeatureFlag).where(FeatureFlag.key == flag_key).values(is_enabled=is_enabled))
        await session.commit()
    return {"status": "updated"}


@router.get("/system-config")
async def get_system_config(_: User = Security(require_role("staff"))):
    async with async_session() as session:
        result = await session.execute(select(SystemConfig))
        configs = result.scalars().all()
    return [{"key": c.key, "value": c.value, "description": c.description} for c in configs]


@router.put("/system-config")
async def update_system_config(data: SystemConfigUpdate, _: User = Security(require_role("admin"))):
    async with async_session() as session:
        existing = await session.execute(select(SystemConfig).where(SystemConfig.key == data.key))
        config = existing.scalar_one_or_none()
        if config:
            await session.execute(
                update(SystemConfig).where(SystemConfig.key == data.key).values(value=data.value, description=data.description)
            )
        else:
            new_config = SystemConfig(id=f"cfg-{shortuuid.uuid()[:12]}", key=data.key, value=data.value, description=data.description)
            session.add(new_config)
        await session.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# System / Health
# ---------------------------------------------------------------------------
@router.get("/health")
async def admin_health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
