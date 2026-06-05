"""FastAPI application entry point — AI Gateway API Server.

Backend-only: serves /v1, /v2, /v3, /admin, /health API routes.
Frontend is deployed separately on Vercel.
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.api.v1 import admin
from app.api.gateway import make_openai_router

# Allowed origins for CORS — the Vercel frontend + local dev
ALLOWED_ORIGINS = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "https://saki-gateway.vercel.app",
    "https://saki-gateway-git-main.vercel.app",
    "https://saki-gateway-saqibsarwar1280-8023.vercel.app",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create / migrate tables
    from app.db.models import Base
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin
    from app.db.session import async_session_maker
    from app.db.models import User
    from app.core.auth import hash_password, create_api_key
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            api_key = create_api_key()
            admin_user = User(
                id="admin-001",
                name="Admin",
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                tier="v3",
                api_key=api_key,
                credits=999999999,
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"Admin created: {settings.ADMIN_EMAIL} / API Key: {api_key}")
        else:
            admin_user.hashed_password = hash_password(settings.ADMIN_PASSWORD)
            admin_user.tier = "v3"
            admin_user.is_active = True
            await session.commit()
            print(f"Admin password refreshed: {settings.ADMIN_EMAIL}")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production AI Gateway — OpenAI-compatible API with provider routing and tiered access",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],  # TODO: tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ────────────────────────────────────────────────────
app.include_router(make_openai_router("v1"), prefix="/v1", tags=["AI Gateway v1"])
app.include_router(make_openai_router("v2"), prefix="/v2", tags=["AI Gateway v2"])
app.include_router(make_openai_router("v3"), prefix="/v3", tags=["AI Gateway v3"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }
