# Contract: Auth OpenAPI Surface (013)

> This is a requirements-level contract for planning and test planning.

## Base Path

`/api/v1/auth`

## Common Auth Headers and Cookies

- Cookie/session-based auth may be accepted in addition to header-based internal calls, but providers remain server-issued and session-backed.
- Existing header-based tenant context used by ingest (`X-Organization-Id`, `X-Workspace-Id`, `X-User-Id`, `X-Device-Id`) remains valid for backward compatibility in migration window.
- New flows should eventually move consumers to `/api/v1/auth/me` and session tokens.

## GET /providers

User-visible provider discovery returns only providers enabled for the requested workspace.
Disabled providers are hidden from this endpoint and remain visible only through the
admin policy surface.

### Query

- `workspace_id` (UUID, required)

### Response `200`

```json
{
  "workspace_id": "uuid",
  "providers": [
    {
      "provider": "yandex|vk|telegram",
      "enabled": true,
      "label": "string",
      "requires_email": true
    }
  ],
  "residency": {
    "require_ru_local": true,
    "residency_region_tag": "ru"
  },
  "consent_version": "string",
  "consent": {
    "language": "ru",
    "version": "v1",
    "content_markdown": "string"
  }
}
```

### Error responses

- `403 provider_policy_denied`
- `503 auth_dependency_unavailable`

## GET /policy

Admin-visible policy read returns the full provider matrix for the workspace,
including disabled providers and residency controls.

### Query

- `workspace_id` (UUID, required)

### Response `200`

Same shape as `GET /providers`, but `providers` includes both enabled and disabled
entries so admins can review and change the complete policy.

## PATCH /policy

Admin-only policy update for provider allowlist and residency fields.

### Query

- `workspace_id` (UUID, required)

### Request body

```json
{
  "allow_yandex": true,
  "allow_vk": false,
  "allow_telegram": true,
  "require_ru_local": true,
  "residency_region_tag": "ru",
  "consent_text_version": "v1"
}
```

### Response `200`

Same shape as `GET /policy`.

### Required side effects

- Emits a redacted `workspace_auth_policy_updated` audit event with changed field names and final residency summary.

## POST /providers/{provider}/start

### Path params

- `provider`: `yandex|vk|telegram|tid|sber_id|mts_id|esia`

### Request body

```json
{
  "workspace_id": "uuid",
  "workspace_return_url": "https://...",
  "continue_session_id": "uuid?"
}
```

### Response `200`

```json
{
  "authorization_url": "string",
  "state_nonce": "string",
  "expires_at": "2026-06-10T12:00:00Z",
  "provider": "yandex|vk|telegram"
}
```

### Error responses

- `403 provider_disabled`
- `403 provider_not_allowed`
- `503 provider_unavailable`

## GET /callback/{provider}

### Path params

- `provider`

### Query

Provider-specific fields plus:

- `state` required
- `code` or provider token payload as provider requires

### Success response `302` or `200`

- session established and redirected with a stable `AuthSession` token.

### Error responses

- `400 callback_state_invalid`
- `400 callback_state_reused`
- `403 callback_denied`
- `503 provider_unavailable`
- `409 link_conflict` if policy requires explicit confirm and conflict is unresolved

## POST /link

### Request body

```json
{
  "candidate_provider": "yandex|vk|telegram",
  "candidate_provider_subject": "string",
  "provider_authorization_code": "string?",
  "expected_workspace_id": "uuid"
}
```

### Response `200`

```json
{
  "status": "confirmed|requires_confirmation|rejected",
  "user_id": "uuid",
  "provider": "yandex",
  "linked_identity_id": "uuid",
  "message": "string"
}
```

### Error responses

- `401 auth_required`
- `409 link_conflict`
- `403 link_rejected`
- `410 link_expired`

## POST /devices/register

### Request body

```json
{
  "device_public_id": "string",
  "platform": "macos",
  "client_version": "string?"
}
```

### Response `200`

```json
{
  "device_id": "uuid",
  "status": "pending|approved",
  "registration_state": "pending|approved|revoked",
  "workspace_id": "uuid",
  "created_at": "2026-06-10T12:00:00Z"
}
```

### Error responses

- `403 device_disabled`
- `403 device_untrusted`
- `409 duplicate_device`
- `503 auth_dependency_unavailable`

## POST /devices/{device_id}/revoke

Authenticated device owner or workspace `owner`/`admin` can revoke a device in
the workspace. Non-admin members cannot revoke another user's device.

### Path params

- `device_id` UUID

### Response `200`

```json
{
  "device_id": "uuid",
  "status": "revoked",
  "revoked_at": "2026-06-10T12:00:00Z"
}
```

## GET /me

### Response `200`

```json
{
  "user_id": "uuid",
  "workspace_id": "uuid",
  "active_session_id": "uuid?",
  "linked_providers": [
    {
      "provider": "yandex|vk|telegram",
      "provider_subject": "string",
      "is_primary": true,
      "confirmed_at": "2026-06-10T12:00:00Z"
    }
  ],
  "registered_devices": [
    {
      "device_id": "uuid",
      "status": "active|revoked|quarantined",
      "registration_state": "pending|approved|revoked"
    }
  ],
  "policy": {
    "workspace_id": "uuid",
    "providers": [],
    "residency": {
      "require_ru_local": true,
      "residency_region_tag": "ru"
    },
    "consent_version": "v1",
    "consent": {
      "language": "ru",
      "version": "v1",
      "content_markdown": "string"
    }
  }
}
```

## Errors across auth endpoints

All errors should use existing `Problem` model and include `code`, `message`, `request_id`, and `context` where safe.
