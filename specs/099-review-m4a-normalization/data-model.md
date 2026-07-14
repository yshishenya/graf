# Data Model: Review M4A Normalization

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

## Overview

Feature 099 keeps the existing ownership model:

- `Meeting` owns the user-visible record and deletion state;
- `MediaRevision` owns immutable accepted-source lineage;
- `TrackArtifact` owns accepted and derived stored objects;
- `ProcessingWorkflow`/`ProcessingResult` continue to own transcript processing.

It adds only durable playback-normalization work:

1. one job per accepted media revision and canonical profile;
2. durably tracked immutable attempt objects;
3. one automatic per-workspace legacy backfill run;
4. canonical-validation fields and a one-active-playback invariant on the
   existing artifact registry.

No `Meeting.playback_status` column is added. Playback state is derived from the
normalization job plus its validated canonical artifact, avoiding a second
source of truth.

## Existing entities

### Meeting *(existing, unchanged schema)*

Relevant existing fields:

- `id`, `workspace_id`, `created_by_user_id`, `device_id`;
- `status`, `processing_status`;
- `deletion_state`, `deletion_requested_at`, `deleted_at`;
- retention fields.

Rules:

- Transcript processing status is not playback status.
- A meeting whose deletion state is not `none` cannot publish a new playback
  artifact.
- Publisher and deletion both lock the meeting row. Deletion wins the race.
- Retention-triggered whole-meeting deletion cancels normalization instead of
  waiting for it.

### MediaRevision *(existing, behavior clarified)*

Relevant existing fields:

- `id`, `workspace_id`, `meeting_id`, `source_kind`;
- `status`, `immutable`, `accepted_at`;
- `manifest_sha256`, `track_sha256_by_role`, `duration_seconds`.

Source fingerprint v1 is SHA-256 over a canonical JSON value containing:

- media revision UUID;
- source kind;
- accepted manifest digest;
- accepted source-role/digest pairs ordered by role;
- accepted duration.

Authoritative source roles:

- `manual_upload`: `media`;
- `initial_recording`: `microphone` and `system`.

`playback` is explicitly excluded because it is a derived candidate. Its bytes
are still checked during upload/finalize and stored in `TrackArtifact`.

Rules:

- Normalization starts only when revision status is `accepted`.
- A changed source fingerprint during work blocks publication with
  `source_mismatch`.
- Automatic retry/backfill never creates a replacement source revision.

### TrackArtifact *(existing, extended)*

Existing fields remain authoritative for meeting/revision ownership, role,
storage key, digest, bytes, duration, codec, rate, channels, status, and
timestamps.

New nullable fields:

- `normalization_profile_version`: canonical profile string, set only on a
  fully validated active playback artifact;
- `validated_at`: timestamp of the complete canonical gate;
- `derivation_kind`:
  - `uploaded_candidate`;
  - `source_byte_copy`;
  - `lossless_faststart_remux`;
  - `single_source_transcode`;
  - `dual_source_mix_transcode`;
  - `legacy_unvalidated`;
- `source_fingerprint_sha256`: accepted source fingerprint proven immediately
  before publication;
- `validation_version`: validator implementation version, initially
  `playback_validator_v1`.

Playback statuses:

- `candidate`: accepted optional playback derivative, hidden from egress;
- `stored`: active only when profile/validation fields are populated;
- `superseded`: retained registry row whose object is no longer active and is
  cleanup/accounting eligible;
- `purged`: object deleted under lifecycle.

Canonical active predicate:

```text
track_role = 'playback'
and status = 'stored'
and normalization_profile_version = 'review_m4a_aac_lc_48k_mono_64k_v1'
and validated_at is not null
```

Constraints/indexes:

- portable PostgreSQL/SQLite partial unique index on
  `(workspace_id, media_revision_id)` for the canonical active predicate;
- index `(workspace_id, meeting_id, track_role, status)` for read/deletion;
- `validated_at`, profile, validation version, and source fingerprint must be
  all present or all absent for role `playback`/status `stored`;
- a present validation bundle also requires non-null `media_revision_id`; this
  prevents nullable revision keys from bypassing canonical uniqueness;
- non-playback source artifacts never receive normalization profile fields.

Migration behavior:

- Existing playback rows receive null validation fields and therefore are
  treated as legacy candidates by the new read model, even if their old status
  says `stored`.
- The partial unique index ignores those unvalidated legacy rows, so migration
  does not guess which duplicate object is valid.
- Automatic backfill validates a unique legacy candidate or derives from
  accepted source. Publication marks every other playback row for the revision
  `superseded` before activating one validated row.

## New entities

### PlaybackNormalizationJob

One durable current normalization truth per accepted revision/profile.

Fields:

- `id`: UUID primary key.
- `organization_id`: accepted-source organization FK copied for bounded
  scheduler handoff without a global content-table lookup.
