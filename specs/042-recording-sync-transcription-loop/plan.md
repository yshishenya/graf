# Implementation Plan: Recording Sync And Transcription Loop

**Branch**: `042-recording-sync-transcription-loop` | **Date**: 2026-06-18 |
**Spec**: `specs/042-recording-sync-transcription-loop/spec.md`

**Input**: Feature specification from
`specs/042-recording-sync-transcription-loop/spec.md`

## Summary

Deliver one proven MVP loop from macOS recording through offline-safe upload,
server acceptance, MediaScribe processing, and transcript display in both the
web cabinet and embedded desktop cabinet. The implementation will build on the
existing macOS local recording package, desktop upload queue, server-mediated
ingest, Temporal processing pipeline, and cabinet review surfaces. The main new
architecture choice is to introduce an explicit initial `MediaRevision` identity
now, while keeping editing, trimming, video capture, replace, restore, and
transcript editing out of the `042` MVP.

## Technical Context

**Language/Version**: Swift 6 / macOS 14+ for desktop app; Python 3.13 for
server; SQLAlchemy/Alembic for schema; HTML/CSS server-rendered cabinet routes.

**Primary Dependencies**: Swift Foundation, URLSession, CryptoKit,
ScreenCaptureKit/AVFoundation-adjacent existing recording code, FastAPI,
SQLAlchemy async, Alembic, MinIO client, Temporal SDK, MediaScribe integration,
WebKit desktop embedding.

**Storage**: Local app support recording packages and `desktop-upload-queue.v2`
JSON on macOS; Postgres for meetings, media revisions, upload sessions,
processing jobs/results, transcripts, audit, deletion/lifecycle metadata; MinIO
for server-mediated artifacts.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`;
`cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q`; focused server
contract/integration tests for ingest, processing, and cabinet; metadata-only
quickstart evidence.

**Target Platform**: macOS MVP desktop app plus Linux/Docker server runtime on
`2brain.dev` infrastructure.

**Project Type**: Native desktop app plus FastAPI backend plus server-owned web
review UI.

**Performance Goals**:

- Recording must complete locally without network dependency.
- Upload must resume by server-accepted byte truth and avoid full re-upload
  when accepted ranges are known.
- Processing pickup must start or reuse exactly one workflow for the accepted
  initial media revision.
- Web and embedded desktop review should show the same processing/transcript
  state for the same meeting and media revision.

**Constraints**:

- No direct desktop egress to MediaScribe or MinIO credentials.
- No raw audio, transcript text, signed URLs, credentials, private local paths,
  or meeting content in logs, diagnostics, screenshots, or Spec Kit evidence.
- Accepted media is immutable. Future edits create new media revisions.
- Server truth wins for upload offsets, accepted ranges, processing state,
  deletion/access state, and review availability.
- `042` must not implement local trim/edit UI, online transcript editing,
  speaker-label editing, video runtime capture, replace, restore, or reprocess.

**Scale/Scope**: One user/workspace MVP path, large meeting recordings split into
bounded parts, reconnect/retry across app restart, one accepted initial media
revision per logical meeting in `042`, future multiple revisions supported by
schema and contracts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Uses accepted local recording packages. Does not alter live capture or revive virtual-driver routing. |
| Visible consent and one-action stop | PASS | Recording controls remain native; upload/processing never implies hidden capture. |
| Data boundary and secret discipline | PASS | Desktop calls only 2brain Rec API; server owns MinIO, Temporal, MediaScribe, and secrets. |
| Deletion truth and lifecycle accounting | PASS | Media revisions, upload sessions, processing results, local buffers, MediaScribe state, and transcript state are lifecycle-addressable. |
| Spec-driven delivery | PASS | Feature has spec/clarification; this plan creates research, data model, contracts, quickstart before tasks/analysis/implementation. |
| macOS-native capture-critical implementation | PASS | Desktop work stays in Swift native app surfaces and existing WebKit cabinet embedding. |
| Metadata-only diagnostics/evidence | PASS | Quickstart and contracts require no private content in evidence. |

No constitution violation is required.

## Project Structure

### Documentation (this feature)

```text
specs/042-recording-sync-transcription-loop/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-sync-contract.md
│   ├── media-revision-contract.md
│   └── review-surface-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/Sources/Capture/
│   ├── LocalRecordingManifestService.swift
│   └── LocalRecordingWriter.swift
├── RecApp/Sources/Upload/
│   ├── DesktopUploadClient.swift
│   └── DesktopUploadQueueService.swift
├── RecApp/Sources/Cabinet/
│   ├── DesktopCabinetConfiguration.swift
│   └── DesktopMeetingShellView.swift
├── Shared/Sources/Models/
│   └── AudioModels.swift
└── Shared/Tests/
    ├── DesktopUploadQueueTests.swift
    ├── LocalRecordingManifestTests.swift
    └── CaptureControlTests.swift

