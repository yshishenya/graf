# Tasks: Восстановление автозаписи встреч

**Input**: Design documents from `specs/124-restore-automatic-recording/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/recording-workflow.md`, `quickstart.md`

**Risk / Validation Lane**: High-risk feature. Tests and contract checks precede
the related runtime restoration; full local CI is required before closeout.

## Phase 1: Setup

**Purpose**: Keep the active Spec Kit anchor and current safety guidance aligned.

- [X] T001 Update the active plan pointer in `AGENTS.md` to
  `specs/124-restore-automatic-recording/plan.md` and confirm the source paths
  in `specs/124-restore-automatic-recording/plan.md` before implementation.

## Phase 2: User Story 1 — Автоматически писать выбранные приложения (P1)

**Goal**: Restore exact-target policy and detector eligibility for saved
auto-record permissions without weakening capture gates.

**Independent Test**: `MeetingDetectionPolicyTests` proves opt-in returns
`autoRecord`, unchecked target returns `prompt`, and every blocked/unknown mode
does not return `autoRecord`; detector tests prove one eligible output per
stable target episode.

### Tests for User Story 1 (write first)

- [X] T002 [US1] Restore positive exact-target auto-record, unchecked-target,
  detect-only and blocked-prerequisite assertions in
  `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T003 [US1] Add detector assertions for `autoRecordEligible`, one
  emission per stable target episode, and preservation of unknown/browser/
  suppressed behavior in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.

### Implementation for User Story 1

- [X] T004 [US1] Restore `MeetingDetectionPolicyAction.autoRecord(targetID:)`
  and exact target-permission branching after existing prerequisite checks in
  `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift`.
- [X] T005 [US1] Restore `autoRecordEligible(targetID:bundleID:)` output,
  policy mapping and emitted-bundle handling in
  `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`.

**Checkpoint**: A saved permission starts only the exact verified target and
all existing capture/policy gates still block unsafe starts.

## Phase 3: User Story 2 — Видимый prompt с таймером и opt-in (P1)

**Goal**: Restore the old visible floating prompt, eight-second countdown,
automatic expiry start and «Всегда писать это приложение» persistence.

**Independent Test**: Source-contract tests find the floating `NSPanel`,
`TimelineView`, `countdownSeconds = 8`, cancellable `autoStartTask`, opt-in
checkbox and legacy labels; manual Start, dismiss and expiry remain single-
resolution paths.

### Tests for User Story 2 (write first)

- [X] T006 [P] [US2] Replace no-countdown/no-autostart assertions with positive
  timer, opt-in checkbox, automatic-start, persistence and legacy-copy
  assertions in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.

### Implementation for User Story 2

- [X] T007 [US2] Restore `autoRecordOptIn` handling, settings persistence,
  `autoRecordEligible` start routing and target-specific status in
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`, preserving current bounded
  logging, permissions, visibility and end-stop fixes.
- [X] T008 [US2] Restore the eight-second `TimelineView` countdown, cancellable
  `autoStartTask`, checkbox and legacy «Записать сейчас»/«Пропустить» copy in
  `MeetingDetectionPromptView` within
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`.

**Checkpoint**: A prompt is visible, timer-driven and reversible; expiry and
manual Start use the same safe detector-assisted capture path.

## Phase 4: User Story 3 — Полный список приложений в настройках (P1)

**Goal**: Restore the common verified native target list and reversible
per-target controls.

**Independent Test**: Settings source-contract tests require registry loading,
verified native filtering, `ForEach`, per-target binding, «Выбрать все»,
«Снять все» and registry/settings change notifications.

### Tests for User Story 3 (write first)

- [X] T009 [P] [US3] Replace absence assertions with positive accessibility and
  settings-list requirements in
  `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` and
  `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.

### Implementation for User Story 3

- [X] T010 [US3] Restore registry-backed target rows, exact-target bindings,
  select-all/clear-all actions, loading/error state and registry notifications
  in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.

**Checkpoint**: Every verified macOS native prompt-capable registry target is
visible and configurable without adding unknown or cross-platform targets.

## Phase 5: User Story 4 — Safety gates и один видимый Stop (P1)

**Goal**: Demonstrate that restoration does not create hidden capture,
arbitrary-audio starts or duplicate sessions.

**Independent Test**: Policy, detector and source-contract tests remain green
for unknown/suppressed/blocked/active-session cases and preserve local visible
Stop plus target-ended cleanup.

