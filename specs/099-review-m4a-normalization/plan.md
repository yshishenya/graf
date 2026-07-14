# Implementation Plan: Review M4A Normalization

**Branch**: `codex/099-review-m4a-normalization` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/099-review-m4a-normalization/spec.md`

## Summary

Feature 099 guarantees a stored, validated `meeting-review.m4a` for every
supported valid accepted recording source without user or administrator work.
Successful finalize creates durable normalization intent in the accepted-source
transaction; a separate non-root Temporal media worker validates an uploaded
playback candidate or derives AAC-LC/M4A from manual media or the explicit
first-party microphone/system pair. Temporary failures retry automatically and
are reconciled after restarts. Legacy records are inventoried first and then
processed in bounded automatic batches.

The design keeps source custody, transcript processing, and playback truth
separate. Only a completely decoded and profile-validated immutable artifact is
published. Playback requests continue to stream the stored object with ranges
and never transcode on demand. The cabinet shows playback preparation/readiness
independently from transcript/summary state and exposes no retry, reprocess, or
backfill control.

## Technical Context

**Language/Version**: Python >=3.13; SQLAlchemy 2/Alembic; FastAPI/Pydantic 2;
Temporal Python SDK; Jinja/HTMX/vanilla JS cabinet; existing Swift 6/macOS 14+
client as a regression surface only.

**Primary Dependencies**: Existing ingest/finalize, MinIO storage, Temporal,
cabinet egress/read models, retention/deletion, support incidents, RLS and
deployment scripts. Add the Debian Bookworm `ffmpeg` package (`ffmpeg` and
`ffprobe`) only to a media-enabled Docker target; no PyAV or frontend framework.

**Storage**: PostgreSQL production with SQLite compatibility. Migration
`0022_playback_normalization.py` (after current `0021` head) adds normalization
jobs, attempts, per-workspace backfill runs, canonical validation fields on
`TrackArtifact`, and a portable partial unique index for one active stored
playback artifact per media revision. MinIO stores immutable accepted source,
candidate, attempt, and canonical objects with distinct ownership.

**Testing**: pytest unit/contract/integration tests; real FFmpeg container
capability and synthetic-media tests; SQLite and disposable PostgreSQL
migration/RLS/concurrency tests; existing Swift upload/capture regression tests;
Chrome and embedded cabinet playback/status E2E; `test-rec` end-to-end evidence;
Ruff; canonical `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk significant feature / active Spec Kit
slice. It handles untrusted media, CPU/disk subprocess work, durable queues,
storage derivation, RLS, deletion races, background recovery, cabinet UX,
Docker/deploy topology, and production backfill.

**Release Gate**: Planning performs no deploy. After implementation, focused
validation, full local CI, independent review, and explicit integration
approval, merge the scoped PR. Then prepare the next free CalVer release and run
`infra/scripts/cd-remote.sh --dry-run`. Release/tag/GitHub Release and
`--execute` require a fresh release/deploy approval for the validated candidate.
Production closeout requires migration, worker health, bounded backfill,
browser/embedded playback, real user-path E2E, and residue-free cleanup.

**Target Platform**: Linux server/cabinet and a dedicated Linux media worker;
Chrome/Safari-compatible HTTP M4A playback; embedded macOS WebView using the
same server cabinet. No native app behavior change is planned.

**Project Type**: Web service with server-rendered cabinet, background Temporal
workers, PostgreSQL/MinIO storage, and a native macOS capture/upload client.

**Performance Goals**:

- finalize adds only bounded database upsert/commit work and never waits for
  probe/transcode;
- accepted-source normalization is queued within 60 seconds even after a lost
  immediate dispatch;
- playback range responses perform no conversion and retain bounded streaming;
- media worker concurrency is 1 at 1 CPU/1 GiB, with no complete source object
  in process memory;
- backfill inventories 100 rows per keyset page and dispatches at most 25 jobs
  per batch, behind new-ingest and due-retry jobs;
- synthetic near-limit benchmark on production-equivalent resources completes
  within the 6-hour activity timeout before release.

**Constraints**:

- every supported valid retained source converges automatically; no user/admin
  retry, reprocess, or backfill mutation;
- exact source limits remain 4 hours, 1 GiB manual file, 2.5 GiB track, and 5
  GiB first-party package;
- at most 16 total/8 audio streams; 128 MiB final output; 6 GiB disk-backed work
  budget; concurrency 1;
- accepted source fingerprint excludes the optional playback derivative;
- byte-for-byte reuse requires the complete canonical gate and full decode;
- manual multi-stream media uses one usable stream or one unique default only;
- first-party fallback mirrors the already defined two-role 50/50 aligned mix;
- playback publication is database-atomic visibility over an immutable object,
  not a claimed MinIO/PostgreSQL distributed transaction;
