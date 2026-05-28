# ─────────────────────────────────────────────
# Stage 1 — Build Frontend (Next.js)
# ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ ./
RUN npm run build

# ─────────────────────────────────────────────
# Stage 2 — Backend + Running Service
# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system deps for FastAPI + asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy & install backend
COPY backend/ ./backend/
WORKDIR /app/backend
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/.next/standalone ./
COPY --from=frontend-builder /app/frontend/.next/static ./static/
COPY --from=frontend-builder /app/frontend/public ./public/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--trusted-host"]