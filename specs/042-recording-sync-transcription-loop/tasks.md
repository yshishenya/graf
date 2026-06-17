# Tasks: Recording Sync And Transcription Loop

**Input**: Design documents from
`specs/042-recording-sync-transcription-loop/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required. This feature touches offline sync, server schema, RLS,
MediaScribe/Temporal processing, transcript display, desktop UI, privacy, and
lifecycle truth. Write failing tests before implementation tasks in each phase.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Prepare feature evidence and shared test scaffolding.

- [ ] T001 Create implementation evidence log in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`
- [ ] T002 [P] Create synthetic fixture README for offline/upload/review evidence in `specs/042-recording-sync-transcription-loop/validation/README.md`
- [ ] T003 [P] Add server fixture helpers for revision-aware recordings in `apps/server/tests/fixtures/recording_sync.py`
- [ ] T004 [P] Add macOS fixture helpers for queue v2 items in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [ ] T005 Record checklist closure notes for `042` in `specs/042-recording-sync-transcription-loop/checklists/requirements.md`

---

## Phase 2: Foundational

**Purpose**: Shared schema, models, contracts, and migration work that blocks
all user stories.

**Critical**: No user story implementation begins until this phase is complete.

### Tests

- [ ] T006 [P] Add failing migration/model tests for media revisions in `apps/server/tests/integration/test_media_revision_migrations.py`
- [ ] T007 [P] Add failing RLS tests for media revision tenant isolation in `apps/server/tests/integration/test_rls_media_revision_policies.py`
- [ ] T008 [P] Add failing OpenAPI contract tests for revision-aware ingest/sync fields in `apps/server/tests/contract/test_recording_sync_contract.py`
- [ ] T009 [P] Add failing desktop queue schema migration tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation

- [ ] T010 Add media revision statuses/source kinds to `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [ ] T011 Add `MediaRevision` model and revision links in `apps/server/src/twobrain_rec_server/db/models/ingest.py`
- [ ] T012 Update model exports for media revision entities in `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T013 Add Alembic migration `0008_recording_sync_transcription_loop.py` in `apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py`
- [ ] T014 Add revision-aware Pydantic schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T015 Add revision service helpers in `apps/server/src/twobrain_rec_server/ingest/media_revisions.py`
- [ ] T016 Add desktop queue v2 fields and conflict enum in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [ ] T017 Add queue v1-to-v2 migration behavior in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T018 Add diagnostic redaction coverage for revision/sync fields in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [ ] T019 Update committed API contract reference for revision-aware ingest in `specs/012-server-ingest-foundation/contracts/openapi.yaml`

**Checkpoint**: Media revision identity, queue v2 shape, and server contract
surface are available for story work.

---

## Phase 3: User Story 1 - Record Offline And Preserve The Local Package (Priority: P1)

**Goal**: Recording works without network, and the local package plus queue
state survive restart with no false server success.

**Independent Test**: Disable upload client/network, create a completed local
package, restart queue service, and verify package identity, initial
`localMediaRevisionId`, queue state, local files, and safe blocked/retry truth.

### Tests

- [ ] T020 [P] [US1] Add offline enqueue/restart tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [ ] T021 [P] [US1] Add local package eligibility tests for blocked/degraded recordings in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [ ] T022 [P] [US1] Add desktop capture/upload copy tests for local-only states in `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation

- [ ] T023 [US1] Generate deterministic `localMediaRevisionId` during queue item creation in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T024 [US1] Preserve non-terminal local artifacts and queue state across service reload in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T025 [US1] Add local-only and blocked upload labels in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T026 [US1] Surface local queue rows without server success claims in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [ ] T027 [US1] Record US1 validation evidence in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`

**Checkpoint**: US1 can be validated without server availability.

---

## Phase 4: User Story 2 - Keep One Meeting With Revision-Ready Media Truth (Priority: P1)

**Goal**: Each recording has one logical meeting and one accepted initial media
revision; retries do not duplicate meetings or mutate accepted media.

**Independent Test**: Create/retry the same local recording repeatedly and
verify one server meeting, one initial media revision, immutable revision
fingerprints, and no duplicate upload/processing records.

