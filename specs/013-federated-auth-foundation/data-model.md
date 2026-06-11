# Data Model: Provider-Neutral Federated Auth Foundation

## Entity Overview

### UserIdentity

Existing table is reused as the internal user root. For 013, `external_subject` continues to represent the current auth anchor when a user first logs in through a provider until additional identities are linked.

- `id`: UUID
- `organization_id`: UUID FK to `organizations.id`
- `external_subject`: string, stable user identity hint for the first linked source
- `display_name`: optional
- `status`: `active`, `disabled`
- `created_at`, `updated_at`

Validation:

- `status` must be active to authenticate.
- Deactivation prevents login and blocks all auth/session actions.

### ExternalIdentity

New table for provider identities.

- `id`: UUID
- `user_id`: UUID FK to `user_identities.id`
- `provider`: enum (`yandex`, `vk`, `telegram`, `tid`, `sber_id`, `mts_id`, `esia`)
- `provider_subject`: stable provider subject/ID
- `provider_username`: optional
- `email`: optional canonicalized
- `phone`: optional normalized
- `display_name`: optional
- `is_verified`: bool
- `subject_issued_at`: optional timestamp
- `last_seen_at`: optional timestamp
- `meta`: JSON for safe provider proof fields
- `created_at`, `updated_at`

Unique constraints:

- `(provider, provider_subject)` globally unique.

Validation:

- `provider_subject` required.
- Optional `email`/`phone` values are only used for verified-link proposals and must be normalized.
- Raw OAuth tokens are not persisted in this table.

### WorkspaceAuthPolicy

Workspace-level policy and residency control.

- `id`: UUID
- `workspace_id`: UUID FK to `workspaces.id`
- `allow_yandex`: bool
- `allow_vk`: bool
- `allow_telegram`: bool
- `allow_tid`: bool
- `allow_sber_id`: bool
- `allow_mts_id`: bool
- `allow_esia`: bool
- `require_ru_local`: bool
- `residency_region_tag`: string, e.g., `ru`
- `consent_text_version`: string
- `created_at`, `updated_at`

Validation:

- At least one of enabled provider booleans should be true, except when workspace is being rolled into locked auth-readonly mode.
- `require_ru_local=true` implies provider selection and storage policies use RU-local boundaries.

### AuthSession

Short-lived server-authenticated session for API access and upload operations.

- `id`: UUID
- `user_id`: UUID FK to `user_identities.id`
- `workspace_id`: UUID FK to `workspaces.id`
- `device_id`: UUID FK to `registered_devices.id`
- `provider`: string
- `session_token_hash`: optional hashed token (rotated)
- `status`: `active`, `expired`, `revoked`, `suspicious`
- `issued_at`: timestamp
- `last_seen_at`: timestamp
- `expires_at`: timestamp
- `claims_fingerprint`: optional short digest
- `created_at`, `updated_at`

Validation:

- Tokens are hashed in persistence.
- Expired/revoked/suspicious sessions are denied.
- Rotation and last-seen updates occur on validation.

### AuthSessionDeviceBinding

Junction between a session and a device heartbeat/authorization context.

- `session_id`: UUID FK to `auth_sessions.id`
- `registered_device_id`: UUID FK to `registered_devices.id`
- `device_state`: `trusted`, `untrusted`, `blocked`
- `last_heartbeat_at`: optional timestamp
- `revocation_reason`: optional string

Validation:

- Active sessions require trusted or explicitly approved untrusted state per workspace policy.
- `blocked` binding forces re-auth and blocks upload/session use.

### RegisteredDevice (extended)

Existing table is reused and extended semantically in 013.

- `id`: UUID
- `workspace_id`: UUID FK to `workspaces.id`
- `user_id`: UUID FK to `user_identities.id`
- `device_public_id`: stable client-visible identifier
- `platform`: `macos`
- `client_version`: optional
- `status`: `active`, `revoked`, `quarantined`
- `registration_state`: `pending`, `approved`, `revoked`
- `trusted_by`: optional `user_id` UUID of approver
- `revoked_by`: optional `user_id` UUID
- `last_seen_at`
- `created_at`, `updated_at`

