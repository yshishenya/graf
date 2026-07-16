# Provider-link API contract

All state-changing browser endpoints require the existing CSRF protection. Neither start nor confirmation accepts a provider subject, contact claim, provider payload, callback state or session token from the caller.

## Start

`POST /api/v1/auth/providers/{provider}/link/start`

- Requires an authenticated principal established by an active session and the selected workspace scope.
- Requires the provider to be enabled by the workspace policy and active membership at the time of start.
- Creates a callback state and bound `WorkspaceProviderLinkState` in `initiated` status. Returns only `authorization_url`, provider label and expiration; it does not expose a separate state nonce.
- Audits `provider_link_started` with safe metadata only.

## Callback

`GET /api/v1/auth/callback/{provider}`

- Continues to serve normal login states unchanged.
- For a state bound to a provider-link record: consumes the state, verifies the provider response, rechecks provider policy, stores a pending candidate and audits `provider_link_callback_verified`.
- It never creates an identity or user, changes a GRAF session, sets a new auth cookie, or returns a token/subject. It redirects only to the local confirmation page with an opaque intent identifier and safe result code.

## Confirmation

`POST /api/v1/auth/provider-links/{link_state_id}/confirm`

- Requires CSRF and `principal.auth_via_session`.
- Accepts no request body fields that could influence identity selection.
- Requires exact initiating user, workspace and session; valid active membership; non-expired `callback_verified` intent; and enabled provider.
- Creates/reuses an `ExternalIdentity` from the stored verified candidate in a nested transaction, marks the link terminal, clears candidate claims and writes a metadata-only audit event.
- Same-user existing identity is idempotent. Other-user identity is generic `409 provider_link_conflict` without owner/contact disclosure. Invalid, expired, replayed, disabled or cross-scope confirmation returns a safe code and does not mutate identities.

## Legacy compatibility

`POST /api/v1/auth/link` remains deprecated and always returns `409 provider_link_requires_verified_callback`; it never creates an identity.
