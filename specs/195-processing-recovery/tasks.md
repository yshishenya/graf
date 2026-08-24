# Tasks: Восстановление обработки и ранняя расшифровка встречи

**Input**: Design documents from `/specs/195-processing-recovery/`

**Risk lane**: `high-risk-feature`. This slice touches MediaScribe, Temporal,
PostgreSQL, deletion fences, retry semantics and degraded-state UX. Every
story needs focused tests before implementation; closeout requires the
quickstart scenarios, completed high-risk checklists, `git diff --check` and
`infra/scripts/ci-local.sh`. No production deploy is part of this task list.

## Phase 1: Setup and contract fixtures

**Purpose**: Establish deterministic, content-safe test inputs and runtime
limits before changing the processing path.

- [x] T001 [P] Add deterministic MediaScribe v1 fake transport fixtures with opaque job ids, headers, retry hints, idempotency replay/conflict and deletion receipts in `apps/server/tests/fakes/mediascribe_v1.py`
- [x] T002 [P] Add bounded processing-recovery settings with safe defaults and validation in `apps/server/src/twobrain_rec_server/config.py`
- [x] T003 [P] Add the v1 contract fixture matrix for capabilities, single/dual upload, status/result/summary, unknown fields and deletion in `apps/server/tests/contract/test_mediascribe_v1_client.py`

## Phase 2: Foundational processing boundary

**Purpose**: Add the durable state and server-only adapter primitives that all
user stories depend on.

- [x] T004 [P] Add the additive processing recovery migration, indexes, same-key uniqueness and rollback boundary in `apps/server/src/twobrain_rec_server/db/migrations/versions/0078_processing_recovery.py`
- [x] T005 Extend `ProcessingWorkflow`, `MediaScribeJob`, `ProcessingResult` and segment metadata with attempt, retry, provider hint, provenance and deletion-fence fields in `apps/server/src/twobrain_rec_server/db/models/processing.py`
- [x] T006 [P] Add forward-compatible provider states, retry classes, artifact states and safe error metadata models in `apps/server/src/twobrain_rec_server/domain/statuses.py` and `apps/server/src/twobrain_rec_server/mediascribe/schemas.py`
- [x] T007 [P] Implement machine-first retry classification, bounded hint/fallback scheduling, deadline handling and schedule-generation fences in `apps/server/src/twobrain_rec_server/processing/recovery.py`
- [x] T008 [P] Add unit coverage for valid/missing/invalid `Retry-After`, provider codes, transport errors, deadline exhaustion and unknown upload outcomes in `apps/server/tests/unit/test_processing_recovery.py`
- [x] T009 Migrate all MediaScribe lifecycle reads to `/v1`, preserve safe response headers and typed provider errors, and tolerate unknown status values in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [x] T010 Add client contract tests for `/v1` paths, request ids, retry headers, Problem Details, safe egress state and no-secret error projections in `apps/server/tests/contract/test_mediascribe_client_contract.py`
- [x] T011 Make result import hash/idempotent, revision-pinned and deletion-epoch safe while preserving bounded provenance, overlaps and track roles in `apps/server/src/twobrain_rec_server/processing/submit.py` and `apps/server/src/twobrain_rec_server/processing/store.py`
- [x] T012 Add import/restart/deletion-fence tests proving duplicate delivery does not regress artifacts or resurrect deleted content in `apps/server/tests/integration/test_processing_result_idempotency.py`
- [x] T013 Extend the content-safe processing status contract with server time, retry class, next attempt, manual action, in-flight state and independent artifact projections in `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/processing/status.py`
- [x] T014 Add status projection contract tests for authorization, hidden provider metadata, artifact independence and refresh-safe timestamps in `apps/server/tests/contract/test_processing_status_contract.py`
- [x] T015 Add atomic command-claim and active-attempt/provider-job fences to the processing store without introducing a second retry service in `apps/server/src/twobrain_rec_server/processing/store.py`
- [x] T016 Add the new stage-oriented Temporal activity boundaries, durable retry state and workflow versioning seam in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [x] T017 Add Temporal time-skipping, replay, payload-size, cancellation and worker-restart tests in the installed-SDK workflow contract suite `apps/server/tests/unit/test_processing_temporal_workflow.py`

