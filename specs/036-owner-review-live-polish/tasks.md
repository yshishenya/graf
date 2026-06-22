# Tasks: Owner Review Live Polish

**Input**: Design documents from `specs/036-owner-review-live-polish/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required for auth/session, notes/action truth, web shell, desktop shell, readiness, and evidence boundaries because this slice touches production auth, privacy, launch claims, and UX.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the feature evidence scaffold and baseline metadata before code changes.

- [X] T001 Create 036 evidence scaffold files in `docs/evidence/036-owner-review-live-polish/README.md`, `docs/evidence/036-owner-review-live-polish/validation-log.md`, `docs/evidence/036-owner-review-live-polish/clean-room-reference.md`, and `docs/evidence/036-owner-review-live-polish/screenshots/.gitkeep`
- [X] T002 [P] Add initial 036 launch gap register copied forward from 035 in `docs/evidence/036-owner-review-live-polish/launch-gap-register.md`
- [X] T003 [P] Add a 036 forbidden-content scan note to `docs/evidence/036-owner-review-live-polish/README.md`
- [X] T004 Record the current Chrome/live blocker observation for `https://rec.2brain.pro/meetings` in `docs/evidence/036-owner-review-live-polish/validation-log.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, test scaffolds, and evidence contracts that block story implementation.

- [X] T005 [P] Add owner-review live proof contract tests in `apps/server/tests/contract/test_owner_review_live_proof_contract.py`
- [X] T006 [P] Add notes/action truth schema contract tests in `apps/server/tests/contract/test_notes_action_truth_contract.py`
- [X] T007 [P] Add readiness claim regression tests for feature 036 in `apps/server/tests/contract/test_mvp_loop_readiness_contract.py`
- [X] T008 [P] Add web owner session integration test scaffolding in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T009 [P] Add notes/action view-model unit test scaffolding in `apps/server/tests/unit/test_notes_action_truth_view_models.py`
- [X] T010 [P] Add desktop polish/accessibility test scaffolding in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T011 Add shared safe evidence helpers for feature 036 in `apps/server/tests/integration/test_owner_review_live_evidence.py`
- [X] T012 Add feature 036 constants and evidence ids in `apps/server/src/twobrain_rec_server/readiness/evidence.py`

**Checkpoint**: Foundation ready - user story work can begin.

---

## Phase 3: User Story 1 - Prove Live Owner Review Access (Priority: P1)

**Goal**: Authenticated owner can access production review list/detail/governance states on `rec.2brain.pro`, or the remaining blocker is explicit and metadata-safe.

**Independent Test**: A temporary owner session or accepted owner browser context proves list, detail or safe empty detail, and governance/access state without committing tokens, cookies, private account identifiers, meeting text, or signed URLs.

### Tests for User Story 1

- [X] T013 [P] [US1] Add unit tests for session-cookie extraction and missing cookie behavior in `apps/server/tests/unit/test_auth_web_session_context.py`
- [X] T014 [P] [US1] Add integration tests for `/meetings` with session cookie and no legacy headers in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T015 [P] [US1] Add integration tests for expired, invalid, denied, and missing web session states in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T016 [P] [US1] Add tests proving owner-review smoke scripts never print raw tokens in `apps/server/tests/integration/test_production_smoke_boundary.py`
- [X] T017 [P] [US1] Add tests for sanitized live proof output in `apps/server/tests/integration/test_owner_review_live_evidence.py`

### Implementation for User Story 1

- [X] T018 [US1] Add browser-safe session cookie extraction constants and parsing in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T019 [US1] Add web owner tenant-scope dependency using `AuthSession.workspace_id` and `AuthSession.device_id` in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T020 [US1] Update cabinet HTML routes to use the web owner tenant-scope dependency in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T021 [US1] Update auth callback/session response behavior to support an HttpOnly owner review session cookie without removing API token response compatibility in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T022 [US1] Extend or wrap `apps/server/scripts/issue_smoke_auth_session.py` for owner-review purpose metadata without printing token values
- [X] T023 [US1] Add sanitized owner review live proof script in `apps/server/scripts/prove_owner_review_live.py`
- [X] T024 [US1] Document owner review execute-mode token-file and cleanup flow in `docs/evidence/036-owner-review-live-polish/README.md`
- [ ] T025 [US1] Capture sanitized `rec.2brain.pro` owner list/detail/governance result in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [ ] T026 [US1] Add metadata-only owner proof artifact in `docs/evidence/036-owner-review-live-polish/screenshots/web-owner-review-evidence.md`

**Checkpoint**: User Story 1 can be validated independently with `quickstart.md` sections 3 and 4.

---

## Phase 4: User Story 2 - Make Notes And Actions Truth Launch-Safe (Priority: P1)

