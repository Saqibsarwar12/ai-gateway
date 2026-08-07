# Saki Gateway — Email Verification Production TODO

## Phase 1: Local Schema & Config
- [x] Inspect current DB state (1 admin user, missing verification columns/tables)
- [x] Review auth/email/config code — most infra already exists
- [ ] Run `migrate_auth_schema()` against local SQLite to add:
  - `email_verified_at` on `users`
  - `pending_registrations` table
  - `verification_tokens` table
- [ ] Verify admin user is preserved and marked verified
- [ ] Confirm no legacy non-admin users exist

## Phase 2: Production Config
- [ ] Set Render env vars:
  - `BREVO_API_KEY`
  - `EMAIL_FROM=no-reply@saki-verifier.ryzedns.org`
  - `EMAIL_FROM_NAME=Saki Gateway`
- [ ] Verify `EMAIL_FROM` exactly matches Brevo verified sender
- [ ] Verify domain `saki-verifier.ryzedns.org` has SPF/DKIM/DMARC in Brevo
- [ ] Confirm app fails fast if `EMAIL_FROM` is missing

## Phase 3: Deploy & Test
- [ ] Build and push backend to Render
- [ ] Run production signup test
- [ ] Check Brevo Email Activity logs for exact status
- [ ] Verify email reaches test inbox
- [ ] Test verification link flow
- [ ] Test login rejection for unverified users
- [ ] Test token expiry

## Phase 4: Frontend & Polish
- [ ] Verify frontend shows verification-required UI
- [ ] Add Brevo response logging to email service
- [ ] Document migration and remaining issues
