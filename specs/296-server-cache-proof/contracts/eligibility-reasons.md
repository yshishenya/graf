# Contract: eligibility reasons

**Used by**: `LocalCacheEligibility`, dry-run report, cleanup/eviction receipts.

## Verdicts

- `potentially_eligible` — every required proof and local check passed at evaluation time. It is not permission to delete; cleanup/eviction must revalidate immediately before unlink.
- `keep` — at least one gate failed, is unknown, or errored.

## Primary reason codes

Ordered by gate precedence. The first failed gate is `primaryReason`; all failed gates are in `allReasons`.

| Code | Gate |
|---|---|
| `not_uploaded` | Item is not in uploaded/finalized state |
| `not_finalized` | No server finalization proof |
| `account_scope_mismatch` | Owner/workspace does not match the active scope |
| `local_unbound` | Item is local-only/unbound |
| `lifecycle_unavailable` | Lifecycle projection is unavailable |
| `deletion_operation_open` | Open deletion operation for this meeting/directory |
| `confirmed_deletion` | Server deletion already confirmed |
| `local_purge_pending` | Pending local purge task |
| `sync_conflict` | Conflict state is not none |
| `proof_missing` | No proof block or required field |
| `proof_stale` | Proof older than the allowed age |
| `meeting_mismatch` | Proof meeting differs from the item |
| `revision_mismatch` | Playback revision differs from the local revision |
| `playback_not_available` | Playback state is not available |
| `playback_not_verified` | `object_verified` is false |
| `verification_stale` | `verified_at` missing or too old |
| `archive_audio_false` | Finalize chose no archive |
| `archive_audio_unknown` | Archive choice missing |
| `grace_not_elapsed` | Server finalization is newer than the grace period |
| `deletion_state_unknown` | Deletion state missing/unknown |
| `access_state_not_owner` | Access is not owner |
| `retention_unknown` | Retention deadline/state missing |
| `retention_unsafe` | Policy is unsafe/blocked |
| `retention_expired` | Deadline is in the past |
| `retention_too_close` | Deadline is within the minimum remaining window |
| `local_artifacts_missing` | Manifest/review/WAV missing |
| `local_artifacts_outside_root` | Path escapes the recordings root |
| `local_integrity_unverified` | Size/hash mismatch |
| `local_bytes_unknown` | Footprint measurement failed |
| `queue_item_undecodable` | Queue item could not be decoded |
| `dependency_unavailable` | Timeout/offline/auth/5xx/unknown |

## Rules

- Any unknown string/enum, missing field, decode failure, timeout, 401/403/404/409/5xx, or account change → `keep`.
- `reviewAvailable`, `processingStatus=processed`, `uploaded`, and cached `serverTruth` are never safety proof.
- `archive_audio=true` alone is not proof; playback and object verification are also required.
- Storage quota/threshold is report metadata only; it never authorizes or blocks cleanup/eviction.
