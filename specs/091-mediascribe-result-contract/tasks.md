# Tasks: MediaScribe Result Contract

**Input**: Design documents from `/specs/091-mediascribe-result-contract/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/mediascribe-result-contract.md](./contracts/mediascribe-result-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Required. This is a high-risk feature touching MediaScribe, processing, outcomes, diagnostics, schema, and user-facing unavailable states.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Confirm high-risk lane and contract artifacts.

- [X] T001 [P] Record high-risk MediaScribe result-contract lane in `specs/091-mediascribe-result-contract/plan.md`
- [X] T002 [P] Add MediaScribe result contract and validation quickstart in `specs/091-mediascribe-result-contract/contracts/mediascribe-result-contract.md` and `specs/091-mediascribe-result-contract/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Schema and safe metadata support used by all stories.

### Tests

- [X] T003 [P] Add migration/model coverage for processing and outcome failure source fields in `apps/server/tests/integration/test_processing_migrations.py`
- [X] T004 [P] Add diagnostic allowlist coverage for new safe metadata keys in `apps/server/tests/contract/test_rls_evidence_contract.py`

### Implementation

- [X] T005 Add nullable failure metadata columns in `apps/server/src/twobrain_rec_server/db/migrations/versions/0018_mediascribe_result_contract.py`
- [X] T006 Add failure metadata fields to `apps/server/src/twobrain_rec_server/db/models/processing.py` and `apps/server/src/twobrain_rec_server/db/models/outcomes.py`
- [X] T007 Add result-contract reason/source constants and audit allowlist keys in `apps/server/src/twobrain_rec_server/processing/reasons.py` and `apps/server/src/twobrain_rec_server/processing/audit.py`

**Checkpoint**: Storage and diagnostics can represent source/reason without content leakage.

---

## Phase 3: User Story 1 - Import Available Transcript (Priority: P1)

**Goal**: Ready/available MediaScribe results import transcript rows and permit outcomes.

**Independent Test**: A mocked ready/available result imports transcript, sets `transcript_status="available"`, counts segments, and generates outcomes.

### Tests

- [X] T008 [P] [US1] Add client parsing coverage for `transcript_status="available"` and absent downloads in `apps/server/tests/contract/test_mediascribe_client_contract.py`
- [X] T009 [P] [US1] Add processing import assertions for available transcript status and segment count in `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`

### Implementation

- [X] T010 [US1] Parse result `transcript_status` and `transcript_reason` in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py` and `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [X] T011 [US1] Persist processing result transcript status from the new contract in `apps/server/src/twobrain_rec_server/processing/store.py`
- [X] T012 [US1] Keep available-result audit metadata explicit in `apps/server/src/twobrain_rec_server/processing/submit.py`

**Checkpoint**: US1 remains independently usable for normal transcript review.

---

## Phase 4: User Story 2 - Processed No Transcript (Priority: P1)

**Goal**: Ready/unavailable no-speech is a processed business outcome, not a MediaScribe outage.

**Independent Test**: A mocked ready/unavailable result creates unavailable processing, blocked outcomes, exact UI copy, and no transcript download action.

### Tests

- [X] T013 [P] [US2] Add no-recognizable-speech import and audit assertions in `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- [X] T014 [P] [US2] Add blocked outcome reason/source assertions in `apps/server/tests/integration/test_meeting_outcomes_generation.py`
- [X] T015 [P] [US2] Add cabinet copy/download state assertions in `apps/server/tests/unit/test_cabinet_view_models.py`

### Implementation

- [X] T016 [US2] Normalize ready/unavailable no-speech results without importing transcript rows in `apps/server/src/twobrain_rec_server/mediascribe/import_results.py`
- [X] T017 [US2] Persist processed-no-transcript result, workflow, dependency, and audit state in `apps/server/src/twobrain_rec_server/processing/store.py` and `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T018 [US2] Copy input-audio failure reason/source into blocked outcomes in `apps/server/src/twobrain_rec_server/outcomes/service.py` and `apps/server/src/twobrain_rec_server/outcomes/store.py`
- [X] T019 [US2] Show no-recognizable-speech copy and hide transcript download actions in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/egress.py`, and `apps/server/src/twobrain_rec_server/admin/files.py`

**Checkpoint**: US2 is terminal and non-service-error.

---

## Phase 5: User Story 3 - Failed Job Origin Classification (Priority: P1)

**Goal**: Failed MediaScribe jobs distinguish invalid input audio from service-origin problems.

**Independent Test**: Failed invalid-audio jobs persist input-audio metadata and service-origin failures keep existing failure status behavior.

### Tests

- [X] T020 [P] [US3] Add failed poll parsing coverage for `error_code` and `error_origin` in `apps/server/tests/contract/test_mediascribe_client_contract.py`
- [X] T021 [P] [US3] Add invalid-audio and service-origin failed-job processing assertions in `apps/server/tests/integration/test_processing_failures.py`

### Implementation

- [X] T022 [US3] Parse poll `error_code` and `error_origin` in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py` and `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [X] T023 [US3] Classify invalid input audio as a terminal business outcome in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T024 [US3] Preserve MediaScribe service failure behavior and diagnostics in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T025 [US3] Show invalid-audio copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`

