FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

# Install build deps as fallback for any wheel that needs compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and core build tools
RUN pip install --no-cache-dir --upgrade pip==24.3.1 setuptools==75.6.0 wheel==0.45.1

# Install Python deps with binary-only preference
# pydantic-core 2.27.1 ships prebuilt manylinux wheels for cp311, so this should succeed
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: -r /app/requirements.txt || \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy app source
COPY backend/ /app/backend/

WORKDIR /app/backend

ENV USE_SQLITE=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
