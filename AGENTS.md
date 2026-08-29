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


## Runtime facts (verified 2026-08-29)

- **DB is Cloudflare D1** (`USE_D1=true` on Render), NOT local SQLite. Local
  `backend/ai_gateway.db` is stale/unused. Inspect live data via the D1
  HTTP API (X-Auth-Email + Cloudflare_Global_API_Key, account/db ids in
  Render env vars).
- **Encryption key**: `PERSONAL_GATEWAY_ENCRYPTION_KEY` (Render env) encrypts
  NVIDIA smart account keys (`nvidia_smart_accounts.encrypted_api_key`,
  Fernet, sha256-derived). Losing it makes all stored keys undecryptable
  (`credential_unavailable`) — accounts must be re-added.
- **API keys**: dashboard keys live in the `api_keys` table (full value
  stored, `sk-...` 46 chars). `_resolve_actor` in
  `backend/app/api/gateway.py` checks JWT → legacy `User.api_key` →
  `APIKey` table.
- **NVIDIA Smart**: public model id `nvidia-smart` (config
  `nvidia_smart_configs`, id `nvidia-smart-default`). 6 accounts in
  `nvidia_smart_accounts`, all `nvidia/nemotron-3-ultra-550b-a55b`.
  z-ai/glm-* models reached EOL on NVIDIA 2026-08-21 — nemotron-3-ultra
  is the current primary.
- **HCNSEC** (`https://api.hcnsec.cn/v1`, id `KAmaKuSve6pgSwY4Tsg7Yy`) is a
  reseller; its `DeepSeek-V4-Flash` channel was 429ing/ran out of balance
  (code 1113 余额不足). Model list there drifts — check /v1/models upstream.
- Render service id: `srv-d8csbti8qa3s73f399ug` (backend, indevs.in
  domain), deploy via git push to master.

## System verification (2026-08-29 16:07 UTC)

- Login (admin + user), /auth/me, /api-keys: all 200 via both indevs.in
  direct and Vercel `/admin/*` proxy.
- Registration → Brevo verification email → verify-code → login: full
  round trip verified live (plus-addressed gmail test). Brevo events show
  requests+delivered. Fake addresses hardbounce (expected).
- `nvidia-smart` chat: 200 OK via nemotron accounts. `auto` routes to
  HCNSEC reseller (agnes-2.5-flash responded — reseller balance OK).
- Chat endpoint auth: wrong/missing key → 401 invalid_api_key. `/v1/models`
  is intentionally open (OpenAI-compat convention).
- Keep-alive: cron-job.org "Health Check" pings /health every 5 min;
  backend stayed awake >5.5 h after last deploy (free tier normally sleeps
  at 15 min idle). GitHub Actions disabled on account (Actions has been
  disabled for this user) — do not rely on .github/workflows.
- Admin creds: see run/start.sh (ADMIN_EMAIL/ADMIN_PASSWORD).