- `workspace_id`: FK to `workspaces.id`.
- `requested_by_user_id`: accepted meeting owner FK used only to reconstruct
  the exact worker tenant context.
- `source_device_id`: accepted meeting device FK used only to reconstruct the
  exact worker tenant context.
- `meeting_id`: FK to `meetings.id`.
- `media_revision_id`: FK to `media_revisions.id`.
- `profile_version`: `review_m4a_aac_lc_48k_mono_64k_v1`.
- `validation_version`: `playback_validator_v1`.
- `trigger_kind`: `finalize`, `reconcile`, or `legacy_backfill`.
- `priority_class`: `new_ingest`, `due_retry`, or `legacy_backfill`.
- `source_kind`: accepted media revision source kind.
- `source_fingerprint_sha256`: expected authoritative-source fingerprint.
- `backfill_run_id`: nullable FK to `playback_backfill_runs.id`.
- `planned_action`:
  - `validate_candidate`;
  - `preserve_valid`;
  - `normalize_source`;
  - `unavailable_source`.
- `state`:
  - `queued`;
  - `running`;
  - `publishing`;
  - `retry_wait`;
  - `ready`;
  - `terminal`;
  - `cancelled`.
- `reason_code`: nullable safe enum.
- `workflow_id`: deterministic value with no title/filename/content.
- `workflow_run_id`: nullable Temporal run ID.
- `attempt_count`: total attempts across cycles.
- `cycle_attempt_count`: attempts in the current bounded execution.
- `retry_cycle_count`: completed four-attempt cycles.
- `next_attempt_at`: nullable due instant for `retry_wait`.
- `lease_owner_sha256`: nullable worker identity hash.
- `lease_expires_at`: nullable recovery boundary.
- `canonical_track_artifact_id`: nullable FK to `track_artifacts.id`.
- `queued_at`, `started_at`, `last_heartbeat_at`, `ready_at`,
  `terminal_at`, `cancelled_at`.
- `created_at`, `updated_at`.

Constraints/indexes:

- unique `(workspace_id, media_revision_id, profile_version)`;
- unique non-null `canonical_track_artifact_id`;
- index `(state, next_attempt_at, priority_class, created_at, id)` for bounded
  pickup;
- index `(state, lease_expires_at, id)` for bounded expired-lease recovery;
- index `(workspace_id, meeting_id, state)` for read/deletion;
- `ready` requires canonical artifact ID, `ready_at`, null reason, and matching
  active artifact profile/source fingerprint;
- `retry_wait` requires a retryable reason and `next_attempt_at`;
- `terminal` requires a permanent source reason and `terminal_at`;
- `cancelled` requires lifecycle reason and `cancelled_at`;
- source fingerprint is immutable after job creation; mismatch creates terminal
  truth for that job and reconciliation may create only a new profile/revision
  job, never mutate source lineage.

State transitions:

```text
queued -> running -> publishing -> ready
             |            |
             +-> retry_wait <-+
retry_wait -> queued
ready -> retry_wait (canonical object missing during reconciliation)
queued/running/publishing/retry_wait -> terminal
queued/running/publishing/retry_wait -> cancelled
ready -> cancelled (meeting deletion only)
```

Safe terminal reasons:

- `empty_source`;
- `unsupported_container`;
- `unsupported_codec`;
- `encrypted_media`;
- `corrupt_source`;
- `no_audio`;
- `ambiguous_audio_tracks`;
- `stream_limit_exceeded`;
- `duration_limit_exceeded`;
- `source_size_limit_exceeded`;
- `source_missing`;
- `source_mismatch`.

Safe retryable reasons:

- `storage_unavailable`;
- `database_unavailable`;
- `temporal_unavailable`;
- `temporary_storage_unavailable`;
- `worker_interrupted`;
- `dependency_unavailable`;
- `normalization_timeout`;
- `publish_interrupted`;
- `generated_output_invalid`.

Lifecycle cancellation reasons:

- `meeting_deleting`;
- `meeting_deleted`;
- `audio_purged`;
- `revision_superseded`.

### PlaybackNormalizationAttempt

One durably tracked immutable output attempt. It accounts for every MinIO candidate
object before upload and survives a worker crash.

Fields:

- `id`: UUID primary key and UUID path component.
- `workspace_id`, `meeting_id`, `media_revision_id`.
- `job_id`: FK to `playback_normalization_jobs.id`.
- `attempt_number`: monotonic within the job.
- `cycle_number`: retry cycle that created it.
- `state`:
  - `local_preparing`;
  - `uploaded`;
  - `published`;
  - `cleanup_pending`;
  - `cleaned`;
  - `purged`.
- `storage_object_key`: private immutable UUID key; never exposed in audit/API.
- `published_track_artifact_id`: nullable unique FK to `track_artifacts.id`, set
  atomically when the attempt transfers object ownership to the canonical row.