apps/server/
├── src/twobrain_rec_server/api/
│   ├── ingest.py
│   ├── processing.py
│   ├── cabinet.py
│   └── schemas.py
├── src/twobrain_rec_server/db/
│   ├── migrations/versions/
│   └── models/
├── src/twobrain_rec_server/ingest/
├── src/twobrain_rec_server/processing/
├── src/twobrain_rec_server/cabinet/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

infra/
├── docker-compose.yml
└── scripts/ci-local.sh
```

**Structure Decision**: Use the existing desktop/server split. Do not introduce
a separate sync service or direct object-upload service in `042`; extend the
current server-mediated ingest and processing contracts.

## Phase 0 Research Decisions

Research output is captured in `research.md`. Key decisions:

1. Keep server-mediated resumable upload, but formalize server-authoritative
   offset/range/checksum behavior instead of adopting a full tus server now.
2. Use a durable local queue schema upgrade (`desktop-upload-queue.v2`) with
   stable `local_recording_id` and `local_media_revision_id`.
3. Add server `media_revisions` as the revision-ready identity boundary; bind
   upload sessions, track artifacts, processing workflows, MediaScribe jobs,
   results, transcript segments through the accepted initial revision.
4. Keep processing idempotency through deterministic workflow identity that
   includes `media_revision_id`.
5. Display the latest accepted initial media revision in existing web and
   embedded desktop cabinet routes; do not add edit/video UI in this feature.

## Phase 1 Design Decisions

Design artifacts:

- `data-model.md`: logical meeting, capture package, media revision, upload
  queue item, upload session, track artifact, processing job/result, transcript
  result, sync conflict state, lifecycle accounting.
- `contracts/desktop-sync-contract.md`: local queue and desktop/server sync API
  semantics.
- `contracts/media-revision-contract.md`: immutability, revision identity,
  state transitions, and future extension rules.
- `contracts/review-surface-contract.md`: web/desktop review state and content
  boundary.
- `quickstart.md`: end-to-end validation scenarios and runnable commands.

## Implementation Approach

1. **Desktop identity and queue**
   - Upgrade `DesktopUploadQueueDocument` to v2 with `localMediaRevisionId`,
     `mediaRevisionId`, `syncGeneration`, and explicit `syncConflictState`.
   - Derive `localMediaRevisionId` deterministically from the local recording
     package and initial media revision, not from retry attempts.
   - Preserve migration from existing v1 queue files.

2. **Upload reconciliation**
   - Extend the desktop client to reconcile from server truth before each
     upload attempt by local recording/revision identity.
   - Treat server accepted bytes/ranges as authoritative.
   - Keep checksums on every accepted part and block mismatched package truth.

3. **Server media revision model**
   - Add `media_revisions` and bind upload sessions, manifest snapshots,
     track artifacts, processing workflows, MediaScribe jobs, processing
     results, and lifecycle accounting to the initial accepted revision.
   - Backfill existing rows as revision `1` where migration data exists.
   - Add tenant isolation/RLS classification and tests for every new
     media-revision-owned table before implementation closure.
   - Preserve one logical `meetings` row for the real meeting.

4. **Processing and transcript**
   - Start or reuse one processing workflow per accepted media revision.
   - Store/import transcript and diarization results against the revision-bound
     processing result.
   - Keep existing cabinet rendering, but expose revision/provenance in API
     response and desktop state.

5. **Web and embedded desktop display**
   - Ensure `/meetings` and `/desktop/meetings` list/detail show upload,
     processing, ready, blocked, failed, and conflict states consistently.
   - Native desktop controls remain outside embedded web content.
   - Add accessibility, localization-safe Russian copy, and compact-width
     requirements for queue rows, retry controls, review links, processing
     states, transcript sections, and conflict notices.

6. **Privacy, lifecycle, and evidence**
   - Add tests and quickstart evidence that prove no raw content or secrets are
     emitted to diagnostics/logs/spec evidence.
   - Include local buffer, server artifact, MediaScribe, Temporal, transcript,
     diagnostics, and future deletion participation in lifecycle truth.
   - Cover local disk-full writes, object-store write failures, DB transaction
     failures, workflow start failures, MediaScribe failures, cabinet timeouts,
     temporary upload cleanup, and aborted/expired upload sessions as explicit
     states.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Design starts after accepted local recording package; no capture-path change. |
| Visible consent and one-action stop | PASS | Recording UX is unchanged; upload/status UI cannot start hidden capture. |
| Data boundary and secret discipline | PASS | Contracts keep desktop on 2brain Rec API only and keep content out of logs/evidence. |
| Deletion truth and lifecycle accounting | PASS | `MediaRevision` becomes the lifecycle unit for artifacts and processing results under one meeting. |
| Spec-driven delivery | PASS | Artifacts exist and enable checklist, tasks, analyze, and implementation gates. |

## Complexity Tracking

No constitution violations. The `MediaRevision` abstraction is added because
the already accepted meeting-only unique constraints would otherwise force
duplicate meetings or destructive mutation for future trim/video/reprocess
features.