**Goal**: Meeting review surfaces truthfully show summary, decisions, action items, and follow-up availability and launch-readiness impact.

**Independent Test**: Ready, partial, processing, failed, empty, denied, and unavailable review states expose notes/action truth as available, processing, blocked, unavailable, or deferred without fabricated output.

### Tests for User Story 2

- [X] T027 [P] [US2] Add notes/action schema contract coverage in `apps/server/tests/contract/test_notes_action_truth_contract.py`
- [X] T028 [P] [US2] Add notes/action derivation unit tests in `apps/server/tests/unit/test_notes_action_truth_view_models.py`
- [X] T029 [P] [US2] Add meeting detail integration tests for available, processing, unavailable, blocked, and deferred notes/action states in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T030 [P] [US2] Add web shell rendering tests for notes/action status copy in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T031 [P] [US2] Add no-secret/no-private-content regression coverage for notes/action evidence in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`

### Implementation for User Story 2

- [X] T032 [US2] Add notes/action truth response models to `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T033 [US2] Derive notes/action truth state from processing result and transcript availability in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T034 [US2] Include notes/action truth state in meeting list and detail responses in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T035 [US2] Replace generic notes placeholder copy with structured outcome status rendering in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T036 [US2] Update fixture-backed cabinet responses for notes/action states in `apps/server/tests/fixtures/cabinet.py`
- [X] T037 [US2] Record notes/action status evidence in `docs/evidence/036-owner-review-live-polish/screenshots/web-notes-action-truth-evidence.md`

**Checkpoint**: User Story 2 can be validated independently with focused cabinet contract/integration/unit tests.

---

## Phase 5: User Story 3 - Polish Desktop And Web Review Surfaces Toward V8 (Priority: P2)

**Goal**: Installed desktop and server-owned web review surfaces feel like a product workspace while preserving native capture authority and clean-room distance.

**Independent Test**: A reviewer can compare runtime desktop/web surfaces to V8 criteria and confirm meeting-workspace-first IA, persistent native capture controls, contextual actions, responsive fit, and no copied Krisp expression.

### Tests for User Story 3

- [X] T038 [P] [US3] Add web list/detail IA and responsive copy tests in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T039 [P] [US3] Add desktop workspace product-surface and persistent cabinet configuration tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` and `apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift`
- [X] T040 [P] [US3] Add capture control accessibility regression tests in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T041 [P] [US3] Add desktop embedded route policy regression tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 3

- [X] T042 [US3] Polish meeting list layout, action labels, empty states, and responsive constraints in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T043 [US3] Polish meeting detail notes/transcript/governance layout and playback/status panels in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T044 [US3] Polish installed desktop meeting workspace hierarchy and cabinet connection status in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T045 [US3] Add persistent or packaged installed-app cabinet configuration resolution and truthful unavailable states in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift` and `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T046 [US3] Preserve embedded route loading/failure behavior and native controls in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- [ ] T047 [US3] Capture installed app idle/active/paused/resumed/stopped and cabinet configured/missing-auth/local-only evidence from `/Applications/2brain Rec.app` into `docs/evidence/036-owner-review-live-polish/screenshots/`
- [X] T048 [US3] Record V8 clean-room comparison and remaining gaps in `docs/evidence/036-owner-review-live-polish/clean-room-reference.md`

**Checkpoint**: User Story 3 can be validated independently with server web tests, Swift build/tests, and installed-app screenshots.

---

## Phase 6: User Story 4 - Update Readiness Claim And Next Slice (Priority: P3)

**Goal**: Readiness report, product status, changelog, gap register, tasks, and issues agree on the final 036 claim.

**Independent Test**: A reviewer sees the same strongest truthful claim and remaining gaps in readiness output, current status, changelog, and tracker closeout.

### Tests for User Story 4

- [X] T049 [P] [US4] Update readiness matrix unit tests for 036 gap closure rules in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [X] T050 [P] [US4] Update readiness report integration tests for 036 evidence pack in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`
- [X] T051 [P] [US4] Update 036 live evidence tests in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`

### Implementation for User Story 4

- [X] T052 [US4] Update readiness evidence matrix for 036 in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [X] T053 [US4] Update readiness report generation for 036 evidence ids in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T054 [US4] Generate 036 readiness JSON and Markdown in `docs/evidence/036-owner-review-live-polish/readiness-report.json` and `docs/evidence/036-owner-review-live-polish/readiness-report.md`
- [X] T055 [US4] Update final gap register in `docs/evidence/036-owner-review-live-polish/launch-gap-register.md`
- [X] T056 [US4] Update accepted status, remaining blockers, and next slice in `docs/current-product-status.md`
- [X] T057 [US4] Add 036 entry under `[Unreleased]` in `CHANGELOG.md`
- [X] T058 [US4] Reconcile 036 task completion evidence in `specs/036-owner-review-live-polish/tasks.md`

**Checkpoint**: User Story 4 can be validated independently with readiness tests and doc consistency review.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full validation, issue sync, cleanup, and launch-quality closeout.

- [X] T059 [P] Run focused server validation from `specs/036-owner-review-live-polish/quickstart.md` and record results in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [X] T060 [P] Run `swift build --package-path apps/macos` and focused Swift tests including cabinet configuration resolution, then record results in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [X] T061 Run `infra/scripts/ci-local.sh` and record the canonical local gate result in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [X] T062 Run forbidden-content scans over `specs/036-owner-review-live-polish` and `docs/evidence/036-owner-review-live-polish`, then record policy-only matches in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [X] T063 Run `git diff --check` and record the result in `docs/evidence/036-owner-review-live-polish/validation-log.md`
- [X] T064 Re-run `$speckit-analyze` after implementation validation and update `specs/036-owner-review-live-polish/analysis.md`
- [ ] T065 Sync and close mapped GitHub issues only after evidence is present in `specs/036-owner-review-live-polish/issues.md`
- [X] T066 Confirm installed launch from `/Applications/2brain Rec.app` after final build/install, including no-shell-env cabinet behavior, and record it in `docs/evidence/036-owner-review-live-polish/validation-log.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundation; highest MVP priority.
- **US2 (Phase 4)**: Depends on Foundation; can run alongside US1 after shared schemas are stable, but must not claim generated output without evidence.
- **US3 (Phase 5)**: Depends on Foundation; can run after US1/US2 contracts are stable so UI labels match truth states.
- **US4 (Phase 6)**: Depends on validated results from US1-US3.
- **Polish (Phase 7)**: Depends on all implemented stories selected for closeout.

