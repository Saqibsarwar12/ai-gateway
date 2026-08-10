# Saki Gateway verification-code design

Date: 2026-08-10
Status: Active implementation

## Goal

Replace the user-facing email-link verification flow with a one-time 4-digit email code while preserving FastAPI, D1, the existing admin account, the existing JWT contract, and the `/v1` and personal gateway routes.

## Data flow

1. Registration validates username, email, and password.
2. The pending registration stores only a PBKDF2 password hash and SHA-256 hash of a randomly generated 4-digit code.
3. Brevo receives the code in the existing REST API payload. The code is never logged or returned by the API.
4. The user enters the code in the frontend.
5. The backend compares a hash, enforces expiry and a small attempt limit, creates the user, deletes the pending row, and returns the existing access-token/user response.
6. The frontend stores that response and redirects to the dashboard.

## Security controls

- Code expiry is configurable and defaults to 15 minutes.
- Five incorrect attempts invalidate the pending registration.
- Code hashes, not codes, are persisted.
- Verification is one-time because the pending row is deleted on success.
- New users cannot log in, use API keys, or access protected routes before verification.
- Admin rows are not changed by this feature.
- The old token endpoint remains available for old emails but is not generated for new registrations.

## Verification checklist

- [ ] New signup sends a code through Brevo.
- [ ] Unverified login is rejected.
- [ ] Correct code creates and signs in the user.
- [ ] Wrong, expired, reused, and too-many-attempt codes fail safely.
- [ ] Duplicate email and username remain rejected.
- [ ] Admin login remains intact.
- [ ] `/v1` and personal gateway authorization remain intact.
- [ ] Frontend production bundle contains the code UI.
