# Data Model: F296

**Date**: 2026-11-16 | **Feature**: `296-server-cache-proof`

## Overview

F296 adds a read-only proof layer and a local deletion ledger. It does not add database tables or columns. Server entities are projections over existing `meetings`, `upload_sessions`, `track_artifacts`, `normalization_jobs`, and billing tables. Local entities live in the macOS app and in the queue directory.

## Server Projections

### DesktopPlaybackProof

| Field | Type | Default | Meaning |
|---|---|---|---|
| `state` | enum string (`PlaybackPreparationStateValue`) | `unavailable` | `available`, `preparing`, `unavailable`, `deleting`, `deleted` |
| `can_play` | bool | `false` | True only when playback is currently servable |
| `reason_code` | enum string | `no_audio` | Canonical reason; `canonical_ready` means ready |
| `media_revision_id` | UUID? | `nil` | Server UUID of the actual playback revision |
| `local_media_revision_id` | string? | `nil` | Local revision ID of the actual playback revision |
| `object_verified` | bool | `false` | Canonical object exists, `stat.size == artifact.byte_length`, and a bounded read probe succeeded |
| `verified_at` | datetime? | `nil` | Server UTC observation time, set only when verified |
| `automatic_recovery` | bool | `false` | True only when a known server path can repair without user action |

Validation:
- `object_verified=true` implies `can_play=true`, `state=available`, `reason_code=canonical_ready`, non-nil `media_revision_id`, non-nil `local_media_revision_id`, non-nil `verified_at`, a successful stat/size match and a successful bounded read.
- `archive_audio != true` forces `can_play=false`, `object_verified=false`, `reason_code=audio_not_archived`.
- `deletion_state != none` forces `deleting`/`deleted`, `can_play=false`.
- Unknown enum/string values are treated as keep-local by the client.

### DesktopSyncRetentionState

| Field | Type | Default | Meaning |
|---|---|---|---|
| `delete_after` | datetime? | `nil` | Effective deletion deadline; null = unknown, not forever |
| `policy_state` | enum string | `not_configured` | `active`, `blocked`, `unsafe`, `expired`, `not_configured` |

Validation:
- `active` requires non-nil `delete_after`.
- `unsafe`/`blocked`/`expired` never authorize local deletion.
- A deadline within 30 days is not safe for eviction.

### DesktopStorageStatusResponse

| Field | Type | Default | Meaning |
|---|---|---|---|
| `billing_role` | enum | required | `owner`, `admin`, `member` |
| `access_mode` | enum | required | `manage`, `read_only` |
| `plan_code` | string | required | Effective plan |
| `used_bytes` | int64? | `nil` | Visible only with management rights |
| `reserved_bytes` | int64? | `nil` | Active reservations |
| `capacity_bytes` | int64? | `nil` | Effective capacity including add-ons |
| `available_bytes` | int64? | `nil` | Capacity minus used/reserved |
| `threshold` | enum | `unknown` | `normal`, `80%`, `95%`, `full`, `unknown` |
| `action` | enum | `none` | `none`, `open_billing_storage`, `contact_owner` |
| `action_path` | string? | `nil` | Set only for manage |
| `meeting_retention_days` | int? | `nil` | Effective setting |
| `source_audio_retention_days` | int? | `nil` | Effective setting |
| `retention_policy_state` | enum | `not_configured` | Same vocabulary as above |
| `observed_at` | datetime? | `nil` | Server observation time |

Validation:
- `access_mode=manage` requires a personal owner with matching payer; amounts are visible and action may be `open_billing_storage`.
- Corporate owner/admin has `read_only`, visible amounts and `contact_owner` when over threshold.
- `member` has `read_only`, null amounts, `threshold=unknown`, `action=none`, `action_path=nil`.
- Unknown role gets the member profile.
- Missing DB session is 503; projection failure returns `threshold=unknown`, not 5xx.

### FinalizedUploadCustody

| Field | Type | Meaning |
|---|---|---|
| `session_id` | UUID | Finalized upload session |
| `media_revision_id` | UUID | Server revision this custody row describes; must equal the playback UUID |
| `local_media_revision_id` | string? | Local revision ID; must equal the playback local ID and the item |
| `archive_audio` | bool | Finalize choice |
| `finalized_at` | datetime? | Server finalization timestamp |

Lookup is scoped by workspace + meeting + **playback revision** + `status=FINALIZED`, newest first. Sync-state exposes it as `finalized_upload`; a mismatch of either server UUID or local ID with `playback`/the item is keep-local. The active `upload_session` is a separate object and is never mixed with custody.

## Client Value Objects

### DesktopServerProof

Decoded optional projection of the server blocks. Fields mirror the server; missing values are `nil`. It is never persisted in the queue in this feature.

### LocalArtifactFacts

