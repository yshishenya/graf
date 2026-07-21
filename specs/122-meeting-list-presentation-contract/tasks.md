# Tasks: Meeting List Presentation Contract

**Input**: Design documents from `/specs/122-meeting-list-presentation-contract/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/meeting-list-presentation.md`, `visual-target.md`, and passed `checklists/ux.md`

**Tests**: Required. This is a high-risk UX/accessibility/deletion slice. Within each story, add the named failing tests first, prove they fail for the intended gap, implement the smallest existing-pattern diff, then run the story's focused checks.

**Organization**: Tasks are grouped by user story so status presentation, row interaction, recovery truth, and responsive/accessibility behavior can each be reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no unresolved dependency.
- **[Story]**: Maps the task to a specification user story.
- Every task names exact repository paths and requirement/success-criterion coverage.

## Phase 1: Setup And Baseline

**Purpose**: Protect the current behavior and feature boundary before product-code changes.

- [ ] T001 Run the focused baseline command from `specs/122-meeting-list-presentation-contract/quickstart.md` §3, investigate any failure before implementation, and record command, counts, duration, warnings, and result in that file (FR-032; SC-012)
- [ ] T002 Confirm `git diff --name-only origin/master...HEAD -- apps/macos` is empty, inventory all 16 synthetic state classes and both target viewports, and record the pre-implementation boundary/evidence identifiers in `specs/122-meeting-list-presentation-contract/quickstart.md` without private screenshots (FR-002, FR-033–FR-034; SC-011)

---

## Phase 2: Foundational Presentation Boundary

**Purpose**: Create one testable projection boundary and truthful default sort used by every story.

**⚠️ CRITICAL**: Do not change row markup or client interaction until this phase passes.

- [ ] T003 Add failing unit coverage for the immutable query/row presentation values, invariant that zero-or-one compact status is possible, generated-title neutrality, full Russian date/time, and updated-time labeling in `apps/server/tests/unit/test_cabinet_view_models.py` (FR-006, FR-008–FR-010, FR-027)
- [ ] T004 Implement the minimum frozen presentation value objects and pure derivation helpers, reusing existing safe title/media/duration/time utilities and exposing no new public schema, in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` (FR-008–FR-016, FR-027, FR-032)
- [ ] T005 Add failing route/query tests proving browser and embedded defaults are `started_desc`, undated rows sort last, unknown sort falls back safely, and explicit `updated_desc` remains supported in `apps/server/tests/integration/test_cabinet_meeting_list.py` and `apps/server/tests/contract/test_cabinet_contract.py` (FR-005–FR-006; SC-004)
- [ ] T006 Change only the existing sort defaults/fallback labels and shared route query contract in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/support.py` (FR-005–FR-006, FR-032; SC-004)

**Checkpoint**: Pure presentation and default ordering are deterministic; public API, database, native capture, and detailed source truth are unchanged.

---

## Phase 3: User Story 1 — Быстро просматривать встречи и замечать исключения (Priority: P1) 🎯 MVP

**Goal**: Make normal rows quiet and exceptions immediately understandable with one compact status.

**Independent Test**: A synthetic mixed list has zero normality badges on ready rows, at most one status on every row, trustworthy title/duration/time, and a reviewer can distinguish ready/waiting/limited/actionable states without internal terminology.

### Tests For User Story 1 ⚠️

- [ ] T007 [US1] Add the full failing one-status precedence table, ready-state silence, playback/calendar-normal suppression, measured/unmeasured upload, partial/failure, and title/time accessible-description cases in `apps/server/tests/unit/test_cabinet_view_models.py` (FR-008–FR-016; SC-001–SC-003)
- [ ] T008 [P] [US1] Add failing HTML tests for zero ordinary `Готово`/`Аудио готово`/calendar tokens, exactly one exceptional status, separate `Выбрать встречу`, trusted meeting/update time, and browser/embedded parity in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-010–FR-016, FR-036; SC-001–SC-004)
- [ ] T009 [P] [US1] Add failing toolbar/refinement tests for one heading/search/filter/sort/upload, exact grouped filter vocabulary, current sort trigger, contextual `Найдено: N`, and removal of the duplicate sort/list headings in `apps/server/tests/integration/test_cabinet_meeting_list.py` (FR-003–FR-006, FR-035–FR-036)

### Implementation For User Story 1

