# Tasks: Recording Date And Smart Title

**Input**: Design documents from `specs/059-recording-date-title/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/recording-metadata-contract.md`, `quickstart.md`

**Tests**: Required. The lane is `high-risk-feature` because the slice touches local recording metadata, upload idempotency, review UI, and privacy boundaries.

**057/058 coordination gate**: Do not start implementation until `057-local-upload-custody` and `058-web-cabinet-htmx-shell` are merged into the implementation branch, or the owner explicitly approves a stacked implementation path. Feature 057 is actively changing upload/manifest/client surfaces; feature 058 is actively changing cabinet web/view-model/template surfaces.

**Organization**: Tasks are grouped by user story to keep each increment independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Maps the task to a user story from `spec.md`
- Every task names exact repository paths

## Phase 1: Setup And Coordination

**Purpose**: Avoid fighting active 057/058 work and pin the exact post-merge touchpoints before coding.

- [X] T001 Record the 057/058 merge basis, touched-file overlap, and final implementation branch policy in `specs/059-recording-date-title/quickstart.md`
- [X] T002 Re-check post-merge source touchpoints from `specs/059-recording-date-title/plan.md` against `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`, `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`

---

## Phase 2: Foundational Metadata Resolver

**Purpose**: Create the smallest shared local metadata resolver needed by all user stories.

**Critical**: No user story implementation starts until this phase is complete.

- [X] T003 [P] Add failing resolver tests for date/title/source/basename behavior and the 500 ms synthetic budget in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`
- [X] T004 [P] Add failing upload queue metadata persistence tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T005 Add recording metadata fields for title, source, confidence, and safe basename to local queue/manifest models in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T006 Implement the minimal app/date/generic resolver in `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift`
- [X] T007 Persist resolved metadata before upload enqueue/create retry in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T008 Update local manifest construction to preserve canonical start/stop instants without replacing them with upload or finalize time in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`

**Checkpoint**: Local metadata is deterministic, persisted, and safe to reuse across upload retries.

---

## Phase 3: User Story 1 - Show The Real Recording Date (Priority: P1)

**Goal**: New recordings display the recording start date/time, not upload or processing time.

**Independent Test**: Create or fixture a recording with delayed upload and verify list/detail date labels use the recording start instant.

### Tests for User Story 1

- [X] T009 [P] [US1] Add delayed-upload payload tests for `started_at` and `ended_at` in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T010 [P] [US1] Add create-meeting persistence coverage for `started_at` and `ended_at` in `apps/server/tests/integration/test_ingest_happy_path.py`
- [X] T011 [P] [US1] Add recording-date list/detail fallback, API sort, and web sort-control tests in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T012 [P] [US1] Add timezone-change date-label tests in `apps/server/tests/unit/test_cabinet_view_models.py`

### Implementation for User Story 1

- [X] T013 [US1] Send manifest `startedAt` and `stoppedAt` as create-meeting `started_at` and `ended_at` in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T014 [US1] Persist meeting start/end time from create-meeting requests in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T015 [US1] Render recording date labels and sort labels from `Meeting.started_at` with truthful fallback in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T016 [US1] Expose recording-date sort controls without legacy-date breakage in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [X] T017 [US1] Update US1 validation steps for delayed upload and timezone fixtures in `specs/059-recording-date-title/quickstart.md`

**Checkpoint**: US1 proves real recording date without any title-source work.

---

## Phase 4: User Story 2 - Generate A Minimal Recording Title (Priority: P1)

**Goal**: New recordings receive a useful app/date or generic date title without calendar or window-title collection.

**Independent Test**: Fixture known app context and unknown context; verify the generated visible title and source are deterministic and safe.

### Tests for User Story 2

