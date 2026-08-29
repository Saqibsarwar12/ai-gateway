# Saki Gateway — NVIDIA Smart / Model Routing Fix

## Diagnosis (verified live against https://saki-gateway.indevs.in + Cloudflare D1)
- NVIDIA Smart provider is **healthy**: live `nvidia-smart` request returned HTTP 200.
- The "Model provider rejected your credentials" errors the user saw are
  **stale historical `request_logs`** rows from before the provider cleanup,
  when OpenRouter (401) and `api.ai1833.shop` (404) were still in the
  fallback chain. Those providers are already removed; only HCNSEC remains.
- **Real current bug**: requests for models the gateway does not serve
  (`gpt4o`, `openai/gpt-4o`, `saqib-ai`) hit HCNSEC, which returns
  `503 model_not_found`; the gateway wraps that as a generic
  `500 "All providers failed"` instead of an OpenAI-standard `404`.

## TODO

### 1. Model existence pre-check in gateway (primary fix)
- [ ] In `backend/app/api/gateway.py` `chat_completions`, after loading
      models + providers + nvidia-smart config, build the set of all
      model ids the gateway can actually serve.
- [ ] If `req.model` is not in that set → raise `HTTPException(404,
      {model_not_found})` with a clean OpenAI-style error body. Stop
      routing to upstream for unknown models.

### 2. Surface a preservable auth key across RULA drysends
- [ ] Make startup create/rotate `PERSONAL_GATEWAY_ENCRYPTION_KEY`
      if missing so NVIDIA Smart keys keep decrypting across deploys.
      (No behavior change when key is stable.)

### 3. Charsofer for upstream auth errors
- [ ] Distinguish 401/403 from the upstream so it surfaces as
      `invalid_api_key` on that provider rather than "Client error '401'".
- [ ] 429 from upstream surfaces with retry-after.

### 4. Tests
- [ ] Add `tests/test_gateway_routing.py`:
      - unknown model → 404 model_not_found
      - upstream 401 → rate-limited/invalid key mapping
      - known model still routes normally
- [ ] Re-run full suite green.

### 5. Test against live deployment
- [ ] Deploy, then re-run the `nvidia-smart`, `auto`, `gpt4o` probes.
      `gpt4o` must now return 404 cleanly; `nvidia-smart` must stay 200.

## Non-goals (per user: don't redo working architecture)
- No new Workers, D1, KV, or auth-flow changes.
- No DB migration.
- No provider schema changes.
