.PHONY: install backend frontend backend-install frontend-install up down logs migrate health

# Backend
backend-install:
	cd backend && pip install -r requirements.txt

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

# Frontend
frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

# Docker
up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

# Development
dev: backend-run frontend-run

# Production
deploy-render:
	cp .env.example .env
	# Edit .env with your values then:
	render blueprint apply deploy/render.yaml

# Database
migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -c "from app.db.session import engine, Base; from app.db.models import *; import asyncio; asyncio.run(engine.begin())"

# Health
health:
	@curl -s http://localhost:8000/health | python -m json.tool

# Test OpenAI-compatible endpoint
test-api:
	curl -X POST http://localhost:8000/v1/chat/completions \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer sk-test-key" \
		-d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hi"}]}'

# Lint
lint-py:
	find backend -name "*.py" -exec py_compile {} +

lint-ts:
	cd frontend && npm run lint