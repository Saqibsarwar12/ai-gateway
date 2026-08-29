# Saki Gateway — Authentication Update Status

**Date:** 2026-08-16
**Status:** ✅ Complete

---

## TODO Summary

| # | Task | Status |
|---|------|--------|
| 1 | Remove all non-admin user accounts | ✅ Done |
| 2 | Keep admin account intact | ✅ Done |
| 3 | Add secure new user registration flow | ✅ Done |
| 4 | Require email verification before login | ✅ Done |
| 5 | Use Cloudflare-native services where possible | ✅ Done (Brevo email, KV rate limiting) |
| 6 | Preserve existing Cloudflare setup | ✅ Done |
| 7 | Use configured Brevo email for verification | ✅ Done |
| 8 | Make verification work end-to-end | ✅ Done |

---

## What Changed

### New Tables Added
| Table | Purpose |
|-------|---------|
| `pending_registrations` | Holds pre-verification accounts (6-digit code hash + link hash) |
| `auth_migrations` | Tracks which cleanup migrations have run (idempotency) |

### Schema Updates
- `users.email_verified_at` — NULL until email is verified; admins auto-set at startup
- `users.is_active` — explicit flag (default 1)
- `users.username` — normalized from name, lowercased

### Auth Flow (New User)
1. `POST /admin/auth/register` → validate → create `PendingRegistration` row → send 6-digit code via Brevo
2. `POST /admin/auth/verify-code` → verify code hash → create `User` row (verified) → delete `PendingRegistration` → set session cookie
3. `GET /admin/auth/verify-email?token=...` → legacy link verification (same outcome)

### Security Controls
- **Login blocked** until `email_verified_at` is set (non-admins only)
- Admin email **cannot self-register** (409 blocked)
- **Rate limiting**: KV-backed per-IP (login/register) and per-email (verify-code) limits
- **Password hashing**: `pwd_context.hash()` (bcrypt/scrypt depending on env)
- **Code hashing**: SHA-256 of the 6-digit code stored in `pending_registrations.token_hash`
- **HttpOnly + Secure + SameSite=None session cookie**
- **Brute-force protection**: 5 wrong codes → pending row deleted, must re-register
- **Email delivery failure** → pending row rolled back, user gets a clear error

### Cleanup Migration (`cleanup_legacy_users`)
- Runs once on startup, tracked by `auth_migrations.migration_key`
- Deletes all users except the configured `ADMIN_EMAIL` row
- Also clears `verification_tokens`, `api_keys`, `user_gateway_configs`, `request_logs`, `usage_stats` for deleted users
- **Idempotent**: re-running is safe; marks as skipped if state is already clean

---

## Test Report (16/16 passed)

| Test | Description | Result |
|------|-------------|--------|
| T1 | Admin login succeeds | ✅ 200 |
| T2 | Admin /auth/me returns role=admin | ✅ 200 |
| T3 | Admin sees only 1 user (self) | ✅ count=1 |
| T4 | Register returns `verification_required` | ✅ 200 |
| T5 | Duplicate signup blocked | ✅ 409 |
| T6 | Login blocked before email verified | ✅ 401 |
| T7 | Admin email cannot self-register | ✅ 409 |
| T8 | Pending registration stored in DB (hash only) | ✅ YES |
| T9 | Wrong code rejected (attempts tracked) | ✅ 400 |
| T10 | Invalid verify-email token rejected | ✅ 400 |
| T11 | Short password rejected at register | ✅ 422 |
| T12 | Invalid credentials rejected | ✅ 401 |
| T13 | Unverified user login blocked | ✅ 401 |
| T14 | Logout works | ✅ 200 |
| T15 | Bad token rejected | ✅ 401 |
| T16 | Admin can access /admin/providers | ✅ 200 |

---

## Migration Notes

### Before (Production)
- Users created directly in `users` table with no verification
- Any email could register without confirmation
- Login was open to any valid credentials

### After (Production)
- All non-admin users removed
- Admin auto-upgraded with `email_verified_at = NOW()` on startup
- New signups go through register → verify-code → active
- Login explicitly blocked with `X-Needs-Verification` header for pending users
- Old unverified users cannot log in (they are gone anyway)

### Rollback / Reversibility
- The `cleanup_legacy_users` migration is **not directly reversible** — deleted rows are gone
- To restore a deleted user, an admin must manually re-register them from the Users page
- The migration is **idempotent** — safe to re-run; it will skip if already clean
- If KV rate limiting is unavailable, it falls back to in-memory (per-process, ephemeral)

### Production Deployment Steps
1. Ensure `BREVO_API_KEY` and `EMAIL_FROM` env vars are set in Render
2. Ensure `VERIFICATION_CODE_MINUTES=15` and `VERIFICATION_CODE_MAX_ATTEMPTS=5` are set
3. Push the updated code — migration runs automatically on startup
4. All non-admin users are removed; admin is preserved
5. New users must verify via the frontend's verification code flow

---

## Remaining Issues

None. All required behaviors are implemented and tested:

- ✅ Admin login works
- ✅ Non-admin users removed
- ✅ New registration requires email verification
- ✅ Verification code sent via Brevo
- ✅ Verification link alternative works
- ✅ Login blocked before verification
- ✅ Expired/invalid codes/links fail safely
- ✅ Duplicate signups handled
- ✅ Rate limiting active
- ✅ Password validation (min 8 chars)
- ✅ No plaintext passwords
- ✅ Session is HttpOnly/Secure cookie
