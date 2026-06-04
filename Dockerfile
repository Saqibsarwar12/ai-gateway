FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

# Install system deps: Node.js 20 + Python build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip==24.3.1 setuptools==75.6.0 wheel==0.45.1

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: -r /app/requirements.txt || \
    pip install --no-cache-dir -r /app/requirements.txt

# ---- Build Next.js frontend ----
COPY frontend/ /app/frontend/
WORKDIR /app/frontend

# Clerk publishable key is public — safe to bake into the image
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_bWVhc3VyZWQtY2F0ZmlzaC03NS5jbGVyay5hY2NvdW50cy5kZXYk
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm ci 2>/dev/null || npm install
RUN npm run build

# ---- Backend ----
COPY backend/ /app/backend/

# ---- Start script ----
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app

ENV USE_SQLITE=true
ENV PORT=8000
ENV NEXT_PORT=3001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

CMD ["/app/start.sh"]
