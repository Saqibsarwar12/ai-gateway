#!/bin/bash
set -e

echo "[start] Starting FastAPI on port ${PORT:-8000}..."
cd /app/backend
exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
