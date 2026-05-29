# ─────────────────────────────────────
# Render Cloud Build (sandbox has all deps pre-installed)
# NO pip install needed — packages are already there!
# ─────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# No system deps needed (no postgres client needed since we use SQLite)
# No pip install needed (all packages pre-installed in Render sandbox)

# Copy source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Python needs "app/" module at /app level
# mv backend/app -> app/ so uvicorn finds "app" module
RUN mv backend/app app

# Port
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# uvicorn loads "app" module from /app
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
