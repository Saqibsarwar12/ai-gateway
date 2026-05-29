"""Admin API — manage providers, routing rules, users."""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from app.db.session import async_session_maker, get_redis
from app.db.models import Provider, RoutingRule, User, Model, APIKey, RequestLog
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse,
    UserCreate, UserUpdate, UserResponse,
)
from app.core.auth import hash_password, verify_password, create_access_token, generate_api_key
from app.providers.adapters import ProviderAdapter
from app.core.rate_limit import check_rate_limit
import shortuuid
from datetime import datetime

router = APIRouter()


def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.replace("Bearer ", "")
    from app.core.auth import decode_token
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return data


# ─── Auth ────────────────────────────────────────────────
@router.post("/auth/login")
async def login(email: str, password: str):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
        return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}


# ─── Providers ────────────────────────────────────────────
@router.get("/providers")
async def list_providers():
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).order_by(Provider.priority))
        providers = result.scalars().all()
        return [ProviderResponse.model_validate(p) for p in providers]


@router.post("/providers")
async def create_provider(provider: ProviderCreate):
    async with async_session_maker() as session:
        existing = await session.execute(select(Provider).where(Provider.slug == provider.slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Provider with this slug already exists")

        p = Provider(
            id=shortuuid.uuid(),
            name=provider.name,
            slug=provider.slug,
            base_url=provider.base_url,
            api_key=provider.api_key,
            enabled=provider.enabled,
            cost_per_1k_input=provider.cost_per_1k_input,
            cost_per_1k_output=provider.cost_per_1k_output,
            daily_limit=provider.daily_limit,
            priority=provider.priority,
            tags=provider.tags,
            headers=provider.headers,
            timeout_seconds=provider.timeout_seconds,
            retry_count=provider.retry_count,
            models=provider.models,
        )
        session.add(p)
        await session.commit()
        return ProviderResponse.model_validate(p)


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, updates: ProviderUpdate):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")

        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(p, key, value)
        await session.commit()
        return ProviderResponse.model_validate(p)


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        await session.delete(p)
        await session.commit()
        return {"deleted": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")

        adapter = ProviderAdapter(p.base_url, p.api_key, p.timeout_seconds or 60, p.headers or {})
        health = await adapter.health_check()
        models = await adapter.list_models()

        # Update latency and status
        p.latency_ms = health.get("latency_ms", 0)
        p.status = "online" if health.get("ok") else "offline"
        if models:
            p.models = models
        await session.commit()

        return {"ok": health.get("ok"), "latency_ms": health.get("latency_ms", 0), "models": models, "status_code": health.get("status_code")}


# ─── Routing Rules ───────────────────────────────────────
@router.get("/routing")
async def list_routing_rules():
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).order_by(RoutingRule.priority.desc()))
        rules = result.scalars().all()
        return [RoutingRuleResponse.model_validate(r) for r in rules]


@router.post("/routing")
async def create_routing_rule(rule: RoutingRuleCreate):
    async with async_session_maker() as session:
        r = RoutingRule(
            id=shortuuid.uuid(),
            name=rule.name,
            strategy=rule.strategy,
            provider_ids=rule.provider_ids,
            enabled=rule.enabled,
            conditions=rule.conditions,
        )
        session.add(r)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.put("/routing/{rule_id}")
async def update_routing_rule(rule_id: str, updates: RoutingRuleUpdate):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(r, key, value)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.delete("/routing/{rule_id}")
async def delete_routing_rule(rule_id: str):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        await session.delete(r)
        await session.commit()
        return {"deleted": True}


# ─── Users ───────────────────────────────────────────────
@router.get("/users")
async def list_users():
    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return [UserResponse.model_validate(u) for u in users]


@router.post("/users")
async def create_user(user: UserCreate):
    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.email == user.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

        api_key_prefix, _ = generate_api_key()
        u = User(
            id=shortuuid.uuid(),
            name=user.name,
            email=user.email,
            hashed_password=hash_password(user.password),
            role=user.role,
            api_key=api_key_prefix,
 )
        session.add(u)
        await session.commit()
        return UserResponse.model_validate(u)


@router.put("/users/{user_id}")
async def update_user(user_id: str, updates: UserUpdate):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(u, key, value)
        await session.commit()
        return UserResponse.model_validate(u)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(u)
        await session.commit()
        return {"deleted": True}


# ─── Analytics ───────────────────────────────────────────
@router.get("/analytics")
async def get_analytics():
    async with async_session_maker() as session:
        result = await session.execute(select(RequestLog))
        logs = result.scalars().all()

        total_requests = len(logs)
        total_tokens = sum(l.total_tokens or 0 for l in logs)
        total_cost = sum(l.cost or 0 for l in logs)
        avg_latency = sum(l.latency_ms or 0 for l in logs) / max(total_requests, 1)
        errors = sum(1 for l in logs if l.status_code >= 400)
        success_rate = ((total_requests - errors) / max(total_requests, 1)) * 100

        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "success_rate": round(success_rate, 2),
            "errors": errors,
        }


# ─── Logs ───────────────────────────────────────────────
@router.get("/logs")
async def get_logs(limit: int = 100):
    async with async_session_maker() as session:
        result = await session.execute(select(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit))
        logs = result.scalars().all()
        return [
            {
                "id": l.id,
                "model": l.model,
                "latency_ms": l.latency_ms,
                "status_code": l.status_code,
                "error": l.error,
                "prompt_tokens": l.prompt_tokens,
                "completion_tokens": l.completion_tokens,
                "total_tokens": l.total_tokens,
                "cached": l.cached,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
