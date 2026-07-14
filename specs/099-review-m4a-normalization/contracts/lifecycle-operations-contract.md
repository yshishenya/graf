# Lifecycle And Operations Contract

**Feature**: `099-review-m4a-normalization`

## Purpose

Define resource isolation, temporary-object ownership, deletion/retention races,
RLS, diagnostics, readiness, deployment, rollback, and production evidence for
automatic playback normalization.

## Runtime topology

Add one `rec-media-worker` service using:

- the existing Python application base;
- a media-only Docker target containing Debian Bookworm FFmpeg/FFprobe;
- the existing PostgreSQL, MinIO, and Temporal services;
- Temporal task queue `twobrain-rec-playback-normalization`;
- unprivileged `twobrain` user;
- 1 CPU, 1 GiB RAM;
- `max_concurrent_activities=1`;
- private disk-backed work volume with configured 6 GiB per-job budget.

API, migrations, and `rec-processing-worker` remain on the non-media target and
do not gain FFmpeg. The existing MediaScribe worker must stop overriding the
image user to root unless a separately evidenced need remains; feature 099 must
not copy that privilege to the media worker.

No new broker, datastore, object bucket, media API, public port, or direct
desktop dependency is introduced.

## Dependency capability gate

Media-worker readiness must prove:

- exact FFmpeg and FFprobe version/build configuration;
- native AAC encoder and `aac_low` profile;
- `ipod`/M4A muxer and `+faststart` behavior;
- required demuxers/decoders for the supported matrix;
- file-protocol restriction works;
- task queue/Temporal configured;
- database migration head present;
- MinIO available;
- work directory writable as non-root with mode `0700`;
- configured free-space threshold available;
- synthetic short encode/probe/full-decode succeeds without persisted residue.

One malformed user file does not make the service globally unready. Missing
runtime dependency, unwritable temp, schema mismatch, or inability to encode the
canonical profile does.

Release evidence records only safe dependency versions/capabilities and result
codes, not media paths or command stderr.

## Resource controls

| Control | Value |
|---|---:|
| Worker activity concurrency | 1 |
| CPU | 1 core |
| Memory | 1 GiB |
| Work-volume configured budget | 6 GiB |
| Final output cap | 128 MiB |
| Per-job reserve | 256 MiB |
| MinIO download chunk | 4 MiB |
| Probe timeout | 60 seconds |
| Activity timeout | 6 hours |
| Workflow execution timeout | 12 hours |
| Heartbeat interval | 30 seconds |
| Probe stdout cap | 256 KiB |
| Probe/FFmpeg stderr cap | 1 MiB, never persisted |
| Total/audio stream cap | 16 / 8 |

Before download and before conversion, require:

```text
free_bytes >= sum(selected accepted source bytes) + 128 MiB + 256 MiB
```

Source and output are disk-backed. No user-facing request and no worker helper
uses full-object `get_bytes()` for source media. Subprocesses use no shell, one
thread, file protocol only, bounded output, process-group cancellation, and
UUID-only private paths.

Near-limit benchmark on production-equivalent resources must pass before
release; defaults may be raised only with evidence and without hiding a smaller
accepted-source contract.

## Temporary ownership

Lifecycle stages:

```text
private local UUID work files
  -> durably tracked immutable MinIO attempt object
  -> validated but hidden uploaded attempt
  -> published canonical TrackArtifact OR cleanup
```

Rules:

- Local directory is `0700`; files are `0600`.
- Original filename is never used in path/process arguments.
- Attempt row and storage key exist before MinIO upload.
- Partial local output is never uploaded.
- Uploaded attempt is never exposed to playback/export/share.
- Publication transfers object ownership to one canonical `TrackArtifact`.
- Every nonpublished attempt has a cleanup owner/state.
- Cleanup runs in `finally`, after cancellation, after publication loss, during
  deletion, and at startup for expired leases/orphans.
- Object deletion is idempotent; missing object is recorded as already absent,
  while storage unavailability fails lifecycle action closed.

## Publication/deletion race

Publisher:

