# Tasks: Meeting Outcomes MVP

**Input**: Design documents from `specs/049-meeting-outcomes-mvp/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests are required. This slice changes meeting content, privacy, deletion, readiness, and user-facing review surfaces. Write focused RED tests first for each story, then implement until they pass.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Phase 1: Setup And Planning Evidence

**Purpose**: Lock the feature context and metadata-safe planning evidence.

- [X] T001 Record initial 049 planning context and branch/master sync in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T002 [P] Ensure `AGENTS.md` Spec Kit pointer references `specs/049-meeting-outcomes-mvp/plan.md`
- [X] T003 [P] Add simple Russian `[Unreleased]` changelog entry for stored meeting outcomes in `CHANGELOG.md`
- [X] T004 Run `SPECIFY_FEATURE_DIRECTORY=specs/049-meeting-outcomes-mvp bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T005 Run checklist status validation for `specs/049-meeting-outcomes-mvp/checklists/*.md` and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

---

## Phase 2: Foundational Outcome Storage And Contracts

**Purpose**: Add the shared schema, models, enums, RLS, and API contract foundation required by all stories.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T006 [P] Add outcome status/category enums and deletion artifact coverage in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [X] T007 [P] Add RED Pydantic contract coverage for stored outcome categories/items/provenance in `apps/server/tests/contract/test_meeting_outcomes_contract.py`
- [X] T008 [P] Add RED migration/model coverage for outcome tables in `apps/server/tests/integration/test_meeting_outcomes_migrations.py`
- [X] T009 Add SQLAlchemy outcome models in `apps/server/src/twobrain_rec_server/db/models/outcomes.py`
- [X] T010 Export outcome models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [X] T011 Add Alembic migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0009_meeting_outcomes_mvp.py` with tables, indexes, unique constraints, and Postgres RLS policies
- [X] T012 Update RLS coverage constants for outcome tables in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [X] T013 Add outcome Pydantic schemas and extend notes/action response contract in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T014 Add outcome store primitives for create/reuse, item replacement, attempt recording, and category state retrieval in `apps/server/src/twobrain_rec_server/outcomes/store.py`
- [X] T015 Add `apps/server/src/twobrain_rec_server/outcomes/__init__.py`
- [X] T016 Run foundational contract/migration tests from `specs/049-meeting-outcomes-mvp/quickstart.md` and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: Outcome storage foundation is ready; user stories can start.


---

## Phase 2A: Pre-Implementation Analyze Gate

**Purpose**: Run the required read-only Spec Kit consistency and GitHub tracker gates before implementation work begins.

- [X] T017 Run read-only Spec Kit analyze pass and record blocker-free result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md` before any user story implementation starts
- [X] T018 Run `$speckit-taskstoissues`, create mapping in `specs/049-meeting-outcomes-mvp/issues.md`, and record GitHub issue canon validation in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md` before user story implementation starts

## Phase 3: User Story 1 - See Stored Meeting Outcomes (Priority: P1) MVP

**Goal**: Processed owner meetings show stored launch-safe outcomes with category truth and transcript evidence.

**Independent Test**: One processed owner meeting with transcript/diarization produces stored summary, key points, decisions/actions/followups/risks/questions/evidence categories or explicit not-found/not-inferable states, and the web review shows stored output instead of placeholders.

### Tests for User Story 1

- [X] T019 [P] [US1] Add RED unit tests for deterministic extractive category generation and non-fabrication in `apps/server/tests/unit/test_meeting_outcomes_generator.py`
- [X] T020 [P] [US1] Add RED integration tests for generation/store idempotency and source evidence in `apps/server/tests/integration/test_meeting_outcomes_generation.py`
- [X] T021 [P] [US1] Add RED cabinet detail tests for stored outcome content replacing deferred placeholders in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`
- [X] T022 [P] [US1] Add fixture helpers for processed meetings with outcome-ready transcripts in `apps/server/tests/fixtures/cabinet.py`

### Implementation for User Story 1

- [X] T023 [US1] Add domain dataclasses/value objects for generated outcome payloads in `apps/server/src/twobrain_rec_server/outcomes/models.py`
- [X] T024 [US1] Implement deterministic extractive generator with category-level not-found/not-inferable states in `apps/server/src/twobrain_rec_server/outcomes/generator.py`
- [X] T025 [US1] Implement outcome generation service orchestration and idempotent stored output creation in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [X] T026 [US1] Trigger or reuse outcome generation after successful transcript import in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T027 [US1] Load latest stored outcomes with transcript review queries in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T028 [US1] Map stored outcomes into review/list notes action state in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T029 [US1] Render stored outcome categories, item text, and timestamp evidence in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T030 [US1] Run focused US1 tests and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Keep Outcomes Honest During Processing And Failure (Priority: P1)

**Goal**: Review surfaces keep transcript/playback available while outcomes show accurate processing, partial, blocked, unavailable, and unsafe states.

