"""Admin-only NVIDIA Smart configuration API."""
from datetime import datetime
from typing import Optional

import shortuuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import encrypt_gateway_secret
from app.db.models import NvidiaSmartAccount, NvidiaSmartConfig
from app.db.session import async_session_maker
from app.services.nvidia_smart import (
    MAX_ACCOUNTS,
    NVIDIA_DEFAULT_BASE_URL,
    get_snapshot,
    invalidate_cache,
    public_account_view,
    public_config_view,
    test_account,
    test_all_accounts,
)
from app.api.v1.admin import require_admin

router = APIRouter(tags=["NVIDIA Smart"])


class SmartConfigBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    public_model_id: str = Field(min_length=2, max_length=120, pattern=r"^[a-z][a-z0-9._-]{1,119}$")
    enabled: bool = True


class SmartAccountBody(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=4096)
    model_id: str = Field(min_length=1, max_length=255)
    enabled: bool = True


async def _load_admin_config(session):
    result = await session.execute(select(NvidiaSmartConfig).where(NvidiaSmartConfig.id == "nvidia-smart-default"))
    return result.scalar_one_or_none()


def _response(config, accounts):
    return {"config": public_config_view(config, accounts), "accounts": [public_account_view(a) for a in accounts]}


@router.get("/admin/nvidia-smart/configuration")
async def get_nvidia_smart(_: dict = Depends(require_admin)):
    config, accounts = await get_snapshot(include_disabled=True)
    return _response(config, accounts)


@router.put("/admin/nvidia-smart/config")
async def save_nvidia_smart_config(body: SmartConfigBody, _: dict = Depends(require_admin)):
    public_model_id = body.public_model_id.strip().lower()
    async with async_session_maker() as session:
        config = await _load_admin_config(session)
        if not config:
            config = NvidiaSmartConfig(
                id="nvidia-smart-default",
                display_name=body.display_name.strip(),
                public_model_id=public_model_id,
                base_url=NVIDIA_DEFAULT_BASE_URL,
                enabled=body.enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(config)
        else:
            duplicate = await session.execute(
                select(NvidiaSmartConfig).where(
                    NvidiaSmartConfig.public_model_id == public_model_id,
                    NvidiaSmartConfig.id != config.id,
                )
            )
            if duplicate.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="That public model ID is already in use")
            config.display_name = body.display_name.strip()
            config.public_model_id = public_model_id
            config.base_url = NVIDIA_DEFAULT_BASE_URL
            config.enabled = body.enabled
            config.updated_at = datetime.utcnow()
        await session.commit()
    await invalidate_cache()
    config, accounts = await get_snapshot(include_disabled=True)
    return _response(config, accounts)


@router.post("/admin/nvidia-smart/accounts")
async def add_nvidia_account(body: SmartAccountBody, _: dict = Depends(require_admin)):
    if not body.api_key or not body.api_key.strip():
        raise HTTPException(status_code=400, detail="NVIDIA API key is required")
    async with async_session_maker() as session:
        config = await _load_admin_config(session)
        now = datetime.utcnow()
        if not config:
            config = NvidiaSmartConfig(
                id="nvidia-smart-default",
                display_name="NVIDIA Smart",
                public_model_id="nvidia-smart",
                base_url=NVIDIA_DEFAULT_BASE_URL,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            session.add(config)
            await session.flush()
        count_result = await session.execute(select(NvidiaSmartAccount).where(NvidiaSmartAccount.config_id == config.id))
        if len(count_result.scalars().all()) >= MAX_ACCOUNTS:
            raise HTTPException(status_code=409, detail=f"NVIDIA Smart supports at most {MAX_ACCOUNTS} accounts")
        account = NvidiaSmartAccount(
            id=shortuuid.uuid(),
            config_id=config.id,
            label=body.label.strip(),
            encrypted_api_key=encrypt_gateway_secret(body.api_key.strip()),
            model_id=body.model_id.strip(),
            enabled=body.enabled,
            status="healthy" if body.enabled else "disabled",
            created_at=now,
            updated_at=now,
        )
        session.add(account)
        await session.commit()
    await invalidate_cache()
    return public_account_view(account)


@router.put("/admin/nvidia-smart/accounts/{account_id}")
async def update_nvidia_account(account_id: str, body: SmartAccountBody, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(NvidiaSmartAccount).where(NvidiaSmartAccount.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="NVIDIA account not found")
        account.label = body.label.strip()
        account.model_id = body.model_id.strip()
        account.enabled = body.enabled
        account.status = "healthy" if body.enabled and account.status == "disabled" else ("disabled" if not body.enabled else account.status)
        if body.api_key:
            account.encrypted_api_key = encrypt_gateway_secret(body.api_key.strip())
            account.status = "healthy" if body.enabled else "disabled"
            account.consecutive_failures = 0
            account.cooldown_until = None
        account.updated_at = datetime.utcnow()
        await session.commit()
    await invalidate_cache()
    return public_account_view(account)


@router.delete("/admin/nvidia-smart/accounts/{account_id}")
async def delete_nvidia_account(account_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(NvidiaSmartAccount).where(NvidiaSmartAccount.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="NVIDIA account not found")
        await session.delete(account)
        await session.commit()
    await invalidate_cache()
    return {"deleted": True}


@router.post("/admin/nvidia-smart/accounts/{account_id}/test")
async def test_nvidia_account(account_id: str, _: dict = Depends(require_admin)):
    try:
        return await test_account(account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/admin/nvidia-smart/test")
async def test_nvidia_smart(_: dict = Depends(require_admin)):
    return await test_all_accounts()
