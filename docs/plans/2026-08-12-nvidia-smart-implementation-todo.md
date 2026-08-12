# NVIDIA Smart implementation TODO

Scope: harden and verify the existing admin-only NVIDIA Smart feature without changing normal providers, authentication, `/v1`, or personal gateways.

- [x] Inspect project instructions, architecture, schema, routes, UI, deployment files, and existing commits.
- [x] Run preflight and baseline backend tests.
- [x] Verify official NVIDIA OpenAI-compatible API endpoint and request contract.
- [x] Preserve useful upstream status and bounded error details.
- [x] Reuse HTTP connections and forward supported request fields.
- [x] Persist account health when admin tests run.
- [x] Add editing controls for existing admin-managed accounts.
- [x] Add focused regression tests for failover, status propagation, request forwarding, and key redaction.
- [x] Run backend tests and frontend production build.
- [ ] Commit changes incrementally.
- [ ] Deploy through the existing Render/Vercel flow.
- [ ] Verify production health and NVIDIA Smart endpoints.

## Protected behavior

- Existing admin account and authentication remain unchanged.
- Normal provider/model management remains unchanged.
- `/v1`, `/v2`, `/v3`, and personal gateway routes remain unchanged.
- NVIDIA API keys remain encrypted, write-only, and absent from responses/logs.

## Implementation plan

1. Harden the existing router and gateway error contract.
2. Improve admin management UX without changing the API contract.
3. Add focused tests and run the complete regression suite.
4. Build and deploy only after local validation passes.
5. Verify live routes; report any credential-dependent test that cannot be run without exposing a key.