**Checkpoint**: US3 prevents false MediaScribe outage signals for invalid input.

---

## Phase 6: User Story 4 - Diagnostics And Download Truth (Priority: P2)

**Goal**: Safe diagnostics distinguish event classes, and unavailable transcript download state remains disabled.

**Independent Test**: Processing audit rows keep safe metadata keys for each terminal class, and download states require stored available transcript rows.

### Tests

- [X] T026 [P] [US4] Add audit metadata assertions for processed/no-transcript and failure-origin events in `apps/server/tests/integration/test_processing_audit.py`
- [X] T027 [P] [US4] Add transcript artifact class/download guard assertions in `apps/server/tests/unit/test_artifact_egress_audit.py` or `apps/server/tests/unit/test_cabinet_view_models.py`

### Implementation

- [X] T028 [US4] Emit `processed_no_transcript`, `input_audio_problem`, and `mediascribe_service_problem` audit/log classes in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T029 [US4] Ensure download availability checks require stored available transcript rows in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/admin/files.py`

**Checkpoint**: US4 is safe for operators without private content leakage.

---

## Phase 7: Polish, Validation, And Closeout

- [X] T030 [P] Update behavior notes in `CHANGELOG.md`
- [X] T031 [P] Run forbidden-content scan from `specs/091-mediascribe-result-contract/quickstart.md`
- [X] T032 Run focused validation from `specs/091-mediascribe-result-contract/quickstart.md`
- [X] T033 Run full local CI with `infra/scripts/ci-local.sh`
- [X] T034 Mark completed tasks `[X]` only after validation evidence passes in `specs/091-mediascribe-result-contract/tasks.md`
- [X] T035 Record high-risk validation lane, GitHub issue links, focused evidence, CI evidence, and no-deploy status in `specs/091-mediascribe-result-contract/tasks.md` closeout notes and the final response or PR

---

## Dependencies & Execution Order

- Phase 1 has no dependencies.
- Phase 2 blocks all user stories.
- US1, US2, and US3 depend on Phase 2.
- US4 depends on audit/download behavior from US1-US3.
- Phase 7 depends on all implemented user stories.

## Parallel Opportunities

- T003-T004 can run in parallel.
- T008-T009 can run in parallel after Phase 2.
- T013-T015 can run in parallel after US1 foundations.
- T020-T021 can run in parallel after Phase 2.
- T026-T027 can run in parallel after diagnostic hooks exist.
- T030-T031 can run in parallel after implementation.

## Analyze Result

Manual `$speckit-analyze` pass on 2026-07-07: no critical blockers found.

- Spec, plan, data model, contract, checklist, and tasks all identify high-risk MediaScribe/diagnostics behavior.
- Tasks are dependency ordered and use exact file paths.
- No unresolved clarification remains because the user supplied the new contract values, business outcome behavior, UI copy, and diagnostic fields.
- Release/deploy remains out of scope.

## Notes

- `[P]` means different files or no dependency on incomplete tasks.
- Implementation commits require explicit user approval after validation.
- No production deploy is part of this task list.
- GitHub tracking created through `$speckit-taskstoissues` equivalent:
  #2654 for contract/schema foundation and US1, #2656 for processed-no-transcript
  outcomes, #2655 for failed-job origin classification, and #2657 for
  diagnostics/download truth and closeout validation.

## Closeout Evidence

- Risk/validation lane: high-risk feature. The change touches MediaScribe,
  processing/outcomes, diagnostics, Postgres schema, and user-facing
  unavailable states.
- GitHub tracking: #2654, #2655, #2656, and #2657. Corrective closure
  comments were added to #2655 and #2656 after their closeout texts were
  initially swapped during parallel issue closure.
- Focused contract/processing/outcome/UI validation:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_mediascribe_processing_happy_path.py tests/integration/test_processing_failures.py tests/integration/test_meeting_outcomes_generation.py tests/unit/test_cabinet_view_models.py tests/unit/test_notes_action_truth_view_models.py tests/integration/test_processing_migrations.py tests/integration/test_postgres_migrations.py`
  passed with `47 passed, 1 warning`.