- [X] T018 [P] [US2] Add app-context and generic fallback resolver cases in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`
- [X] T019 [P] [US2] Add upload client title payload tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T020 [P] [US2] Add create-meeting title persistence tests in `apps/server/tests/integration/test_ingest_happy_path.py`
- [X] T021 [P] [US2] Add cabinet title rendering and title-search tests in `apps/server/tests/integration/test_cabinet_meeting_list.py`

### Implementation for User Story 2

- [X] T022 [US2] Feed already-available approved app/platform context into the resolver in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T023 [US2] Send the generated title in create-meeting requests in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T024 [US2] Preserve create-meeting title values in server ingest without overwriting user-confirmed titles in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T025 [US2] Use visible title fallback rules for list/detail/search view models in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T026 [US2] Update US2 title matrix validation in `specs/059-recording-date-title/quickstart.md`

**Checkpoint**: US2 plus US1 is the 059 MVP.

---

## Phase 5: User Story 3 - Keep A Safe Filename Basename (Priority: P2)

**Goal**: Derive a stable safe basename for future export/download/local labels without changing storage identity.

**Independent Test**: Generate basenames from safe, unsafe, long, Cyrillic, URL, email, and duplicate titles; verify required package files and object keys do not change.

### Tests for User Story 3

- [X] T027 [P] [US3] Add safe basename sanitizer and duplicate suffix cases in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`
- [X] T028 [P] [US3] Add no-package-rename regression coverage in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`

### Implementation for User Story 3

- [X] T029 [US3] Generate `safeFileBasename` from recording date, sanitized title slug, and stable identity suffix in `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift`
- [X] T030 [US3] Persist `safeFileBasename` without renaming `manifest.json`, `mic.wav`, or `incoming.wav` in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T031 [US3] Update US3 safe-basename validation in `specs/059-recording-date-title/quickstart.md`

**Checkpoint**: US3 proves filenames are user-friendly metadata, not storage identity.

---

## Phase 6: User Story 4 - Preserve Privacy And Rename Control (Priority: P2)

**Goal**: Prove 059 does not collect calendar/window/title-private context and keeps generated titles independent from stable recording identity.

**Independent Test**: Resolver runs with no calendar/window inputs, diagnostics stay metadata-only, and explicit user-confirmed title replacement does not alter recording/upload identities.

### Tests for User Story 4

- [X] T032 [P] [US4] Add no-calendar/no-window-source assertions in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`
- [X] T033 [P] [US4] Add title identity compatibility tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T034 [P] [US4] Add metadata-only rendered/evidence assertions for titles and basenames in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`

### Implementation for User Story 4

- [X] T035 [US4] Ensure resolver inputs exclude calendar data, window titles, raw URLs, emails, invite links, tokens, and local paths in `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift`
- [X] T036 [US4] Preserve local recording id, media revision id, upload idempotency key, and object identity when generated titles or user-confirmed replacements differ in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T037 [US4] Keep diagnostics, request validation errors, and committed evidence metadata-only for title provenance in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`, `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`, `apps/server/src/twobrain_rec_server/api/problems.py`, and `apps/server/src/twobrain_rec_server/main.py`
- [X] T038 [US4] Update privacy validation notes in `specs/059-recording-date-title/checklists/privacy-ux.md`

**Checkpoint**: US4 proves privacy boundaries and title identity stability.

---

## Final Phase: Polish And Cross-Cutting Validation

**Purpose**: Close the slice without broadening scope.

- [X] T039 [P] Update behavior notes for recording date/title metadata in `docs/current-product-status.md`
- [X] T040 [P] Add user-facing release note entry for recording date/title behavior in `CHANGELOG.md`
- [X] T041 Run focused Swift validation from `specs/059-recording-date-title/quickstart.md` and record results in `specs/059-recording-date-title/quickstart.md`
- [X] T042 Run focused server validation from `specs/059-recording-date-title/quickstart.md` and record results in `specs/059-recording-date-title/quickstart.md`
- [X] T043 Run `infra/scripts/ci-local.sh` before PR/merge and record the selected risk/validation lane evidence in `specs/059-recording-date-title/quickstart.md`

---

## Post-Merge Review Fixes

**Purpose**: Close merged PR review findings without broadening 059 into calendar, window-title, rename, or export work.

