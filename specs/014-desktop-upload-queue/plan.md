# Implementation Plan: Desktop Upload Queue And Resilient Upload Behavior

**Branch**: `014-desktop-upload-queue` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-desktop-upload-queue/spec.md`

## Summary

Add a durable macOS desktop upload queue for finalized local recording packages.
The app scans completed local recordings at launch, queues uploadable packages,
persists queue state across restarts, maps local dual-track artifacts into the
server-mediated `012` ingest API, retries transient failures safely, and shows
truthful upload state in the existing native recording control surface.

The first implementation keeps owner-controlled boundaries strict: desktop
uploads only to the configured 2brain Rec server, never directly to MediaScribe
or object storage, and local artifacts are retained while upload truth is
pending, retrying, degraded, or blocked.

## Technical Context

**Language/Version**: Swift 6.0 SwiftPM package, macOS 14+ native SwiftUI/AppKit app.

**Primary Dependencies**: Foundation, SwiftUI, CryptoKit, existing
`TwoBrainRecShared`, `TwoBrainRecAppCore`, local recording manifest services,
diagnostic redaction services, and `012-server-ingest-foundation` OpenAPI
contract.

**Storage**: Local JSON queue state under the existing app support area
alongside local recordings. No new database, MinIO, MediaScribe, Langfuse, or
Temporal dependency is introduced on the desktop.

**Testing**: SwiftPM tests under `apps/macos/Shared/Tests`, contract validation
through `swift run ContractValidation`, and metadata-only quickstart scenarios.

**Target Platform**: macOS 14+ on Apple Silicon for MVP desktop validation.

**Project Type**: Native macOS desktop app with shared Swift models and app-core
services.

**Performance Goals**:

- Queue scan and visible queue truth update complete within 30 seconds of app
  launch or recording finalization.
- Transient network failures become retryable queue states without blocking
  capture start/stop UI.
- Upload progress is derived from accepted bytes or local part evidence, never
  from optimistic finalization.

**Constraints**:

- Desktop uploader uses only `012` server-mediated endpoints.
- Desktop never stores MediaScribe credentials, MinIO credentials, signed URLs,
  upload tokens, or direct third-party upload URLs.
- Queue work must not alter active recording indicator, one-action Stop, or
  system-audio capture behavior.
- Local recording artifacts must not be purged while upload truth is non-terminal.
- Diagnostics are metadata-only and must redact credentials, tokens, signed
  URLs, raw audio, transcripts, and meeting content.

**Scale/Scope**: Single-user local MVP desktop queue for completed local
recording packages. Server-side workflow processing, transcript UI, dashboard,
sharing, and deletion propagation remain outside this slice.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. Queue work starts after local recording
  finalization and does not change capture start/stop behavior, active
  indicator, Screen/System Audio capture, microphone capture, driver routing, or
  future advanced routing boundaries.
- **Visible consent and user control**: PASS. Manual recording controls remain
  intact. Upload status is visible after recording and never hides active capture
  state or one-action Stop.
- **Data boundary and secret discipline**: PASS. The desktop uploader uses only
  the configured owner-controlled server ingest API and explicitly excludes
  MediaScribe, object-storage credentials, signed URLs, direct third-party
  upload, and credential logging.
- **Deletion truth and lifecycle accounting**: PASS. Queue states preserve local
  artifacts while truth is unknown and produce metadata that can participate in
  retention/deletion accounting without promising external erasure.
- **Spec-driven delivery with testable gates**: PASS. Clarifications, plan,
  research, data model, contracts, quickstart, checklists, tasks, and analyze
  artifacts are defined before implementation.

## Project Structure

### Documentation (this feature)

```text
specs/014-desktop-upload-queue/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── desktop-upload-queue-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── ux.md
│   └── infra.md
├── evidence/
│   └── test-results.md
├── analysis.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── Capture/CaptureControlView.swift
│       └── Upload/
│           ├── DesktopUploadQueueService.swift
│           └── DesktopUploadClient.swift
├── Shared/
│   ├── Sources/
│   │   ├── Models/
│   │   │   ├── AudioModels.swift
│   │   │   └── AudioStates.swift
│   │   ├── Audit/AuditEvents.swift
│   │   └── Diagnostics/DiagnosticRedactor.swift
│   └── Tests/
│       ├── DesktopUploadQueueTests.swift
│       ├── DesktopUploadClientTests.swift
│       ├── CaptureControlTests.swift
│       └── DiagnosticRedactionTests.swift
└── Scripts/
    └── validate-desktop-upload-queue.sh
```

**Structure Decision**: Put durable queue orchestration and HTTP client code in
`TwoBrainRecAppCore` under `RecApp/Sources/Upload`, keep serializable upload
truth models in `TwoBrainRecShared`, extend the existing capture UI instead of
adding a separate window, and validate through SwiftPM tests plus one
metadata-only shell script.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Use a file-backed JSON queue state and deterministic package identity.
- Use `012` server-mediated ingest endpoints with idempotency keys.
- Map local `local_mic`/`remote_speaker`/manifest files to backend
  `microphone`/`system`/`manifest` tracks.
- Use bounded exponential retry capped by local buffer retention deadline.
- Keep UI compact and status-first inside the existing native recording control.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/desktop-upload-queue-contract.md](./contracts/desktop-upload-queue-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Design hooks after finalization and app
  launch; recording lifecycle behavior remains unchanged except queue enqueue
  after local manifest creation.
- **Visible consent and user control**: PASS. Queue UI coexists with active
  capture status and provides one visible next action for retry/stop/manual
  recovery.
- **Data boundary and secret discipline**: PASS. Contracts forbid direct STT,
  signed URL, object-storage, token, and credential exposure from desktop.
- **Deletion truth and lifecycle accounting**: PASS. State model distinguishes
  non-terminal, manual-only, terminal uploaded, terminal failed, and
  terminal-deleted truth with retention decision evidence.
- **Spec-driven delivery with testable gates**: PASS. All design artifacts are
  present, checklist gates are complete, and analyze has no blocking findings.
