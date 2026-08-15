# Saki Gateway — Custom Prompt Feature TODO

## Scope
Add private, per-account custom prompts that can target one model or all models, expose a safe high-directness preset, and apply the selected prompt consistently to authenticated gateway requests and the Playground.

## Steps
- [x] Inspect project guidance, auth, gateway routing, database migrations, UI primitives, deployment flow, and existing tests.
- [x] Run preflight and baseline regression tests.
- [x] Add the custom-prompts database model and idempotent SQLite/D1 migration.
- [x] Add authenticated prompt CRUD with ownership checks, validation, limits, and safe preset handling.
- [x] Resolve the best matching private prompt at request time and inject it server-side.
- [x] Add Playground prompt selection and a dedicated prompt-management page for users and admins.
- [x] Add regression tests for ownership, wildcard/exact matching, preset behavior, validation, and gateway injection helpers.
- [x] Run compile, pytest, TypeScript, and production frontend build checks.
- [ ] Verify deployment status and live API/UI behavior through the existing deployment flow.
- [x] Record migration and deployment notes; do not expose secrets.

## Product/security decisions
- Prompts are private to the authenticated account; one account cannot read or modify another account's prompts.
- Exact model patterns take precedence over `*`; inactive prompts are ignored.
- The user-facing `Extreme Directness` preset is a blunt, low-hedging style preset. It does not bypass platform, provider, legal, or safety controls.
- Prompt text is length-limited and never treated as executable code.
- Existing admin, auth, provider, model, and gateway behavior remains intact when no prompt is selected.