- deletion wins every publish race and removes registered temporary objects;
- raw filenames, object keys, FFmpeg stderr, media, transcript, summary, URLs,
  signed tokens, credentials, and private paths are forbidden from diagnostics
  and committed evidence.

**Scale/Scope**: MVP/internal workspaces with all existing accepted revisions,
new first-party and manual uploads, one media worker initially, automatic
per-workspace legacy backfill, browser and embedded review parity. Excludes
video playback, source editing, user track selection, manual repair controls,
new upload/finalize ownership, source-only retention policy, and changes to the
MediaScribe contract.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first and manual control**: Pass. No capture, Record/Stop, active
  indicator, one-action Stop, or native source-writer behavior is removed.
  Conversion starts only after server acceptance and cannot block local capture.
- **Accepted-source custody and data boundary**: Pass with required design.
  Normalization uses accepted server artifacts only. Desktop never contacts
  MediaScribe or stores server/dependency credentials.
- **No competing source of truth**: Pass. Existing upload/finalize,
  `MediaRevision`, and `TrackArtifact` remain authoritative. The new job records
  derived playback work and does not create another meeting/source service.
- **Resource-bounded processing**: Pass with required design. Work is isolated
  to a 1-CPU/1-GiB non-root worker with concurrency 1, bounded protocols,
  streams, disk, output, subprocess output, timeouts, retries, and batches.
- **Privacy and metadata-only evidence**: Pass. Probe output is allowlisted;
  raw tags/stderr/content/path/key/filename values never enter audit, incident,
  logs, specs, Issues, PR evidence, or screenshots.
- **Lifecycle and deletion truth**: Pass with required design. Canonical and
  temporary objects are registered, deletion wins publication races, and
  reports account for both classes without promising external erasure.
- **Tenant isolation**: Pass with required design. New tables force RLS. Global
  inventory/dispatch uses two narrow maintenance operations only for bounded
  enumeration, then returns to exact tenant worker context.
- **Truthful product states**: Pass. Playback and transcript statuses are
  independent; partial/failed objects never appear ready; terminal impossible
  inputs do not spin forever; transient failures remain automatic.
- **UX/accessibility/brand distance**: Pass. Existing GRAF status/player
  primitives and one server read model are reused. No reference-product copy,
  asset, or pixel-identical UI is introduced.
- **Spec-driven delivery**: Pass. Specify/clarify are complete. This plan
  produces research, data model, contracts, and quickstart; checklist, tasks,
  analyze, GitHub issue sync, implementation, convergence, review, validation,
  and production closeout remain mandatory.

No constitution violation is accepted or justified.

### Post-Design Constitution Re-Check

- **Research**: Pass. It resolves exact canonical profile, input matrix, stream
  selection, first-party mix, subprocess isolation, limits, timeouts, retry
  cycles, backfill batching, and publication/deletion races.
- **Data model**: Pass. One job per revision/profile, registered attempts, one
  per-workspace run, and existing `TrackArtifact` are the minimum durable truth.
  `Meeting.playback_status` is deliberately not duplicated.
- **Contracts**: Pass. They add no user/admin repair mutation, keep accepted
  source and playback objects separate, expose only safe read states, and make
  deletion/RLS/readiness requirements explicit.
- **Quickstart**: Pass. It covers real format conversion, strict reuse/remux,
  multi-stream ambiguity, dual-source fallback, retries/restarts, inventory
  ordering, deletion races, PostgreSQL uniqueness/RLS, browser seek, production
  backfill, and cleanup.

No post-design constitution violation is introduced.

## Validation Plan

Implementation validation is staged:

1. Unit tests for profile validation, BMFF bounds/order, exact source matrix,
   stream selection, dual-source mix arguments, state transitions, retry due
   times, safe audit metadata, and cabinet status composition.
2. Container capability tests for the exact pinned FFmpeg/FFprobe build,
   allowlisted demuxers/decoders, AAC-LC encoder, `ipod` muxer, `+faststart`,
   protocol restriction, real synthetic formats, full decode, output cap, and
   process-group cancellation.
3. Contract/integration tests for finalize role sets, candidate status, source
   fingerprint, post-commit dispatch, deterministic workflow identity,
   duplicate pickup/publication, transient auto-retry, restart recovery,
   inventory-before-mutation, priority, and no mutation endpoints.
4. SQLite plus disposable PostgreSQL migration, partial uniqueness, row-lock,
   RLS, maintenance-operation, downgrade, and deletion-race tests.
5. Cabinet/OpenAPI/rendering tests for independent playback/transcript states,
   localized accessible copy, no retry controls, range transport, and forbidden
   diagnostic content.
6. Existing Swift capture/upload tests prove candidate descriptors and required
   WAV/source behavior remain compatible; no app rebuild is claimed necessary
   unless implementation later changes `apps/macos`.
