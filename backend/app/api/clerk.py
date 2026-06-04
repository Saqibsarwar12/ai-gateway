"""Clerk integration — provision gateway users from Clerk SSO.

When a Clerk-authenticated user visits /keys for the first time,
the frontend calls POST /clerk/provision with their Clerk user ID,
email, and name. We look up or create a gateway User record,
return their API key and tier.

No Clerk secret key is needed for this simple provisioning flow —
we trust the data sent from the frontend (Clerk already authenticated
the user on the client side). For production hardening you can add
Clerk JWT verification using CLERK_SECRET_KEY.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.models import User
from app.core.auth import create_api_key
from app.core.config import settings
import shortuuid

router = APIRouter()


class ProvisionBody(BaseModel):
    clerk_user_id: str
    email: str
    name: str = ""


@router.post("/provision")
async def provision_clerk_user(body: ProvisionBody):
    """Look up or create a gateway User for a Clerk-authenticated user.

    Returns the user's API key, tier, and credits so the /keys page
    can display them immediately.
    """
    if not body.clerk_user_id or not body.email:
        raise HTTPException(status_code=400, detail="clerk_user_id and email are required")

    async with async_session_maker() as session:
        # 1. Try to find by clerk_user_id first
        result = await session.execute(
            select(User).where(User.clerk_user_id == body.clerk_user_id)
        )
        user = result.scalar_one_or_none()

        # 2. Fall back to email match (handles re-registration)
        if not user:
            result = await session.execute(
                select(User).where(User.email == body.email)
            )
            user = result.scalar_one_or_none()
            if user and not user.clerk_user_id:
                # Link existing account to Clerk
                user.clerk_user_id = body.clerk_user_id
                await session.commit()

        # 3. Create new user
        if not user:
            api_key = create_api_key()
            user = User(
                id=shortuuid.uuid(),
                name=body.name or body.email.split("@")[0],
                email=body.email,
                hashed_password=None,  # Clerk handles auth
                role="user",
                tier="v1",
                api_key=api_key,
                credits=settings.TIER_CREDIT_GRANTS["v1"],
                is_active=True,
                clerk_user_id=body.clerk_user_id,
            )
            session.add(user)
            await session.commit()

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "tier": user.tier or "v1",
                "credits": user.credits,
                "api_key": user.api_key,
                "is_active": user.is_active,
            }
        }