## Phase 3: User Story 1 - Расшифровка после диаризации (Priority: P1) 🎯 MVP

**Goal**: Show the ordinary transcript only when the matching transcript and
diarization are ready, while keeping summary and other artifacts independent.

**Independent test**: A result with transcript plus diarization shows text
while summary is running/failed/unavailable; transcript-only or mismatched
diarization keeps text hidden and explains the next step.

- [x] T018 [P] [US1] Add projection tests for transcript-only, same-attempt diarization, mismatched revision and every summary state in `apps/server/tests/unit/test_cabinet_view_models.py`
- [x] T019 [P] [US1] Add browser/contract assertions that transcript, search and export stay hidden before confirmed diarization in the existing cabinet accessibility and export contract suites
- [x] T020 [US1] Enforce the same-attempt transcript-plus-diarization visibility invariant in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [x] T021 [US1] Separate summary loading/failure copy and actions from transcript availability in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [x] T022 [US1] Render clear pending-diarization, summary-independent and no-recognizable-speech states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [x] T023 [US1] Preserve the same artifact truth on browser and embedded desktop meeting surfaces through the shared cabinet projection and desktop sync response
- [x] T024 [US1] Add transcript visibility, summary independence and embedded-surface regression coverage in `apps/server/tests/unit/test_cabinet_view_models.py`, `apps/server/tests/integration/test_cabinet_meeting_detail.py`, `apps/server/tests/integration/test_transcript_export_egress.py` and `apps/server/tests/contract/test_recording_workflow_accessibility.py`

## Phase 4: User Story 2 - Понятное ожидание и ручная проверка (Priority: P1)

**Goal**: Persist the next automatic check, display a trustworthy countdown and
let the user check the same provider job immediately without duplicate work.

**Independent test**: A retryable fake response creates one durable schedule;
manual action claims it once, disables duplicate clicks, suppresses the old
timer and derives the next state from the server response.

- [x] T025 [P] [US2] Add unit tests for schedule-generation races, two tabs, double click, in-flight operation and manual override in the recovery and Temporal contract suites
- [x] T026 [P] [US2] Add API tests for authorization, CSRF, idempotent manual check and safe user-facing projection in the existing processing status and cabinet API contract suites
- [x] T027 [US2] Add the authenticated manual `check processing` endpoint and route it through the atomic store/workflow fence in `apps/server/src/twobrain_rec_server/api/processing.py` and `apps/server/src/twobrain_rec_server/processing/store.py`
- [x] T028 [US2] Implement the Temporal manual Update or compatible fallback signal so it checks the existing job/key once and returns a safe projection in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [x] T029 [US2] Replace provider polling `asyncio.sleep` with durable workflow timers and bounded activity retry policies in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [x] T030 [US2] Add countdown, server-time offset, refresh/background-tab handling, disabled/busy states and polite live-region announcements in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [x] T031 [US2] Add responsive, reduced-motion, forced-colors and focus-preserving styles for recovery status and manual action in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [x] T032 [US2] Render localized recovery copy, exact-time only when trustworthy, countdown data attributes and `Проверить обработку` action in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [x] T033 [US2] Add keyboard, screen-reader, refresh, race and no-per-second-polling browser coverage in the existing recording workflow accessibility contract suite

## Phase 5: User Story 3 - Безопасное восстановление неопределённой и terminal-ошибки (Priority: P1)

**Goal**: Reconcile unknown upload outcomes with the same key/body, stop blind
re-uploads, give terminal failures a concrete next path and keep deletion truth
honest.

