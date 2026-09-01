# Data Model: Полноценная изолированная Dev-среда GRAF

This feature adds no production application tables. It defines machine-local
Dev metadata and runtime ownership records only.

## DevCandidateManifest

| Field | Required | Rule |
|---|---:|---|
| `schema_version` | yes | Existing `dev-manifest.v1` schema |
| `manifest_id` | yes | Immutable ID derived from exact source SHA |
| `feature_id` | yes | Numeric Feature ID, `229` for this slice |
| `source_sha` | yes | Full 40-character commit SHA |
| `components` | yes | Backend, frontend, worker and `macos_app`; each has source SHA, version and digest |
| `migration_head` | yes | Resolved graph head(s), never guessed or `unknown` at promotion |
| `app_identity` | yes | Bundle ID, channel, signing identity, designated requirement, entitlements digest and update trust |
| `parent_manifest_id` | yes | Previous active manifest or `null` for first candidate |
| `health` | yes | Result, timestamp and metadata-only named checks |
| `dev_boundary` | yes | Development environment, loopback origins and safe data root |

Validation invariants:

- Every component `source_sha` equals the top-level `source_sha`.
- `app_identity.bundle_id` is exactly `pro.2brain.graf.dev` and channel is
  `dev`.
- Origins are HTTP(S) loopback and data root is not production-looking.
- A promotion candidate with unresolved migration head or non-pass required
  health is not eligible for active pointer commit.

## DevActivePointer

One atomic JSON pointer contains `schema_version`, `manifest_id`, `runtime_mode`
(`live` or metadata-only) and `updated_at`. There must be zero or one pointer;
the file is updated only after transaction success.

## DevRuntimeNamespace

Machine-local values bound to the manifest:

- Compose project name;
- service/container names;
- volume and network names;
- loopback host ports;
- state/data root;
- image names/tags and source-SHA labels.

No namespace may point at production, staging, `GRAF.app`, production data or
the historical local volumes.

## MigrationPreflightResult

Metadata-only record containing expected graph heads, observed database revision
or empty-state marker, comparison (`empty`, `match`, `mismatch`, `unknown`,
`multiple_heads`, `error`), action (`initialize`, `continue`, `block`) and a
human-readable safe next action. It must not include SQL dumps, credentials,
meeting content or raw logs.

## RuntimeOwnershipRecord

Metadata required to signal only an owned host backend: PID, source SHA, start
time token, exact command and log path under Dev state. Missing or mismatched
ownership fields make the process unowned and therefore unsignalable.

## PromotionTransaction

Metadata-only lifecycle:

```text
candidate_ready → lock_acquired → namespace_validated →
runtime_staged → app_staged → smoke_passed → pointer_committed
```

Any failure before `pointer_committed` invokes compensation and leaves the
previous manifest active. Compensation failure produces `rollback_required` and
never claims success.
