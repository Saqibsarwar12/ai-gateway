---
name: ai-gateway
purpose: OpenAI-compatible AI gateway with multi-provider routing, fallback,
  rate-limiting, per-user credits, and a built Next.js dashboard
stack: FastAPI (backend) + Next.js 14 static export (frontend) + SQLite
deploy: FastAPI on Render, frontend static export on Vercel

## Critical files

- `backend/app/main.py` — FastAPI entry. Hosts BOTH the API and the
  dashboard HTML. The `SPAFirstMiddleware` resolves the SPA-vs-API
  conflict (HTML for browsers, JSON for fetch).
- `backend/app/api/v1/openai.py` — `/v1/chat/completions`, `/v1/models`.
  Body parameter is `body: ChatCompletionRequest = Body(embed=False)` —
  this is required so OpenAI-standard JSON works.
- `backend/app/api/v1/admin.py` — `/admin/auth/{login,register,me,rotate-key}`,
  `/admin/{providers,users,routing,logs,analytics,models}`. The login
  response and `/auth/me` both include `api_key` so the `/keys` page can
  show it.
- `frontend/lib/auth.tsx` — Client-side auth. `API_BASE` is `process.env.NEXT_PUBLIC_API_URL || ''`.
  Do NOT hardcode any fallback URL.
- `frontend/app/keys/page.tsx` — User's API key dashboard. Must use
  `process.env.NEXT_PUBLIC_API_URL` only, no hardcoded fallback.
- `run/start.sh` — Local backend launcher. Sets `USE_SQLITE=true`,
  `ADMIN_EMAIL=admin@sakigateway.local`, `ADMIN_PASSWORD=Saki@Gateway2026!`,
  `SECRET_KEY=...`.

## Re-deploying

1. Backend: `bash run/start.sh` (local) or push to Render with
   `backend/Dockerfile`.
2. Frontend: `cd frontend && npm run build` produces `frontend/out/`.
   Sync that to Vercel (or any static host). The build reads
   `NEXT_PUBLIC_API_URL` from `.env` at build time — leave it empty so
   the SPA talks to its own origin.
3. **Never** hardcode any URL in the source. Always use env vars.