- Quickstart focused validation:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_mediascribe_processing_happy_path.py tests/integration/test_processing_failures.py tests/integration/test_meeting_outcomes_generation.py tests/unit/test_cabinet_view_models.py tests/unit/test_notes_action_truth_view_models.py`
  passed with `39 passed, 1 warning`.
- Migration check:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_processing_migrations.py tests/integration/test_postgres_migrations.py`
  passed with `8 passed, 1 warning`.
- Direct processing audit validation:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_processing_audit.py`
  passed with `2 passed, 1 warning`.
- Post-review remediation validation:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/unit/test_mediascribe_result_import.py tests/integration/test_processing_result_idempotency.py tests/integration/test_processing_failures.py tests/integration/test_mediascribe_processing_happy_path.py`
  passed with `22 passed, 1 warning`, covering nested `job.error_code` /
  `job.error_origin`, explicit unavailable status authority, and persistence of
  `result.transcript_status` independent of row count. Touched-file Ruff check
  also passed.
- Second-review remediation validation:
  `uv run --directory apps/server ruff check src/twobrain_rec_server/mediascribe/schemas.py src/twobrain_rec_server/processing/audit.py src/twobrain_rec_server/processing/status.py tests/contract/test_mediascribe_client_contract.py tests/contract/test_rls_evidence_contract.py tests/contract/test_processing_status_contract.py`
  passed. `PYTHONPATH=src uv run --directory apps/server pytest -q tests/contract/test_mediascribe_client_contract.py tests/contract/test_rls_evidence_contract.py tests/contract/test_processing_status_contract.py`
  passed with `19 passed, 1 warning`, covering strict safe
  `transcript_status` / `transcript_reason`, audit redaction for unknown
  reasons, and row-count guards for the processing status API.
- Current-master sync validation on 2026-07-09:
  the feature was replayed onto `origin/master` at `d419b5a` after later
  product analytics and meeting detection releases. The only code conflict was
  `apps/server/src/twobrain_rec_server/cabinet/view_models.py`; the resolution
  kept the current `mediascribe_validation_failed` copy and added the new
  `no_recognizable_speech` / `invalid_audio_payload` labels. The migration was
  renumbered from `0017_mediascribe_result_contract.py` to
  `0018_mediascribe_result_contract.py` with
  `down_revision="0017_meeting_detection"` to avoid a multi-head Alembic
  chain.
- Current-master focused validation:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_mediascribe_processing_happy_path.py tests/integration/test_processing_failures.py tests/integration/test_meeting_outcomes_generation.py tests/unit/test_cabinet_view_models.py tests/unit/test_notes_action_truth_view_models.py tests/contract/test_processing_status_contract.py tests/contract/test_rls_evidence_contract.py tests/unit/test_mediascribe_result_import.py tests/integration/test_processing_result_idempotency.py tests/integration/test_processing_audit.py tests/unit/test_artifact_egress_audit.py`
  passed with `71 passed, 1 warning`. Migration sync validation
  `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_processing_migrations.py tests/integration/test_postgres_migrations.py tests/integration/test_meeting_detection_migrations.py`
  passed with `11 passed, 1 warning`.
- Forbidden-content scan from `quickstart.md` completed. Matches were reviewed
  as code identifiers, synthetic test keys/buckets, fake MinIO helpers, and
  existing no-secret test strings; no live secrets, signed URLs, raw audio, raw
  transcript text, object keys with private values, or private meeting content
  were identified.
- Full local CI:
  `infra/scripts/ci-local.sh` passed after current-master sync with
  `ci_local_result=pass`; server tests reported `1177 passed, 4 skipped,
  1 warning`, server lint passed, Python compile completed, production compose
  config rendered, and deployment evidence scan passed. The RLS helper reported
  the expected local boundary `postgres_test_database_required` while the CI
  script completed successfully.
- Production deploy/smoke was not run for this implementation slice.