| Field | Type | Meaning |
|---|---|---|
| `manifestPresent` | bool | Regular file inside recordings root |
| `reviewAudioPresent` | bool | Regular file inside recordings root |
| `transcriptionAudioPresent` | bool | Regular file inside recordings root |
| `transcriptionBytes` | int64? | File size |
| `transcriptionSha256` | string? | Known hash, if computed |
| `reviewPlaybackAvailable` | bool | Read-only projection, not a UI player call |
| `packageBytes` | int64? | Measured package size |
| `error` | string? | Sanitized failure code |

### LocalCacheEligibility

| Field | Type | Meaning |
|---|---|---|
| `verdict` | enum | `potentially_eligible`, `keep` |
| `primaryReason` | string | Stable code |
| `allReasons` | [string] | All failed gates |
| `bytes` | int64 | Package bytes |
| `proof` | DesktopServerProof? | Evidence snapshot |

Reason vocabulary:
`server_playback_ready`, `not_uploaded`, `not_finalized`, `account_scope_mismatch`, `local_unbound`, `lifecycle_unavailable`, `deletion_operation_open`, `confirmed_deletion`, `local_purge_pending`, `sync_conflict`, `proof_missing`, `proof_stale`, `meeting_mismatch`, `revision_mismatch`, `playback_not_available`, `playback_not_verified`, `verification_stale`, `archive_audio_false`, `archive_audio_unknown`, `grace_not_elapsed`, `deletion_state_unknown`, `access_state_not_owner`, `retention_unknown`, `retention_unsafe`, `retention_expired`, `retention_too_close`, `local_artifacts_missing`, `local_artifacts_outside_root`, `local_integrity_unverified`, `local_bytes_unknown`, `queue_item_undecodable`, `dependency_unavailable`.

### DryRunReport

| Field | Type | Meaning |
|---|---|---|
| `schemaVersion` | string | `local-cache-eviction-dry-run.v1` |
| `generatedAt` | date | Report time |
| `scopeFingerprint` | string | Workspace/user fingerprint |
| `policy` | object | Max proof age, grace, minimum retention |
| `totals` | object | inspected, eligible, eligibleBytes, rejected, rejectedBytes, unknownBytes |
| `byReason` | array | primary reason, count, bytes |
| `items` | array | fingerprint, state, verdict, primary/all reasons, bytes, proof summary |

Validation:
- `byReason` counts sum to `inspected`.
- No paths, titles, transcript text, tokens, or signed URLs.
- Report is written only under the injected report directory.

### CleanupReceipt

| Field | Type | Meaning |
|---|---|---|
| `schemaVersion` | string | `local-cache-cleanup-receipt.v1` |
| `action` | enum | `manual_cleanup`, `automatic_eviction` |
| `state` | enum | `pending`, `completed`, `noop` |
| `localRecordingFingerprint` | string | Stable local identity |
| `meetingFingerprint` | string | Stable server identity |
| `mediaRevisionFingerprint` | string | Local revision |
| `playbackRevisionFingerprint` | string | Actual playback revision |
| `verifiedAt` | date | Proof verification time |
| `bytes` | int64 | Bytes removed |
| `ownerScopeFingerprint` | string | Account/workspace |
| `appVersion` | string | App version |
| `createdAt` | date | Receipt time |

Validation:
- Written atomically, 0600, outside the recordings root.
- A `pending` intent is written before unlink and `completed` after. On retry, pending + missing WAV becomes `completed`/`noop`; a missing WAV without intent is reported as unexpected. Repeated completed action appends no duplicate.
- `playbackRevisionFingerprint` and `verifiedAt` are required for both cleanup actions.
- No paths, titles, transcript text, tokens.

## State Transitions

### Local item

`pending/uploading → uploaded` (existing) `→ verified proof → WAV removed → row remains with review/manifest`.

No new `UploadItemState` cases. No `retained/evicted` flag in the queue; the receipt and file presence are the local truth.

### Server playback

`no_audio / preparing / available / unavailable / deleting / deleted` (existing vocabulary). F296 adds `object_verified` as a separate per-response proof, not a new durable state.

### Cleanup/eviction

`eligible → revalidated → unlink WAV → receipt` or `eligible → revalidation failed → keep`. Automatic eviction adds `kill switch off → no-op` and `budget below warning → no-op`.

## Persistence

- No DB migration.
- Server reads use existing indexes: `ix_upload_sessions_transient_revision_custody`, track artifact canonical indexes, normalization job unique constraint.
- Local receipts/reports live in `<queue dir>/LocalCacheEviction/`; queue JSON is never rewritten by dry-run/cleanup except by existing upload/deletion flows.
- Proof is not persisted in `ServerTruthFingerprint` in this feature; if later needed, it must be optional and merge-explicit.
