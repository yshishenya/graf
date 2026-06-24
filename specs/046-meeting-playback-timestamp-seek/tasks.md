# Tasks: Meeting Playback Timestamp Seek

**Input**: Design documents from `specs/046-meeting-playback-timestamp-seek/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/playback-review-contract.md](./contracts/playback-review-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are required for this slice because playback touches retained audio, access policy, deletion truth, and user-facing review.

**Organization**: Tasks are grouped by independently testable user story. Each story can be verified with synthetic fixture content only.

## Phase 1: Setup

**Purpose**: Confirm the current code surface and prepare evidence before changing behavior.

- [X] T001 Inspect current cabinet playback, transcript, artifact egress, and desktop embedded routes in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/web.py`, `apps/server/src/twobrain_rec_server/cabinet/egress.py`, and `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T002 Record the pre-implementation 046 baseline and any fixture assumptions in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T003 [P] Confirm local release-note wording stays simple Russian for this feature in `CHANGELOG.md`

---

## Phase 2: Foundational

**Purpose**: Shared playback contract and fixture support that block all stories.

- [X] T004 [P] Add playback response and transcript seek schema coverage in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T005 [P] Add playback fixture helpers for retained audio and artifact policy states in `apps/server/tests/fixtures/cabinet_access.py`
- [X] T006 [P] Add playback view-model and review-audio source unit coverage in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/unit/test_playback_audio.py`
- [X] T007 Extend `PlaybackReviewState` and `TranscriptSegmentView` in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T008 Add shared playback availability and review-audio source helpers in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/playback_audio.py`
- [X] T009 Wire playback availability into meeting review assembly in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`

**Checkpoint**: Review responses can describe playback availability and review-audio source mode without exposing audio bytes.

---

## Phase 3: User Story 1 - Play Meeting Audio From Review (Priority: P1)

**Goal**: Allowed owners can play retained meeting audio from the meeting review page.

**Independent Test**: A processed meeting with retained audio shows a player and the server route returns playable audio only to the owner.

### Tests for User Story 1

- [X] T010 [P] [US1] Add contract assertions for available playback fields, combined review source mode, and no direct storage URLs in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T011 [P] [US1] Add integration coverage for the owner playback route returning audio bytes in `apps/server/tests/integration/test_cabinet_playback_route.py`
- [X] T012 [P] [US1] Add web-shell coverage for available playback controls in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement the server-mediated playback route in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T014 [US1] Reuse retained audio artifact retrieval and review-audio stream building for playback in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/playback_audio.py`
- [X] T015 [US1] Render the meeting review player, current time, duration, and speed controls in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T016 [US1] Ensure the meeting detail response exposes only a relative playback path in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T017 [US1] Run the US1 focused tests and record results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`

**Checkpoint**: User Story 1 is independently playable and policy-gated for an allowed ready meeting.

---

## Phase 4: User Story 2 - Seek From Transcript Timestamps (Priority: P1)

**Goal**: Transcript timestamps move the player to the matching segment start.

**Independent Test**: A processed meeting with at least three timestamped segments can seek to each segment within one second.

### Tests for User Story 2

- [X] T018 [P] [US2] Add contract assertions for seekable transcript segment metadata in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T019 [P] [US2] Add view-model coverage for valid, missing, duplicated, and out-of-range timestamp seek targets in `apps/server/tests/unit/test_cabinet_view_models.py`
- [X] T020 [P] [US2] Add web-shell coverage for timestamp seek controls and keyboard attributes in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 2

- [X] T021 [US2] Populate transcript seek metadata in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T022 [US2] Render timestamp controls with safe seek metadata in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T023 [US2] Add browser-side seek behavior for timestamp controls in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T024 [US2] Preserve visible transcript rows when a timestamp is not seekable in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T025 [US2] Run the US2 focused tests and record results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`

**Checkpoint**: User Story 2 is independently seekable without transcript breakage.

---

## Phase 5: User Story 3 - Respect Playback Policy And Privacy (Priority: P1)

**Goal**: Playback never exposes audio for unauthorized, deleted, deleting, purged, transcript-only, processing, failed, or no-audio states.

**Independent Test**: Policy fixtures cover all blocked states and each state returns a safe unavailable reason without playable audio.

### Tests for User Story 3

- [X] T026 [P] [US3] Add integration coverage for unauthorized, deleted, deleting, audio-purged, transcript-only, processing, failed, policy-disabled, no-audio, and review-audio-unavailable playback route states in `apps/server/tests/integration/test_cabinet_playback_route.py`
- [X] T027 [P] [US3] Add no-secret playback egress assertions in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [X] T028 [P] [US3] Add artifact egress audit coverage for allowed and denied playback requests in `apps/server/tests/unit/test_artifact_egress_audit.py`
- [X] T029 [P] [US3] Add unavailable-state web-shell coverage in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 3

- [X] T030 [US3] Enforce playback blocked-state mapping in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T031 [US3] Return safe playback route errors without object existence leaks in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T032 [US3] Record metadata-only allowed and denied playback audit rows in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T033 [US3] Render Russian unavailable-state copy and deletion/retention truth in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T034 [US3] Run the US3 focused tests and record results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`

