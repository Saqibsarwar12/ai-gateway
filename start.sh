#!/bin/bash
set -e

# Start Next.js standalone server on NEXT_PORT (default 3001) in background.
# The standalone server lives at frontend/.next/standalone/server.js with
# .next/static and public/ copied alongside it during the Docker build.
echo "[start] Starting Next.js on port ${NEXT_PORT:-3001}..."
cd /app/frontend/.next/standalone
PORT=${NEXT_PORT:-3001} HOSTNAME=0.0.0.0 node server.js &
NEXT_PID=$!

# Start FastAPI on PORT (default 8000)
echo "[start] Starting FastAPI on port ${PORT:-8000}..."
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
FASTAPI_PID=$!

# If either process exits, shut the container down so Render restarts it.
wait -n $NEXT_PID $FASTAPI_PID
echo "[start] A process exited. Shutting down."
kill $NEXT_PID $FASTAPI_PID 2>/dev/null || true
