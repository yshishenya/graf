# Automatic Backfill Contract

**Feature**: `099-review-m4a-normalization`

## Purpose

Define how GRAF automatically discovers, inventories, schedules, retries, and
completes legacy playback normalization without a user/admin command and without
overloading new recording work.

## Automatic ownership

- The media worker starts/resumes reconciliation automatically at process start.
- Reconciliation repeats every 60 seconds.
- No HTTP mutation, admin button, CLI command, feature flag toggle by a user, or
  per-record manual action is required.
- Alembic creates schema only; it never probes/transcodes/downloads media.
- A worker restart resumes persisted inventory cursor, jobs, due times, and
  attempt cleanup.

Production configuration must enable the worker and normalization queue as part
of the release. Deploy is not complete while the worker is absent/unhealthy.

## Scope

Eligible legacy record:

- meeting/revision belongs to an active workspace;
- revision state is `accepted`;
- source kind is supported by the existing first-party/manual contracts;
- meeting is not deleting/deleted;
- profile v1 has not already been completed or terminally classified.

Inventory includes records with:

- validated canonical playback (preserve);
- unvalidated existing playback candidate/legacy artifact (validate);
- retained accepted source but no valid playback (normalize);
- missing/purged/unsafe accepted source (terminal unavailable plan).

Backfill never fabricates source media, changes meeting title, creates another
meeting/revision/upload session, reopens an upload body, or changes transcript
processing.

## Per-workspace run

One `PlaybackBackfillRun` exists for each
`(workspace_id, review_m4a_aac_lc_48k_mono_64k_v1)`.

State sequence:

```text
inventory_pending
  -> inventory_running
  -> inventory_complete
  -> dispatching
  -> complete
```

`blocked` is reserved for a system configuration/RLS/schema condition that
prevents safe inventory. It is not a user-visible per-record failure and is
automatically retried after recovery.

Recovery transitions are:

```text
blocked -> inventory_pending
complete -> inventory_running
```

The second transition is allowed only after reconciliation proves a later
eligible `(created_at, id)` watermark. Reopening retains the cursor and
monotonic counters, clears prior completion/block timestamps and reason, and
requires a fresh `inventory_complete` boundary before newly linked legacy jobs
may mutate artifacts.

## Inventory-before-mutation rule

For each workspace/profile run:

1. Scan accepted revisions by stable `(created_at, id)` keyset pages of 100.
2. For every evaluated revision, upsert one job/inventory action and safe audit
   receipt:
   - `preserve_valid`;
   - `validate_candidate`;
   - `normalize_source`;
   - `unavailable_source`.
3. Advance the persisted cursor and aggregate counters in the same transaction.
4. Resume from that exact cursor after interruption.
5. After the final page, set `inventory_completed_at` and commit state
   `inventory_complete`.
6. Only then may a `legacy_backfill` job from that run enter `running`.

A workspace with zero eligible revisions still records an inventory-complete
run with zero counters and a safe completion receipt. Repeated reconciliation
reuses that completed run until a newly eligible legacy revision changes the
bounded inventory watermark; it never creates duplicate runs or work for rows
already classified under the same profile.

New-ingest jobs are not delayed by a legacy inventory run; the ordering rule
applies to mutations owned by that backfill run.

## Candidate decisions

### Preserve valid

Allowed only when the job already points to one profile-v1 artifact with a
recorded full validation receipt and matching source fingerprint. No object is
rewritten and no title/status outside playback is changed.

### Validate candidate

- A unique existing playback candidate/legacy row is tested through the full
  canonical gate.
- If fully canonical, promote/copy according to the normalization contract.
- If only container layout differs, losslessly remux.
- If invalid, derive from retained accepted source.
- If several legacy candidates exist, do not guess between them; derive from
  authoritative accepted source and supersede the candidates after success.

### Normalize source

Run the same workflow as a new finalized revision. Backfill has no special
weaker validator, object key, status, or publication path.

### Unavailable source

Persist terminal `source_missing`, `source_mismatch`, or lifecycle reason. Do
not create silence, an empty file, a fake player, or a replacement source.
Create the required metadata-only operational incident once.

## Scheduling and priority

Global bounded enumeration:

