# Tasks: Canonical Speaker Turns for Transcript Review

**Input**: Design documents from `/specs/113-transcript-speaker-turns/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and `contracts/canonical-transcript-turns.md`

**Risk lane**: High-risk shared transcript/review behavior. Tests and the full
server gate are required before implementation closeout.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Reuse the existing server, Pydantic, pytest, and server-rendered
cabinet setup. No new dependency, migration, service, or client provider path
is required for this slice.

No setup tasks.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the additive response shape before story-specific review
logic. Existing processing rows remain the source of truth.

### Tests first

- [X] T001 [P] Add failing contract coverage for the additive `transcript.speaker_turns` field, raw `segments` preservation, empty-turn default, and provider-neutral field names in `apps/server/tests/contract/test_transcript_turn_contract.py`.

### Implementation

- [X] T002 Add `TranscriptSpeakerTurnView` and the additive `speaker_turns` field to `apps/server/src/twobrain_rec_server/api/schemas.py` without removing or renaming raw `TranscriptSegmentView` fields.

**Checkpoint**: The response can carry raw and derived data without a provider
or persistence change.

## Phase 3: User Story 1 - Review Continuous Speaker Turns (Priority: P1) 🎯 MVP

**Goal**: Show readable same-speaker turns while preserving exact source timing
and raw segment access.

**Independent Test**: Synthetic mapped transcript rows with sub-second gaps
produce one derived turn; the rendered review uses that turn and retains raw
rows/seek timing.

### Tests for User Story 1 (write first)

- [X] T003 [US1] Add failing view-model tests for same-speaker pairwise merge, first-start/last-end timing, ordered text, source ids, and a gap above one second in `apps/server/tests/unit/test_cabinet_view_models.py`.

### Implementation for User Story 1

- [X] T004 [US1] Implement deterministic `speaker_turns` derivation from mapped review rows in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, reusing existing sorting, label mapping, source-role labels, and seek helpers.
- [X] T005 [US1] Update the server-rendered transcript path to prefer non-empty derived turns while falling back to raw segments in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.

**Checkpoint**: The primary fragmented-speaker review journey is readable,
seekable, and still has raw source rows.

## Phase 4: User Story 2 - Keep One Provider-Agnostic Transcript Contract (Priority: P1)

**Goal**: Ensure all supported import paths populate the same server-owned
turn semantics without provider-specific client logic.

**Independent Test**: Equivalent canonical rows from normal and manual-upload
review paths produce the same additive turn shape while raw segments remain
available.

### Tests for User Story 2 (write first)

- [X] T006 [US2] Extend `apps/server/tests/contract/test_transcript_turn_contract.py` with provider-neutral field assertions and compatibility coverage for both normal transcript and diarization-backed review inputs.

### Implementation for User Story 2

- [X] T007 [US2] Ensure normal transcript mapping and manual-upload diarization mapping populate the same provider-neutral `speaker_turns` field in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.

**Checkpoint**: Existing raw clients remain compatible and the server is the
only component that defines turn semantics.

## Phase 5: User Story 3 - Preserve Safe Boundaries and Recovery (Priority: P2)

**Goal**: Keep turn derivation deterministic, non-destructive, and safe for
speaker changes, retries, unknown labels, and incomplete data.

**Independent Test**: Boundary fixtures rebuild to identical turns without
cross-speaker, cross-track, cross-result, or fallback-label merges.

### Tests for User Story 3 (write first)

- [X] T008 [US3] Add failing boundary and idempotence tests for speaker changes, source-role/result boundaries, unknown mappings, invalid/overlapping timing, empty text, incomplete processing, and repeated rebuilds in `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T009 [P] [US3] Add a server-rendered regression test for derived-turn preference, raw fallback, escaped text, and first-segment seek timing in `apps/server/tests/unit/test_cabinet_web_shell.py`.

### Implementation for User Story 3

- [X] T010 [US3] Harden the turn helper in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` so display fallbacks cannot create merge evidence, malformed rows remain recoverable, and repeated derivation is idempotent.
- [X] T011 [US3] Keep incomplete/non-terminal transcript states from exposing final derived turns in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/api/schemas.py`.

**Checkpoint**: Safety and recovery boundaries are covered without changing
raw stored transcript data.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Record the behavior change and run the selected validation lane.

- [X] T012 [P] Update the Russian `Исправлено` section of `CHANGELOG.md` with the additive canonical speaker-turn review behavior and provider-neutral boundary.
- [X] T013 Run the focused commands and expected scenarios in `specs/113-transcript-speaker-turns/quickstart.md`, then run `infra/scripts/ci-local.sh` from the repository root and record metadata-only evidence in the PR/closeout.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No work; existing project setup is reused.
- **Foundational (Phase 2)**: T001 must fail before T002 adds the additive response field; this phase blocks all story work.
- **User Story 1 (Phase 3)**: T003 follows T002; T004/T005 follow the failing tests.
- **User Story 2 (Phase 4)**: T006 follows T002 and is completed before T007; it consumes the shared helper from US1.
- **User Story 3 (Phase 5)**: T008/T009 are written before T010/T011 and extend existing test files independently where possible.
- **Polish (Phase 6)**: Depends on all desired story tasks and focused validation.

### User Story Dependencies

- **US1 (P1)**: MVP; depends only on the additive schema field T002.
- **US2 (P1)**: Depends on T002 and the shared derivation helper T004; it does not add a new provider adapter.
- **US3 (P2)**: Depends on T004/T005 and hardens the same helper without changing raw storage.

### Parallel Opportunities

- T001 can be prepared in parallel with repository-only review of the existing fixture paths, but it must pass/fail before T002.
- T009 can be prepared in parallel with T008 because it touches a separate test file.
- T012 is independent documentation work and can run in parallel with final focused validation.

## Parallel Example: MVP

```text
T001: additive response contract test
  ↓
T002: response schema field
  ↓
T003: view-model merge tests
  ↓
T004: server turn derivation
  ↓
T005: rendered review preference
```

## Implementation Strategy

1. Write T001, then confirm it fails for the current one-row-per-segment
   contract before implementing T002.
2. Write T003/T006/T008/T009 before their corresponding story changes and
   confirm the current behavior fails the new expectations.
3. Implement T004/T005/T007/T010/T011 as the smallest additive schema,
   view-model, and rendering change; do not add a persistence table or provider
   adapter.
4. Run T012/T013, then review the diff for raw-content, secret, and provider
   coupling violations before requesting commit/PR approval.

## Notes

- `[P]` means separate files with no dependency on incomplete work.
- The implementation should reuse existing `TranscriptSegmentView`, timestamp,
  source-role, escaping, and playback helpers instead of introducing a new
  transcript service.
- Do not mark a task complete until its focused check passes; production
  deployment follows the repository release gate after implementation closeout.