- [ ] T010 [US1] Complete total status/title/time/action projection in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, ensuring the first true priority wins and ready/playback/calendar normality yields no token (FR-008–FR-016; SC-001–SC-003)
- [ ] T011 [US1] Render only the projected title, duration, status/progress, separate calendar-choice action, and selected time basis in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, removing independent overall/playback/calendar token concatenation from compact rows (FR-007–FR-016, FR-027)
- [ ] T012 [US1] Simplify the heading/refinement hierarchy and exact filter/sort/upload/result-count copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html` and its context in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-003–FR-006, FR-035–FR-036)
- [ ] T013 [US1] Add regression assertions that matched/no-context/declined/cleared calendar truth and playback reason truth remain available on detail/recovery surfaces in `apps/server/tests/integration/test_calendar_auto_context_match.py` and `apps/server/tests/integration/test_cabinet_playback_route.py` (FR-012, FR-014, FR-032; SC-012)
- [ ] T014 [US1] Run the US1 unit/rendering/query/calendar/playback tests, perform the five-second synthetic comprehension check for every canonical status, and record evidence in `specs/122-meeting-list-presentation-contract/quickstart.md` (SC-001–SC-004)

**Checkpoint**: User Story 1 is independently demonstrable without any selection, deletion, offline, or responsive enhancement.

---

## Phase 4: User Story 2 — Найти, открыть и выбрать встречу без неоднозначности (Priority: P1)

**Goal**: Separate open, selection, and deletion intent for pointer, keyboard, and assistive technology.

**Independent Test**: Pointer/Enter opens without selection; checkbox/Space selects without navigation; contextual controls do not shift content; batch mode appears only after explicit selection and exposes all four agreed controls.

### Tests For User Story 2 ⚠️

- [ ] T015 [US2] Add failing semantic-row tests for ordered homogeneous items, one primary open action, complete non-duplicated accessible metadata, explicit checkbox state, and row-specific delete names in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-017–FR-019, FR-027–FR-028; SC-005–SC-006, SC-008)
- [ ] T016 [P] [US2] Add failing JavaScript contract assertions for blank/readable-row open, `Enter` open, `Space` selection without scroll/navigation, contextual reveal, batch count/select-all/clear, and selection reconciliation in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` (FR-017–FR-019, FR-026; SC-005–SC-006)
- [ ] T017 [P] [US2] Add failing CSS/HTML assertions for reserved intent/delete columns, 32×32 contextual targets, selected/focus non-color cues, non-hover access, and no hover/focus geometry shift in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-007, FR-018, FR-028–FR-029; SC-008–SC-009)

### Implementation For User Story 2

- [ ] T018 [US2] Render the collection as ordered list items with programmatically associated title, duration, optional status, and time; keep a real primary link, checkbox, separate action, and delete button in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-017–FR-018, FR-027–FR-028)
- [ ] T019 [US2] Replace blank-row selection with primary-link opening, implement row `Enter`/`Space` semantics, contextual focusability, exact `Выбрано: N`/select-all/clear behavior, and HTMX selection reconciliation in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-017–FR-019, FR-026; SC-005–SC-006)
- [ ] T020 [US2] Reserve stable row columns, expose 32×32 controls on hover/focus/selection and coarse-pointer surfaces, and add visible focus/selected non-color cues in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` (FR-007, FR-018, FR-028–FR-029; SC-008–SC-009)
- [ ] T021 [US2] Align batch toolbar markup and exact visible/accessible copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html` without showing any batch control at zero selection (FR-019, FR-036; SC-006)
- [ ] T022 [US2] Run the US2 HTML/JavaScript/CSS tests and pointer/keyboard walkthrough, then record open-versus-selection and batch evidence in `specs/122-meeting-list-presentation-contract/quickstart.md` (SC-005–SC-006, SC-008)

**Checkpoint**: User Story 2 is independently usable with the existing deletion confirmation and endpoints even before recovery-copy polish.

---

## Phase 5: User Story 3 — Понимать ожидание, ограничения и восстановление (Priority: P1)

**Goal**: Give each waiting, limitation, failure, deletion, and recovery state one truthful message and applicable next action.

**Independent Test**: Every upload/processing/calendar/playback/failure/deletion/empty/network/session state yields exact copy, no invented progress/private metadata, and no focus theft.

### Tests For User Story 3 ⚠️

- [ ] T023 [US3] Add failing rendering tests for measured/unmeasured upload transitions, terminal-meter removal, calendar-choice action, audio preparing/absence, failed recovery, first-empty, refined-empty, and exact list-state copy in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-013–FR-016, FR-022–FR-024, FR-036; SC-007)
- [ ] T024 [P] [US3] Add failing asynchronous client tests for loading status, offline/service-unavailable/session-expired HTMX recovery, polite result announcements, one applicable action, and no cached metadata in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` and `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py` (FR-024–FR-026; SC-007–SC-008)
- [ ] T025 [P] [US3] Add failing deletion tests for the single-line accepted copy, feedback region above the list, partial-failure count/retry scope, dialog cancellation, and next→previous→list-anchor focus recovery in `apps/server/tests/integration/test_cabinet_hx_delete_feedback.py` and `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-020–FR-021, FR-026; SC-007–SC-008)