- `derivation_kind`.
- `selected_stream_index`: nullable non-negative integer for single media.
- `source_stream_count`, `source_audio_stream_count`.
- `source_duration_ms`: nullable positive measured value.
- `output_duration_ms`: nullable positive measured value.
- `output_byte_length`: nullable positive integer.
- `output_sha256`: nullable SHA-256.
- `output_audio_bit_rate`: nullable integer.
- `output_sample_rate_hz`, `output_channel_count`.
- `moov_before_mdat`: nullable boolean.
- `fragmented`: nullable boolean.
- `full_decode_passed`: nullable boolean.
- `cleanup_reason`: nullable safe enum.
- `created_at`, `uploaded_at`, `published_at`, `cleaned_at`, `updated_at`.

Constraints/indexes:

- unique `(job_id, attempt_number)`;
- unique `storage_object_key`;
- index `(workspace_id, meeting_id, state)` for deletion;
- index `(state, updated_at, id)` for bounded cleanup/restart recovery;
- `uploaded` requires size/digest;
- `published` requires full output facts, canonical gate pass, and the job's
  canonical artifact pointing at the same object;
- `cleaned`/`purged` require no active canonical artifact using the object;
- raw probe JSON, tags, chapters, stderr, filename, path, object URL, and media
  content are not persisted.

Ownership transfer:

- Before publication, the attempt row owns object cleanup.
- At publication, `TrackArtifact` becomes canonical owner and the attempt is
  marked `published` with the artifact relationship.
- Deletion deletes published objects through `TrackArtifact`; it deletes all
  other attempt objects through the attempt registry, deduplicating keys.

### PlaybackBackfillRun

One automatic inventory/mutation run per workspace/profile version.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK to `workspaces.id`.
- `profile_version`.
- `state`:
  - `inventory_pending`;
  - `inventory_running`;
  - `inventory_complete`;
  - `dispatching`;
  - `complete`;
  - `blocked`.
- `cursor_created_at`: nullable stable keyset timestamp.
- `cursor_media_revision_id`: nullable UUID tie-breaker.
- counters:
  - `evaluated_count`;
  - `preserve_valid_count`;
  - `validate_candidate_count`;
  - `normalize_source_count`;
  - `unavailable_source_count`;
  - `ready_count`;
  - `terminal_count`;
  - `cancelled_count`.
- `safe_block_reason`: nullable enum.
- `inventory_started_at`, `inventory_completed_at`, `completed_at`.
- `created_at`, `updated_at`.

Constraints/indexes:

- unique `(workspace_id, profile_version)`;
- cursor timestamp and UUID are both null or both non-null;
- no linked `legacy_backfill` job may move from inventory truth into `running`
  until `inventory_completed_at` is set and state is at least
  `inventory_complete`;
- counters are non-negative and monotonic;
- run completion requires no queued/running/publishing/retry-wait backfill job.

Inventory jobs, including terminal/skipped entries, are the per-revision report.
A separate backfill-item table is unnecessary. Audit events preserve state
history while the job remains current truth.

Automatic run recovery transitions are explicit:

```text
blocked -> inventory_pending
complete -> inventory_running (only after a later eligible watermark is proven)
```

Reopening clears completion/block timestamps and reason, retains the persisted
cursor and monotonic counters, and again blocks linked legacy mutation until the
new inventory page range reaches `inventory_complete`.

## Existing audit entity reused

### IngestAuditEvent

Normalization adds a strict writer with these event types:

- `playback_normalization_requested`;
- `playback_normalization_started`;
- `playback_normalization_retried`;
- `playback_normalization_retry_cycle_exhausted`;
- `playback_normalization_publishing`;
- `playback_normalization_completed`;
- `playback_normalization_skipped`;
- `playback_normalization_backfilled`;
- `playback_normalization_duplicate_reused`;
- `playback_normalization_failed`;
- `playback_normalization_cancelled`;
- `playback_normalization_temp_cleaned`;
- `playback_backfill_inventory_planned`;
- `playback_backfill_inventory_completed`;
- `playback_backfill_completed`.

Allowed metadata keys are restricted to:

- `profile_version`, `state`, `reason_code`, `trigger_kind`, `planned_action`;
- `attempt_count`, `retry_cycle_count`, `stream_count`, `audio_stream_count`;
- duration/byte buckets rather than source values where exact values are not
  needed;
- `full_decode_passed`, `moov_before_mdat`, `cleanup_result`;
- aggregate run counters and timestamps.

Allowed bucket/result values are closed enums:

- duration: `under_5m`, `under_30m`, `under_2h`, `under_4h`;
- bytes: `under_16mib`, `under_128mib`, `under_1gib`, `under_2_5gib`,
  `under_5gib`;
