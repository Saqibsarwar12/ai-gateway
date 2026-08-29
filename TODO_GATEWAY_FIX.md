# Saki Gateway Auth + NVIDIA Smart Hardening — TODO

## Original task (done already, verify only)
- [x] Remove all non-admin users from D1 (verified: only admin-001 remains)
- [x] Keep admin account intact (saqibsarwar003@gmail.com, verified active)
- [x] Email-verification-gated signup flow (code + link)
- [x] Rate limiting via Cloudflare KV for signup / verify / login
- [x] Token expiry, invalid/expired-link safe rejection
- [x] Brevo email configured (no-reply@saki-verifier.ryzedns.org)

## NEW task (this pass) — fix "Model provider rejected your credentials"
Diagnosis: NVIDIA Smart actually works (200). The real issue is:
  (1) HCNSEC (only enabled generic provider) does NOT serve the models
      the client requests (gpt4o, openai/gpt-4o, saqib-ai).
  (2) Gateway leaks generic "Server error 503 / 401" messages from httpx
      to the client, who then reads it as "provider rejected your credentials".

### TODO
- [ ] 1. Capture upstream error bodies in adapters (don't let httpx eat them)
      - ProviderAdapter.chat: on >=400, parse JSON body, keep error code/message.
      - Raise a typed UpstreamError(status_code, code, message) with the parsed
        error.code from the provider (e.g. "model_not_found", "invalid_api_key").
- [ ] 2. Surface the RIGHT HTTP status in the gateway:
      - 4xx auth/model problems → return the same status to the client, with the
        provider's code/message, instead of a blanket HTTP 500 "All providers failed".
      - 401/403 from upstream → 401 to the client with code "provider_auth_error"
        (so the real cause — invalid/expired provider key — is visible).
      - 503 with model_not_found → 404 model_not_found to the client.
      - True upstream outages (500/502/503 net errors) → 503 to the client.
- [ ] 3. Refactor engine._fallback to track the LAST provider error and let the
      gateway map it to the right client status, instead of always 500.
- [ ] 4. Add a "no matching provider/model" short-circuit in the gateway:
      if NO enabled provider serves the requested bare model AND it's not the
      NVIDIA Smart model, return 404 model_not_found immediately, BEFORE making
      any upstream call. Faster, clearer, no spurious 503.
- [ ] 5. Tests:
      - nvidia-smart still returns 200
      - known HCNSEC model (auto, glm-5.2) returns 200
      - unknown model (gpt4o) now returns 404 model_not_found (not 500)
      - bad provider key (simulate) returns 401 provider_auth_error (not 500)
      - engine _fallback surfaces the correct typed error
- [ ] 6. Run pytest, fix anything that breaks.
- [ ] 7. Commit + push to Render, wait for deploy, re-test live.

## Non-goals
- Do NOT touch the auth migration (already verified clean).
- Do NOT add new providers to HCNSEC; just fix error surfacing + model check.
- Do NOT reset the admin account or change encryption keys.
