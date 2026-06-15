# Tasks: Meeting Dashboard Review

**Input**: Design documents from `/specs/016-meeting-dashboard-review/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are required for this feature because the spec requires contract, privacy, RLS, UI-state, and no-secret/no-content evidence before implementation is accepted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Establish shared files for the server-owned cabinet surface.

- [ ] T001 Create the cabinet package marker in `apps/server/src/twobrain_rec_server/cabinet/__init__.py`
- [ ] T002 [P] Create cabinet test fixture helpers for seeded ready/processing/failed/foreign meetings in `apps/server/tests/fixtures/cabinet.py`
- [ ] T003 [P] Add the feature validation evidence placeholder in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

---

## Phase 2: Foundational

**Purpose**: Shared schemas, state mapping, and route skeletons that all stories depend on.

**Critical**: No user story implementation begins until this phase is complete.

- [ ] T004 Add cabinet Pydantic response schemas and enums in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T005 [P] Implement content-safe status, governance, timestamp, and source-role mapping helpers in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T006 [P] Implement cabinet database query function skeletons in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T007 [P] Implement cabinet HTML shell helpers and shared CSS tokens in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T008 Add the cabinet API router skeleton in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T009 Register cabinet API and web routers in `apps/server/src/twobrain_rec_server/main.py`

**Checkpoint**: Cabinet route modules import successfully and user story tests can be written against stable paths.

---

## Phase 3: User Story 1 - Review Processed Meetings In A Web Cabinet (Priority: P1)

**Goal**: The owner can open an authorized meeting list with truthful status, source, duration, primary action, search/filter/sort controls, and future row slots.

**Independent Test**: Seed ready, processing, failed, partial, and foreign meetings; request `/api/v1/cabinet/meetings` and `/meetings`; verify only authorized rows appear and list responses contain no transcript text, secrets, signed URLs, or raw paths.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add list API contract and schema tests in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T011 [P] [US1] Add list no-secret/no-content egress tests in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [ ] T012 [P] [US1] Add authorized meeting list integration tests in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [ ] T013 [P] [US1] Add list/search/filter/sort view-model unit tests in `apps/server/tests/unit/test_cabinet_view_models.py`

### Implementation for User Story 1

- [ ] T014 [US1] Implement meeting list item mapping and safe fallback titles in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T015 [US1] Implement authorized meeting list query with workspace scoping, status filter, search, sort, and limit in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T016 [US1] Implement `GET /api/v1/cabinet/meetings` in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T017 [US1] Implement browser `/meetings` list shell with dense rows, search, filters, sort, `New` placeholder, and row future slots in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T018 [US1] Update focused validation steps for the authorized list in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

**Checkpoint**: User Story 1 is independently functional through API and browser list routes.

---

## Phase 4: User Story 2 - Read Transcript And Speaker Timeline (Priority: P1)

**Goal**: The owner can open a ready meeting detail with transcript segments, timestamps, source-role truth, speaker labels, speaker lanes, playback context, and provenance.

**Independent Test**: Seed a processed meeting with transcript and diarization rows; request `/api/v1/cabinet/meetings/{meeting_id}` and `/meetings/{meeting_id}`; verify ordered transcript, speaker lanes, provenance, `Notes` unavailable truth, and no credential/path leakage.

### Tests for User Story 2

- [ ] T019 [P] [US2] Add ready detail contract assertions in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T020 [P] [US2] Add ready detail integration tests in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [ ] T021 [P] [US2] Add transcript and speaker mapping unit tests in `apps/server/tests/unit/test_cabinet_view_models.py`
- [ ] T022 [P] [US2] Add web detail shell tests for `Notes` and `Recording & Transcript` IA in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 2

- [ ] T023 [US2] Implement ready meeting detail query with latest processing result, transcript segments, and diarization segments in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T024 [US2] Implement transcript segment, speaker lane, talk-time, playback, provenance, and notes-unavailable view models in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T025 [US2] Implement `GET /api/v1/cabinet/meetings/{meeting_id}` ready-detail response in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T026 [US2] Implement browser `/meetings/{meeting_id}` detail shell with `Notes` and `Recording & Transcript` tabs in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T027 [US2] Update ready-detail validation evidence and clean-room UI notes in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

**Checkpoint**: User Story 2 is independently functional for processed meetings.

---

## Phase 5: User Story 3 - Understand Processing And Degraded States (Priority: P1)

**Goal**: Pending, processing, partial, blocked, failed, unavailable, and denied states are truthful, content-safe, and recoverable without fake transcript or notes.

**Independent Test**: Seed processing, failed/blocked, partial, empty-transcript, and foreign meetings; verify list/detail API and web routes show truthful state, safe next action, and no unavailable content or foreign metadata.

### Tests for User Story 3

- [ ] T028 [P] [US3] Add processing/degraded/detail-state integration tests in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [ ] T029 [P] [US3] Add privacy-preserving denial tests for foreign meetings in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [ ] T030 [P] [US3] Add processing/degraded no-secret/no-content tests in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [ ] T031 [P] [US3] Add processing-state web shell tests in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 3

- [ ] T032 [US3] Implement processing, partial, blocked, failed, unavailable, and empty-transcript status mapping in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T033 [US3] Implement content-safe processing/degraded query fallbacks and privacy-preserving not-found behavior in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T034 [US3] Return privacy-preserving 404/403 problem responses for denied cabinet detail access in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T035 [US3] Render processing/degraded/failed/unavailable web states without fake content in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T036 [US3] Update degraded-state validation evidence in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

**Checkpoint**: User Story 3 is independently functional across non-ready states.

---

## Phase 6: User Story 4 - Reserve Future Governance Actions Without Overpromising (Priority: P2)

**Goal**: Share, export, download, retention, deletion, assistant, template, tags, saved/starred, and collaboration/access slots are discoverable but gated, disabled, planned, or non-mutating.

**Independent Test**: Inspect list/detail API and web routes; verify future actions are in stable locations, do not mutate state, and use deletion/access copy that avoids universal erasure or public-share promises.

### Tests for User Story 4

- [ ] T037 [P] [US4] Add governance action contract assertions in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T038 [P] [US4] Add non-mutating disabled-action web shell tests in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 4

- [ ] T039 [US4] Implement stable governance, assistant, template, and row future-slot states in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T040 [US4] Render gated governance, assistant, template, tag, saved/starred, and collaboration/access controls in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T041 [US4] Update governance validation evidence and deletion-truth copy notes in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

**Checkpoint**: User Story 4 is independently inspectable and non-mutating.

---

## Phase 7: User Story 5 - Use The Same Web-Owned Product Surface In Desktop (Priority: P2)

**Goal**: Desktop-embeddable routes reuse the same server-owned review surface while excluding active capture controls and preserving native capture authority.

**Independent Test**: Open `/desktop/meetings` and `/desktop/meetings/{meeting_id}`; verify they show the same product state as browser routes, contain no recording/device/noise/accent/screen-picker controls, and fail boundedly when unavailable.

### Tests for User Story 5

- [ ] T042 [P] [US5] Add embedded route contract tests in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T043 [P] [US5] Add embedded shell no-native-capture-control tests in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 5

- [ ] T044 [US5] Implement `/desktop/meetings` and `/desktop/meetings/{meeting_id}` route variants in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T045 [US5] Enforce embedded route forbidden-control copy and bounded unavailable states in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T046 [US5] Update embedded-route validation evidence in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`