7. Run [quickstart.md](./quickstart.md) with synthetic fixtures and working
   copies from `test-rec`, then run `infra/scripts/ci-local.sh` after the final
   code-affecting fix.
8. After merge/release approval, deploy with backup/migration/worker health,
   prove both new-ingest and legacy backfill in production, perform Chrome and
   embedded seek/playback E2E, verify transcript/playback independence, and
   remove only feature-specific test records/objects with residue zero.

The standalone feature-097 Codex Security scan remains deferred and untouched.
Normal authorization, RLS, dependency isolation, redaction, and lifecycle
assertions are acceptance tests, not a claim that the deferred scan completed.

## Project Structure

### Documentation (this feature)

```text
specs/099-review-m4a-normalization/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── playback-normalization-contract.md
│   ├── playback-status-contract.md
│   ├── automatic-backfill-contract.md
│   └── lifecycle-operations-contract.md
├── tasks.md
└── validation/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── normalization/
│   ├── audit.py                         # strict safe event metadata
│   ├── media.py                         # bounded probe, BMFF, remux/transcode
│   ├── pickup.py                        # due jobs and inventory-first backfill
│   ├── service.py                       # job state, source, publish, cleanup
│   ├── statuses.py                      # state/reason/profile constants
│   └── worker.py                        # isolated Temporal media worker
├── workflows/
│   └── playback_normalization_workflow.py
├── db/models/
│   ├── ingest.py                        # TrackArtifact validation fields
│   └── normalization.py                 # jobs, attempts, backfill runs
├── db/migrations/versions/
│   └── 0022_playback_normalization.py
├── ingest/
│   ├── finalize.py                      # durable job in accepted transaction
│   ├── manifest.py                      # optional playback candidate role
│   ├── media_revisions.py               # source-only fingerprint
│   ├── processing_dispatch.py           # post-commit side effects
│   └── store.py                         # candidate vs canonical status
├── cabinet/
│   ├── egress.py                        # transcript-independent playback truth
│   ├── queries.py                       # job + canonical artifact reads
│   ├── view_models.py                   # safe status projection
│   └── rendering.py/templates/          # localized no-retry states
├── api/
│   ├── schemas.py                       # playback status/readiness projection
│   └── health.py                        # normalization readiness summary
├── deletion/
│   ├── service.py                       # cancel/purge/lock race handling
│   └── report.py                        # playback/temp accounting classes
├── db/
│   ├── tenant_context.py                # narrow inventory/dispatch maintenance
│   └── rls_validation.py                # new workspace tables
├── storage/
│   ├── minio_client.py                  # bounded attempt upload/stat helpers
│   └── object_keys.py                   # UUID normalization object keys
└── support/                              # metadata-only stalled-job incident reuse

apps/server/tests/
├── unit/test_playback_normalization_*.py
├── contract/test_playback_normalization_*.py
├── integration/test_playback_normalization_*.py
├── integration/test_playback_normalization_migrations.py
├── integration/test_playback_normalization_postgres.py
├── integration/test_playback_normalization_deletion.py
└── integration/test_cabinet_playback_route.py

infra/
├── server/Dockerfile                    # base/runtime/media-runtime targets
├── docker-compose.yml                   # non-root rec-media-worker + work volume
├── docker-compose.dev.yml
├── env/*.example                        # explicit normalization config
└── scripts/
    ├── ci-local.sh                      # media-container capability gate
    └── cd-remote.sh                     # worker health/backfill deploy evidence

specs/012-server-ingest-foundation/contracts/openapi.yaml
CHANGELOG.md
docs/current-product-status.md
```

**Structure Decision**: Keep the existing server/cabinet/macOS split and add one
small server domain plus one isolated worker. `TrackArtifact` remains canonical
artifact ownership; `MediaRevision` remains source lineage; the job is only
durable derived-work truth. The same server read model serves web and embedded
macOS. A separate media Docker target/task queue isolates untrusted FFmpeg work
without adding a new datastore, broker, frontend, or media platform.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md),
[contracts/playback-normalization-contract.md](./contracts/playback-normalization-contract.md),
[contracts/playback-status-contract.md](./contracts/playback-status-contract.md),
[contracts/automatic-backfill-contract.md](./contracts/automatic-backfill-contract.md),
[contracts/lifecycle-operations-contract.md](./contracts/lifecycle-operations-contract.md),
and [quickstart.md](./quickstart.md).

## Complexity Tracking

No constitution violations are introduced. The separate media worker is an
intentional isolation boundary, not a new product subsystem: it reuses the
existing image base, Temporal, PostgreSQL, MinIO, accepted-source registry,
cabinet, and deploy scripts. Keeping FFmpeg out of API/migration/MediaScribe
processes is required for CPU/disk isolation, non-root execution, and predictable
backfill; a shared worker would be simpler in file count but unsafe in runtime
behavior.
