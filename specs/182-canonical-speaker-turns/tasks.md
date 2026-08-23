# Tasks: Canonical Provider Speaker Turns

**Input**: Design documents from `/specs/182-canonical-speaker-turns/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, and completed high-risk checklists

**Tests**: Tests precede implementation because this is a high-risk transcription/data-contract change.

## Phase 1: Setup and baseline

- [X] T001 Record the high-risk lane, no-commit/no-deploy gate, production SHA, active branch, and GRAF-only boundary in `specs/182-canonical-speaker-turns/plan.md`
- [X] T002 [P] Complete requirements, transcription-contract, diagnostics/privacy, and provider-boundary checklists in `specs/182-canonical-speaker-turns/checklists/`
- [X] T003 Ensure and validate the repository GitHub issue canon, then sync these executable tasks to Russian issues without optional commit hooks

---

## Phase 2: Foundational canonical contract

**Purpose**: One pure, deterministic model blocks every consumer change.

- [X] T004 [P] Add failing 2-turn, 3-turn, below-50-percent, 1/2/11-label, exact-time, idempotence, and linear-scan guard tests in `apps/server/tests/unit/test_canonical_speaker_turns.py`
- [X] T005 [P] Add failing malformed-result tests for non-positive time, chronology, 40 ms unknown, triplicated full text, and text conservation in `apps/server/tests/unit/test_mediascribe_result_import.py`
- [X] T006 Implement bounded provider-contract diagnostics in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py` and `apps/server/src/twobrain_rec_server/mediascribe/import_results.py`
- [X] T007 Implement the shared canonical speaker model, stable provider identity, accepted/degraded projections, and talk-time denominator in `apps/server/src/twobrain_rec_server/domain/speaker_turns.py`
- [X] T008 Persist allowlisted metadata-only import diagnostics and defect ownership through `apps/server/src/twobrain_rec_server/processing/audit.py`, `apps/server/src/twobrain_rec_server/processing/store.py`, and `apps/server/src/twobrain_rec_server/processing/submit.py`

**Checkpoint**: Synthetic production defect classes fail closed without guessed repair.

---

## Phase 3: User Story 1 - Review faithful speaker turns (Priority: P1)

**Goal**: Review transcript uses provider turns and never assigns a whole ASR segment to one overlap winner.

**Independent Test**: Two/three valid provider turns remain separate with exact keys, text, and boundaries.

- [X] T009 [US1] Add failing review API and transcript/timeline tests for accepted provider turns in `apps/server/tests/unit/test_cabinet_view_models.py`
- [X] T010 [US1] Route `transcript_state` and `speaker_state` through the shared canonical model and remove the legacy winner, derived-turn, and ordinal-label projections from `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T011 [US1] Expose provider key, canonical result state, unknown copy, and the `Доля распознанной речи` label through `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

**Checkpoint**: Review and timeline independently preserve provider truth.

---

## Phase 4: User Story 2 - Truthful degraded results (Priority: P1)

**Goal**: Structurally unsafe provider attribution becomes one uncertain ASR representation everywhere; a tiny explicit unknown remains isolated without hiding valid confirmed turns.

**Independent Test**: Triplicated text becomes one uncertain ASR copy; a 40 ms unknown creates neither repeated text nor an extra participant and leaves valid confirmed turns intact.

- [X] T012 [US2] Add failing degraded review/timeline tests in `apps/server/tests/unit/test_cabinet_view_models.py`
- [X] T013 [US2] Apply one degraded state/reason to review and timeline projections in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T014 [US2] Add safe diagnostic contract/redaction tests in `apps/server/tests/contract/test_processing_status_contract.py` and `apps/server/tests/contract/test_transcript_export_no_secret_egress.py`

**Checkpoint**: Degraded content is visible once and diagnostics contain no content.

---

## Phase 5: User Story 3 - Stable speaker identity (Priority: P1)

**Goal**: Names bind to stable provider identities, while unknown identities cannot be renamed.

**Independent Test**: Renumbering display order never moves a saved name.

- [X] T015 [US3] Add failing stable-name, legacy ambiguity, and unknown-rename tests in `apps/server/tests/integration/test_speaker_names.py`
- [X] T016 [US3] Resolve names by stable key, migrate only provable current-result legacy names, and reject non-confirmed rename keys in `apps/server/src/twobrain_rec_server/domain/speaker_turns.py`, `apps/server/src/twobrain_rec_server/cabinet/speakers.py`, `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/speakers.py`, and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`

**Checkpoint**: User names cannot silently rebind to another provider identity.

---

## Phase 6: User Story 4 - One model for every consumer (Priority: P2)

**Goal**: Review, timeline, exports, and outcomes use the same ordered turns and degraded state.

**Independent Test**: A parity fixture produces the same authoritative tuple across every consumer and ingest path.

- [X] T017 [P] [US4] Add failing Markdown/CSV/XLSX/JSON/SRT/VTT parity and rounding tests in `apps/server/tests/unit/test_transcript_exports.py`
- [X] T018 [P] [US4] Add failing normal-recording/manual-upload and downstream outcomes parity tests in `apps/server/tests/integration/test_meeting_outcomes_generation.py` and `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- [X] T019 [US4] Replace independent export reconstruction with the shared canonical model and add VTT in `apps/server/src/twobrain_rec_server/cabinet/exports.py`
- [X] T020 [US4] Add VTT to request/UI format contracts in `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T021 [US4] Replace independent outcome reconstruction with the shared canonical model and keep unambiguous legacy source links readable in `apps/server/src/twobrain_rec_server/outcomes/service.py` and `apps/server/src/twobrain_rec_server/api/cabinet.py`

**Checkpoint**: All requested consumers and both ingest histories are semantically identical.

---

## Phase 7: User Story 5 - Diagnose without private content (Priority: P2)

**Goal**: Support can distinguish provider and GRAF defects using metadata only.

**Independent Test**: Import audit contains every required field and no forbidden field/value.

- [X] T022 [US5] Add import provenance extraction tests in `apps/server/tests/unit/test_mediascribe_result_import.py` and `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- [X] T023 [US5] Preserve available provider version metadata in `apps/server/src/twobrain_rec_server/mediascribe/client.py` and emit bounded attribution diagnostics in `apps/server/src/twobrain_rec_server/processing/submit.py`

**Checkpoint**: Diagnostics identify defect origin without storing meeting content.

---

## Phase 8: Validation and closeout

- [X] T024 Run all focused unit/contract/PostgreSQL commands in `specs/182-canonical-speaker-turns/quickstart.md`
- [X] T025 Run the `high-risk-feature` repository gate `infra/scripts/ci-local.sh --fast`
- [X] T026 Re-run Spec Kit analyze and all high-risk checklist gates after implementation
- [X] T027 Reconcile completed tasks with GitHub issues using Russian status comments; do not close incomplete tasks or create a PR
- [X] T028 Inspect `git diff --check`, scan for forbidden content, prove no external MediaScribe/config/deploy change, and stop without commit or deploy
- [ ] T029 After all preceding validation is clean, run `infra/scripts/ci-local.sh --full` once and stop without commit or deploy

## Dependencies and execution order

- T001-T003 precede implementation.
- T004-T008 are foundational; T006/T007/T008 follow their failing tests.
- US1-US3 depend on the shared canonical model and may then be validated independently.
- US4 depends on US1/US2 semantics; US5 depends on foundational diagnostics.
- T024-T029 require all implemented story tasks; T029 runs last.

## Parallel opportunities

- T004 and T005 touch different test files.
- T017 and T018 touch unit and integration suites separately.
- No implementation task is marked parallel where it shares the canonical model or API contract.
