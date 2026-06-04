"""FastAPI application entry point — AI Gateway Platform.

Serves BOTH the API and the dashboard UI from one server.
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.api.v1 import admin
from app.api.gateway import make_openai_router
from app.api.clerk import router as clerk_router

STATIC_DIR = Path(__file__).parent.parent / "static"


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
                tier="v3",  # Admin gets full access
                api_key=api_key,
                credits=999999999,
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"Admin created: {settings.ADMIN_EMAIL} / API Key: {api_key}")
        else:
            # Ensure existing admin has v3 tier
            if not admin_user.tier or admin_user.tier != "v3":
                admin_user.tier = "v3"
                await session.commit()

    yield

    # Shutdown
    from app.db.session import redis_client
    try:
        await redis_client.aclose()
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production AI Gateway — OpenAI-compatible API with provider routing, tiered access, and Clerk auth",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes (MUST come before static/splat) ────────────────────────

# Tiered OpenAI-compatible endpoints
app.include_router(make_openai_router("v1"), prefix="/v1", tags=["AI Gateway v1"])
app.include_router(make_openai_router("v2"), prefix="/v2", tags=["AI Gateway v2"])
app.include_router(make_openai_router("v3"), prefix="/v3", tags=["AI Gateway v3"])

# Admin panel API
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Clerk provisioning
app.include_router(clerk_router, prefix="/clerk", tags=["Clerk"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


# ─── Serve _next assets (immutable) ──────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/_next", StaticFiles(directory=str(STATIC_DIR / "_next")), name="next-assets")


# ─── SPA catch-all ────────────────────────────────────────────────────
@app.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def serve_spa(path: str):
    """Serve the Next.js static export as an SPA."""
    if not STATIC_DIR.exists():
        return HTMLResponse("Dashboard not built", status_code=503)

    candidate = STATIC_DIR / path
    if candidate.is_file():
        return FileResponse(str(candidate))

    candidate = STATIC_DIR / path / "index.html"
    if candidate.is_file():
        return FileResponse(str(candidate))

    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(str(index))

    return HTMLResponse("Not found", status_code=404)
