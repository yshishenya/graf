# Data Model: F297

## Local recording manifest (additive, v5)

Existing `local-recording-manifest.v5` remains. New optional fields are additive and absent in historical packages.

| Field | Type | Meaning | Validation |
|---|---|---|---|
| `continuityGapBridgedFrames` | Int64? | Number of system-reference frames bridged with silence; only gaps <= 500 ms qualify | `>= 0`; absent for historical/clean recordings |
| `continuityRouteChangeCount` | Int? | Number of default-output route changes during the recording | `>= 0`; absent for historical/clean recordings; not the existing stream `routeChangeCount` |
| `partialContinuity` | Bool? | True when the recording is an explicitly partial continuity result (gap > 500 ms or unrecoverable route change) | Must be absent/false unless `failureReason == timelineMisaligned`; must not be set for a clean short gap <= 500 ms |

Rules:
- `partialContinuity == true` requires a playable review M4A and a non-empty canonical WAV.
- `partialContinuity == true` must not be used for AEC failure, invalid samples, format change or missing required source.
- Existing queue schema, track roles, retention fields and upload eligibility remain unchanged.
- Old clients ignore the new fields; new clients keep local files when proof is absent.

## Server retention

No new tables. Existing entities:

| Entity | Use |
|---|---|
| `RetentionPolicySnapshot` | Snapshot of meeting/backup/local-buffer days at scan time |
| `Meeting` | `retention_delete_after`, `retention_policy_state`, processing/deletion fences |
| `MeetingLifecycleAuditEvent` | Metadata-only audit for evaluation/block/skip/accept |
| `MeetingDeletionReport` | Backup state `pending_expiry` until operator prune proves expiry |

### Retention run state

| State | Meaning | Transition |
|---|---|---|
| `not_configured` | No retention days configured | scan records blocked/skip |
| `pending` | Not yet due | stays until due |
| `expired` | Deletion request created | terminal for the meeting |
| `blocked` | Processing/deleting/policy unsafe | re-evaluated next scan |

## Backup directory

| Field | Value |
|---|---|
| Name | `YYYYMMDDTHHMMSSZ` |
| Root | `TWOBRAIN_BACKUP_ROOT` or `/opt/projects/2brain-rec/backups` (not `TWOBRAIN_BACKUP_DIR`, which is one full backup path) |
| Required contents | `postgres.dump`, `schema.sql`, `inventory.jsonl`, `checksums.sha256`, `minio-objects/` |
| Prune eligibility | Own directory, name matches exact pattern, mtime/name older than `--older-than-days`, not symlink, not newest/current |
| Dry-run | Default; prints candidate paths and never changes files |
| Execute | `--execute` required; deletes only eligible directories |

## Referral pages

| State | HTTP | Render |
|---|---|---|
| Active valid token | 200 | Invitation page; analytics optional |
| Expired token | 410 | Clear unavailable state |
| Unknown/invalid token | 410 | Clear unavailable state |
| Referral disabled | 410 | Clear unavailable state |
| Database unavailable | 503 | Retryable unavailable state |
| Missing `public_analytics` | 200/410 | Must not raise; template uses safe default |

## Offer / checkout

| Field | Rule |
|---|---|
| `recurring_consent` | Checked by default in checkout; can be unchecked; server stores actual bool |
| Offer text | Says pre-checked by default and can be removed before payment; no “must not be pre-checked” |
| Duration limit | 4 hours (14,400 seconds) per recording; shown in offer and landing |
| Offer version | Existing `personal-2026-09-27` or next approved edition; no silent historical rewrite |