### Implementation For User Story 3

- [ ] T026 [US3] Render exact first-empty/refined-empty/loading hooks and one-action recovery templates, preserving persistent upload/native recording actions, in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html` (FR-022–FR-024, FR-036; SC-007)
- [ ] T027 [US3] Add bounded HTMX send/response error handling, loading/progress/result announcements, retry/sign-in behavior, and metadata-safe state replacement in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-024–FR-026; SC-007–SC-008)
- [ ] T028 [US3] Move the deletion live region above the collection, align accepted feedback copy, preserve the existing bounded dialog/request flow, keep failed batch rows selected, and implement deterministic post-removal focus in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/deletion_feedback.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-020–FR-021, FR-026; SC-007–SC-008)
- [ ] T029 [US3] Align access-revoked copy to `Встреча больше недоступна` without repeating private metadata in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_unavailable_content.html` (FR-025, FR-036; SC-007)
- [ ] T030 [US3] Run the US3 rendering/static/privacy/deletion compatibility suites and record exact recovery, announcement, privacy, and focus evidence in `specs/122-meeting-list-presentation-contract/quickstart.md` (SC-007–SC-008, SC-012)

**Checkpoint**: All P1 stories are functional and independently validated with existing server/auth/deletion contracts.

---

## Phase 6: User Story 4 — Спокойный доступный список во всех состояниях (Priority: P2)

**Goal**: Preserve meaning and every critical action at normal/minimum windows and with keyboard, assistive technology, increased contrast, and Reduce Motion.

**Independent Test**: The 16-state synthetic matrix has no overlap/horizontal scroll or inaccessible action at both target sizes; accessible names/order are complete and clean-room review finds zero copied reference expression.

### Tests For User Story 4 ⚠️

- [ ] T031 [US4] Add failing responsive/accessibility assertions for `1280×760`/`1040×680`, long/no-date rows, 48/60 px geometry, full accessible descriptions, 32×32 targets, visible focus, increased contrast, Reduce Motion, and zero horizontal overflow in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py` (FR-027–FR-030; SC-008–SC-010)

### Implementation And Evidence For User Story 4

- [ ] T032 [US4] Apply the minimum responsive, long-title, exceptional-row, high-contrast, non-hover, focus, and reduced-motion CSS needed to satisfy the target in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` (FR-018, FR-028–FR-029; SC-008–SC-009)
- [ ] T033 [US4] Capture matched synthetic browser/embedded evidence for all 16 classes at `1280×760` and every layout-sensitive class at `1040×680`, run the keyboard/accessibility-tree walkthrough, and record only privacy-safe measurements/results in `specs/122-meeting-list-presentation-contract/quickstart.md` (FR-029, FR-034; SC-008–SC-009, SC-011)
- [ ] T034 [US4] Perform the clean-room and forbidden-copy/feature audit against the supplied Krisp reference, verify zero copied text/assets/icons/composition/proprietary flow, and record the result in `specs/122-meeting-list-presentation-contract/quickstart.md` (FR-030–FR-031; SC-010)

**Checkpoint**: All four stories pass the same browser/embedded, visual, keyboard, accessibility, privacy, and clean-room contract.

---

## Phase 7: Polish And Closeout

**Purpose**: Prove repository compatibility and prepare an approval-ready handoff without committing product code or deploying.

- [ ] T035 Update `CHANGELOG.md` with Russian user-visible list hierarchy/status/interaction changes, compatibility impact, validation scope, and no-migration/no-native/no-deploy notes (FR-032; SC-012)
- [ ] T036 Run the complete focused and compatibility commands plus static audits in `specs/122-meeting-list-presentation-contract/quickstart.md` §§3–5, record exact counts/results there, and fix only feature-owned regressions (SC-001–SC-012)
- [ ] T037 Run `infra/scripts/ci-local.sh`, record the complete gate result and any environment-owned warning in `specs/122-meeting-list-presentation-contract/quickstart.md`, and do not weaken or bypass the gate (SC-012)
- [ ] T038 Verify `git diff --check`, no diff under `apps/macos`, no migration/public API/dependency/secret/private evidence, all desired tasks/evidence complete, and add status/evidence comments to the linked GitHub issues; record the approval-ready state in `specs/122-meeting-list-presentation-contract/quickstart.md` without committing product code or deploying (FR-002, FR-032–FR-034; SC-010–SC-012)