**Independent Test**: Meetings in ready, processing, failed, dependency-unavailable, transcript-only, partial-output, no-inferable, and unsafe states show truthful category-level states without hiding transcript/playback when allowed.

### Tests for User Story 2

- [X] T031 [P] [US2] Add RED integration tests for processing/blocked/failed/partial outcome truth in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`
- [X] T032 [P] [US2] Add RED service tests for retry safety and preserving prior accepted output in `apps/server/tests/integration/test_meeting_outcomes_generation.py`
- [X] T033 [P] [US2] Add RED one-hour orchestration benchmark for non-blocking outcome generation in `apps/server/tests/integration/test_meeting_outcomes_orchestration_benchmark.py`

### Implementation for User Story 2

- [X] T034 [US2] Add safe failure reason mapping, timeout handling, and attempt status transitions in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [X] T035 [US2] Add prior-output preservation and retry supersession behavior in `apps/server/src/twobrain_rec_server/outcomes/store.py`
- [X] T036 [US2] Ensure `build_review_response` preserves transcript, diarization, and playback while outcomes are processing or blocked in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T037 [US2] Render processing/partial/blocked/unsafe outcome copy without content exposure in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T038 [US2] Run focused US2 tests and one-hour benchmark and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Match Web And macOS Embedded Review (Priority: P1)

**Goal**: Web cabinet and macOS embedded review show the same outcome truth and layout without overlap or overflow.

**Independent Test**: The same meeting opened through ordinary web review and `/desktop/meetings/{meeting_id}` shows matching outcome states/items/evidence and keeps the bottom playback bar usable at desktop and mobile widths.

### Tests for User Story 3

- [X] T039 [P] [US3] Add RED web-shell tests for stored outcome markup, long category content, and playback coexistence in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T040 [P] [US3] Add RED browser runtime verifier for web, mobile, and desktop embedded outcome review in `specs/049-meeting-outcomes-mvp/evidence/browser-runtime-check.cjs`
- [X] T041 [P] [US3] Add RED integration assertions for web/embedded route parity in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`

### Implementation for User Story 3

- [X] T042 [US3] Update cabinet CSS/HTML for responsive outcome cards and source evidence rows in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T043 [US3] Ensure embedded review uses the same outcome response and no separate native-only state in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T044 [US3] Run web-shell and browser runtime validation and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: User Story 4 - Preserve Privacy, Access, Deletion, And Evidence Boundaries (Priority: P1)

**Goal**: Outcomes follow the same access, retention, deletion, export/download, audit, and metadata-only evidence boundaries as meeting content.

**Independent Test**: Denied/deleted/deleting/retention-blocked meetings expose no outcome content; deletion reports account for outcomes; scans show no meeting content or secrets in committed evidence.

### Tests for User Story 4

- [X] T045 [P] [US4] Add RED no-secret/no-content egress tests for outcomes in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [X] T046 [P] [US4] Add RED deletion/lifecycle tests for outcome artifact accounting in `apps/server/tests/integration/test_meeting_outcomes_deletion.py`
- [X] T047 [P] [US4] Add RED access denial tests for outcome content hiding in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`
- [X] T048 [P] [US4] Add RED RLS coverage assertions for outcome tables in `apps/server/tests/contract/test_rls_tenant_isolation_contract.py`

### Implementation for User Story 4

- [X] T049 [US4] Hide outcome content for denied, unauthenticated, deleted, deleting, and retention-blocked review states in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T050 [US4] Include outcome artifacts in deletion reports and controlled artifact summaries in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [X] T051 [US4] Purge or mark outcome rows through meeting deletion execution in `apps/server/src/twobrain_rec_server/deletion/service.py`
- [X] T052 [US4] Add metadata-only outcome audit events without generated text in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [X] T053 [US4] Run focused US4 privacy/deletion/RLS tests and forbidden-content scan and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: US4 is independently functional and testable.

---

## Phase 7: User Story 5 - Update MVP Readiness Truth (Priority: P2)

**Goal**: Status docs, readiness report, launch gap register, changelog, release notes, and evidence agree on whether `notes-action-output` is closed.

**Independent Test**: Reading readiness outputs and status docs shows that the blocker closes only with stored outcome proof, or remains blocked/partial/explicitly deferred with simple Russian limitations.

### Tests for User Story 5

- [X] T054 [P] [US5] Add RED readiness matrix/report tests for closing `notes-action-output` only after stored outcomes are proven in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [X] T055 [P] [US5] Add RED readiness/status integration tests for current product truth in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`

### Implementation for User Story 5