- [X] T044 [P] Add server regression tests for unsafe fallback titles, visible-title sort, display-timezone labels, and legacy unsafe-title idempotent retry in `apps/server/tests/unit/test_cabinet_view_models.py`, `apps/server/tests/integration/test_cabinet_meeting_list.py`, and `apps/server/tests/integration/test_ingest_happy_path.py`
- [X] T045 [P] Add Swift regression tests for display timezone payload and ponytail metadata simplifications in `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`, `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`, and `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [X] T046 Fix unsafe fallback title rendering and visible-title sort behavior in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T047 Persist and use recording display timezone offset through create-meeting in `apps/macos/Shared/Sources/Models/AudioModels.swift`, `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift`, `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/db/models/meeting.py`, `apps/server/src/twobrain_rec_server/db/migrations/versions/0010_recording_display_timezone.py`, `apps/server/src/twobrain_rec_server/ingest/store.py`, `apps/server/src/twobrain_rec_server/ingest/meetings.py`, `apps/server/src/twobrain_rec_server/api/ingest.py`, and `specs/012-server-ingest-foundation/contracts/openapi.yaml`
- [X] T048 Preserve exact legacy unsafe-title create-meeting retries in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T049 Apply ponytail review simplifications in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, `apps/macos/Shared/Sources/Models/AudioModels.swift`, `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`, and `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift`
- [X] T050 Run focused server and Swift validation for post-merge fixes and record results in `specs/059-recording-date-title/quickstart.md`
- [X] T051 Run `infra/scripts/ci-local.sh` after post-merge fixes and record the result in `specs/059-recording-date-title/quickstart.md`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Phase 1**: No dependencies. It blocks implementation if 057/058 are not merged or explicitly stacked.
- **Phase 2**: Depends on Phase 1 and blocks all stories.
- **US1 (Phase 3)**: Depends on Phase 2.
- **US2 (Phase 4)**: Depends on Phase 2 and should normally follow US1 because both touch upload/create-meeting payloads.
- **US3 (Phase 5)**: Depends on Phase 2 and can follow US2.
- **US4 (Phase 6)**: Depends on Phase 2 and can run alongside US3 after US2 inputs exist.
- **Final Phase**: Depends on selected stories being complete.

### User Story Dependencies

- **US1 Real Recording Date**: First P1 increment; independently testable.
- **US2 Minimal Recording Title**: P1 and part of MVP; uses resolver foundation and create-meeting payload path.
- **US3 Safe Filename Basename**: P2; uses resolver foundation, independent from server rendering.
- **US4 Privacy And Rename Control**: P2; validates that 059 did not broaden into calendar/window/rename/export work.

### Parallel Opportunities

- T003 and T004 can run in parallel.
- T009, T010, T011, and T012 can run in parallel after Phase 2.
- T018, T019, T020, and T021 can run in parallel after Phase 2.
- T027 and T028 can run in parallel after US2.
- T032, T033, and T034 can run in parallel after US2.
- T039 and T040 can run in parallel after desired stories are complete.

## Parallel Example: US1

```text
Task: "T009 [P] [US1] Add delayed-upload payload tests in apps/macos/Shared/Tests/DesktopUploadClientTests.swift"
Task: "T010 [P] [US1] Add create-meeting persistence coverage in apps/server/tests/integration/test_ingest_happy_path.py"
Task: "T011 [P] [US1] Add recording-date list/detail fallback, API sort, and web sort-control tests in apps/server/tests/integration/test_cabinet_meeting_list.py"
Task: "T012 [P] [US1] Add timezone-change date-label tests in apps/server/tests/unit/test_cabinet_view_models.py"
```

## Parallel Example: US2

```text
Task: "T018 [P] [US2] Add app-context and generic fallback resolver cases in apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift"
Task: "T019 [P] [US2] Add upload client title payload tests in apps/macos/Shared/Tests/DesktopUploadClientTests.swift"
Task: "T020 [P] [US2] Add create-meeting title persistence tests in apps/server/tests/integration/test_ingest_happy_path.py"
Task: "T021 [P] [US2] Add cabinet title rendering and title-search tests in apps/server/tests/integration/test_cabinet_meeting_list.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and wait for merged or explicitly stacked 057/058 basis.
2. Complete Phase 2.
3. Complete US1 and US2.
4. Stop and validate delayed upload, app/date title, generic title, legacy fallback, and retry idempotency.

### Incremental Delivery

1. US1: date truth.
2. US2: minimal title.
3. US3: safe basename.
4. US4: privacy and identity proof.

### Scope Guard

- Do not implement calendar lookup, calendar matching, window-title collection, new app/window observer, rename UI/API, or download/export in 059.
- Reuse existing local manifest, upload queue, create-meeting, and cabinet view-model paths after 057/058 merge.
- If 057/058 change the named files, update only the affected task paths before implementation; do not broaden 059.