**Checkpoint**: User Story 3 preserves privacy, access, deletion, and evidence boundaries.

---

## Phase 6: User Story 4 - Match Web And Desktop Review (Priority: P2)

**Goal**: Web cabinet and macOS embedded review show the same playback state and seek behavior.

**Independent Test**: The same fixture meeting opened through `/meetings/{id}` and `/desktop/meetings/{id}` shows matching playback availability, unavailable reason, and timestamp controls.

### Tests for User Story 4

- [X] T035 [P] [US4] Add desktop embedded route parity assertions in `apps/server/tests/contract/test_cabinet_playback_contract.py`
- [X] T036 [P] [US4] Add web-shell embedded parity coverage in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T037 [P] [US4] Add integration coverage for `/desktop/meetings/{meeting_id}` playback state in `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation for User Story 4

- [X] T038 [US4] Ensure desktop embedded detail uses the same playback review state in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T039 [US4] Keep desktop embedded navigation and auth headers compatible with playback route requests in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T040 [US4] Run the US4 focused tests and record results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`

**Checkpoint**: Web and desktop embedded review do not contradict each other.

---

## Phase 7: Polish And Cross-Cutting Validation

**Purpose**: Finish release readiness, UI proof, tracker sync, and repository gates.

- [X] T041 [P] Update the 046 changelog entry in simple Russian in `CHANGELOG.md`
- [X] T042 [P] Update current MVP status with the 046 result and remaining honest blockers in `docs/current-product-status.md`
- [X] T043 [P] Run the focused quickstart command set from `specs/046-meeting-playback-timestamp-seek/quickstart.md`
- [X] T044 [P] Run browser runtime checks for desktop and mobile-width review surfaces and record metadata-only results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T045 [P] Run desktop embedded review validation or record why server-shared embedded review required no macOS code change in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T046 Run forbidden-content scans for playback evidence, screenshots, logs, and docs, then record results in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T047 Run `infra/scripts/ci-local.sh` and record the result in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T048 Run `infra/scripts/cd-remote.sh --dry-run` and record the deploy-readiness boundary in `specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`
- [X] T049 Reconcile all completed task checkboxes in `specs/046-meeting-playback-timestamp-seek/tasks.md` only after validation evidence exists

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Stories 1-3 (P1)**: Depend on Foundational. They should run in order because they touch the same playback contract and files.
- **User Story 4 (P2)**: Depends on User Stories 1-3 because parity uses the completed review state.
- **Polish (Phase 7)**: Depends on completed user stories and focused validation.

### User Story Dependencies

- **US1 Play Meeting Audio**: Foundational only.
- **US2 Timestamp Seek**: Depends on US1 player state.
- **US3 Playback Policy And Privacy**: Depends on shared availability state from US1 and must finish before release validation.
- **US4 Web/Desktop Parity**: Depends on US1-US3.

### Parallel Opportunities

- T003 can run while baseline inspection is recorded.
- T004-T006 can run in parallel before shared implementation.
- Tests inside each user story marked `[P]` can be authored together before implementation.
- T041-T045 can run in parallel after story implementation, then T046-T049 must reconcile final evidence.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational tasks.
2. Complete US1 so a retained audio meeting can play from review.
3. Complete US2 so transcript timestamps can seek playback.
4. Complete US3 before any release claim because it controls source-audio privacy.
5. Complete US4 so desktop embedded review matches web review.
6. Run Phase 7 validation before PR or release readiness.

### Validation Rule

Do not mark a task `[X]` until its implementation and evidence are present. Do not claim full MVP readiness from 046 alone; this feature only closes the playback/timestamp review gap.
