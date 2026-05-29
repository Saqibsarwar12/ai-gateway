#!/bin/bash
set -e

echo "Starting AI Gateway on port $PORT"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
