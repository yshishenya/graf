# Tasks: Real Playback Availability

**Input**: Design documents from `specs/048-real-playback-availability/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/review-playback-contract.md](./contracts/review-playback-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are required. This slice fixes a real MVP regression touching retained audio playback, access/deletion boundaries, streaming/range behavior, and web/embedded UX.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Establish isolated evidence and preserve current in-flight work.

- [X] T001 Create metadata-safe 048 validation log in `specs/048-real-playback-availability/evidence/validation-log.md`
- [X] T002 Confirm 048 runs in isolated worktree and does not include dirty `045` or in-progress `047` changes in `specs/048-real-playback-availability/evidence/validation-log.md`
- [X] T003 [P] Add simple Russian unreleased changelog note for real review playback in `CHANGELOG.md`
- [X] T004 [P] Update `AGENTS.md` Spec Kit plan reference to `specs/048-real-playback-availability/plan.md`

---

## Phase 2: Foundational

**Purpose**: Define a shared playback availability boundary that is separate from artifact download/export.

- [X] T005 [P] Add RED contract coverage that owner ready review playback is available without `audio_download="allowed"` in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T006 [P] Add RED integration coverage that web and embedded detail render playback while audio download/export controls remain policy-disabled in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T007 [P] Add RED route coverage for byte-range playback responses in `apps/server/tests/integration/test_cabinet_playback_route.py`
- [X] T008 Add shared review playback availability helper in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T009 Update playback response assembly to use review playback availability, not artifact download state, in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`

**Checkpoint**: Review playback state can be available while download/export states remain disabled.

---

## Phase 3: User Story 1 - Real Recording Shows Playback (Priority: P1) MVP

**Goal**: Processed owner recordings show playback in web and embedded review without manual artifact policy changes.

**Independent Test**: Contract and integration tests prove available playback for a ready owner meeting with retained dual-track audio and default disabled download policy.

### Tests for User Story 1

- [X] T010 [P] [US1] Add assertion that review `playback.available` is true with default disabled artifact policy in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T011 [P] [US1] Add assertion that transcript seek metadata is enabled when playback is available without download policy in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T012 [P] [US1] Add assertion that web and embedded ready pages include the player route under default policy in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T013 [P] [US1] Add assertion that audio download/export controls stay unavailable when download/export policy is disabled in `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation for User Story 1

- [X] T014 [US1] Use review playback availability for `PlaybackReviewState` in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T015 [US1] Keep artifact egress states download/export-policy driven in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T016 [US1] Run focused US1 server tests from `specs/048-real-playback-availability/quickstart.md` and record metadata-only result in `specs/048-real-playback-availability/evidence/validation-log.md`

**Checkpoint**: Real owner review playback is visible by default and does not grant file download.

---

## Phase 4: User Story 2 - Playback Feels Like Review, Not Download (Priority: P1)

**Goal**: Review UI uses a persistent bottom player with timestamp seek and speaker timeline.

**Independent Test**: Web-shell and browser runtime checks prove bottom player, timestamp seek, speaker timeline, unavailable state, and responsive layout.

### Tests for User Story 2

- [X] T017 [P] [US2] Add web-shell test for persistent bottom playback bar controls in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T018 [P] [US2] Add web-shell test for speaker timeline segment marks from diarization timing in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T019 [P] [US2] Add web-shell test that unavailable playback renders bottom unavailable state without audio element in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T020 [P] [US2] Add browser runtime validation script or fixture command for timestamp seek and responsive overflow in `specs/048-real-playback-availability/evidence/validation-log.md`

### Implementation for User Story 2

- [X] T021 [US2] Replace inline playback block with persistent bottom review player markup in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T022 [US2] Add custom player controls, timestamp seek, skip controls, speed control, and time displays in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T023 [US2] Render speaker timeline segment marks from diarization timing in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T024 [US2] Update CSS spacing/responsive behavior so bottom player does not cover transcript content in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T025 [US2] Run web-shell and browser runtime validation and record metadata-only result in `specs/048-real-playback-availability/evidence/validation-log.md`

**Checkpoint**: Playback is a usable review experience, not a buried download-like audio block.

---

## Phase 5: User Story 3 - Stream Safely Without Public Audio Egress (Priority: P1)

**Goal**: Playback route supports safe range requests and keeps blocked states closed.

**Independent Test**: Route tests prove 206 range responses, safe headers, denied states, and no direct storage egress.

### Tests for User Story 3

- [X] T026 [P] [US3] Add route assertions for `206`, `Accept-Ranges`, `Content-Range`, and partial body in `apps/server/tests/integration/test_cabinet_playback_route.py`
- [X] T027 [P] [US3] Add malformed and unsatisfiable range assertions in `apps/server/tests/integration/test_cabinet_playback_route.py`
- [X] T028 [P] [US3] Add no-secret range response assertions in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [X] T029 [P] [US3] Add audit assertions that playback allowed/denied metadata stays safe in `apps/server/tests/unit/test_artifact_egress_audit.py`

### Implementation for User Story 3

- [X] T030 [US3] Add range parsing and safe playback response metadata in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T031 [US3] Update playback route to forward request `Range` and return 200/206/416 with safe headers in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T032 [US3] Keep review audio source validation dual-track and fail-closed in `apps/server/src/twobrain_rec_server/cabinet/playback_audio.py`
- [X] T033 [US3] Run focused US3 server tests and record metadata-only result in `specs/048-real-playback-availability/evidence/validation-log.md`

**Checkpoint**: Browser seeking uses server-mediated range playback without public audio egress.

---

## Phase 6: User Story 4 - Preserve Product Truth And Operations (Priority: P2)

**Goal**: Status docs and release text honestly explain playback behavior and remaining limitations.

**Independent Test**: Docs and changelog state real playback availability, separate downloads, server-mediated streaming, and out-of-scope limitations in simple Russian.

- [X] T034 [US4] Update `docs/current-product-status.md` to remove stale contradictory 046 playback status and describe 048 truth
- [X] T035 [US4] Update `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md` or 048 evidence with the corrected 046/048 boundary without changing past facts
- [X] T036 [US4] Ensure `CHANGELOG.md` uses simple Russian for 048 behavior and limitations
- [X] T037 [US4] Run forbidden-content scan from `specs/048-real-playback-availability/quickstart.md` and record result in `specs/048-real-playback-availability/evidence/validation-log.md`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full validation, embedded desktop parity, release readiness, and task reconciliation.

- [X] T038 Run `SPECIFY_FEATURE_DIRECTORY=specs/048-real-playback-availability bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
- [X] T039 Run checklist status validation for all `specs/048-real-playback-availability/checklists/*.md`
- [X] T040 Run read-only Spec Kit analyze pass and record clean result in `specs/048-real-playback-availability/evidence/validation-log.md`
- [X] T041 Run focused server validation from `specs/048-real-playback-availability/quickstart.md`
- [X] T042 Run macOS embedded review validation or record why server-owned embedded route coverage is sufficient
- [X] T043 Run full `infra/scripts/ci-local.sh`
- [X] T044 Run `infra/scripts/cd-remote.sh --dry-run`
- [X] T045 Reconcile completed tasks with evidence and leave any unverified tasks open

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on setup and blocks all stories.
- **US1 (Phase 3)**: Depends on foundational playback availability.
- **US2 (Phase 4)**: Depends on US1 playback state.
- **US3 (Phase 5)**: Depends on foundational route behavior and US1 route path.
- **US4 (Phase 6)**: Depends on implemented behavior and validation evidence.
- **Polish (Phase 7)**: Depends on all target stories.

