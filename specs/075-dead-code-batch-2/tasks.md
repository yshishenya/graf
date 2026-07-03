# Tasks: Dead Code Batch 2

**Input**: Design documents from `/specs/075-dead-code-batch-2/`

**Tests**: Required. This is a small but product-sensitive macOS cleanup.

## Phase 1: Evidence

- [X] T001 Record zero-reference evidence for `statusChip` and `waitUntil` in `specs/075-dead-code-batch-2/audit-candidates.md`.

## Phase 2: Deletion

- [X] T002 [US1] Delete `statusChip` from `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` and `waitUntil` from `apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift`.
- [X] T003 [US1] Confirm `rg -n "statusChip\\(|waitUntil\\(" apps/macos apps/server/src apps/server/tests infra scripts` returns no matches.

## Phase 3: Validation

- [X] T004 [US1] Run focused Swift validation for `LivePassthroughPolicyTests` and the smallest available desktop shell compile/proof command.
- [X] T005 [US1] Run `git diff --check` and required closeout gate.

## Phase 4: Closeout

- [X] T006 [US1] Update `CHANGELOG.md`, report Swift LOC delta separately from Spec Kit/docs delta, run Ponytail review, and mark tasks after evidence.
