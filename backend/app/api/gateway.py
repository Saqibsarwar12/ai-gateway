"""Shared OpenAI-compatible gateway logic used by /v1, /v2, /v3.

All three versions expose the same request/response schema.
The only difference is which tier of users can access them and
what rate limits / model availability they get.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatCompletionRequest
from app.routing.engine import RoutingEngine, AllProvidersFailed
from app.db import session as db_session
from app.db.models import Provider, RoutingRule, RequestLog, User, Model, APIKey
from app.core.rate_limit import rate_limiter
from app.core.auth import decode_token
from app.core.config import settings
from sqlalchemy import select
import shortuuid
import time
import json
from app.routing.nvidia_smart import NvidiaSmartRouter, NvidiaUpstreamError
from app.providers.adapters import UpstreamError
from app.services.prompts import load_user_prompt, combine_with_system_prompt
from datetime import datetime

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
        async with db_session.async_session_maker() as session:
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
    async with db_session.async_session_maker() as session:
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

    # Try dashboard API keys (APIKey table — keys created via /keys page)
    async with db_session.async_session_maker() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.key == token, APIKey.is_active == True)
        )
        ak = result.scalar_one_or_none()
        if ak and (not ak.expires_at or ak.expires_at > datetime.utcnow()):
            result2 = await session.execute(
                select(User).where(User.id == ak.user_id)
            )
            user = result2.scalar_one_or_none()
            if user and user.is_active and (user.role == "admin" or user.email_verified_at):
                return {
                    "id": user.id,
                    "role": user.role,
                    "tier": user.tier or "v1",
                    "label": "api_key",
                    "key_id": ak.id,
                }

    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "message": "Invalid or expired API key. Get a fresh key from the dashboard (/keys page) or log in again.",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    )


def _upstream_error_response(e: UpstreamError) -> HTTPException:
    """Map a typed upstream provider error to the RIGHT client-facing status.

    401/403 from the provider = the provider credential is bad/expired -> 401
    provider_auth_error (so "key not working" is visible instead of a fake 500).
    404/model_not_found from the provider -> 404 model_not_found.
    429 -> 429 with Retry-After. Real outages (5xx/network) -> 503.
    """
    provider = f"Provider '{e.provider_id}'" if e.provider_id else "Upstream provider"
    if e.status_code in (401, 403):
        return HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": f"{provider} rejected the configured API key ({e.code}). "
                               f"Update the provider key in the dashboard. Details: {e.message or 'unauthorized'}",
                    "type": "upstream_auth_error",
                    "code": "provider_auth_error",
                    "provider": e.provider_id,
                    "upstream_code": e.code,
                }
            },
        )
    if e.status_code == 404 or "model" in (e.code or ""):
        return HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{e.message or 'requested model'}' is not served by {provider}. "
                               f"Check /v1/models for available models.",
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                    "provider": e.provider_id,
                    "upstream_code": e.code,
                }
            },
        )
    if e.status_code == 429:
        return HTTPException(
            status_code=429,
            detail={
                "error": {
                    "message": f"{provider} is rate limited. {e.message or 'Try again shortly.'}",
                    "type": "rate_limit_error",
                    "code": "provider_rate_limited",
                    "provider": e.provider_id,
                    "upstream_code": e.code,
                }
            },
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else None,
        )
    return HTTPException(
        status_code=503,
        detail={
            "error": {
                "message": f"{provider} is unavailable ({e.code}). {e.message or ''}".strip(),
                "type": "upstream_error",
                "code": "upstream_unavailable",
                "provider": e.provider_id,
                "upstream_code": e.code,
            }
        },
    )


def _all_providers_failed_response(e: AllProvidersFailed) -> HTTPException:
    """Map engine fallback exhaustion to the correct client status."""
    last = e.last_error
    if isinstance(last, UpstreamError) and last.status_code and last.status_code < 500:
        return _upstream_error_response(last)
    detail_msg = "; ".join(e.errors[-3:]) if e.errors else str(e)
    return HTTPException(
        status_code=503,
        detail={
            "error": {
                "message": f"All providers failed to serve this model. Last errors: {detail_msg}",
                "type": "upstream_error",
                "code": "all_providers_failed",
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

            async with db_session.async_session_maker() as session:
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
                        "is_active": p.enabled,
                    }
                    for p in providers
                ]

            # Route through NVIDIA Smart when the active routing rule points at it and no
            # enabled regular provider covers the requested model (or the caller asked
            # for "auto"/the smart model explicitly). Keeps the gateway usable when all
            # regular providers are disabled.
            use_smart = bool(smart_config and smart_config.enabled)
            provider_ids = {p["id"] for p in provider_data}

            def _bare(m: str) -> str:
                head, sep, tail = m.partition("/")
                return tail if sep and head in provider_ids else m

            if use_smart and req.model != smart_config.public_model_id:
                rule_order = []
                if rule:
                    try:
                        rule_order = json.loads(rule.provider_order or "[]")
                    except Exception:
                        rule_order = []
                smart_in_rule = "__nvidia_smart__" in rule_order or not rule
                covered = any(
                    (not (p.get("models") or []))
                    or req.model in (p.get("models") or [])
                    or _bare(req.model) in (p.get("models") or [])
                    for p in provider_data if p.get("is_active", True)
                )
                use_smart = smart_in_rule and (not covered or req.model == "auto")
            if not use_smart:
                # Short-circuit: if NO enabled provider can serve this model,
                # fail fast with a clear 404 instead of hammering every
                # provider and returning a misleading 500.
                if provider_data and not any(
                    (not (p.get("models") or [])) or req.model in (p.get("models") or []) or _bare(req.model) in (p.get("models") or [])
                    for p in provider_data if p.get("is_active", True)
                ):
                    available = sorted({m for p in provider_data for m in (p.get("models") or [])})
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": {
                                "message": f"Model '{req.model}' is not served by any enabled provider. "
                                           f"Available models: {', '.join(available[:30]) or 'none configured'}. "
                                           f"See /{version}/models.",
                                "type": "invalid_request_error",
                                "code": "model_not_found",
                            }
                        },
                    )
            if req.stream:
                # OpenAI-compatible SSE streaming. stream:true clients previously
                # got a single JSON blob, which breaks Chatbox/LobeChat/etc.
                stream_messages = [m.model_dump() if hasattr(m, "model_dump") else m for m in req.messages]
                stream_messages = combine_with_system_prompt(stream_messages, selected_prompt.content if selected_prompt else None)
                stream_engine = RoutingEngine(provider_data, rule.strategy if rule else "fallback")

                async def _log_request_ok(provider_name: str | None) -> None:
                    try:
                        async with db_session.async_session_maker() as session:
                            session.add(RequestLog(
                                id=log_id,
                                user_id=actor["id"],
                                provider=provider_name,
                                model=req.model,
                                latency_ms=int((time.time() - start) * 1000),
                                status_code=200,
                            ))
                            await session.commit()
                    except Exception:
                        pass

                async def _engine_stream():
                    sent_any = False
                    try:
                        async for payload in stream_engine.chat_stream(
                            req.model, stream_messages,
                            temperature=req.temperature, max_tokens=req.max_tokens,
                        ):
                            if payload == "[DONE]":
                                break
                            sent_any = True
                            yield f"data: {payload}\n\n"
                        if sent_any:
                            await _log_request_ok(stream_engine.last_provider)
                    except (UpstreamError, AllProvidersFailed):
                        if sent_any:
                            yield "data: [DONE]\n\n"
                        raise
                    yield "data: [DONE]\n\n"
                    if sent_any:
                        await _log_request_ok(stream_engine.last_provider)

                async def _smart_stream():
                    smart_router = NvidiaSmartRouter(smart_config, smart_accounts, db_session.async_session_maker)
                    result = await smart_router.chat(
                        req.model, stream_messages,
                        temperature=req.temperature, max_tokens=req.max_tokens,
                        top_p=req.top_p, stop=req.stop,
                    )
                    content = ""
                    try:
                        content = result["choices"][0]["message"]["content"] or ""
                    except Exception:
                        pass
                    chunk = {
                        "id": result.get("id", "chatcmpl-smart"),
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req.model,
                        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    await _log_request_ok(smart_config.public_model_id)

                stream_agen = _smart_stream() if use_smart else _engine_stream()

                # Pull the first chunk BEFORE opening the SSE response so that
                # pre-stream failures map to real HTTP statuses (401/404/429/503)
                # instead of a 200 with an error buried in the stream.
                first_chunk = None
                try:
                    first_chunk = await stream_agen.__anext__()
                except StopAsyncIteration:
                    pass

                async def _rest():
                    if first_chunk is not None:
                        yield first_chunk
                    try:
                        async for ev in stream_agen:
                            yield ev
                    except (UpstreamError, AllProvidersFailed) as stream_exc:
                        stream_last = stream_exc.last_error if isinstance(stream_exc, AllProvidersFailed) else stream_exc
                        if isinstance(stream_last, UpstreamError):
                            err = {"error": {"message": str(stream_last.message or stream_last.code), "type": "upstream_error", "code": stream_last.code}}
                        else:
                            err = {"error": {"message": "All providers failed", "type": "upstream_error", "code": "all_providers_failed"}}
                        yield f"data: {json.dumps(err)}\n\n"
                        yield "data: [DONE]\n\n"
                    finally:
                        await stream_agen.aclose()

                return StreamingResponse(
                    _rest(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
                )

            if use_smart:
                smart_router = NvidiaSmartRouter(smart_config, smart_accounts, db_session.async_session_maker)
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

            async with db_session.async_session_maker() as session:
                log = RequestLog(
                    id=log_id,
                    user_id=actor["id"],
                    provider=(smart_config.public_model_id if use_smart else engine.last_provider),
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
        except AllProvidersFailed as e:
            latency_ms = int((time.time() - start) * 1000)
            try:
                async with db_session.async_session_maker() as session:
                    log = RequestLog(
                        id=log_id,
                        user_id=actor["id"],
                        model=req.model,
                        latency_ms=latency_ms,
                        status_code=502,
                        error="; ".join(e.errors)[-500:],
                    )
                    session.add(log)
                    await session.commit()
            except Exception:
                pass
            raise _all_providers_failed_response(e)
        except UpstreamError as e:
            latency_ms = int((time.time() - start) * 1000)
            try:
                async with db_session.async_session_maker() as session:
                    log = RequestLog(
                        id=log_id,
                        user_id=actor["id"],
                        model=req.model,
                        latency_ms=latency_ms,
                        status_code=e.status_code,
                        error=str(e)[:500],
                    )
                    session.add(log)
                    await session.commit()
            except Exception:
                pass
            raise _upstream_error_response(e)
        except NvidiaUpstreamError as e:
            latency_ms = int((time.time() - start) * 1000)
            status_code = e.status_code or 503
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": {
                        "message": ("NVIDIA Smart upstream credentials rejected - update the NVIDIA account keys in the admin dashboard"
                                    if status_code in (401, 403) else "NVIDIA Smart upstream request failed"),
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
                async with db_session.async_session_maker() as session:
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

        async with db_session.async_session_maker() as session:
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