### Parallel Opportunities

- T003 and T004 can run in parallel.
- T005, T006, and T007 can be written in parallel.
- T010 through T013 can be written in parallel after foundational tests.
- T017 through T020 can be written in parallel.
- T026 through T029 can be written in parallel.

## Implementation Strategy

1. Preserve isolated 048 worktree and metadata-safe evidence.
2. Write RED tests that reproduce the real 046 gap.
3. Implement review playback availability separate from download policy.
4. Upgrade review UI to bottom player and speaker timeline.
5. Add safe range playback route behavior.
6. Validate web, embedded desktop route, and full local gates.
7. Update product truth docs and reconcile tasks only after evidence exists.

## Traceability

| Requirement | Task Coverage |
|---|---|
| FR-001 owner review playback by default | T005, T006, T010, T012, T014, T016 |
| FR-002 no manual `audio_download=allowed` | T005, T010, T014, T016 |
| FR-003 playback separate from download/export | T006, T013, T015, T034, T036 |
| FR-004 server-owned playback route | T007, T026, T028, T031 |
| FR-005 byte-range streaming semantics | T007, T026, T027, T030, T031 |
| FR-006 dual-source review audio | T028, T032, T033 |
| FR-007 fail-closed blocked states | T027, T028, T029, T030, T033 |
| FR-008 persistent bottom review player | T017, T021, T022, T024, T025 |
| FR-009 transcript timestamps seek playback | T011, T017, T022, T025 |
| FR-010 speaker activity lanes | T018, T023, T025 |
| FR-011 web and macOS embedded parity | T006, T012, T025, T042 |
| FR-012 transcript readability when unavailable | T019, T021, T024, T025 |
| FR-013 metadata-only audit/evidence | T028, T029, T033, T037, T045 |
| FR-014 truthful Russian status/release text | T003, T034, T035, T036 |
| SC-001 real owner processed playback visible | T005, T010, T012, T014, T016, T041 |
| SC-002 downloads remain separate | T006, T013, T015, T034 |
| SC-003 timestamp seek within one second | T020, T022, T025 |
| SC-004 range route and no secret egress | T026, T028, T030, T031, T037 |
| SC-005 blocked states expose no audio | T027, T028, T029, T033 |
| SC-006 responsive web/embedded layout | T020, T024, T025, T042 |
| SC-007 simple Russian docs and notes | T003, T034, T036 |
