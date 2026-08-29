# Saki Gateway — Model not-found guard + provider-key reuse fix

## Root cause (diagnosed, proven against live D1 + live gateway)
- Old `request_logs` showed `401 Unauthorized` from OpenRouter and `404 Not Found`
  from ai1833.shop. Those providers have since been cleaned up; only HCNSEC remains.
- NVIDIA Smart is fully working (live 200, returns content).
- HCNSEC returns HTTP 503 with body `{"error":{"code":"model_not_found",...}}`
  for models it does not serve (e.g. `gpt4o`, `openai/gpt-4o`, `saqib-ai`).
- The gateway's `RoutingEngine._fallback` treats any non-2xx as a provider
  failure and surfaces a raw 500 `All providers failed: ...`, which Saki/Saki
  clients render as "Model provider rejected your credentials".
- Real cause for the user-visible error: requesting models that are not in the
  `models` table. The gateway should short-circuit with a clean OpenAI-style
  404 instead of sending the request upstream.

## TODO
- [x] Read gateway routing + adapters + engine to confirm failure path
- [x] Confirm against live D1: providers, models, nvidia_smart state, request_logs
- [x] Establish green test baseline (7 passed)
- [ ] Add `_known_model_ids(...)` helper in `gateway.py` that unions:
      - `Model.model_id` / `Model.id` for enabled+active rows
      - provider `models` JSON entries (bare + prefixed)
      - NVIDIA Smart `public_model_id`
- [ ] Reject unknown models with 404 `model_not_found` (OpenAI-shaped error)
      BEFORE calling RoutingEngine / NvidiaSmartRouter
- [ ] Add regression tests:
      - unknown model -> 404 model_not_found, no upstream call
      - known model -> passes through
      - nvidia-smart model still works
- [ ] Run full pytest suite, keep green
- [ ] Deploy-trigger note (git push) — no schema change needed
- [ ] Test live after deploy: gpt4o (404), known model (200), nvidia-smart (200)