### Tests

- [ ] T028 [P] [US2] Add server tests for idempotent meeting and media revision creation in `apps/server/tests/integration/test_media_revision_identity.py`
- [ ] T029 [P] [US2] Add server tests for immutable accepted revision fingerprints in `apps/server/tests/unit/test_media_revision_state_machine.py`
- [ ] T030 [P] [US2] Add desktop tests preserving meeting/revision ids across re-enqueue in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation

- [ ] T031 [US2] Create or reuse initial media revision during meeting creation in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [ ] T032 [US2] Implement media revision creation/reuse rules in `apps/server/src/twobrain_rec_server/ingest/media_revisions.py`
- [ ] T033 [US2] Include media revision identity in meeting responses in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T034 [US2] Bind upload sessions to media revisions in `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [ ] T035 [US2] Bind track artifacts and manifest snapshots to media revisions in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [ ] T036 [US2] Persist server `mediaRevisionId` into desktop queue truth in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T037 [US2] Record US2 validation evidence in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`

**Checkpoint**: US2 proves revision-ready identity without edit/trim runtime.

---

## Phase 5: User Story 3 - Resume Upload With Client/Server Consistency (Priority: P1)

**Goal**: Upload resumes from server accepted ranges/checksums and finalizes
exactly one accepted media revision.

**Independent Test**: Interrupt upload at multiple offsets, repeat and corrupt
parts in controlled tests, reconnect, and verify missing-range repair,
idempotent part acceptance, and safe blocking on mismatch.

### Tests

- [ ] T038 [P] [US3] Add server sync-state contract tests in `apps/server/tests/contract/test_recording_sync_contract.py`
- [ ] T039 [P] [US3] Add upload resume and expired-session integration tests in `apps/server/tests/integration/test_recording_sync_upload_resume.py`
- [ ] T040 [P] [US3] Add desktop client reconciliation tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [ ] T041 [P] [US3] Add checksum mismatch tests in `apps/server/tests/unit/test_upload_idempotency.py`

### Implementation

- [ ] T042 [US3] Add desktop sync-state service in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [ ] T043 [US3] Expose `GET /api/v1/desktop/recordings/{local_recording_id}/sync-state` in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T044 [US3] Return revision-aware accepted bytes and conflict states in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [ ] T045 [US3] Reconcile before upload attempts in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T046 [US3] Persist reconciliation truth and conflict states in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T047 [US3] Handle expired sessions and missing ranges without duplicate meetings in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T048 [US3] Record US3 validation evidence in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`

**Checkpoint**: US3 proves reconnect/resume consistency.

---

## Phase 6: User Story 4 - Process And Display Transcript In Web And Desktop (Priority: P1)

**Goal**: Accepted uploads are processed once per media revision and transcript
truth appears consistently in browser and embedded desktop review.

**Independent Test**: Finalize an upload, run processing pickup with fake
Temporal/MediaScribe, import synthetic transcript, open web and desktop routes,
and verify matching meeting/revision/transcript/provenance truth.

### Tests

- [ ] T049 [P] [US4] Add revision-keyed processing workflow tests in `apps/server/tests/unit/test_processing_workflow_identity.py`
- [ ] T050 [P] [US4] Add processing pickup integration tests for media revisions in `apps/server/tests/integration/test_recording_sync_processing.py`
- [ ] T051 [P] [US4] Add cabinet API contract tests for media revision provenance in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T052 [P] [US4] Add desktop embedded review link tests for revision-aware queue items in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [ ] T053 [P] [US4] Add review accessibility, localization, and compact-width contract tests in `apps/server/tests/contract/test_cabinet_contract.py`
- [ ] T054 [P] [US4] Add embedded desktop review accessibility and status-link tests in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`

### Implementation

