# Tasks: Meaningful Recording Titles

**Input**: Design documents from `/specs/155-recording-title/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required by the high-risk validation lane and the acceptance
scenarios in spec.md.

## Phase 1: Setup (Shared Test Infrastructure)

**Purpose**: Prepare focused regression coverage using existing fixtures and
helpers. No dependency or schema setup is required.

- [X] T001 [P] Add shared calendar, app-context, generic, authoritative, and missing-time meeting cases to `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T002 [P] Add browser and embedded-desktop recording title assertions to `apps/server/tests/integration/test_cabinet_meeting_detail.py` using the existing meeting fixtures.

**Checkpoint**: Focused tests describe the required title contract before the
shared projection changes.

## Phase 2: Foundational (Shared Projection Boundary)

**Purpose**: Establish one server-side presentation boundary for every cabinet
surface. No database migration, endpoint, or new dependency is needed.

- [X] T003 Add a failing contract-level projection assertion in `apps/server/tests/unit/test_cabinet_view_models.py` that requires one deterministic title path without mutating the stored `Meeting`.

**Checkpoint**: The helper has one source precedence and does not mutate the
stored `Meeting` or any recording artifact.

## Phase 3: User Story 1 - Recognize a Meeting Recording (Priority: P1) 🎯 MVP

**Goal**: Show a matched calendar/meeting title with the recording date and
time in the web cabinet and the embedded macOS cabinet.

**Independent Test**: A recording with a safe calendar title appears with that
title and start date/time in list, detail, shared, and embedded desktop views.

### Tests for User Story 1

- [X] T004 [P] [US1] Add unit assertions for calendar title formatting, timezone offset, Unicode/punctuation safety, long-title bounds, and missing start time in `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T005 [P] [US1] Add integration assertions that browser and `/desktop/meetings` list/detail routes render the same calendar-derived title in `apps/server/tests/integration/test_cabinet_meeting_detail.py`.

### Implementation for User Story 1

- [X] T006 [US1] Route `safe_title`, `meeting_list_title`, list-item construction, search/sort title projection, and shared-with-me cards through the helper in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [X] T007 [US1] Preserve HTML escaping and accessible full-title behavior in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` while rendering the new projected title.

**Checkpoint**: User Story 1 is independently testable; the embedded macOS
surface receives the same title because it reuses the desktop cabinet route.

## Phase 4: User Story 2 - Identify Recordings Without Meeting Titles (Priority: P1)

**Goal**: Use source application name plus date/time, then a dated generic
fallback, when calendar title is unavailable.

**Independent Test**: App-context, unsafe/missing app-context, and missing-time
fixtures each produce a non-empty safe title without blocking the recording.

### Tests for User Story 2

- [X] T008 [P] [US2] Add unit assertions for app-context titles, generic fallback, unsafe metadata fallback, and deterministic date/time formatting in `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T009 [P] [US2] Add integration assertions for a recording with `title_source=app_context` and one with no usable title in `apps/server/tests/integration/test_cabinet_meeting_detail.py`.

### Implementation for User Story 2

- [X] T010 [US2] Extend the projection helper in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` to restore the stored app-context label, append the recording time, and fall through to the localized generic title without exposing unsafe text.

**Checkpoint**: User Stories 1 and 2 both work independently and use the same
projection path.

## Phase 5: User Story 3 - Preserve User Intent (Priority: P1)

**Goal**: Never replace a user-confirmed or manual-upload title and never alter
recording identity or audio filenames.

**Independent Test**: A user-confirmed title remains unchanged after calendar
metadata is present, while stable IDs and media paths remain identical.

### Tests for User Story 3

- [X] T011 [P] [US3] Add unit assertions that `user_confirmed`, `upload_provided`, and file-name-derived titles retain their existing display semantics in `apps/server/tests/unit/test_cabinet_view_models.py`.
- [X] T012 [P] [US3] Add integration regression coverage for late calendar matching not replacing an authoritative title in `apps/server/tests/integration/test_calendar_auto_context_match.py`.
- [X] T013 [P] [US3] Keep existing macOS metadata/upload contract coverage green for title source, stable suffix, and unchanged safe file basename in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift` and `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.

### Implementation for User Story 3

- [X] T014 [US3] Keep authoritative-title and artifact-identity branches explicit in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`; do not change `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift` or local media naming.

**Checkpoint**: All three user stories are independently testable without a
schema change or capture-path change.

## Phase 6: Polish & Cross-Cutting Validation

**Purpose**: Run the planned gates and verify the final diff is limited to the
title projection feature.

- [X] T015 [P] Run focused server unit tests from `specs/155-recording-title/quickstart.md`.
- [X] T016 [P] Run focused cabinet integration tests from `specs/155-recording-title/quickstart.md`.
- [X] T017 [P] Run `swift test --package-path apps/macos --filter RecordingMetadataResolver` and `swift test --package-path apps/macos --filter DesktopUploadClient`.
- [X] T018 Run `infra/scripts/ci-local.sh`, confirm no migration/dependency/audio-file changes, and record results in the implementation handoff.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 and T002 can run in parallel.
- **Foundational (Phase 2)**: Depends on T001 and T002; T003 blocks story implementation and must fail before the helper is added.
- **User Stories (Phases 3–5)**: Depend on T003. T004/T005 precede T006/T007; T008/T009 precede T010; T011–T013 precede T014.
- **Polish (Phase 6)**: Depends on all implementation tasks; T015–T017 can run in parallel, then T018 closes the gate.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after T003; no dependency on other stories.
- **User Story 2 (P1)**: Starts after T003; shares the helper with US1 but is independently covered by app/generic cases.
- **User Story 3 (P1)**: Starts after T003; protects existing authoritative and artifact contracts.

### Parallel Opportunities

- T001 and T002 can run in parallel.
- T004 and T005 can run in parallel after T003.
- T008 and T009 can run in parallel after the US1 implementation is available.
- T011, T012, and T013 can run in parallel because they touch separate test concerns/files.
- T015, T016, and T017 can run in parallel after implementation.

## Parallel Example: User Story 1

```text
Task T004: unit title projection cases in apps/server/tests/unit/test_cabinet_view_models.py
Task T005: browser/embedded cabinet cases in apps/server/tests/integration/test_cabinet_meeting_detail.py
```

## Implementation Strategy

### MVP First

1. Complete T001–T003.
2. Complete User Story 1 (T004–T007).
3. Run T015–T016 and verify the calendar-title path independently.

### Incremental Delivery

1. Add User Story 2's app/generic fallbacks.
2. Add User Story 3's authoritative-title and media-identity regression gates.
3. Run macOS compatibility and full local CI validation.

## Notes

- `[P]` marks tasks that can run in parallel without touching the same
  incomplete implementation.
- No new API, migration, dependency, native recording UI, or audio-file rename
  is planned.
