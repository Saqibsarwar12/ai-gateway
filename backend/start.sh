#!/bin/bash
# Render startup script — reads PORT from Render's environment
set -e

echo "Starting AI Gateway on port $PORT"

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 2
