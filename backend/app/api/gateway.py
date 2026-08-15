"""Shared OpenAI-compatible gateway logic used by /v1, /v2, /v3.

All three versions expose the same request/response schema.
The only difference is which tier of users can access them and
what rate limits / model availability they get.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from app.models.schemas import ChatCompletionRequest
from app.routing.engine import RoutingEngine
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, RequestLog, User, Model
from app.core.rate_limit import rate_limiter
from app.core.auth import decode_token
from app.core.config import settings
from sqlalchemy import select
import shortuuid
import time
from app.routing.nvidia_smart import NvidiaSmartRouter, NvidiaUpstreamError
from app.services.prompts import load_user_prompt, combine_with_system_prompt

# Tier hierarchy: a v3 user can call v1, v2, v3
TIER_ORDER = ["v1", "v2", "v3"]


def _tier_index(tier: str) -> int:
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 0


async def _resolve_actor(
    authorization: str | None,
    x_api_key: str | None,
) -> dict:
    """Resolve user from JWT bearer or raw API key. Returns user dict."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing API key or bearer token. Pass Authorization: Bearer <token> or X-API-Key: sk-...",
                    "type": "invalid_request_error",
                    "code": "missing_api_key",
                }
            },
        )

    # Try JWT first
    payload = decode_token(token, settings.SECRET_KEY)
    if payload and "sub" in payload:
        # Fetch full user to get tier
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == payload["sub"]))
            user = result.scalar_one_or_none()
            if user and user.is_active and (user.role == "admin" or user.email_verified_at):
                return {
                    "id": user.id,
                    "role": user.role,
                    "tier": user.tier or "v1",
                    "label": "jwt",
                }

    # Try API key
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.api_key == token, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if user and (user.role == "admin" or user.email_verified_at):
            return {
                "id": user.id,
                "role": user.role,
                "tier": user.tier or "v1",
                "label": "api_key",
            }

    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "message": "Invalid API key or token",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    )