- [ ] T055 [US4] Key processing workflow identity by `media_revision_id` in `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [ ] T056 [US4] Bind processing workflows and jobs to media revisions in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [ ] T057 [US4] Bind MediaScribe job submit/import records to media revisions in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T058 [US4] Include media revision provenance in processing status responses in `apps/server/src/twobrain_rec_server/processing/status.py`
- [ ] T059 [US4] Include media revision provenance in cabinet queries and view models in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T060 [US4] Render revision-aware status in cabinet web templates in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T061 [US4] Open revision-aware uploaded queue items in embedded review in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`
- [ ] T062 [US4] Apply localization-safe accessible status labels and compact-width review behavior in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T063 [US4] Apply embedded desktop review accessibility and status-link behavior in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [ ] T064 [US4] Record US4 validation evidence in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`

**Checkpoint**: US4 proves upload-to-transcript-to-review value loop.

---

## Phase 7: User Story 5 - Make Out-Of-Sync States Visible And Recoverable (Priority: P1)

**Goal**: Local/server mismatches are visible, safe, and recoverable without
silent overwrite, duplicate processing, or false success.

**Independent Test**: Simulate deleted local files, changed checksums, revoked
access, deleted server meeting, expired auth, stale device identity, expired
upload session, and processing failure; verify safe labels and next actions.

### Tests

- [ ] T065 [P] [US5] Add desktop conflict-state tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [ ] T066 [P] [US5] Add server sync conflict integration tests in `apps/server/tests/integration/test_recording_sync_conflicts.py`
- [ ] T067 [P] [US5] Add cabinet blocked/failed state tests in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [ ] T068 [P] [US5] Add desktop UX copy tests for conflict states in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [ ] T069 [P] [US5] Add infrastructure dependency failure tests for object-store writes, DB transactions, workflow start, MediaScribe, cabinet timeout, and expired upload sessions in `apps/server/tests/integration/test_recording_sync_conflicts.py`
- [ ] T070 [P] [US5] Add local disk-full and temporary upload cleanup tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation

- [ ] T071 [US5] Map server sync conflicts to safe desktop states in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [ ] T072 [US5] Apply conflict transitions in queue update paths in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T073 [US5] Return auth/access/deletion/session conflict states from `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [ ] T074 [US5] Show conflict-safe queue copy and next actions in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T075 [US5] Show blocked/failed review status without fake transcript in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T076 [US5] Map dependency-unavailable infrastructure failures to safe sync-state responses in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [ ] T077 [US5] Show disk-full, temporary cleanup, and dependency-failure next actions without private paths in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T078 [US5] Record US5 validation evidence in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`

**Checkpoint**: US5 proves mismatch recovery and no silent drift.

---

## Phase 8: User Story 6 - Preserve Privacy, Security, And Lifecycle Truth (Priority: P1)

**Goal**: The loop preserves local buffer, server storage, MediaScribe,
Langfuse, deletion, diagnostics, evidence, and tenant-isolation boundaries.

**Independent Test**: Inspect synthetic logs, diagnostics, API responses,
evidence, RLS behavior, and deletion/lifecycle state after success/failure
flows; verify no forbidden content leaks and lifecycle state is complete.

### Tests

- [ ] T079 [P] [US6] Add no-secret/no-content contract tests for recording sync in `apps/server/tests/contract/test_recording_sync_no_secret_egress.py`
- [ ] T080 [P] [US6] Add diagnostic redaction tests for queue/revision fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [ ] T081 [P] [US6] Add lifecycle/deletion accounting tests for media revisions in `apps/server/tests/integration/test_recording_sync_lifecycle.py`
- [ ] T082 [P] [US6] Add RLS enforcement tests for media revisions in `apps/server/tests/integration/test_rls_media_revision_policies.py`

### Implementation

- [ ] T083 [US6] Add media revision lifecycle state updates in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [ ] T084 [US6] Include media revision artifacts in deletion dependency reporting in `apps/server/src/twobrain_rec_server/processing/lifecycle.py`
- [ ] T085 [US6] Redact queue/revision diagnostics on desktop in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [ ] T086 [US6] Add RLS policy declarations for media revision tables in `apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py`
- [ ] T087 [US6] Add metadata-only evidence scan notes in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`
- [ ] T088 [US6] Update release notes for `042` in `CHANGELOG.md`

**Checkpoint**: US6 proves privacy/lifecycle boundaries for the complete loop.

---

## Phase 9: Polish And Validation

