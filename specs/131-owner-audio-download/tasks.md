# Tasks: Скачивание аудио владельцем по умолчанию

**Input**: Design documents from `specs/131-owner-audio-download/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/meeting-owner-audio-download.md`, and `quickstart.md`.

**Risk lane**: `high-risk-feature`; tests and `infra/scripts/ci-local.sh` are
required before closeout. No production deploy is included.

## Phase 1: Setup

**Purpose**: Add only the test-fixture control needed to represent implicit and
explicit policy sources without changing production schema.

- [X] T001 [P] Extend `set_artifact_policy` in `apps/server/tests/fixtures/cabinet_access.py` with an optional `policy_source` argument defaulting to `test_fixture`, preserving existing fixture behavior.

**Checkpoint**: Tests can create production-shaped `workspace_default` rows and
explicit `meeting_override` rows without touching live data or adding a
migration.

## Phase 2: User Story 1 - Владелец сохраняет готовое аудио (Priority: P1) 🎯 MVP

**Goal**: A meeting owner receives the existing server-mediated audio download
when a validated playback artifact exists, even without a separate audio
permission.

**Independent Test**: A synthetic owner meeting with no policy row and another
with `workspace_default/disabled` render the existing action in both detail
shells and return a non-empty synthetic playback artifact through the existing
route.

### Tests for User Story 1 (write before implementation)

- [X] T002 [P] [US1] Add an integration test in `apps/server/tests/integration/test_artifact_egress_policy.py` proving an owner with no policy row can download a retained playback M4A and receives the existing metadata-only audit sequence.
- [X] T003 [US1] Add an integration test in `apps/server/tests/integration/test_artifact_egress_policy.py` proving an owner with `policy_source=workspace_default` and `audio_download=disabled` can download the retained playback M4A.
- [X] T004 [P] [US1] Add web/embedded parity assertions in `apps/server/tests/integration/test_cabinet_meeting_detail.py` proving the existing relative download action is rendered for the owner only when the validated playback artifact is present.

### Implementation for User Story 1

- [X] T005 [US1] Implement the smallest effective audio-policy mapping in `apps/server/src/twobrain_rec_server/cabinet/egress.py`: promote only `disabled` values from implicit `meeting_default` or `workspace_default` sources to `owner_only` before `_audio_state`, while preserving accepted explicit values and fail-closed unknown/test sources.
- [X] T006 [US1] Update the `[Unreleased]` `Changed`, `Fixed`, and `Безопасность` sections in `CHANGELOG.md` with the owner-default behavior, explicit-denial boundary, and metadata-only validation scope for Feature 131.

**Checkpoint**: User Story 1 works through both the rendered detail action and
the direct route, with no client-only workaround.

## Phase 3: User Story 2 - Явные ограничения сохраняют силу (Priority: P1)

**Goal**: An explicit per-meeting denial and the existing owner-only policy do
not get widened by the implicit owner default.

**Independent Test**: Synthetic owner and permitted non-owner requests return
bounded denial responses with no audio bytes under the explicit/owner-only
cases, while existing allowed behavior remains unchanged.

### Tests for User Story 2

- [X] T007 [P] [US2] Add an integration regression test in `apps/server/tests/integration/test_artifact_egress_policy.py` proving `policy_source=meeting_override` with `audio_download=disabled` rejects the owner and records only the existing denied audit metadata.
- [X] T008 [US2] Add an integration regression test in `apps/server/tests/integration/test_artifact_egress_policy.py` using an active permitted non-owner grant to prove the implicit owner-only result returns 409 and never serves audio bytes.

### Implementation for User Story 2

- [X] T009 [US2] Keep the existing access, `owner_only`, direct-route, and audit gates authoritative in `apps/server/src/twobrain_rec_server/cabinet/egress.py`; adjust only the shared effective-policy call site needed for T005 and do not add a second permission path.

**Checkpoint**: Explicit denial and non-owner privacy boundaries remain
fail-closed while the owner default works.

## Phase 4: User Story 3 - Отказ остаётся понятным и безопасным (Priority: P1)

**Goal**: Missing, processing, deleting, corrupt, or unavailable audio remains a
bounded failure and never becomes an empty successful download.

**Independent Test**: A synthetic owner request without a validated playback
artifact returns the existing bounded 409 and metadata-only denial, with the
meeting detail still available for retry.

### Tests for User Story 3

- [X] T010 [P] [US3] Add an integration regression test in `apps/server/tests/integration/test_artifact_egress_policy.py` proving owner-default policy does not bypass the existing missing-playback-artifact failure or return audio bytes.

### Implementation for User Story 3

- [X] T011 [US3] Reuse the existing validated-artifact, deletion, storage-size, bounded-error, and metadata-only audit paths in `apps/server/src/twobrain_rec_server/cabinet/egress.py`; make no new lifecycle or storage boundary.

**Checkpoint**: All three stories are independently covered by focused server
tests and the existing UI/route contracts.

## Phase 5: Polish & Cross-Cutting Validation

**Purpose**: Close the high-risk shared behavior with repository evidence.

- [X] T012 Run the Feature 131 quickstart focused pytest suite from `specs/131-owner-audio-download/quickstart.md`, record only metadata-only results there, and mark completed tasks `[X]` only after the assertions pass.
- [ ] T013 Run `infra/scripts/ci-local.sh` from the repository root, review the diff for secret/content leakage, and record the high-risk validation result and any expected no-production-DB limitation in `specs/131-owner-audio-download/quickstart.md`.

T013 remains open until the full local gate completes without the unrelated
SC-017 timing failure documented in the quickstart evidence.

## Dependencies & Execution Order

### Phase Dependencies

- Setup T001 comes first because the new integration cases need source control.
- User Story 1 tests T002–T004 must be written before implementation T005.
- User Story 2 tests T007–T008 validate T005 and must pass before T009 is
  considered complete; T009 is a guard against adding a second permission path.
- User Story 3 reuses the same implementation and existing lifecycle gates.
- T012 and T013 run only after all implementation and regression tasks pass.

### User Story Dependencies

- **US1 (P1)**: Starts after T001 and is the MVP; no other story dependency.
- **US2 (P1)**: Uses the shared egress mapping from US1 but remains independently
  testable through explicit source and non-owner requests.
- **US3 (P1)**: Uses the existing artifact/lifecycle path and guards the owner
  default against bypassing bounded failures.

### Parallel Opportunities

- T002 and T004 touch different test files and can be prepared in parallel.
- T007 and T010 can be prepared in parallel after T001; T003/T008 share the
  egress test file and should be applied sequentially to avoid conflicts.
- T013 is the final repository gate and is not parallel with implementation.

## Implementation Strategy

1. Complete T001 and write the red/guard integration and parity tests.
2. Implement one shared effective-policy mapping in T005; do not alter the
   route, client JavaScript, database schema, or storage layer.
3. Complete explicit-denial, non-owner, and bounded-failure regressions.
4. Update the changelog and run the quickstart, then the full local CI gate.
5. Stop before commit/deploy and request explicit approval for the next action.