- [X] T011 [P] [US4] Add/retain regression assertions for unknown targets,
  diagnostic/browser suppression, permission/storage/policy/readiness blockers,
  duplicate active sessions, visible indicator and one-action Stop in
  `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` and
  `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.
- [X] T012 [US4] Preserve and, where needed, restore explicit event handling in
  `apps/macos/RecApp/App/TwoBrainRecApp.swift` so automatic and timer starts
  use `startManualRecording(meetingDetectionTarget:)`, while
  `stopMeetingDetectionRecordingIfNeeded(bundleID:)`, capture visibility and
  prerequisite gates remain unchanged.

**Checkpoint**: Safety/privacy contract is preserved independently of the
restored automatic path.

## Phase 6: User Story 5 — Документы и регрессионная защита (P2)

**Goal**: Make Feature 124 the durable source of truth and remove active
contradictions that could lead to another accidental deletion.

**Independent Test**: Documentation search finds one active policy for timer,
auto-start, checkbox and target list; historical Feature 121 removal notes link
to the superseding Feature 124 contract.

- [X] T013 [P] [US5] Update the current product baseline and capture gates in
  `docs/current-product-status.md`, `docs/prd-voice-layer-final.md` and
  `docs/agent-guidance/product-gates.md` to describe the restored,
  policy-gated target-scoped workflow.
- [X] T014 [P] [US5] Annotate the superseded no-countdown/no-autostart wording
  and preserve historical truth in `specs/121-recording-workflows/spec.md`,
  `specs/121-recording-workflows/ux-ia.md`,
  `specs/121-recording-workflows/tasks.md`,
  `specs/121-recording-workflows/quickstart.md`, and align Feature 092/119
  cross-references with Feature 124.
- [X] T015 [P] [US5] Add the Russian user-facing restoration note to the
  `[Unreleased]` section of `CHANGELOG.md`, including safety gates, validation
  scope and no-deploy status.
- [X] T016 [US5] Reconcile `.specify/memory/constitution.md`,
  `specs/124-restore-automatic-recording/spec.md`,
  `plan.md`, `data-model.md`, `contracts/recording-workflow.md`,
  `quickstart.md` and checklists mutually consistent; no active document may
  instruct a cleanup to remove the restored contract.

**Checkpoint**: Code, requirements, governance and current status point to the
same automatic-recording contract.

## Phase 7: Polish And Validation

- [X] T017 Run the Feature 124 focused policy, capture, accessibility and
  `ContractValidation` checks from `specs/124-restore-automatic-recording/quickstart.md`.
- [X] T018 Run `infra/scripts/ci-local.sh` and record metadata-only evidence for
  the high-risk capture/UX lane in
  `specs/124-restore-automatic-recording/quickstart.md` and
  `docs/current-product-status.md`.
- [X] T019 Run the Ponytail review on the final diff covering
  `apps/macos/Shared/Sources/MeetingDetection/`,
  `apps/macos/RecApp/Sources/MeetingDetection/` and
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`; remove unnecessary new
  code/dependencies without weakening the restored contract or safety gates.

## Phase 8: Post-review Corrections And Closeout

**Purpose**: Close the runtime gaps found by the independent review before the
restored capture workflow is called ready.

- [X] T020 [US2] Add regression assertions for cancelled prompt countdowns,
  external prompt disappearance and one recording trigger per detector-output
  batch in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.
- [X] T021 [US2] Make `MeetingDetectionPromptView` return from a cancelled
  `Task.sleep` and re-check cancellation on the main actor before calling
  `resolveStart()` in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T022 [US4] Coalesce prompt/auto-record outputs while a prompt or another
  recording trigger is active so repeated or concurrent detector events cannot
  replace a prompt or create a second trigger in
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T023 [P] [US5] Record the post-review decisions and validation scenarios,
  including the native-only boundary for Feature 124 and the separate browser
  detection path, in `specs/124-restore-automatic-recording/`,
  `docs/spec-kit-feature-index.md` and `CHANGELOG.md`.
- [X] T024 [US5] Record the post-fix metadata-only validation evidence and
  closeout status in `specs/124-restore-automatic-recording/quickstart.md`,
  `docs/current-product-status.md`, `CHANGELOG.md` and the feature index.
- [X] T025 Run the focused regression checks, full local CI, issue-canon
  validation and an independent second code/documentation review; mark this
  task complete only when no blocking finding remains.

## Dependencies And Execution Order

### Phase Dependencies

- Phase 1 is a documentation/setup anchor and must complete first.
- Phase 2 tests (T002–T003) precede policy/detector implementation (T004–T005).
- Phase 3 tests (T006) precede prompt implementation (T007–T008).
- Phase 4 tests (T009) precede settings implementation (T010).
- Phase 5 safety review depends on the restored runtime paths from Phases 2–4.
- Phase 6 documentation can be edited in parallel after the contract is fixed,
  but must be complete before final validation.
- Phase 7 depends on all code and documentation phases.
- Phase 8 starts only after the independent review has identified the gaps and
  depends on the restored runtime and contract documentation from Phases 1–7.

### User Story Dependencies

- US1 has no dependency on other user stories beyond the existing registry and
  prerequisite gates.
- US2 depends on US1's `autoRecord` action and detector output.
- US3 can proceed in parallel with US1/US2 after the registry/store contract is
  confirmed, but its final test must match the policy target IDs.
- US4 depends on US1–US3 and validates their common safety boundary.
- US5 depends on the final restored behavior and owns the durable documentation.

### Parallel Opportunities

- T002/T003 touch the same test module and remain serial.
- T006 and T009 are independent test-surface edits and can run in parallel.
- T013, T014 and T015 touch different documentation groups and can run in
  parallel after the implementation contract is settled.
- T017 and markdown consistency checks can run in parallel before CI.
- T020 must precede T021/T022; T023 can run in parallel with the runtime fixes
  after the scope decision is recorded; T024 records evidence after validation
  and T025 is the final sequential gate.

## Implementation Strategy

1. Restore policy/detector tests and code from the known-good parent.
2. Restore prompt timer/checkbox and settings list, keeping current safety fixes.
3. Update positive regression tests so future cleanup cannot silently remove the
   behavior.
4. Reconcile current and historical documentation with Feature 124 as owner.
5. Run focused checks, `ContractValidation`, Ponytail review and full local CI.
6. Stop before commit/release; implementation commit requires explicit user
   approval after validation.
