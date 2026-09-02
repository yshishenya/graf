# Tasks: Повторная обработка записи пользователем

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

## Phase 1: Setup

- [X] T001 Reuse the existing processing/cabinet fixtures for multiple workflow attempts and owner/shared-recipient views; no fixture-only abstraction was needed
- [X] T002 Confirm no schema change is needed and the existing workflow identity is sufficient against current `origin/master` in `specs/213-user-reprocess/research.md`

## Phase 2: Foundational identity and result selection

**Goal**: Make exact workflow identity and one complete-result selector safe before exposing the action.

### Tests

- [X] T003 [P] Add predecessor/successor replay and stale-predecessor tests in `apps/server/tests/integration/test_processing_attempts.py`
- [X] T004 [P] Add ordering/completeness tests for old-complete/new-active/partial/terminal/complete attempts in `apps/server/tests/unit/test_processing_results.py`
- [X] T005 [P] Add new-payload, legacy-history replay and delayed-old-activity tests in `apps/server/tests/unit/test_processing_workflow_identity.py` and `apps/server/tests/unit/test_processing_temporal_workflow.py`

### Implementation

- [X] T006 Add predecessor/successor CAS admission using the existing workflow ID and attempt ordinal in `apps/server/src/twobrain_rec_server/processing/store.py`
- [X] T007 Make `effective_processing_result_query()` require `complete_processing_result_clause()` and order by workflow attempt then result version in `apps/server/src/twobrain_rec_server/processing/results.py`
- [X] T008 Carry exact `processing_workflow_id` in all new Temporal starts and load/validate that row in activities and error persistence in `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, `apps/server/src/twobrain_rec_server/workflows/worker.py`, `apps/server/src/twobrain_rec_server/processing/pickup.py` and `apps/server/src/twobrain_rec_server/api/processing.py`

**Checkpoint**: A new partial attempt cannot hide a complete result, and a delayed activity cannot attach to another workflow row.

## Phase 3: User Story 1 — Запустить повторную обработку

**Goal**: The recording owner starts exactly one replacement attempt from the ordinary meeting.

### Tests

- [X] T009 [P] Add owner/non-owner, stale revision, missing source and CSRF API contracts in `apps/server/tests/contract/test_processing_status_contract.py` and `apps/server/tests/integration/test_processing_attempts.py`
- [X] T010 [P] Add replay, two-tab coalescing, terminal fresh request, provider-job and no-second-charge integration tests in `apps/server/tests/integration/test_processing_attempts.py`
- [X] T011 [P] Add owner-only menu, confirmation and busy-state contracts in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation

- [X] T012 Extend processing attempt admission to accept a complete published result, return an existing immediate successor, coalesce active work and preserve ordinary terminal-recovery behavior in `apps/server/src/twobrain_rec_server/processing/store.py`
- [X] T013 Add request/response schemas and owner-authorized `POST /api/v1/meetings/{meeting_id}/processing/reprocess` in `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/api/processing.py`
- [X] T014 Add eligible owner action and confirmation to the existing `Ещё` menu/dialog components in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

**Checkpoint**: One owner action creates one durable workflow; admin pages and reason fields remain untouched.

## Phase 4: User Story 2 — Сохранить рабочую версию

**Goal**: Every customer channel uses the previous complete result until a newer complete result exists.

### Tests

- [X] T015 [P] Add latest-workflow versus effective-result projection tests in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/contract/test_processing_status_contract.py`
- [X] T016 [P] Add detail/share/export/egress/desktop consistency tests in `apps/server/tests/integration/test_cabinet_meeting_detail.py`, `apps/server/tests/integration/test_artifact_egress_policy.py` and `apps/server/tests/integration/test_desktop_sync.py`
- [X] T017 Remove Feature 213 outcome-generation, summary-export and stale-summary UI tests; preserve the summary tests from current `master` unchanged

### Implementation

