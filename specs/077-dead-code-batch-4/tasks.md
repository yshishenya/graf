# Tasks: Dead Code Batch 4

**Input**: Design documents from `/specs/077-dead-code-batch-4/`

**Tests**: Required. This is a small macOS cleanup touching audio, capture, and
shared model source files.

## Phase 1: Evidence

- [X] T001 Record scanner and compile-probe evidence in `specs/077-dead-code-batch-4/audit-candidates.md`.

## Phase 2: Deletion

- [X] T002 [US1] Remove compile-proven unused `Foundation` imports from `apps/macos/RecApp/Sources/AudioHealth/BluetoothRoutePolicy.swift`, `apps/macos/RecApp/Sources/AudioSetup/GuidedDeviceManagementService.swift`, `apps/macos/RecApp/Sources/AudioSetup/PhysicalDeviceSelectionViewModel.swift`, `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`, `apps/macos/RecApp/Sources/Capture/RecordingRouteMetadataService.swift`, `apps/macos/Shared/Sources/Models/AudioStates.swift`, `apps/macos/Shared/Sources/Models/RecordingTimelineEvidence.swift`, and `apps/macos/Shared/Sources/Routing/LiveRouteClientActivity.swift`.

## Phase 3: Validation

- [X] T003 [US1] Run `swift build --package-path apps/macos`.
- [X] T004 [US1] Run focused Swift validation from `specs/077-dead-code-batch-4/quickstart.md`.
- [X] T005 [US1] Run `git diff --check`, Spec Kit prerequisites, and GitHub issue canon validation.
- [X] T006 [US1] Run `infra/scripts/ci-local.sh`.

## Phase 4: Closeout

- [X] T007 [US1] Update `CHANGELOG.md`, report Swift tracked LOC delta, run Ponytail review, and mark completed tasks after evidence.
