# AI Gateway Platform

A fully customizable AI infrastructure control plane — admin dashboard, provider management, intelligent routing engine, and OpenAI-compatible API gateway. Deploy on Render (or Docker/VPS/Kubernetes).

## Architecture Overview

```
ai-gateway/
├── backend/          FastAPI API server
│   ├── app/
│   │   ├── api/v1/endpoints/   OpenAI-compatible + Admin REST API
│   │   ├── core/       Config, auth (JWT + API key), rate limiting
│   │   ├── db/         SQLAlchemy 2.0 async models, Redis client
│   │   ├── models/     Pydantic v2 request/response schemas
│   │   ├── providers/  Pluggable provider adapters (OpenAI, Anthropic, etc.)
│   │   └── routing/    Routing engine with 5 strategies + failover chains
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         Next.js 14 admin dashboard
│   ├── app/(dashboard)/   Dashboard pages (overview, providers, users, etc.)
│   ├── components/       Reusable UI components
│   └── lib/               API client
├── deploy/
│   └── render.yaml       Render.com blueprint (PostgreSQL + Redis + API + Frontend)
├── docker-compose.yml     Full-stack local development
├── Makefile               Development commands
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.11 + FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Asyncpg |
| Cache/Queue | Redis 7 (aioredis) |
| Auth | JWT + API Key (bcrypt hashed) |
| Rate Limiting | Redis sliding window |
| Frontend | Next.js 14 (App Router) + TypeScript |
| UI | TailwindCSS 4 + custom design system |
| Charts | Recharts |
| Animations | Framer Motion |
| Deployment | Docker + Render.com + Kubernetes-ready |

## Features

### API Gateway
- **OpenAI-compatible endpoints**: `/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/v1/embeddings`, `/v1/images`, `/v1/audio`
- **Streaming**: SSE/Server-Sent Events support
- **WebSocket**: Upgrade support for real-time streaming
- **Provider-agnostic**: Route to any OpenAI-compatible endpoint

### Provider Management
- Connect **any** API: OpenAI, Anthropic, Google Gemini, Groq, DeepSeek, Ollama, NVIDIA NIM, LM Studio, vLLM, Together AI, Fireworks, Mistral, Azure OpenAI, Cohere, or any custom endpoint
- Per-provider: Base URL, API key, custom headers, timeout, retry policy, region, weight, TLS/SSL options
- **Real connection testing**: Live API key validation, latency measurement, model detection, streaming capability check
- Health monitoring: Online/offline status, response times, failure rates, token speeds

### Intelligent Routing Engine
Five routing strategies, fully configurable per-model or per-request:
- **Latency**: Route to fastest responding provider
- **Cost**: Route to cheapest provider
- **Weighted**: Round-robin with custom weights
- **Failover**: Primary + automatic fallback chain (e.g., OpenAI → DeepSeek → Groq)
- **Priority**: Use highest priority active provider

### Admin Dashboard
- **Overview**: Live stats, request volume charts, provider distribution pie chart, system health
- **Providers**: Add/edit/test/delete providers with real-time diagnostics
- **Users**: User management, role assignment, rate limits, credits, suspension
- **Models**: Model registry with pricing, context windows, visibility toggles
- **Routing**: Create routing rules, visualize failover chains
- **Analytics**: Daily request/cost trends, model breakdown, latency histograms
- **Logs**: Live request tailing, terminal UI, status code distribution
- **Settings**: Feature flags, security settings, general config — all togglable in real-time
- **API Playground**: Test any endpoint with live requests

### Security
- JWT Bearer tokens + `sk-` API key authentication
- Role-based access: `admin` > `staff` > `enterprise` > `user`
- Per-user rate limiting (Redis sliding window)
- IP whitelisting support
- Request/response logging with audit trail

## Quick Start

### Local with Docker

```bash
cp .env.example .env
# Fill in .env with your SECRET_KEY and credentials
docker-compose up -d
```

Backend: http://localhost:8000 | Frontend: http://localhost:3000 | Docs: http://localhost:8000/docs

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Deploy to Render.com

```bash
# 1. Push to GitHub
git init && git add . && git commit -m "AI Gateway"
git remote add origin https://github.com/YOUR_USERNAME/ai-gateway.git
git push -u origin main

# 2. Connect repo to Render.com
# Go to render.com → Blueprints → New → Connect your repo
# Select deploy/render.yaml
# Set environment variables (SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD)

# 3. Render provisions:
#    - PostgreSQL 16 (persistent)
#    - Redis 7 (ephemeral, or persistent with paid plan)
#    - API Web Service (Docker, auto-scales)
#    - Frontend Web Service (Docker, auto-scales)
```

## API Reference

### OpenAI-Compatible Endpoints

```bash
# Chat completions
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}]}'

# List models
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-your-api-key"

# Embeddings
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":"Hello world"}'
```

### Admin Endpoints

```bash
# List providers
curl http://localhost:8000/admin/providers \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Create provider
curl -X POST http://localhost:8000/admin/providers \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"OpenAI","provider_type":"openai","base_url":"https://api.openai.com/v1","api_key":"sk-..."}'

# Test provider connection
curl -X POST http://localhost:8000/admin/providers/PROVIDER_ID/test \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get analytics overview
curl http://localhost:8000/admin/analytics/overview \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# List routing rules
curl http://localhost:8000/admin/routing \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me` | JWT signing key (required in production) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DEBUG` | `false` | Enable debug mode |
| `ADMIN_EMAIL` | `admin@localhost` | Initial admin email |
| `ADMIN_PASSWORD` | `changeme` | Initial admin password |
| `DEFAULT_RATE_LIMIT` | `100` | Requests per minute per user |
| `REQUEST_TIMEOUT` | `120` | Provider request timeout (seconds) |
| `MAX_RETRIES` | `3` | Max provider retry attempts |

## Database Schema

**Providers** — AI provider configs (base_url, api_key, models, weight, stats)
**GatewayModels** — Available models with pricing and metadata
**Users** — User accounts with roles and rate limits
**ApiKeys** — User API keys (bcrypt hashed, prefixed for display)
**RoutingRules** — Routing strategy per model/condition
**RequestLogs** — Every request with latency, tokens, status
**FeatureFlags** — Dynamic feature toggles
**SystemConfig** — Arbitrary key-value system configuration
**UserProviderAssignments** — Per-user provider access control

## Routing Strategies

```python
# Example: Failover chain for gpt-4o
# 1. Try OpenAI (primary, weight=100)
# 2. If OpenAI fails or returns 5xx → try DeepSeek
# 3. If DeepSeek fails → try Groq
# 4. If all fail → return 503

# Strategies are set per-routing-rule, not globally
# User-level routing rules override global defaults
```

## License

MIT — customize freely for your infrastructure needs.