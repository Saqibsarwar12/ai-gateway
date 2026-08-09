# Saki Gateway — Approved Cleanup, Auth Timing, and Personal Gateway

## 1. Approved deployment cleanup
- [x] Remove plaintext `ADMIN_PASSWORD` from `render.yaml`
- [x] Repair malformed `APP_NAME` / `APP_BASE_URL` YAML entries
- [x] Validate YAML and confirm the existing admin account is not modified
- [x] Confirm local backend imports and route registration; existing tests are blocked by stale fixture DB files and one outdated Brevo mock

## 2. Login/signup timing investigation
- [x] Instrument request-path timings without logging passwords, tokens, or provider keys
- [x] Measure user lookup, password verification, and token creation separately; signup email timing remains isolated in the existing email service
- [x] Remove avoidable duplicate user lookup queries from login (email/name lookup is one query)
- [x] Preserve PBKDF2 password verification, email verification, and session checks
- [ ] Add regression tests for timing instrumentation and auth behavior

## 3. Personal gateway backend
- [x] Add safe username/slug migration and preserve existing names
- [x] Add `user_gateway_configs` migration for SQLite and Cloudflare D1
- [x] Add authenticated owner-only configuration CRUD
- [x] Encrypt provider API keys at rest and never return them
- [x] Add owner-bound `/{username}/v1/models` and `/{username}/v1/chat/completions`
- [x] Support only provider types already supported by the gateway
- [x] Add provider test and disabled/unconfigured/error handling
- [x] Keep `/v1`, `/v2`, and `/v3` behavior unchanged

## 4. Dashboard
- [x] Add a user-facing personal gateway configuration page
- [x] Show the personal base URL and safe key status only
- [x] Allow enable/disable, provider/model selection, replacement, testing, and deletion
- [x] Add navigation without exposing credentials

## 5. Validation and deployment
- [x] Run Python compile and frontend type/build checks
- [ ] Run auth regression tests and personal-gateway tests; current suite is blocked by stale SQLite fixtures and outdated Brevo mock
- [ ] Test invalid, expired, disabled, unconfigured, nonexistent, and cross-user access
- [ ] Commit incremental changes
- [ ] Push through the existing Render/Vercel deployment flow
- [ ] Verify production `/v1` and personal gateway URLs
- [ ] Report measured before/after timing and any blocker honestly