**Independent test**: Lost POST response creates no duplicate provider job;
same-key conflict blocks recovery; terminal failure has no countdown; deletion
202 remains pending until receipt.

- [x] T034 [P] [US3] Add same-key reconciliation and changed-body conflict tests in the processing failure and worker-restart integration suites
- [x] T035 [US3] Implement submit/reconcile state transitions using the original request fingerprint and idempotency key in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [x] T036 [P] [US3] Add terminal failure/new explicit attempt tests and ensure a new provider job requires terminal evidence and user action in the processing failure, status and cabinet projection suites
- [x] T037 [US3] Expose an explicit, authorized new-attempt action only for safely closed terminal failures in `apps/server/src/twobrain_rec_server/api/processing.py` and `apps/server/src/twobrain_rec_server/processing/store.py`
- [x] T038 [P] [US3] Add deletion 200/202/receipt and late-result fence tests in the deletion and transcript-export integration suites
- [x] T039 [US3] Reconcile MediaScribe cancellation/deletion receipts and keep provider `202 cancelling` out of completed user state in `apps/server/src/twobrain_rec_server/processing/deletion.py` and `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [x] T040 [US3] Add restart-at-every-stage and no-dead-end support handoff coverage in `apps/server/tests/integration/test_processing_worker_restart.py` and the existing safe support/status projection suites

## Phase 6: User Story 4 - Полный и восстанавливаемый MediaScribe v1 результат (Priority: P2)

**Goal**: Use the expanded v1 API to its safe extent without leaking provider
details or making optional capabilities a hard dependency.

**Independent test**: Contract fixtures cover capabilities/version, single and
dual upload, list cursor, status/result/summary, authenticated downloads,
forward-compatible fields and deletion.

- [x] T041 [P] [US4] Add runtime capability/version snapshot tests and safe degradation for missing optional features in the MediaScribe v1/client contract suites
- [x] T042 [US4] Implement capabilities/version caching, list cursor recovery and active-job admission in `apps/server/src/twobrain_rec_server/mediascribe/client.py` and `apps/server/src/twobrain_rec_server/processing/submit.py`
- [x] T043 [US4] Implement server-side authenticated artifact download resolution without persisting signed URLs in `apps/server/src/twobrain_rec_server/mediascribe/downloads.py` and `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [x] T044 [P] [US4] Add result normalization tests for timing, source roles, acoustic turns, overlap intervals, provenance and unknown fields in the existing result-import and MediaScribe v1 contract suites
- [x] T045 [US4] Preserve the v1 result metadata through import and user-safe projection in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py`, `apps/server/src/twobrain_rec_server/processing/submit.py` and `apps/server/src/twobrain_rec_server/processing/store.py`

## Phase 7: Polish, analytics, security and validation

**Purpose**: Close cross-cutting gates and leave evidence for every required
scenario; do not add a provider console, webhook layer or second retry service.

- [x] T046 [P] Add allowlisted aggregate events for first usable result, retry request/outcome, reconciliation, artifact availability and support handoff in `apps/server/src/twobrain_rec_server/processing/audit.py` and `apps/server/src/twobrain_rec_server/api/product_analytics.py`
- [x] T047 [P] Add no-secret/no-content and server-only egress regression checks for browser, desktop, logs, analytics and Temporal payloads in the existing processing status, cabinet egress and client contract suites
- [x] T048 [P] Add an operator-safe status/metrics view for retryable failures, stale workflows, duplicate-job invariant and queue fairness buckets in `apps/server/src/twobrain_rec_server/admin/metrics.py` and `apps/server/src/twobrain_rec_server/admin/templates/admin/metrics.html`
- [x] T049 Update `specs/195-processing-recovery/checklists/infra.md`, `specs/195-processing-recovery/checklists/security.md`, `specs/195-processing-recovery/checklists/ux.md` and `specs/195-processing-recovery/checklists/requirements.md` only with observed implementation evidence
- [x] T050 Add Feature 195 behavior, compatibility, known limitations and validation evidence to `CHANGELOG.md` and `specs/195-processing-recovery/quickstart.md`
- [x] T051 Run the full quickstart matrix, focused tests, `git diff --check` and `infra/scripts/ci-local.sh`; record failures and limits in `specs/195-processing-recovery/quickstart.md`

## Completion evidence notes

Some planned filenames were consolidated into the existing processing suites
to avoid duplicate fixture layers. The evidence is still executable and
covered by the full collection:

- T012/T034/T038/T040: `tests/integration/test_processing_result_idempotency.py`,
  `tests/integration/test_processing_worker_restart.py`,
  `tests/integration/test_processing_failures.py` and
  `tests/integration/test_transcript_export_egress.py`.
- T014/T019/T025/T026/T033/T047: existing processing status,
  accessibility, MediaScribe client contract and recovery contract suites,
  plus `tests/unit/test_processing_recovery_contracts.py`.
- T017/T028/T029: `tests/unit/test_processing_temporal_workflow.py` with
  time-skipping, replay, signal/update, cancellation and payload-boundary
  assertions.
- T018/T024/T041/T044: existing cabinet view-model, result-import and v1
  client contract suites; the focused recovery run includes the bounded
  provenance/download regression.
- T046/T048: allowlisted aggregate-event validation and the existing admin
  metrics API/view suites; live dashboard delivery remains out of scope.

## Dependencies and execution order

- Phase 1 has no code dependencies and can run in parallel.
- Phase 2 blocks all user stories. T004/T005 precede any database projection;
  T006–T008 precede retry code; T009–T012 precede provider workflow changes;
  T013–T017 precede API/UI and Temporal integration.
- US1 and US2 can be developed in parallel after Phase 2, but share the status
  projection and must be integrated before UI validation. US3 depends on the
  provider error/idempotency primitives from Phase 2. US4 can run alongside
  US3 once the adapter boundary is stable.
- Phase 7 starts only after all selected user stories pass their independent
  tests. T051 is the closeout gate and does not authorize deployment.

## Parallel execution examples

- Phase 2: T006, T007, T008, T009 and T010 touch disjoint modules/tests and can
  proceed in parallel after the migration/model shape is agreed.
- US1: T018 and T019 can run in parallel before T020–T024.
- US2: T025 and T026 can run in parallel before T027–T033.
- US3: T034, T036 and T038 can run in parallel before their implementation
  tasks.
- US4: T041 and T044 can run in parallel before T042–T045.

## Implementation strategy

1. Ship the smallest safe MVP as US1: visibility invariant plus independent
   summary state, backed by the foundational additive projection.
2. Add US2 recovery controls and durable timer/update semantics before exposing
   retryable failures to ordinary users.
3. Add US3 reconciliation/deletion fences before enabling any new-attempt path.
4. Complete US4 and cross-cutting gates, then run the repository validation lane.
5. Keep all provider credentials, raw payloads, signed URLs and content out of
   client responses, logs, analytics and Temporal history.

## Requirement and success-criteria traceability

| Requirement | Tasks |
|---|---|
| FR-001 | T005, T013, T020–T022 |
| FR-002–FR-003 | T018–T024 |
| FR-004–FR-008 | T006–T010, T025–T033 |
| FR-009 | T005, T009, T013, T047 |
| FR-010–FR-011 | T034–T037 |
| FR-012–FR-015 | T003, T006, T009–T012, T041–T045, T047 |
| FR-016–FR-017 | T005, T012, T016–T017, T040, T046–T048 |
| FR-018–FR-020 | T023, T038–T040 |
| FR-021 | T030–T033 |
| FR-022 | T046–T048 |
| SC-001–SC-002 | T018–T024 |
| SC-003–SC-004 | T007–T010, T025–T033 |
| SC-005–SC-008 | T012, T017, T034–T040 |
| SC-009 | T003, T009–T010, T041–T045, T047 |
| SC-010 | T046–T048 |
