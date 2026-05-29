# AI Gateway Platform
# Deploys directly to Render (native Python runtime — no Docker)

## Architecture
- Backend: FastAPI (Python 3.11+)
- Database: PostgreSQL (Render)
- Cache/Queue: Redis (Render)
- Frontend: Next.js 14 (can be deployed to Vercel or Render)

## Quick Deploy to Render

### 1. Backend (API Server)
```bash
# Push to GitHub, then connect to Render:
# https://dashboard.render.com/blueprint
```

### 2. Frontend (Admin Dashboard)
```bash
cd frontend
npm run build
# Deploy to Vercel or Render static
```

## Project Structure
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/v1/              # API routes
│   ├── core/                # Config, auth, rate limiting
│   ├── db/ # Database models & session
│   ├── models/              # Pydantic schemas
│   ├── providers/            # Provider adapters
│   ├── routing/             # Routing engine
│   ├── services/            # Business logic
│   └── middleware/          # Request middleware
├── requirements.txt
├── render.yaml              # Render blueprint
└── start.sh                 # Startup script

frontend/
├── app/                     # Next.js app
├── components/              # UI components
└── package.json