1. uploads complete validated immutable object;
2. opens DB transaction;
3. locks `Meeting`, job, and revision;
4. rechecks deletion state and source fingerprint;
5. publishes or loses/cleans.

Deletion:

1. locks `Meeting`;
2. enters deletion state;
3. cancels open jobs;
4. collects distinct unpublished attempt and artifact keys;
5. deletes server-controlled objects fail-closed;
6. marks attempts/artifacts purged and persists report truth.

Because both use the same meeting lock and publisher rechecks after object
upload, no new playback artifact can commit after deletion begins. A worker
that uploaded before losing the race deletes its tracked attempt and records
safe cleanup outcome.

## Deletion report

Add explicit server-controlled classes:

- `playback_audio_object`;
- `playback_normalization_temp`.

Report states distinguish:

- no artifact existed;
- purge requested;
- purge complete;
- retryable storage failure;
- local worker cleanup pending/complete where applicable.

Canonical playback remains part of the broader audio-content deletion result,
but the explicit rows prove the new derivative and temp lifecycle. Copy must not
promise deletion from backups before their existing expiry or from systems
outside GRAF control.

## Retention

- Whole-meeting retention uses the existing deletion workflow.
- Active normalization is not a reason to postpone an eligible whole-meeting
  deletion; deletion cancels it and wins the publish race.
- Accepted source and canonical playback follow the existing meeting retention
  policy.
- Existing valid playback may remain readable if accepted source is already
  absent and meeting policy still permits it; regeneration is unavailable and
  reported honestly.
- Feature 099 does not add source-only retention, playback-only retention, or a
  new backup expiry policy.

## RLS and maintenance

New direct-workspace tables:

- `playback_normalization_jobs`;
- `playback_normalization_attempts`;
- `playback_backfill_runs`.

Requirements:

- enable and force RLS on PostgreSQL;
- request/worker policy requires exact current workspace;
- include tables in application and test RLS inventories;
- cover read/write/cross-workspace denial on PostgreSQL;
- use portable SQLite constraints for local behavior, without claiming SQLite
  proves PostgreSQL locks/RLS;
- register only `playback_normalization_inventory` and
  `playback_normalization_dispatch` as new maintenance operations;
- keep those operations out of the historical global
  `rec_maintenance_allowed()` bypass, which is shared by unrelated tables;
- authorize them through a normalization-specific helper and `FOR SELECT`
  scheduler policies only on `playback_normalization_jobs` and
  `playback_backfill_runs`; attempts and all DML require exact tenant scope;
- maintenance queries read only bounded safe enumeration fields;
- all content/artifact operations switch to exact worker tenant context.

Foreign IDs are indistinguishable from not found. No cross-workspace backlog or
reason count appears in tenant UI.

## Audit and logging

Normalization audit reuses `IngestAuditEvent` through a dedicated strict writer.
Allowed values:

- event type, profile/validator version;
- state/reason/action/trigger codes;
- attempt/retry/stream counts;
- safe byte/duration buckets;
- timestamps, booleans, aggregate run counters;
- cleanup outcome.

Forbidden everywhere outside the authorized media process:

- original/raw filename;
- local path or MinIO object key/URL;
- signed URL;
- raw FFmpeg/FFprobe stdout/stderr or exception text;
- container tags, chapters, titles, artists, comments;
- raw audio/video;
- transcript/summary/provider payload;
- token, password, credential, secret path.

The subprocess wrapper maps exit/error patterns to a fixed reason enum and
discards raw text after bounded in-memory classification. The general logger
must never receive the exception message containing process arguments or
stderr.

## Operational incidents

Reuse the existing metadata-only support-incident surface for:

- retry cycle exhausted;
- normalization dependency/configuration unavailable;
- generated output fails canonical validation;
- impossible legacy source loss;
- stale publishing/cleanup lease not recovered in threshold;
- backfill blocked or no progress.

Incident deduplication key uses job/profile/reason hashes, never title/filename/
object key. Incidents are system visibility, not user/admin workflow steps.
Recovery remains automatic.

## Readiness and metrics

Allowed read-only metrics:

