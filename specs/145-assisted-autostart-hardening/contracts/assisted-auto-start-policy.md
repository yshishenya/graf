# Contract: Assisted Auto-Start Policy in Target Registry

## Transport

`GET /api/v1/desktop/meeting-detection/target-registry` keeps its existing owner
session/device authentication. The optional top-level field below participates in
the response ETag and cache document.

```json
{
  "schemaVersion": 1,
  "registryVersion": "2026.07.21.1",
  "generatedAt": "2026-08-12T12:00:00Z",
  "targets": [],
  "nonTargetRules": [],
  "assistedAutoStartPolicy": {
    "policyRef": "sha256:<opaque-hex>",
    "acknowledgementSubjectRef": "sha256:<opaque-hex>",
    "deviceRef": "sha256:<opaque-hex>",
    "policyVersion": "2026.08.12.1",
    "acknowledgementVersion": "2026.08.12.1",
    "enabled": true,
    "issuedAt": "2026-08-12T12:00:00Z",
    "expiresAt": "2026-09-12T12:00:00Z",
    "noticeMode": "internal_no_participant_notice"
  }
}
```

## Server rules

- Field is omitted unless the runtime switch is enabled.
- Field is omitted unless the authenticated tenant workspace exactly matches the
  configured internal workspace.
- Enabled configuration is invalid unless workspace ID, policy version,
  acknowledgement version and expiry are all present.
- Policy is omitted before `issuedAt` and at/after `expiresAt`, even if
  configuration still says enabled.
- `policyRef` is SHA-256 over workspace ID plus policy version and is not a raw ID.
- `acknowledgementSubjectRef` is SHA-256 over authenticated user ID, workspace ID
  and policy version; it prevents acknowledgement reuse after account switching
  without exposing raw IDs.
- `deviceRef` is SHA-256 over authenticated device ID, workspace ID and policy
  version for metadata-only capture evidence.
- Policy is never added to the persisted global registry document.
- Existing registry response remains backward compatible when the field is absent.

## Client rules

- Missing, malformed, disabled or expired policy means deny.
- Cached policy is usable only before both registry and policy expiry.
- Acknowledgement must exactly match `policyRef`, `acknowledgementSubjectRef`,
  `deviceRef` and `acknowledgementVersion`, and its timestamp must be inside the
  current policy validity window.
- Policy/acknowledgement must be checked both when offering countdown and
  immediately before capture start.
- Unknown fields remain rejected according to the existing strict server schema;
  the Swift decoder only accepts the declared policy shape.

## Runtime configuration

Committed defaults remain disabled:

```text
TWOBRAIN_ASSISTED_AUTO_START_ENABLED=false
TWOBRAIN_ASSISTED_AUTO_START_WORKSPACE_ID=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_VERSION=
TWOBRAIN_ASSISTED_AUTO_START_ACKNOWLEDGEMENT_VERSION=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_ISSUED_AT=
TWOBRAIN_ASSISTED_AUTO_START_POLICY_EXPIRES_AT=
```

Setting production values or deploying them is outside this implementation turn
until separately approved.
