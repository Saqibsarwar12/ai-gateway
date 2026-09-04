"""FastAPI application entry point — AI Gateway Platform.

In production (Render), FastAPI runs on port 8000 and Next.js runs on port 3001.
FastAPI handles all /v1, /v2, /v3, /admin, /health API routes.
All other GET requests are proxied to the Next.js server on port 3001.
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.api.v1 import admin
from app.api.v1.nvidia_smart import router as nvidia_smart_admin_router
from app.api.personal_gateway import router as personal_gateway_router
from app.api.gateway import make_openai_router
from app.db.migrations import migrate_auth_schema, cleanup_legacy_users, cleanup_generic_nvidia_providers

NEXT_PORT = int(os.getenv("NEXT_PORT", "3001"))
NEXT_BASE = f"http://localhost:{NEXT_PORT}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate required production configuration before touching data.
    from app.db.session import init_db, async_session_maker, USE_D1
    if not settings.EMAIL_FROM:
        raise RuntimeError("EMAIL_FROM is not configured. Set it in Render environment variables.")
    await init_db()
    await migrate_auth_schema()

    # Test the actual configured database path with a backend-compatible query.
    if USE_D1:
        from app.db.cloudflare import fetchone
        await fetchone("SELECT 1 AS ok")
    else:
        from sqlalchemy import text
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))

    # Seed default admin
    from app.db.models import User
    from app.core.auth import hash_password, create_api_key
    from sqlalchemy import select

    try:
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                api_key = create_api_key()
                admin_user = User(
                    id="admin-001",
                    name="Admin",
                    username="admin",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                    tier="v3",
                    api_key=api_key,
                    credits=999999999,
                    is_active=True,
                    email_verified_at=datetime.utcnow(),
                )
                session.add(admin_user)
                await session.commit()
                print(f"Admin created: {settings.ADMIN_EMAIL} / API Key: {api_key}")
            else:
                admin_user.username = admin_user.username or "admin"
                admin_user.email_verified_at = admin_user.email_verified_at or datetime.utcnow()
                if os.getenv("ADMIN_PASSWORD_ROTATE_ON_STARTUP", "false").lower() == "true" and settings.ADMIN_PASSWORD:
                    admin_user.hashed_password = hash_password(settings.ADMIN_PASSWORD)
                    print(f"Admin password updated for {settings.ADMIN_EMAIL}")
                await session.commit()
                print(f"Admin preserved: {settings.ADMIN_EMAIL}")
    except Exception as e:
        print(f"WARNING: Admin seed skipped — {e}")

    try:
        await cleanup_legacy_users()
    except RuntimeError:
        pass

    await cleanup_generic_nvidia_providers()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production AI Gateway — OpenAI-compatible API with provider routing and tiered access",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_BASE_URL,
        "https://ai-gateway-dashboard.onrender.com",
        "https://saki-gateway.vercel.app",
        "https://saki-gateway.indevs.in",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ────────────────────────────────────────────────────
# Admin routes must be registered BEFORE personal gateway to avoid /admin/v1 being matched as /{username}/v1
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(nvidia_smart_admin_router)
app.include_router(make_openai_router("v1"), prefix="/v1", tags=["AI Gateway v1"])
app.include_router(make_openai_router("v2"), prefix="/v2", tags=["AI Gateway v2"])
app.include_router(make_openai_router("v3"), prefix="/v3", tags=["AI Gateway v3"])
app.include_router(personal_gateway_router, prefix="/{username}/v1", tags=["Personal Gateway"])
# Root-level alias so OpenAI clients work with base URL https://saki-gateway.indevs.in
# with or without a trailing /v1 (Zo and most SDKs append /chat/completions directly).
app.include_router(make_openai_router("v1"), prefix="", tags=["AI Gateway (root alias)"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/health/d1")
async def health_d1():
    from app.db.cloudflare import fetchone
    row = await fetchone("SELECT 1 AS ok")
    return {"status": "ok", "database": "d1", "result": row}


# ─── Root / is API-only base URL ───────────────────────────────────────
async def root_info():
    return {
        "service": "Saki Gateway API",
        "status": "ok",
        "version": settings.VERSION,
        "docs": "/openapi.json",
        "frontend": settings.FRONTEND_BASE_URL,
    }

app.add_api_route("/", root_info, methods=["GET"])

# NOTE: Dashboard is served exclusively from Vercel (saki-gateway.vercel.app).
# This Render backend is API-only.
