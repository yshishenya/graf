# Tasks: Видимый прогресс загрузки записи

**Input**: Design documents from `specs/128-upload-progress-visibility/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/native-upload-progress.md`, `quickstart.md`

**Tests**: Required before implementation because this is a high-risk native
upload/custody UX slice with accessibility and truthful-state gates.

## Phase 1: Setup

**Purpose**: Lock the existing queue/projection boundary before code changes.

- [X] T001 Confirm the no-new-storage/no-new-egress boundary and exact native row/test paths in `specs/128-upload-progress-visibility/plan.md` and `specs/128-upload-progress-visibility/contracts/native-upload-progress.md` (FR-007, FR-011).

## Phase 2: Foundational Regression Contracts

**Purpose**: Make active, finalizing, unavailable and accessible states
executable before changing the native shell.

- [X] T002 [US1] Add focused XCTest fixtures and assertions for active measured progress, 0%, partial progress, 100%-before-`uploaded`, and `uploaded` state separation in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift` (FR-001, FR-002, FR-003, FR-007, SC-001, SC-002).
- [X] T003 [US2] Add a source/accessibility contract for the existing local row's progress indicator, percentage label, missing-total fallback and absence of manual retry/stop controls in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift` (FR-004, FR-005, FR-006, FR-008, FR-009, FR-012, SC-003, SC-005).

**Checkpoint**: New tests fail only because the native local row does not yet
expose measured progress and finalization copy.

## Phase 3: User Story 1 — Понять, что запись отправляется (Priority: P1) 🎯 MVP

**Goal**: Show measured per-record upload progress in the existing local list
without changing queue or custody semantics.

**Independent Test**: Synthetic uploading rows at 0%, partial and 100%
accepted bytes show a progress bar and bounded text; `uploaded` retains the
existing ready state.

- [X] T004 [US1] Add the bounded measured-progress helper and render the existing SwiftUI local recording row's linear progress bar and percentage in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` (FR-001, FR-003, FR-010, SC-001).

**Checkpoint**: The local row explains active upload progress without opening
the inspector or making a request.

## Phase 4: User Story 2 — Сохранить спокойный и доступный custody-flow (Priority: P1)

**Goal**: Keep accessibility, localization and automatic-custody boundaries
truthful across non-active and finalizing states.

**Independent Test**: VoiceOver reads state and percentage for active upload;
queued/retrying/blocked rows have no stale progress; 100% accepted bytes do not
announce readiness before `uploaded`.

- [X] T005 [US2] Update uploading/finalization detail and combined accessibility copy in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, preserving existing queued/retrying/blocked wording and hiding progress visuals from duplicate accessibility announcements (FR-004, FR-005, FR-006, FR-008, FR-009, SC-002, SC-003).

**Checkpoint**: The visible row and assistive technology communicate the same
bounded state without adding user-operated transport controls.

## Phase 5: Polish And Cross-Cutting Validation

**Purpose**: Record the user-visible change and complete the high-risk native
validation lane.

- [X] T006 [P] Update the user-visible change and current P2 launch-gap status in `CHANGELOG.md` and `docs/current-product-status.md` without claiming production owner-journey readiness (FR-012).
- [X] T007 Run the Feature 128 quickstart focused tests, native build, `git diff --check` and metadata-only forbidden-content scan; record results in `specs/128-upload-progress-visibility/quickstart.md` and mark validated tasks `[X]` only after evidence exists (SC-001, SC-002, SC-003, SC-005).
- [X] T008 Run `infra/scripts/ci-local.sh`, record the result and documented no-deploy RLS boundary in `specs/128-upload-progress-visibility/quickstart.md`, then complete the task/evidence reconciliation (SC-004).
- [X] T009 Run Ponytail and final security/accessibility review over the complete diff, remove unjustified abstraction or duplicated policy logic, and verify all Feature 128 checklists are clean (FR-011, FR-012, SC-004, SC-005).

## Dependencies And Execution Order

- T001 precedes the implementation tasks.
- T002 and T003 must be written before T004/T005 and may not weaken existing
  custody or privacy assertions.
- T004 precedes T005 because accessibility copy depends on the final visible
  progress presentation.
- T006 may proceed in parallel with T004/T005 because it touches only release
  and product-status documentation.
- T007 and T008 run after T004/T005; T009 is the final closeout review.

## Parallel Example

```text
T002: state/projection regression tests
T003: native row/accessibility source contract tests
T006: changelog and current-product-status update
```

## Implementation Strategy

1. Lock the existing custody and accessibility boundaries in tests.
2. Ship the smallest MVP: measured per-row progress only for active upload.
3. Add finalization and accessibility copy without introducing controls or
   transport state.
4. Run focused native checks, then the canonical repository gate.

## Validation Evidence

Validation evidence (2026-07-25): focused `CaptureControlTests` passed `41/41`;
`swift build --package-path apps/macos` passed; `git diff --check` and the
metadata-only forbidden-content scan passed. `infra/scripts/ci-local.sh` passed
macOS `639/639`, server `2420 passed / 1 skipped`, strict PostgreSQL
`41 passed / 1 skipped`, lint, compile, Compose and deployment evidence scan.
The runner reported `rls_validation_result=blocked` because no live production
database was supplied; no deploy or production acceptance is claimed. Only
metadata-only results may be recorded; no audio, transcript, private meeting
content, local path, credential, signed URL or server identifier belongs here.
