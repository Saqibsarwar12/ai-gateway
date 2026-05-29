"""OpenAI-compatible /v1/chat/completions endpoint."""
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import ChatCompletionRequest
from app.routing.engine import RoutingEngine
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, RequestLog
from app.core.rate_limit import rate_limiter
from sqlalchemy import select
import shortuuid
import time

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    auth_header = request.headers.get("authorization", "")
    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else "anonymous"

    allowed = await rate_limiter.is_allowed(f"rpm:{api_key}", limit=60, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a few seconds.")

    start = time.time()
    log_id = shortuuid.uuid()

    try:
        async with async_session_maker() as session:
            result = await session.execute(select(RoutingRule).where(RoutingRule.is_active == True).order_by(RoutingRule.priority.desc()).limit(1))
            rules = result.scalars().all()
            rule = rules[0] if rules else None

            result2 = await session.execute(select(Provider).where(Provider.enabled == True))
            providers = result2.scalars().all()
            provider_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "base_url": p.base_url,
                    "api_key": p.api_key,
                    "models": p.models or [],
                    "requires_proxy": p.requires_proxy,
                    "proxy_url": p.proxy_url,
                }
                for p in providers
            ]

        strategy = rule.strategy if rule else "fallback"
        engine = RoutingEngine(provider_data, strategy)

        messages = [m.model_dump() if hasattr(m, "model_dump") else m for m in req.messages]
        result = await engine.chat(req.model, messages, temperature=req.temperature, max_tokens=req.max_tokens)

        latency_ms = int((time.time() - start) * 1000)

        async with async_session_maker() as session:
            log = RequestLog(
                id=log_id,
                provider=engine.last_provider,
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
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        try:
            async with async_session_maker() as session:
                log = RequestLog(
                    id=log_id,
                    model=req.model,
                    latency_ms=latency_ms,
                    status_code=500,
                    error=str(e)[:500],
                )
                session.add(log)
                await session.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/completions")
async def completions(req: ChatCompletionRequest, request: Request):
    return await chat_completions(req, request)


@router.get("/models")
async def list_models():
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.enabled == True))
        providers = result.scalars().all()
        models = []
        for p in providers:
            for m in (p.models or []):
                models.append({
                    "id": f"{p.id}/{m}",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": p.id,
                    "root": p.id,
                })
        return {"object": "list", "data": models}


@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