Validation:

- In 013, `status` and `registration_state` must be aligned with workspace policy before ingest scope acceptance.
- Revoked/quarantined devices cannot pass tenant authorization.

### WorkspaceProviderLinkState

Tracks pending/active/in-progress identity linking operations.

- `id`: UUID
- `workspace_id`: UUID FK to `workspaces.id`
- `initiating_user_id`: UUID FK to `user_identities.id`
- `source_provider_identity_id`: UUID FK to `external_identities.id`
- `target_provider_identity_id`: UUID nullable FK to `external_identities.id`
- `candidate_identity_subject`: optional string
- `candidate_email`: optional string
- `candidate_phone`: optional string
- `status`: `initiated`, `requires_confirmation`, `confirmed`, `rejected`, `expired`, `conflicted`
- `resolution`: optional string
- `expires_at`
- `created_at`, `updated_at`

Validation:

- `confirmed` state must map to exactly one stable `user_id`.
- Conflicts are logged and must not silently auto-resolve.

### AuthCallbackState

- `id`: UUID
- `provider`: enum
- `state_nonce`: string unique
- `workspace_id`: UUID FK to `workspaces.id`
- `requested_redirect`: optional string
- `expected_state`: string
- `expires_at`: timestamp
- `used_at`: optional timestamp
- `result`: `pending`, `completed`, `rejected`, `expired`
- `error_code`: optional string
- `created_at`

Validation:

- `state_nonce` must be unique and single-use.
- Expired states must be rejected and auditable.

### AuthAuditEvent

Auditable security/privacy metadata for auth flows.

- `id`: UUID
- `workspace_id`: UUID FK to `workspaces.id`
- `user_id`: UUID nullable
- `event_type`: enum
  - `provider_auth_started`, `provider_callback_success`, `provider_callback_failed`
  - `provider_link_requested`, `provider_link_confirmed`, `provider_link_rejected`, `provider_link_conflict`
  - `device_registered`, `device_revoked`, `session_revoked`, `session_expired`, `session_rotated`
- `provider`: optional string
- `actor_user_id`: UUID nullable
- `actor_ip_hash`: optional string
- `request_id`: optional UUID
- `outcome`: `success`, `failure`, `rejected`
- `metadata`: JSON with safe policy fields only
- `created_at`

Validation:

- Redacted redaction policy applies to `metadata`.
- Raw tokens/claim payloads are forbidden in stored metadata.

### WorkspaceConsentCopy

- `id`: UUID
- `workspace_id`: UUID FK to `workspaces.id`
- `language`: string (`ru`, `en`)
- `version`: string
- `content_markdown`: markdown or short rich text
- `is_active`: bool
- `published_at`: timestamp
- `created_at`, `updated_at`

Validation:

- RU-visible copy should be available when workspace has RU requirements enabled.
- Versioning used for transparency and audit replay.

## State Transitions

### AuthSession

```text
active -> expired
active -> revoked
suspicious -> revoked
suspicious -> active (after re-validation)
```

### WorkspaceProviderLinkState

```text
initiated -> requires_confirmation
requires_confirmation -> confirmed
requires_confirmation -> rejected
initiated -> conflicted
conflicted -> expired
initiated -> expired
confirmed -> revoked
```

### RegisteredDevice

```text
status: active -> quarantined
status: active -> revoked
status: quarantined -> active
status: quarantined -> revoked

registration_state: pending -> approved
registration_state: pending -> revoked
registration_state: approved -> revoked
```

## Query Patterns

- Auth context lookups always join `WorkspaceMembership` + `WorkspaceAuthPolicy` + `AuthSession` + `RegisteredDevice`.
- Provider link proposals evaluate candidate `email`/`phone` against active `ExternalIdentity` in the same workspace.
- Auth callback validation joins `AuthCallbackState` by nonce and validates expiry, provider, and workspace.
