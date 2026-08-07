# Saki Gateway Email Verification Design

Date: 2026-08-07
Status: Active implementation plan

## TODO checklist

- [x] Inspect FastAPI authentication, user schema, D1 adapter, frontend auth, and deployment configuration.
- [x] Audit Render environment variable names without exposing values.
- [x] Confirm the existing deployment uses FastAPI + D1 on Render and Next.js static output on Vercel.
- [x] Confirm the current project has no email delivery provider or verification flow.
- [ ] Add verification state and expiring, one-time token persistence.
- [ ] Add migration that preserves the admin row and removes non-admin users safely.
- [ ] Add registration rate limiting, input validation, and email delivery.
- [ ] Block login, JWT issuance, API-key use, and authenticated access until verification.
- [ ] Add verification and resend endpoints with safe failure behavior.
- [ ] Preserve admin login and existing API contracts where possible.
- [ ] Update signup/login UI for verification-required behavior.
- [ ] Add automated local tests for registration, duplicate handling, verification, expiry, login, logout, reset compatibility, and endpoint regression.
- [ ] Apply the cleanup migration to the live D1 database only after code validation.
- [ ] Deploy through the existing Render/Vercel flow and run live smoke tests.

## Architecture decision

Keep FastAPI as the authentication authority and keep Cloudflare D1 as the production database. Add a `verification_tokens` table for hashed, single-use email tokens and add `email_verified_at` to `users`. Existing admin rows are grandfathered as verified; newly registered users are inactive until the token is consumed.

Use the existing project email configuration if present. The audit found none, so the sender abstraction supports Resend and SMTP through Render secrets. Registration fails closed with a server configuration error if no sender is configured, rather than creating an account that can never be verified. Local tests use an in-memory capture transport and never send mail.

Keep the current bearer JWT contract for compatibility. JWT issuance is denied to unverified users, and database-backed auth dependencies re-check the user row so an already-issued token cannot bypass verification. Logout remains client-side token removal because the current system has no server-side session table; logout is tested as token disposal and no protected request after disposal.

## Safe migration

The migration is idempotent. It adds missing user verification columns, creates the token table, marks the existing admin account verified, deletes all non-admin users and their API keys, and records a cleanup marker. It does not update the admin password or replace the admin row. A pre-migration metadata backup should be taken before applying it to D1.

## Testing

Local tests use SQLite and dependency overrides. They assert admin login, unverified signup/login rejection, token verification, duplicate registration, expired-token rejection, resend throttling, password reset compatibility, logout behavior, and health/OpenAI route availability. Email delivery is asserted through the capture transport; live delivery requires configured Render sender secrets and a real inbox smoke test.