- worker health/capability version;
- queue state counts;
- oldest job age bucket;
- attempt/retry cycle buckets;
- ready/terminal/cancelled totals;
- backfill run progress/counters;
- temp cleanup pending count;
- last safe heartbeat;
- error reason counts.

Required readiness states:

- `ready`: dependency, schema, storage, queue, temp and synthetic capability pass;
- `degraded`: individual jobs retrying but worker capability remains intact;
- `blocked`: missing dependency/schema/temp/Temporal/MinIO capability prevents all
  safe work.

These states describe worker capability only. `ready` does not imply that an
individual recording, a legacy backfill run, or the production user journey
has completed; those require their own persisted states and closeout evidence.

No metric label contains workspace title, meeting title, filename, object key,
codec tag text, or content.

## Deployment gate

`infra/scripts/cd-remote.sh --dry-run` and `--execute` must include:

1. media target build and dependency/version capability checks;
2. compose config validation, non-root user, 1 CPU/1 GiB limit, concurrency 1,
   private work-volume configuration;
3. backup and restore rehearsal evidence;
4. migration `0022` upgrade and RLS validation;
5. API, processing worker, media worker, Temporal, MinIO and PostgreSQL health;
6. runtime SHA and image identity;
7. synthetic media capability smoke with cleanup;
8. one new accepted-source automatic normalization receipt;
9. legacy inventory creation before mutation and bounded backfill progress;
10. playback Range/seek/browser evidence;
11. transient retry/restart evidence without a user action;
12. deletion-race cleanup and residue scan;
13. metadata-forbidden-content scan.

Infrastructure smoke alone does not prove the user journey. Production closeout
also requires the normal recording and manual-upload review paths on authorized
working copies from `test-rec`, with safe metadata-only evidence and cleanup.

### Rolling-version compatibility

- Migration `0022` is additive. The pre-099 API and processing worker may run
  briefly against the upgraded schema but never create or claim normalization
  jobs.
- The 099 API may create durable jobs only after `0022` is present. Finalize
  remains successful when the media worker is temporarily unavailable; the
  reconciler owns dispatch once readiness returns.
- The media worker refuses pickup when its schema head, profile version or
  validator capability differs from the persisted job contract.
- Deployment must not report ready while API and media-worker runtime SHAs or
  profile contracts are mixed unexpectedly. The exact allowed transition is:
  migration, new API/read model, media-worker readiness, automatic dispatch.
- The previous processing worker remains unaffected because it neither reads
  nor writes playback-normalization tables and retains its separate task queue.
- After any 099 job or artifact exists, application rollback must retain the
  099 playback-readiness guard (forward-fix or compatibility rollback build).
  A raw pre-099 binary that could expose an unvalidated legacy playback row is
  not an allowed rollback target.
- Schema downgrade is last, only after dispatch stops and job/object truth is
  preserved or restored through the approved backup boundary.

## Rollback

- Stop new media-worker dispatch first.
- Existing API playback continues only for artifacts already valid under the
  deployed read contract; never fall back to source/on-demand conversion.
- Preserve accepted source and durable attempt/job truth for forward retry.
- Use deployment backup/restore for schema rollback when required.
- Do not delete canonical/source objects merely to downgrade application code.
- Record pending attempt cleanup owner and run the safe cleanup path before
  claiming rollback complete.
- A rollback must not re-enable unvalidated legacy playback as ready.

## Closeout evidence

Record:

- exact merged/release/runtime SHA;
- exact FFmpeg/FFprobe build capability result;
- migration/RLS/partial-uniqueness result;
- worker resource/concurrency/temp result;
- focused and full CI commands/counts;
- safe format/reuse/remux/transcode/full-decode matrix;
- automatic retry/restart and backfill counters;
- browser/embedded play+seek result;
- transcript/playback independent state result;
- deletion/cleanup residue zero;
- PR/issues/release/deploy links;
- limitation that the separate feature-097 security scan remains deferred.

Evidence must not include media content, transcript/summary text, filenames
outside approved aliases, object keys, signed links, or secrets.
