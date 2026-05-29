"""OpenAI-compatible /v1/chat/completions endpoint."""
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.routing.engine import RoutingEngine
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, RequestLog
from app.core.rate_limit import check_rate_limit
from sqlalchemy import select
import shortuuid
import time
import json

router = APIRouter()


async def get_routing_engine() -> RoutingEngine:
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.enabled == True).order_by(RoutingRule.priority.desc()).limit(1))
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
                "cost_per_1k_input": p.cost_per_1k_input,
                "cost_per_1k_output": p.cost_per_1k_output,
                "timeout_seconds": p.timeout_seconds,
                "priority": p.priority,
                "headers": p.headers or {},
            }
            for p in providers
        ]
        strategy = rule.strategy if rule else "fallback"
        return RoutingEngine(provider_data, strategy)


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    # Check rate limit
    auth_header = request.headers.get("authorization", "")
    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else "anonymous"
    allowed, remaining = await check_rate_limit(api_key,100, 60)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    start = time.time()
    log_id = shortuuid.uuid()

    try:
        engine = await get_routing_engine()
        adapter = await engine.select(req.model)

        if not adapter:
            raise HTTPException(status_code=503, detail="No providers available")

        messages = [m.model_dump() for m in req.messages]
        result = await adapter.chat(req.model, messages, temperature=req.temperature, max_tokens=req.max_tokens, top_p=req.top_p, stop=req.stop)

        latency_ms = int((time.time() - start) * 1000)

        # Log request
        async with async_session_maker() as session:
            log = RequestLog(
                id=log_id,
                model=req.model,
                latency_ms=latency_ms,
                status_code=200,
                prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=result.get("usage", {}).get("completion_tokens", 0),
                total_tokens=result.get("usage", {}).get("total_tokens", 0),
            )
            session.add(log)
            await session.commit()

        return result

    except HTTPException:
        raise
    except Exception as e:
        async with async_session_maker() as session:
            log = RequestLog(id=log_id, model=req.model, latency_ms=int((time.time() - start) * 1000), status_code=500, error=str(e))
            session.add(log)
            await session.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/completions")
async def completions(req: ChatCompletionRequest, request: Request):
    return await chat_completions(req, request)


@router.get("/v1/models")
async def list_models():
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.enabled == True))
        providers = result.scalars().all()
        models = []
        for p in providers:
            for m in (p.models or []):
                models.append({
                    "id": f"{p.slug}/{m}",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": p.slug,
                    "root": p.slug,
                })
        return {"object": "list", "data": models}


@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