- [X] T056 [US5] Update readiness matrix evidence and launch-gap behavior in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [X] T057 [US5] Update readiness report copy and generated artifact expectations in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T058 [US5] Update `docs/current-product-status.md` with simple Russian/English product truth for 049 outcome readiness
- [X] T059 [US5] Update 036/045 readiness evidence pointers or add 049 evidence links without editing private meeting content in `docs/evidence/036-owner-review-live-polish/readiness-report.md`
- [X] T060 [US5] Run focused readiness tests and record metadata-only result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`

**Checkpoint**: US5 is independently functional and testable.

---

## Phase 8: Validation, Tracker Sync, Release, And Closeout

**Purpose**: Prove the full feature and prepare release/production truth.

- [X] T061 Run final post-implementation task/evidence consistency recheck and record result in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md` before PR closeout
- [X] T062 Run all focused commands from `specs/049-meeting-outcomes-mvp/quickstart.md` and record metadata-only results in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T063 Run full `infra/scripts/ci-local.sh` and record `ci_local_result` in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T064 Run `infra/scripts/cd-remote.sh --dry-run` and record deploy dry-run evidence in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T065 Verify macOS embedded review surface through server-owned route or focused Swift tests if native files changed, then record evidence in `specs/049-meeting-outcomes-mvp/evidence/validation-log.md`
- [X] T066 Run final forbidden-content scan from `specs/049-meeting-outcomes-mvp/quickstart.md` over specs, docs, release notes, and evidence
- [X] T067 Reconcile completed tasks with evidence and leave any unverified task unchecked in `specs/049-meeting-outcomes-mvp/tasks.md`
- [X] T068 Prepare PR description, release notes draft in simple Russian, and production closeout plan in `specs/049-meeting-outcomes-mvp/evidence/pr-draft.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies.
- **Phase 2 Foundation**: depends on Phase 1; blocks all user stories.
- **US1**: depends on Phase 2.
- **US2**: depends on Phase 2 and integrates with US1 store/service behavior.
- **US3**: depends on Phase 2 and can proceed after outcome review response exists.
- **US4**: depends on Phase 2 and can proceed alongside US2/US3 after outcome tables exist.
- **US5**: depends on US1-US4 evidence because readiness must not overclaim.
- **Phase 8**: depends on all implemented stories selected for MVP.

### User Story Order

1. US1 stored outcomes.
2. US2 processing/failure truth.
3. US3 web/embedded parity.
4. US4 privacy/access/deletion/evidence boundaries.
5. US5 readiness truth.

### Parallel Opportunities

- T002 and T003 can run in parallel.
- T007 and T008 can run in parallel.
- T019 through T022 can run in parallel.
- T031 through T033 can run in parallel.
- T039 through T041 can run in parallel.
- T045 through T048 can run in parallel.
- T054 and T055 can run in parallel.

## Implementation Strategy

### MVP First

Complete all P1 stories (US1-US4) before claiming MVP outcome readiness. US5
then updates readiness truth. Do not close `notes-action-output` from US1 alone
unless privacy/deletion/access/UI parity evidence is also present.

### Traceability Matrix

| Requirement | Tasks |
| --- | --- |
| FR-001 stored launchable outcomes | T009-T015, T019-T030 |
| FR-002 categories | T007, T013, T019, T023-T029 |
| FR-003 transcript evidence | T019, T020, T023-T029 |
| FR-004 no fabrication | T019, T024, T028, T030 |
| FR-005 category-level availability | T007, T013, T023-T029, T031-T038 |
| FR-006 available state only with stored truth | T021, T028, T029, T054-T060 |
| FR-007 transcript/playback independent | T031, T036, T037, T039-T044 |
| FR-008 web/embedded parity | T039-T044 |
| FR-009 start/reuse after transcript ready | T020, T025, T026 |
| FR-010 idempotent retry-safe processing | T020, T032, T034, T035 |
| FR-011 provenance | T007, T013, T014, T023, T025 |
| FR-012 meeting content lifecycle | T045-T053 |
| FR-013 fail-closed states | T031, T034, T037, T045-T049 |
| FR-014 metadata-only evidence | T045, T052, T053, T066 |
| FR-015 simple Russian copy | T029, T037, T058, T068 |
| FR-016 non-blocking review | T031, T033, T036-T038 |
| FR-017 one-hour/30-second budget | T033, T038, T062 |
| FR-018 readiness truth | T054-T060 |
| FR-019 out-of-scope boundaries | T058, T068 |

### Success Criteria Matrix

| Success Criterion | Tasks |
| --- | --- |
| SC-001 stored outcomes visible in web and embedded review | T020-T030, T039-T044, T062 |
| SC-002 factual items include transcript evidence | T019-T020, T023-T030 |
| SC-003 no-inferable categories do not fabricate content | T019, T024, T028-T030 |
| SC-004 failure/deleted/unauthorized states expose no outcome content | T031-T038, T045-T053 |
| SC-005 one-hour orchestration budget or safe non-blocking fallback | T033, T038, T062 |
| SC-006 browser runtime layout/parity validation | T039-T044, T062, T065 |
| SC-007 forbidden-content scans stay clean | T052, T066 |
| SC-008 readiness and release/status truth agree | T054-T060, T068 |

## Notes

- Mark tasks `[X]` only after the task-specific validation evidence exists.
- Do not commit generated private content, transcript text, outcome text,
  prompts, provider responses, audio, screenshots with meeting content, signed
  URLs, credentials, storage keys, private paths, or private meeting IDs.
