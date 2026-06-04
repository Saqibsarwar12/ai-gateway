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

# Ensure the app directory is in the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.api.v1 import openai, admin

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    from app.db.models import Base
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin if none exists
    from app.db.session import async_session_maker
    from app.db.models import User
    from app.core.auth import hash_password, create_api_key
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            api_key = create_api_key()
            admin_user = User(
                id="admin-001",
                name="Admin",
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                api_key=api_key,
                credits=999999999,
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"Admin created: {settings.ADMIN_EMAIL} / API Key: {api_key}")

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
    description="Production AI Gateway — OpenAI-compatible API with provider routing",
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
app.include_router(openai.router, prefix="/v1", tags=["AI Gateway"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


# ─── Serve _next assets (immutable) ────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/_next", StaticFiles(directory=str(STATIC_DIR / "_next")), name="next-assets")


# ─── SPA catch-all: serve the matching HTML file, or index.html ────────
@app.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def serve_spa(path: str):
    """Serve the Next.js static export as an SPA.

    For any GET request that isn't an API route, try to find a matching
    HTML file in the static/ directory.  If none exists, fall back to
    index.html (SPA client-side routing).
    """
    if not STATIC_DIR.exists():
        return HTMLResponse("Dashboard not built", status_code=503)

    # Try exact file match (e.g. /dashboard/index.html)
    candidate = STATIC_DIR / path
    if candidate.is_file():
        return FileResponse(str(candidate))

    # Try directory index (e.g. /dashboard -> /dashboard/index.html)
    candidate = STATIC_DIR / path / "index.html"
    if candidate.is_file():
        return FileResponse(str(candidate))

    # Fallback: serve index.html for SPA client-side routing
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(str(index))

    return HTMLResponse("Not found", status_code=404)