---

## Dependencies And Execution Order

### Phase Dependencies

- **Setup (Phase 1)** has no dependency and protects the baseline.
- **Foundational boundary (Phase 2)** depends on T001–T002 and blocks every story.
- **US1 (Phase 3)** depends on the pure projection and sort boundary.
- **US2 (Phase 4)** depends on US1 row content so interaction is implemented against final row zones.
- **US3 (Phase 5)** depends on US1 status projection and US2 selection/deletion triggers.
- **US4 (Phase 6)** depends on final P1 markup/behavior so accessibility and responsive evidence audits the delivered surface.
- **Polish/closeout (Phase 7)** depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: independently testable after Foundation as a read-only mixed-status list.
- **US2 (P1)**: uses US1 row content but is independently testable through open/select/batch interaction.
- **US3 (P1)**: uses US1 projection and US2 delete trigger, independently testable through exact recovery/deletion states.
- **US4 (P2)**: validates the final markup/behavior at responsive and assistive-technology boundaries.

### Within Each Story

1. Add the named failing tests.
2. Confirm failure is the intended missing behavior, not environment damage.
3. Implement the smallest existing-pattern diff.
4. Run the story's focused tests and independent scenario.
5. Record synthetic/privacy-safe evidence.
6. Mark tasks `[X]` only after that evidence exists.

### Parallel Opportunities

- T008 and T009 can run in parallel after T007 because they touch separate test files.
- T016 and T017 can run in parallel after T015.
- T024 and T025 can run in parallel after T023.
- Documentation/evidence edits are intentionally serialized to avoid conflicts in `quickstart.md`.

## Parallel Examples

### User Story 1

```text
T008: row HTML/status/browser-embedded tests
T009: toolbar/query/refinement integration tests
```

### User Story 2

```text
T016: JavaScript open/select/batch contract tests
T017: CSS geometry/control-access tests
```

### User Story 3

```text
T024: async recovery/privacy client tests
T025: deletion feedback/focus tests
```

## Implementation Strategy

### MVP First

The smallest useful slice is Foundation + US1: it removes normality noise and makes the state of every row understandable without changing interactions. Because open/selection ambiguity and recovery truth are P1 requirements, the feature must also complete US2 and US3 before it is represented as implementation-ready.

### Incremental Delivery

1. Baseline and pure presentation boundary.
2. Quiet, deterministic mixed-status list (US1).
3. Unambiguous open/select/batch behavior (US2).
4. Truthful waiting/recovery/deletion states (US3).
5. Responsive/accessibility/clean-room convergence (US4).
6. Focused tests, full repository gate, and approval handoff.

## Requirement Coverage

| Requirement group | Primary tasks |
|---|---|
| FR-001–FR-002 scope/native authority | T002, T038 |
| FR-003–FR-006 toolbar/sort | T005–T006, T009, T012 |
| FR-007–FR-016 row/title/status/progress | T003–T004, T007–T011, T023 |
| FR-017–FR-019 open/selection/batch | T015–T022 |
| FR-020–FR-021 deletion | T025, T028, T030 |
| FR-022–FR-026 empty/recovery/privacy/live status | T023–T030 |
| FR-027–FR-029 accessibility/responsive | T015–T020, T024, T031–T033 |
| FR-030–FR-031 clean-room/out-of-scope features | T002, T034, T038 |
| FR-032 compatibility/no new data | T001, T004–T006, T013, T035–T038 |
| FR-033–FR-034 target/evidence privacy | T002, T033–T034, T038 |
| FR-035–FR-036 vocabulary/exact copy | T009, T012, T021, T023, T026, T029 |
| SC-001–SC-004 scanning/state/sort | T007–T014 |
| SC-005–SC-006 open/selection | T015–T022 |
| SC-007 recovery states | T023–T030 |
| SC-008–SC-011 a11y/responsive/clean-room/evidence | T024–T025, T031–T034 |
| SC-012 compatibility | T001, T013, T035–T038 |

## Notes

- `tasks.md` is the implementation source of truth; GitHub issues mirror tasks after a clean analyze pass.
- No task authorizes a product-code commit, push, PR, release, installer replacement, deploy, or production rollout.
- Documentation checkpoint commits may run only through the enabled Spec Kit hooks already approved by the user.
- Private runtime screenshots stay outside git; only synthetic or deliberately redacted evidence may be committed.
- Apply the Ponytail ladder throughout: reuse helpers/semantics, remove duplicate rendering, add no dependency/API/schema/migration, and avoid broad cabinet/native refactors.