- [X] T018 Split operational latest attempt from effective complete content in `apps/server/src/twobrain_rec_server/processing/status.py`, `apps/server/src/twobrain_rec_server/cabinet/queries.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T019 Route transcript downloads, egress and desktop review availability through the shared complete selector without changing summary exports in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [X] T020 Remove Feature 213 changes from `outcomes/service.py`, `outcomes/ai_service.py`, summary runtime and summary export paths
- [X] T021 Show transcript-only continuity copy without changing stale-summary UI in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`

**Checkpoint**: Active, partial and failed replacement attempts never remove the last complete customer result.

## Phase 5: User Story 3 — Статус и восстановление

**Goal**: The owner sees truthful status and can wake the same retryable attempt.

### Tests

- [X] T022 [P] Add owner authorization, schedule-generation and same-job retry tests in `apps/server/tests/contract/test_processing_status_contract.py`
- [X] T023 [P] Add active/retryable/no-time/terminal copy and countdown contracts in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T024 [P] Add keyboard, focus restoration and quiet-live-region checks in `apps/server/tests/contract/test_recording_workflow_accessibility.py`

### Implementation

- [X] T025 Revalidate meeting creator for replacement-attempt manual actions without changing initial-processing recovery in `apps/server/src/twobrain_rec_server/api/processing.py`
- [X] T026 Reuse server time, `schedule_generation`, existing manual check and quiet countdown; refresh live reprocess eligibility and keep transcript-only copy in `cabinet.js` and `meeting_detail_content.html`

**Checkpoint**: Manual and automatic retry cannot run in parallel, and terminal failure has a fresh user action.

## Phase 6: Polish and validation

- [X] T027 Update `CHANGELOG.md` and `docs/current-product-status.md` with transcript-only Feature 213 behavior and compatibility
- [X] T028 Run every focused command and scenario in `specs/213-user-reprocess/quickstart.md` and record metadata-only evidence
- [X] T029 Run `infra/scripts/ci-local.sh --fast`; full CI remains deferred to the exact release candidate
- [X] T030 Run final Ponytail/code review for duplicate selectors, unnecessary schema/layers, trust boundaries and accessibility

## Dependencies and execution order

- Phase 2 blocks every user story.
- User Story 1 may be coded after T006–T008 but must not be exposed until User Story 2 passes.
- User Story 2 is the safety gate for enabling the action.
- User Story 3 depends on the User Story 1 attempt identity and existing check route.
- Phase 6 follows all stories.

## Implementation strategy

1. Land exact identity and the shared complete-result selector behind no new action.
2. Add owner admission and confirmation.
3. Switch transcript customer readers while leaving outcomes untouched.
4. Add replacement-specific status/retry copy.
5. Run focused checks, quickstart and fast CI.

No admin implementation, publication pointer, command table, new queue, workflow type or dependency is included.

## Phase 7: Simplified replacement UX

**Goal**: Hide the owner's stale version behind one neutral state, restore it on terminal failure and publish transcript/player speaker labels together.

This phase supersedes only the replacement-presentation portions of completed T021, T023 and T026; their server-side result-selection and initial-recovery behavior remains valid.

- [X] T031 [P] [US1] Update the approved warning and replacement-state contract tests in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` and `apps/server/tests/contract/test_recording_workflow_accessibility.py`
- [X] T032 [P] [US2] Add web/embedded active, terminal-restoration and result-scoped speaker-name coverage in `apps/server/tests/integration/test_cabinet_meeting_detail.py` and `apps/server/tests/integration/test_speaker_names.py`
- [X] T033 [US1] Replace the confirmation copy with the minimal manual-name warning in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T034 [US2] Add server-rendered and dynamic replacement visibility markers and neutral replacement styling in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T035 [US2] Replace the main detail and adjacent player from one response so new speaker labels publish together in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T036 [US3] Keep expected retries and temporary status-fetch failures under the neutral indicator, restore old content on terminal failure and expose `Попробовать снова` in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [ ] T037 Run the focused Feature 213 quickstart, JavaScript syntax, `git diff --check` and `infra/scripts/ci-local.sh --fast`; record that full CI remains the release-candidate gate in `specs/213-user-reprocess/quickstart.md`
