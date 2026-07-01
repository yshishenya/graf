# Tasks: Dead Code Batch 3

**Input**: Design documents from `/specs/076-dead-code-batch-3/`

**Tests**: Required. This is a small macOS cleanup touching capture/audio UI
source files.

## Phase 1: Evidence

- [X] T001 Record scanner and compile-probe evidence in `specs/076-dead-code-batch-3/audit-candidates.md`.

## Phase 2: Deletion

- [X] T002 [US1] Remove unused imports from `apps/macos/RecApp/Sources/AudioHealth/BluetoothRouteMonitor.swift`, `apps/macos/RecApp/Sources/AudioSetup/VolumeMuteMapper.swift`, and `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.

## Phase 3: Validation

- [X] T003 [US1] Run `swift build --package-path apps/macos`.
- [X] T004 [US1] Run focused Swift validation from `specs/076-dead-code-batch-3/quickstart.md`.
- [X] T005 [US1] Run `git diff --check` and `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`.
- [X] T006 [US1] Run `infra/scripts/ci-local.sh`.

## Phase 4: Closeout

- [X] T007 [US1] Update `CHANGELOG.md`, report Swift tracked LOC delta, run Ponytail review, and mark completed tasks after evidence.
