# Implementation Plan: Transcription Results Pipeline

**Branch**: `045-transcription-results-pipeline` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`specs/045-transcription-results-pipeline/spec.md`

## Summary

Finish the user-facing transcription loop after upload acceptance. This slice
keeps the server upload integrity gate, removes local audio-quality and
leakage-readiness as upload/transcription blockers for structurally valid
recordings, starts or reuses server-owned processing automatically when
processing is enabled, and verifies that web and desktop review show the same
processing and transcript result truth.

Feature `044` remains the AEC/noise-suppression evidence track. Feature `045`
does not require AEC to be product-ready before transcription can run.

## Technical Context

**Language/Version**: Swift 6 for macOS app and shared models; Python 3.13 for
server runtime and tests.

**Primary Dependencies**: macOS local recording package and upload queue,
FastAPI, SQLAlchemy async, Alembic, MinIO storage, Temporal processing
workflows, MediaScribe server integration, server-rendered web cabinet, WebKit
desktop cabinet embedding.

**Storage**: Local app support recording packages and desktop upload queue JSON;
Postgres for meetings, media revisions, upload sessions, track artifacts,
processing workflows/jobs/results, transcripts, diarization, audit, and deletion
lifecycle; MinIO for server-mediated artifacts.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`;
`cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q`; focused
contract and integration tests for upload eligibility, finalize integrity,
processing pickup, MediaScribe import, cabinet review, and content-safe status
payloads.

**Target Platform**: macOS MVP desktop app plus Linux/Docker server runtime on
the existing 2brain Rec infrastructure.

**Project Type**: Native macOS desktop app plus FastAPI backend plus
server-owned web review UI.

**Performance Goals**:

- Accepted online uploads reach a visible processing state within 60 seconds
  when processing is enabled and dependencies are healthy.
- Product-owned orchestration before MediaScribe submission and after result
  availability completes in under 3 minutes for a one-hour benchmark recording.
- Retry and duplicate pickup paths create 0 duplicate processing jobs and 0
  duplicate imported transcript result sets per accepted media revision.

**Constraints**:

- Desktop never sends audio directly to MediaScribe and never stores
  MediaScribe credentials.
- Server finalization must keep required-file, role, size, checksum, consent,
  permission, access, and deletion gates.
- Local audio quality, leakage, echo, silence, duration-difference, and
  transcription-readiness observations are diagnostic signals for this slice,
  not upload/transcription blockers when package files are structurally valid.
- No raw audio, transcript text, signed URLs, credentials, private local paths,
  or meeting content may appear in logs, diagnostics, screenshots, or Spec Kit
  evidence.
- Existing offline upload and delayed retry behavior must keep one meeting and
  one accepted initial media revision.

**Scale/Scope**: One MVP owner/workspace flow, large recordings split into
bounded parts, reconnect/retry across app restart, one accepted initial media
revision per logical meeting, and existing review surfaces. Local media
trimming, transcript editing, replace/reprocess, video review, and local
two-speaker microphone optimization remain out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Uses accepted recording packages and does not alter live capture, permissions, or routing. |
| Visible consent and one-action stop | PASS | Does not change recording controls; consent and permission truth remain hard gates. |
| Data boundary and secret discipline | PASS | Desktop talks only to 2brain Rec server; server owns MinIO, Temporal, MediaScribe, and secrets. |
| Deletion truth and lifecycle accounting | PASS | Processing and review remain bound to meeting/media revision lifecycle and access state. |
| Spec-driven delivery | PASS | This plan creates research, data model, contracts, and quickstart before tasks/implementation. |
| Metadata-only diagnostics/evidence | PASS | Validation artifacts are required to exclude raw audio, transcript text, credentials, signed URLs, and private paths. |

No constitution violation is required.

## Project Structure

### Documentation (this feature)

```text
specs/045-transcription-results-pipeline/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- checklists/
|   |-- pipeline.md
|   `-- requirements.md
|-- contracts/
|   |-- processing-result-delivery-contract.md
|   `-- upload-transcription-eligibility-contract.md
|-- evidence/
|   `-- validation-log.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/macos/
|-- RecApp/Sources/Upload/
|   |-- DesktopUploadClient.swift
|   `-- DesktopUploadQueueService.swift
|-- RecApp/Sources/Cabinet/
|   |-- DesktopCabinetConfiguration.swift
|   `-- DesktopMeetingShellView.swift
|-- Shared/Sources/Models/
|   `-- AudioModels.swift
`-- Shared/Tests/
    |-- DesktopUploadQueueTests.swift
    |-- LocalRecordingLeakageFinalizationTests.swift
    |-- LocalRecordingManifestTests.swift
    `-- DesktopCabinetUploadLinkTests.swift

apps/server/
|-- src/twobrain_rec_server/api/
|   |-- ingest.py
|   |-- processing.py
|   |-- cabinet.py
|   `-- schemas.py
|-- src/twobrain_rec_server/ingest/
|   |-- finalize.py
|   `-- manifest.py
|-- src/twobrain_rec_server/processing/
|   |-- pickup.py
|   |-- store.py
|   `-- submit.py
|-- src/twobrain_rec_server/workflows/
|   |-- processing_workflow.py
|   |-- temporal_client.py
|   `-- worker.py
|-- src/twobrain_rec_server/cabinet/
|   |-- queries.py
|   `-- view_models.py
`-- tests/
    |-- contract/
    |-- integration/
    `-- unit/

infra/
`-- scripts/
    |-- ci-local.sh
    `-- cd-remote.sh
```

**Structure Decision**: Use the existing desktop/server split from `042`. Do
not add a new processing service, desktop provider credential path, or direct
object-storage upload path. This slice narrows the local upload eligibility
gate and closes the server pickup/result-delivery loop.

## Complexity Tracking

No constitution violations are required.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

1. Keep server package integrity as the hard pre-processing gate.
2. Demote local leakage, echo, silence, timeline, and transcription-readiness
   signals to diagnostics for upload/transcription eligibility.
3. Use server auto-pickup after successful finalization when processing is
   enabled, with visible blocked/retryable state when dependencies are absent.
4. Preserve deterministic processing identity per accepted media revision.
5. Reuse existing web and desktop review contracts for result delivery rather
   than adding a separate result surface.

## Phase 1 Design Decisions

Design artifacts:

- [data-model.md](./data-model.md): recording package, eligibility decision,
  accepted media revision, processing attempt, transcript result, review
  surface, and state transitions.
- [contracts/upload-transcription-eligibility-contract.md](./contracts/upload-transcription-eligibility-contract.md):
  local and server gate boundary.
- [contracts/processing-result-delivery-contract.md](./contracts/processing-result-delivery-contract.md):
  processing pickup, status, import, and review-result contract.
- [quickstart.md](./quickstart.md): focused validation commands and expected
  outcomes.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | No live capture behavior changes; structurally valid recorded packages are processed for best available transcript. |
| Visible consent and one-action stop | PASS | Consent and permission gates remain hard blockers; no hidden capture behavior is introduced. |
| Data boundary and secret discipline | PASS | Desktop egress remains server-only; status/evidence contracts are content-safe. |
| Deletion truth and lifecycle accounting | PASS | Processing respects meeting access/deletion state and keeps upload success separate from transcription state. |
| Spec-driven delivery | PASS | Design artifacts map to testable tasks and no unresolved critical decisions remain. |
| Metadata-only diagnostics/evidence | PASS | Quickstart requires content-safe evidence checks and forbids private audio/transcript content in committed artifacts. |