- cleanup: `not_required`, `deleted`, `already_missing`,
  `already_missing_pending_recheck`, `deferred_retry`. The pending-recheck value
  keeps a deleted in-flight attempt eligible for storage reconciliation without
  a time limit until a late immutable object is observed and removed.

Unknown keys, nested values, arbitrary strings, negative counters, booleans in
integer fields, naive timestamps, or event-incomplete metadata fail closed.

Forbidden values include raw filename, title, object key/path/URL, FFmpeg
stderr, tags, chapters, audio, transcript, summary, signed URL, provider
payload, credentials, and secret paths.

## Derived read models

### PlaybackPreparationState

Not persisted separately.

Fields:

- `state`: `preparing`, `available`, `unavailable`, `deleting`, or `deleted`;
- `reason_code`: safe enum;
- `label`: localized server-owned copy;
- `automatic_recovery`: boolean, true for queued/running/publishing/retry-wait;
- `can_play`: true only for a validated canonical artifact;
- `action`: always `disabled` for normalization repair; playback itself remains
  the only available action when ready.

Derivation rules:

1. Deletion state wins.
2. Access policy wins before content existence is disclosed.
3. Validated canonical artifact plus matching ready job -> `available`.
4. Open/retry job -> `preparing`.
5. Terminal source reason -> `unavailable`.
6. Accepted revision without job -> `preparing/reconciliation_pending`.
7. Transcript/summary status never changes this result.

## Transaction and race invariants

### Finalize

```text
lock/update accepted MediaRevision
persist source and optional playback candidate artifacts
upsert PlaybackNormalizationJob(state=queued)
persist ingest audit
commit accepted-source transaction
attempt normalization dispatch
attempt MediaScribe dispatch independently
```

An external dispatch failure cannot roll back accepted source custody.

### Publication

```text
upload complete immutable attempt object
begin database transaction
lock Meeting, PlaybackNormalizationJob, MediaRevision
verify meeting not deleting/deleted
verify revision accepted and source fingerprint unchanged
verify no active canonical artifact already won
mark prior playback rows superseded
insert/update one validated TrackArtifact
set job ready + canonical artifact pointer
set attempt published
commit
```

If any check fails, the attempt moves to cleanup and never becomes egress
visible. A uniqueness conflict means another worker won; the loser cleans its
attempt and converges on the winner.

### Deletion

```text
lock Meeting
set/observe deletion state
cancel open normalization jobs
collect unpublished attempt keys and all TrackArtifact keys
delete each distinct server object fail-closed
mark attempts/artifacts purged
persist deletion report classes
commit lifecycle truth
```

Publisher rechecks the same locked meeting and therefore cannot commit a new
ready artifact after deletion begins.

## RLS and maintenance boundaries

New tables force PostgreSQL RLS and use the standard request/worker workspace
predicate plus approved maintenance access.

Two new maintenance operations are allowed:

- `playback_normalization_inventory`;
- `playback_normalization_dispatch`.

They may enumerate only bounded IDs, tenant scope fields, state, due time,
profile, safe counters, and lineage digests. After choosing a candidate, the
worker constructs exact organization/workspace/user/device tenant scope from
the meeting and performs all content/artifact work under `context_kind=worker`.

The table names must be added to:

- application RLS validation inventory;
- test fixtures and future-table contract;
- PostgreSQL upgrade/downgrade tests;
- maintenance allowlist contract tests.

## Migration `0022_playback_normalization`

Upgrade order:

1. Add nullable validation/derivation fields to `track_artifacts`.
2. Create `playback_backfill_runs`.
3. Create `playback_normalization_jobs` without the canonical artifact FK if
   required to avoid circular create order.
4. Create `playback_normalization_attempts`.
5. Add canonical/backfill FKs and indexes.
6. Add the partial unique canonical-playback index for PostgreSQL and SQLite.
7. Create/refresh RLS policies and maintenance-operation function allowlist.
8. Leave existing playback rows unvalidated; perform no FFmpeg/MinIO backfill.

Downgrade order reverses schema changes after dropping policies, indexes, and
FKs. Downgrade does not delete object storage and must refuse to pretend that a
published derived object was externally erased; release rollback uses the
normal deployment backup/restore boundary.

## Data lifecycle

- Accepted source retention is unchanged.
- Canonical playback follows meeting retention/deletion.
- Published attempt history remains metadata-only under the meeting lifecycle;
  its object is owned by `TrackArtifact`.
- Unpublished attempts are deleted on success, supersession, cancellation,
  deletion, and startup reconciliation.
- Backfill run/job rows are meeting/workspace operational metadata and are
  purged or redacted with their owning workspace/meeting policy.
- Feature 099 does not introduce source-only retention, universal external
  erasure claims, or a new backup expiry policy.