**Purpose**: Run cross-story validation and prepare implementation closure.

- [ ] T089 Run focused macOS validation from `specs/042-recording-sync-transcription-loop/quickstart.md`
- [ ] T090 Run focused server validation from `specs/042-recording-sync-transcription-loop/quickstart.md`
- [ ] T091 Run `infra/scripts/ci-local.sh` and record result in `specs/042-recording-sync-transcription-loop/validation/implementation-evidence.md`
- [ ] T092 Review `specs/042-recording-sync-transcription-loop/contracts/desktop-sync-contract.md` against implemented desktop/server behavior
- [ ] T093 Review `specs/042-recording-sync-transcription-loop/contracts/media-revision-contract.md` against implemented schema and processing behavior
- [ ] T094 Review `specs/042-recording-sync-transcription-loop/contracts/review-surface-contract.md` against web and embedded desktop behavior
- [ ] T095 Update `docs/current-product-status.md` with accepted `042` implementation status and remaining gaps
- [ ] T096 Scan `specs/042-recording-sync-transcription-loop/validation` for forbidden private content before commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies.
- **Phase 2 Foundational**: depends on Phase 1; blocks all user stories.
- **US1**: depends on Phase 2; can validate without live server.
- **US2**: depends on Phase 2; should complete before US3/US4 for canonical
  media revision identity.
- **US3**: depends on US2 for revision-aware upload session behavior.
- **US4**: depends on US2 and server finalization path; can use synthetic
  finalized fixtures while US3 is still under active implementation.
- **US5**: depends on US2/US3 contracts; can start once sync-state API exists.
- **US6**: depends on Phase 2 and should run in parallel review with each story,
  but final closure depends on US1-US5 evidence.
- **Polish**: depends on desired story scope completion.

### User Story Dependencies

- **US1**: local-only MVP slice; no dependency on other stories after foundation.
- **US2**: identity foundation for upload/processing/review.
- **US3**: requires US2 media revision identity.
- **US4**: requires accepted media revision and processing pipeline.
- **US5**: requires sync-state and status surfaces from US3/US4.
- **US6**: cross-cutting privacy/lifecycle validation over all stories.

### Parallel Opportunities

- T002-T004 can run in parallel after T001.
- T006-T009 can run in parallel as failing tests.
- T010-T019 touch different server/desktop files and can be split after test
  expectations are agreed.
- Tests inside each user story marked `[P]` can run in parallel.
- US1 desktop work and US2 server identity work can proceed in parallel after
  Phase 2 if integration points remain contract-compatible.
- US6 tests can be drafted in parallel with US3-US5, but final implementation
  evidence waits for all paths.

## Parallel Example: US3

```text
Task: "T038 [US3] Add server sync-state contract tests in apps/server/tests/contract/test_recording_sync_contract.py"
Task: "T039 [US3] Add upload resume and expired-session integration tests in apps/server/tests/integration/test_recording_sync_upload_resume.py"
Task: "T040 [US3] Add desktop client reconciliation tests in apps/macos/Shared/Tests/DesktopUploadQueueTests.swift"
Task: "T041 [US3] Add checksum mismatch tests in apps/server/tests/unit/test_upload_idempotency.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to prove offline local package retention.
3. Complete US2 to prove one meeting and initial media revision identity.
4. Complete US3 to prove reconnect/resume upload.
5. Complete US4 to prove transcript display in web and desktop.
6. Complete US5/US6 before any launch-readiness claim.

### Stop Points

- Stop after US1 if local offline recording/queue retention is the only desired
  demo.
- Stop after US3 if upload consistency is ready but processing/display still
  needs dependency validation.
- Do not claim MVP loop completion until US4, US5, US6, quickstart, and
  `infra/scripts/ci-local.sh` evidence are complete.

## Notes

- `[P]` means different files and no dependency on incomplete tasks.
- All implementation tasks include concrete repo-relative paths.
- Tests should fail before implementation when the behavior is not yet present.
- Editing, trimming, video capture, transcript editing, speaker editing,
  replace, restore, and reprocess remain reserved for `044`-`047`, not `042`.
