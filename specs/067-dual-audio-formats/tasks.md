# Tasks: Dual Audio Formats

**Input**: Design documents from `specs/067-dual-audio-formats/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required because the lane is high-risk product area.

## Phase 1: Spec Kit Artifacts

- [X] T001 [P] Update clarification/status in `specs/067-dual-audio-formats/spec.md`.
- [X] T002 [P] Create implementation plan in `specs/067-dual-audio-formats/plan.md`.
- [X] T003 [P] Create artifact data model in `specs/067-dual-audio-formats/data-model.md`.
- [X] T004 [P] Create upload and egress contracts in `specs/067-dual-audio-formats/contracts/audio-artifact-contract.md` and `specs/067-dual-audio-formats/contracts/playback-egress-contract.md`.
- [X] T005 [P] Create high-risk quality checklists in `specs/067-dual-audio-formats/checklists/audio-capture.md`, `specs/067-dual-audio-formats/checklists/security.md`, `specs/067-dual-audio-formats/checklists/infra.md`, and `specs/067-dual-audio-formats/checklists/ux.md`.
- [X] T006 [P] Create feature quickstart in `specs/067-dual-audio-formats/quickstart.md`.

## Phase 2: Foundational Audio Artifact Model

- [X] T007 [P] Add playback transport role and review path model in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T008 [P] Add server playback role/source-mode schema support in `apps/server/src/twobrain_rec_server/domain/statuses.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, and `specs/012-server-ingest-foundation/contracts/openapi.yaml`.

## Phase 3: User Story 1 - Preserve Two WAV Files For Transcription (P1)

**Independent Test**: `swift test --package-path apps/macos --filter SystemAudioRecordingPackageTests`

- [X] T009 [US1] Add macOS package tests for preserved WAV transcription tracks and optional M4A derivative in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`.
- [X] T010 [US1] Implement capture-rate M4A review writer without changing WAV transcription output in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.

## Phase 4: User Story 2 - Write And Upload Optimized Playback Asset (P1)

**Independent Test**: `swift test --package-path apps/macos --filter DesktopUploadClientTests` and `swift test --package-path apps/macos --filter DesktopUploadQueueTests`

- [X] T011 [US2] Add desktop upload descriptor tests for optional playback M4A in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.
- [X] T012 [US2] Add queue tests for valid M4A, invalid M4A, renamed WAV, and upload-session role changes in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`.
- [X] T013 [US2] Implement optional playback descriptor and expected upload roles in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`.
- [X] T014 [US2] Implement validated playback artifact discovery and existing upload-session preservation in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.

## Phase 5: User Story 3 - Use Playback Asset For Review, Download, And Sharing Policy (P1)

**Independent Test**: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_playback_contract.py tests/integration/test_cabinet_playback_route.py tests/integration/test_artifact_egress_policy.py`

- [X] T015 [US3] Add server contract and integration tests for stored M4A playback and audio download policy in `apps/server/tests/contract/test_cabinet_playback_contract.py`, `apps/server/tests/integration/test_cabinet_playback_route.py`, and `apps/server/tests/integration/test_artifact_egress_policy.py`.
- [X] T016 [US3] Implement stored M4A preference, WAV fallback, range response, and download/export media selection in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/playback_audio.py`.
- [X] T017 [US3] Surface `stored_review_m4a` review state in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.

## Phase 6: User Story 4 - Preserve Lifecycle, Diagnostics, And Custody Truth (P1)

**Independent Test**: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_minio_async_wrappers.py` plus quickstart evidence.

- [X] T018 [US4] Add storage missing-object tests for safe playback fallback in `apps/server/tests/unit/test_minio_async_wrappers.py`.
- [X] T019 [US4] Normalize missing MinIO object errors without hiding non-missing storage failures in `apps/server/src/twobrain_rec_server/storage/minio_client.py`.
- [X] T020 [US4] Update release notes in `CHANGELOG.md` with the playback artifact behavior and safety boundaries.

## Phase 7: Analyze And Validation

- [X] T021 Run Spec Kit prerequisite check with `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`.
- [X] T022 Record cross-artifact analyze pass in `specs/067-dual-audio-formats/analysis.md`.
- [X] T023 Run the full feature quickstart from `specs/067-dual-audio-formats/quickstart.md`.
- [X] T024 Run repository gate `infra/scripts/ci-local.sh`.

## Dependencies

- Phase 1 must complete before analyze and closeout.
- Phase 2 must complete before upload and server story tasks.
- US1 protects transcription truth and must remain green while US2 and US3 add
  playback behavior.
- US3 depends on the server recognizing the optional `playback` role.
- US4 lifecycle and diagnostics checks must pass before PR/release closeout.

## Parallel Opportunities

- T001-T006 can be reviewed in parallel after `spec.md` and `research.md` exist.
- T007 and T008 touch separate platforms and can proceed in parallel.
- Server tests in T015 and storage tests in T018 can run in parallel with macOS
  upload tests after foundational models are in place.

## Notes

- GitHub issue sync is required before PR closeout when this slice is tracked
  externally. Avoid creating duplicate issues; search by feature `067`, task ID,
  and title first.
