"""Admin API — manage providers, routing rules, users, analytics.

All admin endpoints (other than /auth/login and /auth/register) require a
valid JWT bearer token. The previous version left every admin route
unauthenticated, which is a security hole — this version enforces auth
on every protected route.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, User, Model, RequestLog, UsageStats
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse,
    UserCreate, UserUpdate, UserResponse,
)
from app.core.auth import (
    hash_password, verify_password, create_access_token, create_api_key,
    decode_token, get_current_user_id,
)
from app.core.config import settings
import shortuuid
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr

router = APIRouter()


# ─── Pydantic login body (replaces query-string login so credentials
# are never put in URLs/server logs) ──────────────────────────────
class LoginBody(BaseModel):
    email: str
    password: str


class RegisterBody(BaseModel):
    name: str
    email: str
    password: str


# ─── Auth dependency ───────────────────────────────────────────
async def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """Decode the JWT bearer token and return the token payload.

    Raises 401 if missing or invalid. Used on every protected admin route.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header. Provide a Bearer token.",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token, settings.SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def require_admin(payload: dict = Depends(require_user)) -> dict:
    """Same as require_user but also requires role == 'admin'."""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


# ─── Auth (PUBLIC — no token required) ────────────────────────
@router.post("/auth/login")
async def login(body: LoginBody):
    """Authenticate with email + password (JSON body — never in URL)."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()
        if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")

        token = create_access_token(
            {"sub": user.id, "email": user.email, "role": user.role},
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "credits": user.credits,
                "is_active": user.is_active,
            },
        }


@router.post("/auth/register")
async def register(body: RegisterBody):
    """Public sign-up. Returns the new user's API key ONCE — never again."""
    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

        api_key = create_api_key()
        u = User(
            id=shortuuid.uuid(),
            name=body.name,
            email=body.email,
            hashed_password=hash_password(body.password),
            role="user",
            api_key=api_key,
            credits=100,
            is_active=True,
        )
        session.add(u)
        await session.commit()
        return {
            "user": {"id": u.id, "email": u.email, "role": u.role, "credits": u.credits},
            "api_key": api_key,
        }