**Checkpoint**: User Story 5 is independently inspectable through desktop embedded routes.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Final validation, evidence, docs, and release-readiness updates.

- [ ] T047 [P] Update `[Unreleased]` changelog entry for feature 016 in `CHANGELOG.md`
- [ ] T048 Run focused cabinet test suite from `specs/016-meeting-dashboard-review/quickstart.md`
- [ ] T049 Run full server pytest and Ruff validation from `specs/016-meeting-dashboard-review/quickstart.md`
- [ ] T050 Capture sanitized implementation screenshots for list, ready detail, processing detail, and embedded route into `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`
- [ ] T051 Scan tracked feature evidence for private content, secrets, signed URLs, raw audio, live paths, and account identifiers in `specs/016-meeting-dashboard-review/validation/implementation-evidence.md`
- [ ] T052 Reconcile completed tasks and validation evidence in `specs/016-meeting-dashboard-review/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1, US2, US3 (P1)**: Depend on Foundational. US2 and US3 reuse the shared detail/query/view-model foundation and can proceed after US1 list route exists.
- **US4, US5 (P2)**: Depend on the shared web/API detail surface from US1-US3.
- **Polish**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1**: MVP start after Foundational.
- **US2**: Starts after Foundational; practically follows US1 so list-to-detail navigation exists.
- **US3**: Starts after Foundational; can run in parallel with US2 after detail skeleton exists.
- **US4**: Starts after US1-US3 establish list/detail states.
- **US5**: Starts after web shell supports list/detail states.

### Within Each User Story

- Tests must be written first and fail before implementation when practical.
- View-model/query implementation precedes API endpoint behavior.
- API behavior precedes web shell integration.
- Validation evidence is updated after each story checkpoint.

## Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T005, T006, and T007 can run in parallel after T004 decisions are clear.
- US1 test tasks T010-T013 can run in parallel.
- US2 test tasks T019-T022 can run in parallel.
- US3 test tasks T028-T031 can run in parallel.
- US4 test tasks T037-T038 can run in parallel.
- US5 test tasks T042-T043 can run in parallel.

## Parallel Example: User Story 1

```bash
# Contract, integration, and unit tests can be authored in parallel:
Task: "T010 [US1] Add list API contract and schema tests in apps/server/tests/contract/test_cabinet_contract.py"
Task: "T012 [US1] Add authorized meeting list integration tests in apps/server/tests/integration/test_cabinet_meeting_list.py"
Task: "T013 [US1] Add list/search/filter/sort view-model unit tests in apps/server/tests/unit/test_cabinet_view_models.py"
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 to make the authorized meeting list visible.
3. Complete US2 and US3 before product demo because ready and non-ready detail states are launch-critical.
4. Add US4 and US5 to preserve future governance and desktop embedding without expanding 016 into sharing/deletion/capture work.

### Validation Rhythm

1. Run focused tests after each story checkpoint.
2. Update `specs/016-meeting-dashboard-review/validation/implementation-evidence.md` after each checkpoint.
3. Run full server pytest and Ruff before claiming implementation complete.
4. Capture sanitized screenshots only after the UI is stable and private data is absent.
