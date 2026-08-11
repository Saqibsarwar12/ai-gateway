# NVIDIA Smart design

## Scope

Add an admin-only NVIDIA-specific routing layer without changing the existing provider/model or user gateway systems. A configured NVIDIA Smart profile is one public OpenAI-compatible model while the backend selects among up to 50 configured NVIDIA accounts.

## Configuration

`nvidia_smart_configs` stores the administrator-selected public model ID, display name, fixed NVIDIA API base URL, and enabled state. `nvidia_smart_accounts` stores one encrypted credential, manually entered upstream model ID, label, enabled state, and persisted health/cooldown counters. The API never returns encrypted or plaintext credentials.

The fixed upstream base URL is `https://integrate.api.nvidia.com/v1`. Account model IDs are independent, so the same public NVIDIA Smart model can fan out to accounts using the same or different NVIDIA model IDs.

## Routing

The router caches only non-sensitive configuration metadata for a short TTL. It uses a short per-profile asyncio lock for account selection and state transitions, then releases the lock before making the upstream request. Selection uses a power-of-two candidate choice scored by in-flight load, recent failures, observed latency, and recency, rather than static account order. It honors `Retry-After` on 429/temporary upstream responses.

Temporary failures (408, 409, 429, 5xx, timeout, and transport errors) move an account into cooldown with bounded exponential backoff. Authentication failures are marked separately with a longer cooldown. Successful requests restore healthy status and reduce failure pressure. The router retries other healthy accounts and never retries a permanently known bad request on the same account.

## Authorization

All management endpoints require the existing admin dependency. Normal users cannot list, create, update, test, disable, or delete NVIDIA Smart configurations. Gateway callers still authenticate with the existing Saki bearer/API-key mechanism; the public NVIDIA Smart ID is only model routing metadata.

## Compatibility

`/v1`, `/v2`, `/v3`, existing providers, existing models, authentication, and personal gateways remain in place. NVIDIA Smart is added to model listing only when an enabled profile exists and is intercepted before the normal provider selection path only when the requested model matches its configured public model ID.

## Verification

Tests cover schema/migration creation, admin-only endpoints, key redaction, selection distribution, cooldown and Retry-After behavior, failover, recovery, concurrent selection, invalid credentials, and regression of the existing suite. A live NVIDIA test is run only when an admin-configured credential is available; credentials are never printed.