@router.get("/auth/me")
async def me(payload: dict = Depends(require_user)):
    """Return the current user (resolved from token) — for the dashboard."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == payload["sub"]))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "credits": u.credits,
            "is_active": u.is_active,
        }


# ─── Providers (admin only) ───────────────────────────────────
@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(_: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).order_by(Provider.priority))
        providers = result.scalars().all()
        # Mask api_key in the list view
        out = []
        for p in providers:
            r = ProviderResponse.model_validate(p)
            if r.api_key:
                r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
            out.append(r)
        return out


@router.post("/providers", response_model=ProviderResponse)
async def create_provider(data: ProviderCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        p = Provider(
            id=data.id or shortuuid.uuid(),
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            api_key=data.api_key,
            enabled=data.enabled,
            priority=data.priority,
            max_rpm=data.max_rpm,
            max_tpm=data.max_tpm,
            requires_proxy=data.requires_proxy,
            proxy_url=data.proxy_url,
            models=data.models,
            extra_config=data.extra_config or {},
        )
        session.add(p)
        await session.commit()
        r = ProviderResponse.model_validate(p)
        if r.api_key:
            r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
        return r


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: str, data: ProviderUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(p, key, value)
        p.updated_at = datetime.utcnow()
        await session.commit()
        r = ProviderResponse.model_validate(p)
        if r.api_key:
            r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
        return r


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        await session.delete(p)
        await session.commit()
        return {"deleted": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str, _: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")

        from app.providers.adapters import OpenAIAdapter
        adapter = OpenAIAdapter(name=p.id, base_url=p.base_url, api_key=p.api_key or "")
        return await adapter.health_check()


@router.post("/providers/{provider_id}/sync-models")
async def sync_provider_models(provider_id: str, _: dict = Depends(require_user)):
    """Fetch models from the provider's /models endpoint and create Model rows.
    Existing models with the same (provider_id, model_id) get their name refreshed."""
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        if not p.api_key:
            raise HTTPException(status_code=400, detail="Provider has no API key configured")

        from app.providers.adapters import OpenAIAdapter
        adapter = OpenAIAdapter(name=p.id, base_url=p.base_url, api_key=p.api_key)
        remote_ids = await adapter.list_models()
        if not remote_ids:
            remote_ids = list(p.models or [])

        created, updated = 0, 0
        now = datetime.utcnow()
        for mid in remote_ids:
            mid_str = str(mid).strip()
            if not mid_str:
                continue
            existing = await session.execute(
                select(Model).where(Model.provider_id == provider_id, Model.model_id == mid_str)
            )
            m = existing.scalar_one_or_none()
            if m:
                m.name = mid_str
                m.updated_at = now
                updated += 1
            else:
                session.add(Model(
                    id=shortuuid.uuid(),
                    name=mid_str,
                    provider_id=provider_id,
                    model_id=mid_str,
                    mode="chat",
                    input_cost_per_1m=0.0,
                    output_cost_per_1m=0.0,
                    context_window=8192,
                    supports_functions=False,
                    supports_vision=False,
                    enabled=True,
                    is_active=True,
                ))
                created += 1
        p.models = remote_ids
        p.updated_at = now
        await session.commit()
        return {"created": created, "updated": updated, "total": len(remote_ids), "models": remote_ids}


# ─── Routing Rules (admin) ────────────────────────────────────
@router.get("/routing", response_model=list[RoutingRuleResponse])
async def list_routing_rules(_: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).order_by(RoutingRule.priority.desc()))
        return [RoutingRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/routing", response_model=RoutingRuleResponse)
async def create_routing_rule(data: RoutingRuleCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        r = RoutingRule(
            id=shortuuid.uuid(),
            name=data.name,
            strategy=data.strategy,
            model_pattern=data.model_pattern,
            provider_order=data.provider_ids,
            weights=data.weights,
            is_active=data.is_active,
            priority=data.priority or 0,
            fallback_enabled=data.fallback_enabled,
            max_retries=data.max_retries,
            timeout_ms=data.timeout_ms,
        )
        session.add(r)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.put("/routing/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(rule_id: str, data: RoutingRuleUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        update_data = data.model_dump(exclude_unset=True)
        if "provider_ids" in update_data:
            update_data["provider_order"] = update_data.pop("provider_ids")
        for key, value in update_data.items():
            setattr(r, key, value)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.delete("/routing/{rule_id}")
async def delete_routing_rule(rule_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        await session.delete(r)
        await session.commit()
        return {"deleted": True}


# ─── Users (admin) ───────────────────────────────────────────
@router.get("/users", response_model=list[UserResponse])
async def list_users(_: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        api_key = create_api_key()
        u = User(
            id=shortuuid.uuid(),
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
            role=data.role,
            api_key=api_key,
            credits=data.credits,
            is_active=True,
        )
        session.add(u)
        await session.commit()
        return UserResponse.model_validate(u)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, data: UserUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        for key, value in update_data.items():
            setattr(u, key, value)
        await session.commit()
        return UserResponse.model_validate(u)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(u)
        await session.commit()
        return {"deleted": True}


# ─── Analytics (any logged-in user) ──────────────────────────
@router.get("/analytics")
async def get_analytics(days: int = 7, _: dict = Depends(require_user)):
    async with async_session_maker() as session:
        since = datetime.utcnow() - timedelta(days=days)

        count_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.created_at >= since)
        )
        total_requests = count_result.scalar() or 0

        if total_requests == 0:
            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
                "error_count": 0,
            }

        token_result = await session.execute(
            select(
                func.sum(RequestLog.input_tokens),
                func.sum(RequestLog.output_tokens),
                func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
            ).where(RequestLog.created_at >= since)
        )
        row = token_result.one()
        total_input = row[0] or 0
        total_output = row[1] or 0
        total_cost = row[2] or 0.0

        lat_result = await session.execute(
            select(func.avg(RequestLog.latency_ms)).where(RequestLog.created_at >= since)
        )
        avg_latency = lat_result.scalar() or 0.0

        err_result = await session.execute(
            select(func.count(RequestLog.id)).where(
                RequestLog.created_at >= since,
                RequestLog.status_code >= 400,
            )
        )
        error_count = err_result.scalar() or 0

        success_rate = ((total_requests - error_count) / max(total_requests, 1)) * 100

        return {
            "total_requests": total_requests,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(float(avg_latency), 1),
            "success_rate": round(success_rate, 2),
            "error_count": error_count,
        }


# ─── Logs (any logged-in user) ───────────────────────────────
@router.get("/logs")
async def get_logs(limit: int = 100, offset: int = 0, _: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(
            select(RequestLog)
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()
        return [
            {
                "id": l.id,
                "provider": l.provider,
                "model": l.model,
                "input_tokens": l.input_tokens,
                "output_tokens": l.output_tokens,
                "latency_ms": l.latency_ms,
                "status_code": l.status_code,
                "error": l.error,
                "cost_usd": l.cost_usd,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]


# ─── Models (any logged-in user) ─────────────────────────────
@router.get("/models")
async def list_models(_: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(Model).where(Model.enabled == True))
        models = result.scalars().all()
        return [{"id": m.id, "name": m.name, "provider_id": m.provider_id, "mode": m.mode} for m in models]


@router.post("/models")
async def create_model(data: dict, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        m = Model(
            id=data.get("id", shortuuid.uuid()),
            name=data.get("name", ""),
            provider_id=data.get("provider_id"),
            model_id=data.get("model_id", ""),
            mode=data.get("mode", "chat"),
            context_window=data.get("context_window", 8192),
            enabled=True,
        )
        session.add(m)
        await session.commit()
        return {"id": m.id, "name": m.name}
