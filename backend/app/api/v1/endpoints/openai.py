"""OpenAI-compatible /v1/chat/completions endpoint."""
from fastapi import APIRouter, Request, Security, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse
from app.routing.engine import RequestRouter, RoutingEngine
from app.core.auth import get_current_user_api_key
from app.db.session import async_session
from sqlalchemy import select
from app.db.models import User, ProviderModel, GatewayModel, RequestLog
from app.providers.adapters import get_provider_adapter, ProviderConfig
import shortuuid
import json
import time
import asyncio

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.api_route("/chat/completions", methods=["POST", "OPTIONS"])
async def chat_completions(request: Request, payload: ChatCompletionRequest, user: User = Security(get_current_user_api_key)):
    """
    OpenAI-compatible /v1/chat/completions endpoint.
    Handles both streaming and regular responses.
    """
    # If OPTIONS, return CORS headers
    if request.method == "OPTIONS":
        return JSONResponse(content={}, status_code=200)

    # Validate user
    if not user:
        raise HTTPException(status_code=401, detail="API key required")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account suspended")

    # Check credits (if not trusted/admin)
    if not user.trusted and user.credits <= 0:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # Rate limit
    from app.core.rate_limit import check_rate_limit
    allowed, remaining = await check_rate_limit(user.id, user.rate_limit or 100)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"X-RateLimit-Remaining": "0"})

    # Load providers
    async with async_session() as session:
        result = await session.execute(select(ProviderModel).where(ProviderModel.status == "active"))
        providers = list(result.scalars().all())

    if not providers:
        raise HTTPException(status_code=503, detail="No providers available")

    engine = RoutingEngine(providers)
    router_obj = RequestRouter(engine)
    request_id = f"chatcmpl-{shortuuid.uuid()[:8]}"

    # Route and forward
    payload_dict = payload.model_dump(exclude_none=True)
    response = await router_obj.route_and_forward(
        payload_dict,
        payload.model,
        user.id,
        None,
        request_id,
    )

    if response.status_code >= 500:
        # Try failover
        response = await engine.execute_with_failover(payload.model, payload_dict, user.id)

    if response.status_code >= 400:
        return JSONResponse(
            content={"error": {"message": response.error or "Provider error", "type": "provider_error", "code": str(response.status_code)}},
            status_code=response.status_code
        )

    # Return cached or live response
    return JSONResponse(
        content=response.content,
        status_code=200,
        headers={
            "X-Request-ID": request_id,
            "X-RateLimit-Remaining": str(remaining),
        }
    )


@router.api_route("/completions", methods=["POST", "OPTIONS"])
async def completions(request: Request, payload: dict, user: User = Security(get_current_user_api_key)):
    """OpenAI-compatible /v1/completions endpoint."""
    if request.method == "OPTIONS":
        return JSONResponse(content={}, status_code=200)
    if not user:
        raise HTTPException(status_code=401, detail="API key required")
    # TODO: implement completions routing similar to chat_completions
    return JSONResponse(content={"error": {"message": "Not yet implemented", "type": "unhandled_error"}}, status_code=501)


@router.get("/models")
async def list_models(user: User = Security(get_current_user_api_key)):
    """OpenAI-compatible /v1/models listing."""
    async with async_session() as session:
        result = await session.execute(select(GatewayModel).where(GatewayModel.hidden == False))
        models = list(result.scalars().all())

    return {
        "object": "list",
        "data": [
            {
                "id": m.id,
                "object": "model",
                "created": int(m.created_at.timestamp()),
                "owned_by": m.provider_id or "gateway",
                "model_type": m.model_type,
            }
            for m in models
        ]
    }


@router.post("/embeddings")
async def embeddings(payload: dict, user: User = Security(get_current_user_api_key)):
    """OpenAI-compatible /v1/embeddings endpoint."""
    if not user:
        raise HTTPException(status_code=401, detail="API key required")
    model = payload.get("model", "text-embedding-3-small")
    async with async_session() as session:
        result = await session.execute(select(ProviderModel).where(ProviderModel.status == "active").limit(1))
        provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=503, detail="No provider available")

    config = ProviderConfig(
        id=provider.id, name=provider.name, provider_type=provider.provider_type,
        base_url=provider.base_url, api_key=provider.api_key,
        headers=provider.headers or {}, timeout=provider.timeout
    )
    adapter = get_provider_adapter(config)
    resp = await adapter.embeddings({**payload, "model": model})
    return JSONResponse(content=resp.content, status_code=resp.status_code)