def make_openai_router(version: str) -> APIRouter:
    """Factory: returns an APIRouter for the given version (v1 | v2 | v3).

    All versions share identical endpoint logic. The version string is used
    to enforce tier access control.
    """
    router = APIRouter()
    required_tier_index = _tier_index(version)

    async def _check_tier(actor: dict):
        user_tier_index = _tier_index(actor.get("tier", "v1"))
        if user_tier_index < required_tier_index:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "message": f"Your account tier ({actor.get('tier', 'v1')}) does not have access to /{version}. "
                                   f"Contact the admin to upgrade your tier.",
                        "type": "permission_error",
                        "code": "tier_access_denied",
                        "required_tier": version,
                        "your_tier": actor.get("tier", "v1"),
                    }
                },
            )

    @router.post("/chat/completions")
    async def chat_completions(req: ChatCompletionRequest, request: Request):
        actor = await _resolve_actor(
            authorization=request.headers.get("authorization"),
            x_api_key=request.headers.get("x-api-key"),
        )
        await _check_tier(actor)

        # Tier-aware rate limiting
        rpm_limit = settings.TIER_RATE_LIMITS.get(actor["tier"], 60)
        allowed = await rate_limiter.is_allowed(
            f"rpm:{actor['id']}:{version}", limit=rpm_limit, window_seconds=60
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "message": f"Rate limit exceeded ({rpm_limit} rpm for tier {actor['tier']}). Try again shortly.",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded",
                    }
                },
            )

        start = time.time()
        log_id = shortuuid.uuid()

        try:
            from app.services.nvidia_smart import get_snapshot
            smart_config, smart_accounts = await get_snapshot()

            async with async_session_maker() as session:
                result = await session.execute(
                    select(RoutingRule)
                    .where(RoutingRule.is_active == True)
                    .order_by(RoutingRule.priority.desc())
                    .limit(1)
                )
                rules = result.scalars().all()
                rule = rules[0] if rules else None

                result2 = await session.execute(
                    select(Provider).where(Provider.enabled == True)
                )
                providers = result2.scalars().all()

                selected_prompt = await load_user_prompt(session, actor["id"], req.model, req.prompt_id)
                result3 = await session.execute(
                    select(Model).where(Model.enabled == True, Model.is_active == True)
                )
                model_entries = result3.scalars().all()
                provider_model_map = {}
                for m in model_entries:
                    provider_model_map.setdefault(m.provider_id, []).append(m.model_id or m.id)

                provider_data = [
                    {
                        "id": p.id,
                        "name": p.name,
                        "base_url": p.base_url,
                        "api_key": p.api_key,
                        "models": provider_model_map.get(p.id, p.models or []),
                        "requires_proxy": p.requires_proxy,
                        "proxy_url": p.proxy_url,
                    }
                    for p in providers
                ]

            if smart_config and smart_config.public_model_id == req.model:
                smart_router = NvidiaSmartRouter(smart_config, smart_accounts, async_session_maker)
                smart_messages = [m.model_dump() if hasattr(m, "model_dump") else m for m in req.messages]
                smart_messages = combine_with_system_prompt(smart_messages, selected_prompt.content if selected_prompt else None)
                result = await smart_router.chat(
                    req.model,
                    smart_messages,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    top_p=req.top_p,
                    stop=req.stop,
                )
                engine = None
            else:
                strategy = rule.strategy if rule else "fallback"
                engine = RoutingEngine(provider_data, strategy)
                messages = [m.model_dump() if hasattr(m, "model_dump") else m for m in req.messages]
                messages = combine_with_system_prompt(messages, selected_prompt.content if selected_prompt else None)
                result = await engine.chat(req.model, messages, temperature=req.temperature, max_tokens=req.max_tokens)

            latency_ms = int((time.time() - start) * 1000)

            async with async_session_maker() as session:
                log = RequestLog(
                    id=log_id,
                    user_id=actor["id"],
                    provider=(req.model if smart_config and smart_config.public_model_id == req.model else engine.last_provider),
                    model=req.model,
                    input_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                    output_tokens=result.get("usage", {}).get("completion_tokens", 0),
                    latency_ms=latency_ms,
                    status_code=200,
                    cost_usd=0.0,
                )
                session.add(log)
                await session.commit()

            return result

        except HTTPException:
            raise
        except NvidiaUpstreamError as e:
            latency_ms = int((time.time() - start) * 1000)
            status_code = e.status_code or 503
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": {
                        "message": "NVIDIA Smart upstream request failed",
                        "type": "upstream_error",
                        "code": e.code,
                        "retry_after": e.retry_after,
                    }
                },
                headers={"Retry-After": str(e.retry_after)} if e.retry_after else None,
            )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            try:
                async with async_session_maker() as session:
                    log = RequestLog(
                        id=log_id,
                        user_id=actor["id"],
                        model=req.model,
                        latency_ms=latency_ms,
                        status_code=500,
                        error=str(e)[:500],
                    )
                    session.add(log)
                    await session.commit()
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": str(e),
                        "type": "server_error",
                        "code": "internal_error",
                    }
                },
            )

    @router.post("/completions")
    async def completions(req: ChatCompletionRequest, request: Request):
        return await chat_completions(req, request)

    @router.get("/models")
    async def list_models(request: Request):
        """List models available to the caller's tier."""
        # Auth is optional for model listing (some clients probe without a key)
        try:
            actor = await _resolve_actor(
                authorization=request.headers.get("authorization"),
                x_api_key=request.headers.get("x-api-key"),
            )
            user_tier = actor.get("tier", "v1")
        except HTTPException:
            user_tier = "v1"  # unauthenticated: show v1 models only

        user_tier_index = _tier_index(user_tier)

        from app.services.nvidia_smart import get_snapshot
        smart_config, _ = await get_snapshot()

        async with async_session_maker() as session:
            result = await session.execute(
                select(Model).where(Model.enabled == True, Model.is_active == True)
            )
            model_entries = result.scalars().all()

            # Backward compat: also read from Provider.models JSON column
            result2 = await session.execute(
                select(Provider).where(Provider.enabled == True)
            )
            providers = result2.scalars().all()

        models = []
        seen = set()

        # Models from Model table (primary source)
        for m in model_entries:
            model_id = m.model_id or m.id
            if model_id not in seen:
                seen.add(model_id)
                models.append({
                    "id": model_id,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": m.provider_id or "unknown",
                    "root": m.provider_id or "unknown",
                })

        for p in providers:
            for m in (p.models or []):
                if m not in seen:
                    seen.add(m)
                    models.append({
                        "id": m,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": p.id,
                        "root": p.id,
                    })

        if smart_config and smart_config.public_model_id not in seen:
            models.append({
                "id": smart_config.public_model_id,
                "object": "model",
                "created": 1700000000,
                "owned_by": smart_config.display_name,
                "root": smart_config.public_model_id,
            })

        return {"object": "list", "data": models}

    @router.get("/health")
    async def health():
        return {"status": "ok", "version": version}

    return router
