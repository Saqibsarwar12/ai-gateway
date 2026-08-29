import re
from urllib.parse import urlparse
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.auth import decode_token, decrypt_gateway_secret
from app.core.config import settings
from app.db.models import APIKey, Model, User, UserGatewayConfig
from app.db import session as db_session
from app.models.schemas import ChatCompletionRequest
from app.providers.adapters import make_adapter, UpstreamError
from app.services.prompts import load_user_prompt, combine_with_system_prompt


USERNAME_SEGMENT = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


def _valid_username(username: str) -> bool:
    return bool(USERNAME_SEGMENT.fullmatch(username or ""))


async def _authenticate(request: Request) -> dict:
    authorization = request.headers.get("authorization", "")
    api_key = request.headers.get("x-api-key", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else api_key.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key or bearer token")

    payload = decode_token(token, settings.SECRET_KEY)
    async with db_session.async_session_maker() as session:
        if payload and payload.get("sub"):
            result = await session.execute(select(User).where(User.id == payload["sub"]))
            user = result.scalar_one_or_none()
        else:
            result = await session.execute(select(User).where(User.api_key == token, User.is_active == True))
            user = result.scalar_one_or_none()
            if not user:
                key_result = await session.execute(select(APIKey).where(APIKey.key == token, APIKey.is_active == True))
                key = key_result.scalar_one_or_none()
                user = None
                if key:
                    user_result = await session.execute(select(User).where(User.id == key.user_id, User.is_active == True))
                    user = user_result.scalar_one_or_none()

    if not user or not user.is_active or (user.role != "admin" and not user.email_verified_at):
        raise HTTPException(status_code=401, detail="Invalid API key or token")
    return {"id": user.id, "role": user.role, "username": user.username}


async def _resolve_owned_config(username: str, request: Request) -> tuple[dict, UserGatewayConfig]:
    if not _valid_username(username):
        raise HTTPException(status_code=404, detail="Personal gateway not found")
    actor = await _authenticate(request)
    async with db_session.async_session_maker() as session:
        user_result = await session.execute(select(User).where(User.username == username, User.is_active == True))
        target = user_result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Personal gateway not found")
        if actor["id"] != target.id:
            raise HTTPException(status_code=403, detail="You are not authorized to use this personal gateway")
        config_result = await session.execute(
            select(UserGatewayConfig)
            .where(UserGatewayConfig.user_id == target.id, UserGatewayConfig.enabled == True)
            .order_by(UserGatewayConfig.updated_at.desc())
        )
        config = config_result.scalars().first()
    if not config:
        raise HTTPException(status_code=409, detail="Personal gateway is not configured or is disabled")
    return actor, config


def _adapter(config: UserGatewayConfig):
    try:
        parsed = urlparse(config.base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("invalid provider base URL")
        api_key = decrypt_gateway_secret(config.encrypted_api_key)
        if not api_key:
            raise ValueError("missing provider credential")
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Personal provider configuration is invalid") from exc
    return make_adapter({
        "id": config.provider,
        "provider_type": config.provider_type,
        "base_url": config.base_url,
        "api_key": api_key,
    })


router = APIRouter()


@router.get("/models")
async def list_personal_models(username: str, request: Request):
    _, config = await _resolve_owned_config(username, request)
    return {
        "object": "list",
        "data": [{
            "id": config.default_model,
            "object": "model",
            "created": 1700000000,
            "owned_by": config.provider,
            "root": config.provider,
        }],
    }


@router.post("/chat/completions")
async def personal_chat(username: str, req: ChatCompletionRequest, request: Request):
    actor, config = await _resolve_owned_config(username, request)
    model = req.model or config.default_model
    adapter = _adapter(config)
    try:
        messages = [message.model_dump() if hasattr(message, "model_dump") else message for message in req.messages]
        async with db_session.async_session_maker() as session:
            prompt = await load_user_prompt(session, actor["id"], model, req.prompt_id)
        messages = combine_with_system_prompt(messages, prompt.content if prompt else None)
        return await adapter.chat(
            model,
            messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except HTTPException:
        raise
    except UpstreamError as exc:
        # Surface the REAL cause (bad provider key / unknown model / rate
        # limit) instead of a blanket 502.
        if exc.status_code in (401, 403):
            status, code = 401, "provider_auth_error"
            msg = f"Provider rejected the configured API key ({exc.code}). Update it in your personal gateway settings. Details: {exc.message or 'unauthorized'}"
        elif exc.status_code == 404 or "model" in (exc.code or ""):
            status, code = 404, "model_not_found"
            msg = f"Model is not served by your personal provider. Details: {exc.message or exc.code}"
        elif exc.status_code == 429:
            status, code = 429, "provider_rate_limited"
            msg = f"Provider is rate limited. {exc.message or 'Try again shortly.'}"
        else:
            status, code = 502, "provider_request_failed"
            msg = f"Personal provider request failed ({exc.code}). {exc.message or ''}".strip()
        raise HTTPException(status_code=status, detail={
            "error": {
                "message": msg,
                "type": "upstream_error",
                "code": code,
                "upstream_code": exc.code,
            }
        }) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail={
            "error": {
                "message": "Personal provider request failed",
                "type": "upstream_error",
                "code": "provider_request_failed",
            }
        }) from exc


@router.post("/completions")
async def personal_completions(username: str, req: ChatCompletionRequest, request: Request):
    return await personal_chat(username, req, request)


@router.get("/health")
async def personal_health(username: str, request: Request):
    await _resolve_owned_config(username, request)
    return {"status": "ok", "gateway": username}
