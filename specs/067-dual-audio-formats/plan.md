# Implementation Plan: Dual Audio Formats

**Branch**: `067-dual-audio-formats` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/067-dual-audio-formats/spec.md`

## Summary

Keep the existing dual WAV transcription contract intact and add one optional
playback/distribution artifact, `meeting-review.m4a`, for review playback and
approved audio download/export. The desktop app writes the M4A derivative from
the capture-rate writer path, validates it before upload, and uploads it as an
optional `playback` track. The server keeps MediaScribe on the separate WAV
tracks and prefers the stored M4A for playback/download egress, with the
existing mixed WAV route as a safe fallback.

## Technical Context

**Language/Version**: Swift 6 package for macOS app code; Python 3 server code.

**Primary Dependencies**: AVFoundation/Core Audio on macOS; FastAPI, SQLAlchemy,
MinIO storage adapter, existing cabinet egress code on the server.

**Storage**: Local recording package files on macOS; server `TrackArtifact`
records and MinIO object storage for uploaded tracks.

**Testing**: XCTest for macOS writer/upload behavior; pytest for server contract,
integration, and storage behavior; repository gate through
`infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk product area. The slice touches capture
artifacts, upload semantics, storage, playback egress, download/export policy,
diagnostics, and deletion/lifecycle accounting.

**Release Gate**: No production deploy in this turn. Closeout requires local
quickstart validation and `infra/scripts/ci-local.sh`; deploy remains a separate
release lane.

**Target Platform**: macOS app plus Docker-hosted 2brain Rec server.

**Project Type**: Native desktop capture/upload plus backend web/API service.

**Performance Goals**:

- Stored review M4A is at least 70% smaller than an equivalent mixed WAV in the
  validation set.
- Playback route supports byte ranges and timestamp seek with browser/macOS
  review startup within the spec target.
- Upload retry preserves active server session truth when optional playback
  appears later and does not upload unexpected local playback descriptors.

**Constraints**:

- Desktop never calls MediaScribe or stores MediaScribe credentials.
- Playback/download routes never expose storage object keys, signed URLs, or
  local file paths.
- Diagnostics and evidence stay metadata-only.
- Invalid or wrong-container local M4A derivatives fail closed and are ignored
  for upload.
- Review playback availability must not imply audio download/export permission.

**Scale/Scope**: One playback/distribution derivative per accepted recording.
No Opus/MP3 ladder, waveform generation, public links, transcript editing, echo
cancellation, or virtual-driver capture work in this slice.

## Constitution Check

**Pre-design gate**: Pass.

- Capture-first integrity: the authoritative `mic.wav` and `incoming.wav`
  transcription tracks remain unchanged.
- Visible consent/control: no change to start/stop or capture visibility.
- Data boundary/secret discipline: desktop upload remains server-owned; no new
  direct external STT egress or client-side credentials.
- Deletion truth/lifecycle accounting: the new playback artifact is modeled as a
  normal uploaded track artifact and participates in local purge and server
  storage/deletion policy.
- Spec-driven delivery: high-risk lane uses clarify, plan, checklists, tasks,
  analyze, quickstart, and repository validation.

**Post-design re-check**: Pass. The plan adds no new storage backend, no new
external dependency, and no new public sharing surface.

## Design Decisions

- Use `meeting-review.m4a` as the single playback/distribution derivative for
  this MVP slice.
- Encode M4A/AAC-LC, 48 kHz mono, 64 kbps from capture-rate samples when both
  microphone and incoming sample sources are present.
- Treat `meeting-review.m4a` as optional. Missing or invalid playback derivative
  must not block upload of the required WAV transcription pair.
- Validate local playback derivative before upload by checking file size,
  AVFoundation readability, AAC format ID, 48 kHz sample rate, mono channel
  count, and non-zero duration.
- Upload the derivative as optional `playback` transport role and include it in
  expected upload session tracks only when validated.
- Preserve active upload session truth when a refreshed package gains optional
  `playback`; the desktop client must filter upload/finalize descriptors to the
  server session's expected roles.
- Prefer stored M4A for server playback and allowed audio download/export.
  Fall back to the existing server-mixed WAV only when the stored M4A object is
  absent or unavailable and both WAV sources exist.

## Validation Plan

Focused development checks:

- `swift test --package-path apps/macos --filter SystemAudioRecordingPackageTests`
- `swift test --package-path apps/macos --filter DesktopUploadClientTests`
- `swift test --package-path apps/macos --filter DesktopUploadQueueTests`
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_playback_contract.py`
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_playback_route.py`
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_artifact_egress_policy.py`
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_minio_async_wrappers.py`

Feature quickstart:

- Run [quickstart.md](./quickstart.md) scenarios and record pass/fail evidence
  in the final response or PR.

Repository gate:

- `infra/scripts/ci-local.sh`

Deploy gate:

- None for this turn. Use `infra/scripts/cd-remote.sh --dry-run` and then
  `--execute` only in a separate release/deploy lane with user approval.

## Project Structure

### Documentation

```text
specs/067-dual-audio-formats/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── analysis.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   ├── infra.md
│   ├── security.md
│   └── ux.md
├── contracts/
│   ├── audio-artifact-contract.md
│   └── playback-egress-contract.md
└── tasks.md
```

### Source Code

```text
apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift
apps/macos/Shared/Sources/Models/AudioModels.swift
apps/macos/Shared/Tests/DesktopUploadClientTests.swift
apps/macos/Shared/Tests/DesktopUploadQueueTests.swift
apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift

apps/server/src/twobrain_rec_server/api/schemas.py
apps/server/src/twobrain_rec_server/cabinet/egress.py
apps/server/src/twobrain_rec_server/cabinet/playback_audio.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/domain/statuses.py
apps/server/src/twobrain_rec_server/storage/minio_client.py
apps/server/tests/contract/test_cabinet_playback_contract.py
apps/server/tests/integration/test_artifact_egress_policy.py
apps/server/tests/integration/test_cabinet_playback_route.py
apps/server/tests/unit/test_minio_async_wrappers.py
specs/012-server-ingest-foundation/contracts/openapi.yaml
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Reuse the existing macOS recording/upload package and
server cabinet egress surfaces. Do not add a new encoding service, background
worker, storage bucket, or external codec dependency for this slice.

## Complexity Tracking

No constitution violations require exception tracking.
