#!/bin/bash
set -e

# Start Next.js on port 3001 in background
echo "[start] Starting Next.js on port 3001..."
cd /app/frontend
NEXT_PORT=3001 PORT=3001 node .next/standalone/server.js &
NEXT_PID=$!

# Start FastAPI on port 8000
echo "[start] Starting FastAPI on port 8000..."
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for either process to exit
wait -n $NEXT_PID $FASTAPI_PID
echo "[start] A process exited. Shutting down."
kill $NEXT_PID $FASTAPI_PID 2>/dev/null || true
