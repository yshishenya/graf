# Tasks: MediaScribe v0.5.3 integration fidelity

**Input**: Design documents from `/specs/203-mediascribe-v053-integration/`

**Risk lane**: `high-risk-feature`. This slice touches MediaScribe, Temporal, PostgreSQL, tenant-scoped result storage and user-visible degraded states. Focused tests, high-risk checklists, `git diff --check` and `infra/scripts/ci-local.sh` are required before closeout. No deployment is part of this task list.

## Phase 1: Contract and regression fixtures

- [X] T001 [P] [US1] Add v0.5.3 WordItem, block-boundary, source-role and incomplete-timestamp fixtures without private content in `apps/server/tests/fakes/mediascribe_v1.py`.
- [X] T002 [P] [US3] Update capabilities fixture speaker modes from legacy values to `exact`/`max` and add queue/retry terminal states in `apps/server/tests/fakes/mediascribe_v1.py`.
- [X] T003 [P] [US4] Add client contract tests for valid/invalid words, nullable words, omitted source_role and forward-compatible fields in `apps/server/tests/contract/test_mediascribe_client_contract.py`.

## Phase 2: Foundational provider boundary and storage

- [X] T004 [P] [US1] Add typed `MediaScribeWordItem` and `words` to `MediaScribeDiarizationSegment` with safe validation in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py`.
- [X] T005 [US1] Validate word structure at the provider trust boundary while preserving full segment text in `apps/server/src/twobrain_rec_server/mediascribe/client.py`.
- [X] T006 [US1] Normalize omitted single-track source_role to `mixed`, keep dual-track omission degraded/unknown, and update `apps/server/src/twobrain_rec_server/mediascribe/client.py` and `apps/server/src/twobrain_rec_server/mediascribe/import_results.py`.
- [X] T007 [P] [US4] Add nullable `words_json` to `DiarizationSegment` and an additive migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0081_mediascribe_words.py` with downgrade safety.
- [X] T008 [US4] Persist validated words through the existing result lineage and deletion path in `apps/server/src/twobrain_rec_server/processing/store.py`.
- [X] T009 [P] [US1] Add result-import tests proving exact provider block count/boundaries, source-role separation, text conservation and words persistence in `apps/server/tests/unit/test_mediascribe_result_import.py` and `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`.

## Phase 3: User Story 1 - Provider-owned blocks (Priority: P1)

- [X] T010 [US1] Audit and adjust canonical speaker projection so it preserves provider block rows and never merges/splits them in `apps/server/src/twobrain_rec_server/domain/speaker_turns.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.
- [X] T011 [P] [US1] Add regression coverage for return-after-speaker, long pause, punctuation/UNKNOWN, dual-track overlap and incomplete words in `apps/server/tests/unit/test_canonical_speaker_turns.py` and `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T012 [US1] Verify structured exports and embedded/browser projections preserve the same block count/source-role semantics, while human-readable heading grouping keeps every provider block as a separate child line, in `apps/server/tests/unit/test_transcript_exports.py`, `apps/server/tests/integration/test_transcript_export_egress.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`.

## Phase 4: User Story 2 - Independent transcript and summary (Priority: P1)

- [X] T013 [P] [US2] Extend summary matrix tests for null/running/ready/failed summary alongside ready diarization in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`.
- [X] T014 [US2] Confirm no result-import or projection path makes summary a prerequisite for transcript in `apps/server/src/twobrain_rec_server/processing/results.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/egress.py`.

## Phase 5: User Story 3 - Durable recovery and Temporal compatibility (Priority: P1)

- [X] T015 [P] [US3] Add provider `retrying`, `next_retry_at`, terminal error and Retry-After contract cases in `apps/server/tests/contract/test_mediascribe_client_contract.py` and `apps/server/tests/unit/test_processing_recovery_contracts.py`.
- [X] T016 [US3] Reuse/adjust existing durable timer and provider-hint schedule integration in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`, `apps/server/src/twobrain_rec_server/workflows/worker.py` and `apps/server/src/twobrain_rec_server/processing/submit.py` only where v0.5.3 evidence shows a gap.
- [X] T017 [US3] Add replay/restart/manual-check race coverage proving one job and one active schedule in `apps/server/tests/unit/test_processing_temporal_workflow.py` and `apps/server/tests/integration/test_processing_worker_restart.py`.
- [X] T018 [US3] Re-run status/UI parity tests for countdown reset, terminal no-countdown and no-dead-end recovery in `apps/server/tests/contract/test_processing_status_contract.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.

## Phase 6: User Story 4 and cross-cutting closeout

- [X] T019 [P] [US4] Preserve allowlisted v0.5.3 provenance fields and distinguish provider degradation from GRAF malformed-result failure in `apps/server/src/twobrain_rec_server/processing/store.py` and `apps/server/src/twobrain_rec_server/mediascribe/schemas.py`.
- [X] T020 [P] [US4] Add no-secret/no-content and workspace-lineage regression assertions for words, logs, analytics and Temporal payloads in the existing contract suites.
- [X] T021 [P] Update Feature 203 checklists and `CHANGELOG.md` only with observed implementation/validation evidence.
- [X] T022 Run Feature 203 quickstart, focused suites, `git diff --check` and `infra/scripts/ci-local.sh`; record all incomplete/environment-gated checks in `specs/203-mediascribe-v053-integration/quickstart.md`.

## Dependencies and execution order

- Phase 1 precedes boundary implementation. T004–T006 and T007–T008 are foundational before import/projection changes.
- US1 and US2 can proceed after foundational work. US3 reuses the Feature 195 workflow and should only change code where v0.5.3 tests expose a gap.
- T016 is deliberately conditional: no Temporal rewrite is justified if existing provider hint/timer behavior passes the v0.5.3 matrix.
- T022 is the closeout gate and does not authorize commit, merge, release or deployment.

## Traceability

| Requirement | Tasks |
|---|---|
| FR-001 | T001, T009–T012 |
| FR-002 | T003, T006, T009–T012 |
| FR-003 | T003, T006, T009–T012 |
| FR-004 | T001, T003–T005, T009–T011 |
| FR-005 | T001, T003–T005, T009–T011 |
| FR-006 | T007–T009, T019–T020 |
| FR-007 | T013–T014 |
| FR-008 | T015–T018 |
| FR-009 | T015–T018 |
| FR-010 | T015–T018 |
| FR-011 | T019–T022 |
| FR-012 | T019–T022 |
| SC-001 | T001, T003–T005, T009 |
| SC-002 | T009–T012 |
| SC-003 | T003, T006, T009 |
| SC-004 | T015–T018 |
| SC-005 | T013–T014 |
| SC-006 | T019–T022 |
