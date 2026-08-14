# Saki Gateway Auth Update — TODO

## Current State
- D1 database has exactly one preserved admin: `saqibsarwar003@gmail.com` (verified, active)
- No other users or pending registrations remain in D1
- Local SQLite schema and auth flow have been validated
- Codebase already has email verification flow (register → verify-code/verify-email → login)
- Brevo email is configured (`no-reply@saki-verifier.ryzedns.org`)
- Cloudflare KV is used for durable rate limiting when configured; local tests use the in-memory fallback

## Tasks

### 1. Local environment sync
- [x] Update local SQLite admin to `saqibsarwar003@gmail.com` with password `Biscoe@@3`
- [x] Verify local DB schema matches D1 schema

### 2. User cleanup / migration
- [x] Create migration script `migrations/cleanup_users.py` that:
  - Connects to D1
  - Deletes all non-admin users
  - Deletes all pending registrations
  - Deletes all verification tokens for non-admin users
  - Preserves admin `saqibsarwar003@gmail.com`
  - Logs what was deleted
  - [x] Make migration idempotent (safe to run multiple times)

### 3. Rate limiting improvements (Cloudflare KV)
- [x] Add KV-based rate limiting for login attempts
- [x] Add KV-based rate limiting for verify-code attempts
- [x] Add KV-based rate limiting for registration attempts
- [x] Fall back to in-memory if KV not configured (backward compat)

### 4. Security hardening
- [x] Reject and delete expired pending registrations/tokens during verification
- [x] Add startup cleanup path for legacy user data
- [x] Ensure admin account cannot be deleted via API
- [x] Add input sanitization for usernames/emails

### 5. End-to-end testing
- [x] Test signup → receive email → verify code → login
- [x] Test signup → receive email → verify link → login
- [x] Test login with unverified account is blocked
- [x] Test duplicate signup handling
- [x] Test expired code handling
- [x] Test expired link handling
- [x] Test admin login still works
- [x] Test old non-admin users are rejected if they try to login

### 6. Deployment & docs
- [x] Update README with auth flow summary
- [x] Add migration run instructions
- [x] Verify Render deployment picks up changes


## Verification notes

- Frontend target: `https://saki-gateway.vercel.app/`.
- Backend/API target: `https://saki-gateway.indevs.in/`.
- Cloudflare D1 remains the production database; Cloudflare KV is used for durable rate-limit keys when its credentials are configured.
- The tracked legacy `backend/test_auth.py` manual script was removed from the working tree because pytest collected helper functions as tests and produced false failures.
