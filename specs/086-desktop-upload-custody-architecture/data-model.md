# Data Model: Desktop Upload Custody Architecture

086 models architecture evidence, not new runtime tables or DTOs.

## Entities

### Local Recording Package

- **Represents**: Completed local recording artifacts ready for desktop queue
  discovery.
- **Current evidence paths**:
  - `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
  - `apps/macos/Shared/Sources/Models/LocalRecordingModels.swift`
- **Key fields to preserve**: local recording identity, manifest, track
  artifact paths, duration/size/checksum metadata, completion/failure state.
- **Boundary rule**: Do not weaken local package integrity or capture completion
  truth inside an upload refactor.

### Desktop Upload Queue Item

- **Represents**: Persisted desktop upload state for one local recording.
- **Current evidence paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
  - shared model files under `apps/macos/Shared/Sources/Models/`
- **Key fields to preserve**: queue id, local package identity, upload state,
  retry state, server reconciliation state, support incident state, local purge
  state.
- **Boundary rule**: Queue persistence compatibility must be validated before
  field or type moves.

### Desktop Upload Client Contract

- **Represents**: Desktop-to-server upload/reconciliation/local-purge/support
  request behavior.
- **Current evidence path**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- **Key operations**: create meeting, create upload session, upload ranges,
  missing-range retry, finalize upload, reconcile server truth, list/ack local
  purge tasks, submit support incident.
- **Boundary rule**: DTO and endpoint behavior must stay aligned with server
  routes and tests.

### Server Ingest State

- **Represents**: Server-side meeting/upload session/media revision truth.
- **Current evidence paths**:
  - `apps/server/src/twobrain_rec_server/api/ingest.py`
  - `apps/server/src/twobrain_rec_server/ingest/`
  - `apps/server/src/twobrain_rec_server/api/schemas.py`
- **Key states**: meeting created, upload session created, parts received,
  missing ranges, finalized, processing submitted, reconciliation response.
- **Boundary rule**: Desktop refactors must not change server status vocabulary
  unless a separate contract slice approves it.

### Custody Projection

- **Represents**: User-facing and support-facing interpretation of local,
  server, processing, deletion, and support ownership.
- **Current evidence path**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- **Key outputs**: custody state, owner, retry class, normal user action,
  metadata-safety flag, upload/processing/deletion/local purge states, copy
  keys, safe reports.
- **Boundary rule**: A split must preserve copy meaning and support-safe
  metadata.

### Local Purge Task

- **Represents**: Server-created deletion lifecycle task acknowledged by the
  desktop.
- **Current evidence paths**:
  - `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
  - `apps/server/src/twobrain_rec_server/api/cabinet.py`
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- **Key fields**: task id, meeting/local recording identity, task type, state,
  verification state, safe reason code, acknowledgement URL.
- **Boundary rule**: Local purge acknowledgement must remain metadata-only and
  verified before server state is marked acknowledged.

### Support Incident Report

- **Represents**: Metadata-only support evidence for upload/custody blockers.
- **Current evidence paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`
  - `apps/server/src/twobrain_rec_server/api/support_incidents.py`
  - `apps/server/src/twobrain_rec_server/support/`
- **Key fields**: schema version, safe identifiers/fingerprints, upload/custody
  state, safe reason codes, local file completeness buckets, local purge state.
- **Boundary rule**: No raw audio, transcript text, tokens, signed URLs, or
  private local paths.

### Refactor Batch

- **Represents**: Future behavior-preserving PR proposal.
- **Fields**: id, classification, included paths, excluded behavior, expected
  diff shape, validation gates, rollback/stop condition.
- **Boundary rule**: One responsibility boundary per PR.

## Relationships

```text
Local Recording Package
  -> Desktop Upload Queue Item
  -> Desktop Upload Client Contract
  -> Server Ingest State
  -> Custody Projection
  -> Cabinet/Review visibility

Deletion request
  -> Server Local Purge Task
  -> Desktop acknowledgement
  -> Deletion report local purge state

Custody/support blocker
  -> Support Incident Report
  -> Server support incident route
  -> Operator/developer triage
```

## State Transition Notes

- Upload retry and reconciliation are separate from active capture truth.
- Local purge acknowledgement is part of deletion lifecycle, not upload success.
- Support incident state must not become a source of custody truth; it is
  evidence for troubleshooting.
- Server ingest finalization and processing readiness are related but distinct
  states.
