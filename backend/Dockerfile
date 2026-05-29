FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy asyncpg pydantic pydantic-settings python-jose passlib python-multipart redis httpx bcrypt shortuuid python-dotenv || true

# Copy app
COPY app/ ./app/
COPY start.sh .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
