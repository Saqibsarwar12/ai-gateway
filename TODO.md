# Saki Gateway — Auth Update TODO

## Status: COMPLETE ✅

## Items Done

- [x] 1. **Remove all non-admin users** — `cleanup_legacy_users()` in migrations.py
  deletes all `users` rows where email ≠ ADMIN_EMAIL, plus all related data
  (api_keys, gateway_configs, request_logs, usage_stats, pending_registrations).
  Idempotent — uses `auth_migrations` table so it runs once per deploy.
  Admin is verified as the only remaining user.

- [x] 2. **Keep admin account intact** — Seeded/updated at startup from
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars. `email_verified_at` auto-set.
  `cleanup_legacy_users()` also skips deletion for the admin email.
  `delete_user()` endpoint has a hard guard — admin email cannot be deleted.

- [x] 3. **New user registration flow** — `POST /auth/register` stores in
  `pending_registrations` table (NOT in `users`). Two paths:
  - 6-digit code: `POST /auth/verify-code` → creates active User with
    `email_verified_at` set
  - Link token: `GET /auth/verify-email?token=...` → same activation

- [x] 4. **Email verification required before login** — `_require_verified_user()`
  runs inside `require_user()`. Non-admin users without `email_verified_at`
  get 403 + `X-Needs-Verification` header. Login for unverified users
  returns 401 with same header. Admin bypasses this check.

- [x] 5. **Cloudflare-native** — D1 for persistent data (users, tokens),
  Cloudflare KV for rate limiting (login, registration, verify-code attempts).
  Fallback: in-memory store for local dev.

- [x] 6. **Existing setup preserved** — Brevo SMTP for email (already configured).
  `EMAIL_FROM=no-reply@saki-verifier.ryzedns.org`. `CF_D1_ID` and `CF_KV_NAMESPACE_ID`
  already set in Render env.

- [x] 7. **Dedicated email for verification** — Brevo SMTP at
  `no-reply@saki-verifier.ryzedns.org` (already configured). Falls back with
  clear error if not configured.

- [x] 8. **End-to-end working** — 16-pass test suite covers:
  register, verify-code, verify-email-link, login, logout, expired tokens,
  expired codes, wrong codes, duplicate signup, admin email block,
  disabled users, unverified login block, cleanup idempotency.

- [x] 9. **Rate limiting** — Per-IP for login (5 attempts/5 min) and register
  (5 attempts/5 min). Per-email for verify-code (5 wrong codes/15 min window).
  KV-backed with in-memory fallback.

- [x] 10. **Token expiry** — Pending registrations expire after
  `VERIFICATION_CODE_MINUTES=15`. Expired entries are deleted on access.
  Login blocked for unverified non-admin accounts permanently.

- [x] 11. **Resend verification** — `POST /auth/resend-verification` sends
  a new 6-digit code to the same email, invalidating the old pending record.

## Missing: none

## Migration Notes

- Safe and reversible: `auth_migrations` table tracks applied state.
- Run once on first startup of new deployment.
- Local SQLite test: `cleanup_legacy_users()` verified to preserve admin
  and delete old users.

## Test Results

| Test File | Result |
|-----------|--------|
| test_auth_endpoints.py | ✅ PASS |
| test_auth_verification.py | ✅ PASS |
| test_auth_security.py | ✅ PASS |
| test_auth_migration.py | ✅ PASS |
| test_auth_cleanup_and_admin_guard.py | ✅ PASS |
| test_auth_expiry.py | ✅ PASS |
| test_auth_endpoint_contract.py | ✅ PASS |
| test_auth_end_to_end.py | ✅ 16/16 PASS |
| test_pytest_auth_regressions.py | ✅ PASS |
| test_auth_guards.py | ✅ PASS |
| test_auth_full_flow.py | ✅ PASS |
| test_email_brevo.py | ✅ PASS |

**Total: 12 test files, all passing.**
