# Tasks: Dead Code Batch 5

**Input**: Design documents from `/specs/078-dead-code-batch-5/`

**Tests**: Required. This is a small macOS cleanup touching shared buffering,
latency, and low-resource route-truth source files.

## Phase 1: Evidence

- [X] T001 Record scanner and compile-probe evidence in `specs/078-dead-code-batch-5/audit-candidates.md`.

## Phase 2: Deletion

- [X] T002 [US1] Remove compile-proven unused `Foundation` imports from `apps/macos/Shared/Sources/Buffering/LocalBufferContracts.swift`, `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift`, and `apps/macos/Shared/Sources/Routing/LowResourceRouteTruth.swift`.

## Phase 3: Validation

- [X] T003 [US1] Run `swift build --package-path apps/macos`.
- [X] T004 [US1] Run focused Swift validation from `specs/078-dead-code-batch-5/quickstart.md`.
- [X] T005 [US1] Run `git diff --check`, Spec Kit prerequisites, and GitHub issue canon validation.
- [X] T006 [US1] Run `infra/scripts/ci-local.sh`.

## Phase 4: Closeout

- [X] T007 [US1] Update `CHANGELOG.md`, report Swift tracked LOC delta, run Ponytail review, and mark completed tasks after evidence.

## Dependencies

1. T001 before T002.
2. T002 before T003-T006.
3. T003 before T004-T006.
4. T007 after all validation tasks pass.

## Independent Test Criteria

- **US1**: The branch removes only the listed import lines, focused Swift
  validation passes, full local CI passes, and the audit artifact records every
  reviewed candidate.

## Implementation Strategy

Complete the single cleanup story in one small PR. Do not broaden the batch if
new candidates appear; record them as deferred unless they have the same
compile-proof and validation coverage.