- workspace page: 50;
- per-workspace inventory page: 100;
- dispatch batch: 25;
- media activity concurrency per worker: 1.

Priority order:

1. newly finalized accepted source;
2. due transient retry for a user-visible record;
3. legacy backfill.

Within one priority class, order by due/created time then UUID for stable pickup.
No workspace may enqueue unbounded in-memory work; only persisted IDs in the
current batch are held.

## Retry without manual action

One Temporal execution performs no more than four attempts:

- first retry after 30 seconds;
- exponential coefficient 2;
- interval capped at 15 minutes.

After cycle exhaustion, persisted `retry_wait` due times are:

1. 15 minutes;
2. 1 hour;
3. 6 hours;
4. 24 hours;
5. every 24 hours thereafter.

The reconciler starts a new bounded execution when due while:

- meeting/revision remains eligible;
- accepted source still exists;
- deletion has not started;
- another workflow is not active;
- canonical playback has not already succeeded.

Cycle exhaustion emits one safe operational incident per cooldown escalation,
not one alert per low-level attempt. It never asks the user/admin to click Retry.

Permanent source reasons do not loop. A generated-output validation failure,
dependency absence, temp pressure, timeout, DB/storage/Temporal failure, or
crash is a system/retryable class, not a permanent source class.

## Workflow identity and duplicate pickup

Deterministic identity:

```text
playback-normalization/<media-revision-uuid>/v1
```

Rules:

- One DB job exists for revision/profile.
- Pickup atomically claims/leases a due job before Temporal start.
- “Already started/running” reuses the existing workflow and records a safe
  duplicate-reused receipt.
- An expired lease returns to pickup after checking current workflow/job truth.
- A completed ready job is never restarted.
- A second worker that loses publication cleans its attempt and reuses the
  canonical winner.
- Duplicate finalize, two browser tabs, refresh, network retry, and worker
  restart cannot create a second meeting or active playback artifact.

## Tenant and maintenance boundary

Two maintenance operation names are allowed only for the global scheduler:

- `playback_normalization_inventory`;
- `playback_normalization_dispatch`.

Maintenance enumeration may read only bounded IDs, workspace/organization/user/
device scope, profile/state/due time, source lineage digests, and safe counters.
It cannot read raw object bytes, filenames, titles, transcript, summary, tags,
or provider payload.

After selecting a row, all content/artifact work switches to the exact meeting's
`context_kind=worker` tenant scope. New tables use force-RLS policies and appear
in application/test inventories.

## Restart recovery

At startup, before normal dispatch:

1. Validate FFmpeg/FFprobe capability, task queue, database schema, writable
   work volume, and safe free-space threshold.
2. Reap UUID work directories not owned by an active local process.
3. Find attempts in `local_preparing/uploaded/cleanup_pending` whose
   lease expired.
4. Delete unpublished orphan objects or resume their job safely.
5. Reset expired `running/publishing` jobs to due recovery after checking whether
   a canonical artifact committed.
6. Resume backfill inventory cursor.
7. Dispatch new-ingest, due retry, then backfill batches.

No stale local file can be promoted merely because its name exists.

## Progress and read-only operations visibility

Allowed aggregate evidence:

- run state and timestamps;
- evaluated/action/ready/terminal/cancelled counts;
- queued/running/retry-wait counts;
- oldest job age bucket;
- retry cycle count bucket;
- profile/validator/dependency version;
- worker health and last safe heartbeat;
- cleanup result.

Forbidden:

- user/admin mutation controls;
- per-record filename, title, object key, URL, source path;
- probe/FFmpeg stderr or tags;
- audio/transcript/summary content;
- credentials or signed links.

## Completion criteria

A workspace run is `complete` only when:

- inventory completed and counters reconcile with persisted job rows;
- every linked job is `ready`, `terminal`, or `cancelled`;
- no linked attempt remains unpublished without a cleanup owner;
- each ready job points to exactly one validated canonical artifact;
- no title/source/transcript state changed as a side effect;
- safe audit receipts exist for inventory completion and run completion.

Feature production closeout additionally requires the expected legacy inventory
count, bounded batch execution, backlog drain or explicit impossible-source
terminal counts, worker health, and no unaccounted object residue.
