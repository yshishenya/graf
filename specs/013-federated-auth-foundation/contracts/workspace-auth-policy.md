# Contract: Workspace Auth Policy and Residency

## Scope

Defines workspace-level controls for provider availability, residency, and user-facing consent.

## Data Objects

### WorkspaceAuthPolicy

- `workspace_id` (UUID, required)
- `allow_yandex` (bool)
- `allow_vk` (bool)
- `allow_telegram` (bool)
- `allow_tid` (bool, optional)
- `allow_sber_id` (bool, optional)
- `allow_mts_id` (bool, optional)
- `allow_esia` (bool, optional)
- `require_ru_local` (bool)
- `residency_region_tag` (string)
- `consent_text_version` (string)

## Behavioral Rules

1. `GET /api/v1/auth/providers` returns only enabled providers with workspace context.
2. Disabled providers are hidden from standard user flows.
3. `require_ru_local=true` requires:
   - auth session and profile metadata to route into RU policy-controlled stores
   - policy-specific consent copy
   - no claim fields indicating storage outside RU policy
4. Future providers can be configured as hidden feature flags and are not visible unless explicitly enabled.
5. Policy changes take effect on next auth interaction; existing active sessions remain deny/allow according to active policy and explicit revoke rules.

## Administrative Controls

- Admin can update allowlist and residency flags.
- Admin changes produce `AuthAuditEvent` with policy-diff metadata.
- Admin list includes current consent text version and whether providers are in trial/adapted mode.

## Residency Validation

- Any write path touching:
  - `ExternalIdentity` (safe profile fields),
  - `AuthSession`,
  - `AuthAuditEvent`,
  - `RegisteredDevice`,
must honor workspace residency mode.

For RU-local mode, implementation must avoid:
- cross-region object/metadata writes if policy forbids them,
- provider fallback that implicitly moves auth handling out of RU policy boundary.

## Consent Contract

- Consent text must be deterministic and link to current provider list.
- Russian-required locales should expose RU copy where `workspace` policy is Russian.
- Consent copy content is versioned and auditable.
- `GET /api/v1/auth/providers`, `GET /api/v1/auth/policy`, and `/api/v1/auth/me`
  expose the active consent version and content so clients can show the text
  before provider auth or account linking.
- Provider auth start persists an active RU consent copy for the workspace
  version before final account link or callback completion.
