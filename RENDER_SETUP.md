# Render Setup Guide

## Quick deploy

1. Push this repo to GitHub (or connect GitLab via mirror).
2. Create a new **Web Service** on Render, select **Docker** runtime.
3. Set the following environment variables in the Render dashboard:

| Variable | Value | Notes |
|---|---|---|
| `ADMIN_EMAIL` | `saqibsarwar003@gmail.com` | Your admin login |
| `ADMIN_PASSWORD` | `Biscoe@@3` | Your admin password |
| `SECRET_KEY` | *(auto-generated)* | JWT signing key — Render generates this |
| `USE_SQLITE` | `true` | Uses `/tmp/ai_gateway.db` on Render free tier |
| `DATABASE_URL` | `sqlite+aiosqlite:////tmp/ai_gateway.db` | SQLite path |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_bWVhc3VyZWQtY2F0ZmlzaC03NS5jbGVyay5hY2NvdW50cy5kZXYk` | Safe to commit |
| `CLERK_SECRET_KEY` | *(your rotated secret)* | **ROTATE THIS** — the old key was exposed. Get a new one from [clerk.com/dashboard](https://dashboard.clerk.com) |

> ⚠️ **Important:** The Clerk secret key that was shared in chat is compromised. Go to your Clerk dashboard, rotate it, and paste the new value into Render's env vars. Never commit it to the repo.

## Architecture

- **Single Docker container** serves both the FastAPI backend and the Next.js static frontend.
- **SQLite** is used on Render free tier (data resets on redeploy — upgrade to PostgreSQL for persistence).
- **Health check** at `/health` — Render uses this to confirm the service is up.

## API tiers

| Tier | Endpoint | Rate limit | Who gets it |
|---|---|---|---|
| v1 | `/v1/chat/completions` | 60 rpm | All users (default) |
| v2 | `/v2/chat/completions` | 200 rpm | Admin upgrades users |
| v3 | `/v3/chat/completions` | 600 rpm | Admin upgrades users |

All tiers are fully OpenAI-compatible. Users call the endpoint matching their tier.
Admin can upgrade any user's tier from the **Users & Keys** page in the admin panel.

## User flows

- **Public visitors** → land on home page, see Sign Up / Sign In (Clerk)
- **After sign-up** → auto-provisioned with v1 tier + API key → redirected to `/keys`
- **Admin** → logs in at `/login` with email/password → goes to `/admin`
- **Admin upgrades user** → Users & Keys page → click ↑ upgrade next to any user

## Local development

```bash
# Backend
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env.local` and fill in your values.