### User Story Dependencies

- **US1**: Required before closing `web-owner-live-auth-context`.
- **US2**: Required before closing or truthfully deferring `notes-action-output`.
- **US3**: Required before downgrading `desktop-product-surface-polish`.
- **US4**: Requires final results from US1-US3 to avoid overclaiming readiness.

### Parallel Opportunities

- T002-T003 can run in parallel after T001.
- T005-T010 can run in parallel after Setup.
- T013-T017 can run in parallel before US1 implementation.
- T027-T031 can run in parallel before US2 implementation.
- T038-T041 can run in parallel before US3 implementation.
- T049-T051 can run in parallel before US4 implementation.
- T059-T060 can run in parallel after implementation, before canonical CI.

---

## Parallel Example: User Story 1

```text
Task: "T013 [US1] Add unit tests for session-cookie extraction and missing cookie behavior in apps/server/tests/unit/test_auth_web_session_context.py"
Task: "T014 [US1] Add integration tests for /meetings with session cookie and no legacy headers in apps/server/tests/integration/test_web_owner_session_context.py"
Task: "T017 [US1] Add tests for sanitized live proof output in apps/server/tests/integration/test_owner_review_live_evidence.py"
```

## Parallel Example: User Story 2

```text
Task: "T027 [US2] Add notes/action schema contract coverage in apps/server/tests/contract/test_notes_action_truth_contract.py"
Task: "T028 [US2] Add notes/action derivation unit tests in apps/server/tests/unit/test_notes_action_truth_view_models.py"
Task: "T030 [US2] Add web shell rendering tests for notes/action status copy in apps/server/tests/unit/test_cabinet_web_shell.py"
```

## Parallel Example: User Story 3

```text
Task: "T038 [US3] Add web list/detail IA and responsive copy tests in apps/server/tests/unit/test_cabinet_web_shell.py"
Task: "T039 [US3] Add desktop workspace product-surface tests in apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift"
Task: "T041 [US3] Add desktop embedded route policy regression tests in apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift"
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 enough to prove or explicitly bound `web-owner-live-auth-context`.
3. Complete US2 enough to show notes/action truth and preserve a truthful readiness claim.
4. Validate before moving to visual polish claims.

### Incremental Delivery

1. US1 closes or narrows owner-review auth proof.
2. US2 prevents notes/action overclaiming.
3. US3 improves runtime desktop/web product quality against V8.
4. US4 updates claim, docs, readiness, and tracker truth.

### Stop Conditions

- Stop implementation if a task requires committing tokens, cookies, private account identifiers, private transcript text, raw audio, private reference captures, signed URLs, or private local paths.
- Stop implementation if web owner proof requires bypassing RLS/session/device validation.
- Stop readiness upgrade if notes/action output remains unavailable or deferred without an accepted narrower pilot claim.
