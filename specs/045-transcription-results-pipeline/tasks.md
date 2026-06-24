# Tasks: Transcription Results Pipeline

**Input**: Design documents from `specs/045-transcription-results-pipeline/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included because this feature touches capture-derived upload gating, server-owned MediaScribe processing, privacy boundaries, and user-visible result delivery.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`, `US4`)
- Every task includes an exact repository path

## Phase 1: Setup

**Purpose**: Establish feature-specific evidence and focused test fixtures without changing product behavior.

- [X] T001 Create metadata-safe validation log scaffold in `specs/045-transcription-results-pipeline/evidence/validation-log.md`
- [X] T002 [P] Add or extend local package fixture helpers for quality-warning upload cases in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T003 [P] Add or extend server fake processing pickup helpers for finalize auto-start tests in `apps/server/tests/fixtures/processing.py`
- [X] T004 [P] Add checklist review notes for gate boundary readiness in `specs/045-transcription-results-pipeline/checklists/pipeline.md`

---

## Phase 2: Foundational

**Purpose**: Keep package integrity and privacy boundaries explicit before user-story implementation.

- [X] T005 Add contract coverage for "quality warning is not upload blocker" and "integrity remains blocker" in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T006 Add contract coverage that server finalization still rejects role, byte-length, checksum, and fingerprint mismatches in `apps/server/tests/integration/test_finalize_integrity.py`
- [X] T007 Add content-safe processing auto-start audit expectations in `apps/server/tests/contract/test_processing_status_contract.py`
- [X] T008 Update `CHANGELOG.md` with an unreleased metadata-safe entry for the 045 pipeline behavior change

**Checkpoint**: Foundation ready - story implementation can begin while preserving integrity and privacy gates.

---

## Phase 3: User Story 1 - Upload Imperfect Recordings For Transcription (Priority: P1) MVP

**Goal**: Structurally valid packages are eligible for upload/transcription even when local quality, leakage, echo, silence, timing, or transcription-readiness is imperfect.

**Independent Test**: A valid package with degraded/failed local quality readiness is queued/upload eligible, while missing files, consent failure, permission failure, and integrity failures remain blocked.

### Tests for User Story 1

- [X] T009 [P] [US1] Add failing tests for leakage-detected but structurally valid package eligibility in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T010 [P] [US1] Add failing tests for leakage-unproven, leakage-not-measured, insufficient-reference, timeline-misaligned, and silent-input eligibility in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T011 [P] [US1] Add failing tests proving missing microphone/system files, consent denial, and permission denial remain blocked in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T012 [P] [US1] Add diagnostic redaction coverage for newly non-blocking quality states in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`

### Implementation for User Story 1

- [X] T013 [US1] Replace local upload eligibility logic in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` so `transcriptionReadiness`, leakage gates, timeline/duration mismatch, silence, and AEC/derived cleanup outcome are diagnostic-only for structurally valid packages
- [X] T014 [US1] Narrow hard-block failure reasons in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` to privacy, permission, missing/unreadable file, write/finalization, protected audio, device/capture, legacy, app-closed, and unknown safety failures
- [X] T015 [US1] Preserve quality warning metadata in queued item creation and refresh merge behavior in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T016 [US1] Update local manifest expectations affected by the gate decision in `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- [X] T017 [US1] Update local manifest expectations affected by transcription readiness semantics in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [X] T018 [US1] Record metadata-safe US1 validation results in `specs/045-transcription-results-pipeline/evidence/validation-log.md`

**Checkpoint**: User Story 1 is independently testable and can be shipped as the MVP gate fix.

---

## Phase 4: User Story 2 - Start Processing Automatically After Accepted Upload (Priority: P1)

**Goal**: Accepted server uploads create or reuse one processing attempt automatically when processing is enabled.

**Independent Test**: Finalizing a valid upload starts/reuses processing without manually calling the internal pickup endpoint, and dependency failures show processing status without undoing upload success.

### Tests for User Story 2

- [X] T019 [P] [US2] Add failing finalize auto-start happy-path test in `apps/server/tests/integration/test_finalize_processing_autostart.py`
- [X] T020 [P] [US2] Add failing finalize auto-start dependency-unavailable test in `apps/server/tests/integration/test_finalize_processing_autostart.py`
- [X] T021 [P] [US2] Add failing duplicate finalize/pickup reuse test in `apps/server/tests/integration/test_processing_pickup.py`
- [X] T022 [P] [US2] Update ingest OpenAPI contract expectations for processing-enabled and processing-disabled finalize responses in `apps/server/tests/contract/test_ingest_openapi_contract.py`

### Implementation for User Story 2

- [X] T023 [US2] Add processing dispatch helper for finalize-triggered pickup in `apps/server/src/twobrain_rec_server/ingest/processing_dispatch.py`
- [X] T024 [US2] Call processing dispatch after accepted finalization when processing is enabled in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T025 [US2] Populate `workflow_started` and `mediascribe_job_created` truthfully in finalize response in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T026 [US2] Ensure finalize-triggered blocked dependency state preserves upload success in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [X] T027 [US2] Ensure processing workflow reuse audit metadata stays content-safe in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [X] T028 [US2] Record metadata-safe US2 validation results in `specs/045-transcription-results-pipeline/evidence/validation-log.md`

**Checkpoint**: User Story 2 is independently testable through server finalize + processing status.

---

## Phase 5: User Story 3 - See Transcript And Diarization Results In Web And Desktop (Priority: P1)

**Goal**: Imported transcript and diarization availability are visible and consistent in web cabinet and desktop embedded review.

**Independent Test**: A processed meeting shows matching transcript availability, diarization availability, media revision identity, and safe processing status in web and desktop review.

### Tests for User Story 3

- [X] T029 [P] [US3] Add cabinet review assertion after MediaScribe happy-path import in `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- [X] T030 [P] [US3] Add desktop sync review-ready state coverage in `apps/server/tests/integration/test_degraded_ingest.py`
- [X] T031 [P] [US3] Add web/desktop review parity coverage for ready, partial, blocked, and failed states in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T032 [P] [US3] Add desktop review link coverage for processed upload queue items in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`

### Implementation for User Story 3

- [X] T033 [US3] Ensure processing status and review availability are returned in desktop sync state in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [X] T034 [US3] Ensure cabinet review query binds latest result to accepted media revision in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T035 [US3] Ensure review view models expose ready, partial, blocked, failed, and running state consistently in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T036 [US3] Ensure desktop cabinet review link resolves processed meetings from upload queue context in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`
- [X] T037 [US3] Record metadata-safe US3 validation results in `specs/045-transcription-results-pipeline/evidence/validation-log.md`

**Checkpoint**: User Story 3 is independently testable through imported fake result and review surfaces.

---

## Phase 6: User Story 4 - Preserve Privacy And Content Boundaries (Priority: P1)

**Goal**: Status, diagnostics, logs, and evidence remain metadata-safe while processing and review become observable.

**Independent Test**: Success, degraded, dependency-blocked, and failed flows expose safe status and no raw audio, transcript text, credentials, signed URLs, secret paths, or private local paths outside controlled content stores.

### Tests for User Story 4

- [X] T038 [P] [US4] Add no-secret/no-content assertions for new finalize auto-start payloads in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [X] T039 [P] [US4] Add redaction assertions for processing dispatch/audit metadata in `apps/server/tests/contract/test_rls_evidence_contract.py`
- [X] T040 [P] [US4] Add macOS diagnostic bundle assertions for newly diagnostic-only quality states in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`

### Implementation for User Story 4

- [X] T041 [US4] Redact and bound any new processing dispatch audit metadata in `apps/server/src/twobrain_rec_server/processing/audit.py`
- [X] T042 [US4] Ensure new status/reason fields avoid transcript text and private provider payloads in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T043 [US4] Ensure macOS diagnostics keep quality warnings metadata-only in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [X] T044 [US4] Record metadata-safe US4 validation results in `specs/045-transcription-results-pipeline/evidence/validation-log.md`

**Checkpoint**: User Story 4 proves observability without content or secret leakage.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, docs, and release-readiness updates.

- [X] T045 [P] Update `docs/current-product-status.md` with the 045 gate and pipeline status after validation
- [X] T046 [P] Update `docs/audio-capture-backlog.md` to point AEC/noise work back to 044 and product pipeline work to 045
- [X] T047 [P] Update `docs/post-mvp-editing-media-backlog.md` if any reprocess/derived-revision follow-up is discovered during implementation
- [X] T048 Run focused macOS validation from `specs/045-transcription-results-pipeline/quickstart.md`
- [X] T049 Run focused server validation from `specs/045-transcription-results-pipeline/quickstart.md`
- [X] T050 Run one-hour orchestration benchmark from `specs/045-transcription-results-pipeline/quickstart.md`
- [X] T051 Run full local gate `infra/scripts/ci-local.sh`
- [X] T052 Finalize `specs/045-transcription-results-pipeline/evidence/validation-log.md` with metadata-safe command results and known limitations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1.
- **User Stories (Phases 3-6)**: Depend on Phase 2.
- **Polish (Phase 7)**: Depends on completed target user stories.

### User Story Dependencies

- **US1**: First MVP slice. Required before product behavior can send imperfect-but-valid packages.
- **US2**: Depends on server integrity foundation; can start after Phase 2, but final product value assumes US1 behavior.
- **US3**: Depends on imported processing results from US2 for full end-to-end proof.
- **US4**: Can run in parallel with US2/US3 after Phase 2, but final proof depends on all status/result fields.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel.
- T009-T012 can be written in parallel before US1 implementation.
- T019-T022 can be written in parallel before US2 implementation.
- T029-T032 can be written in parallel before US3 implementation.
- T038-T040 can be written in parallel before US4 implementation.
- T045-T047 can run in parallel after implementation behavior is known.

---

## Parallel Example: User Story 1

```bash
Task: "Add failing leakage-detected eligibility tests in apps/macos/Shared/Tests/DesktopUploadQueueTests.swift"
Task: "Add failing diagnostic redaction coverage in apps/macos/Shared/Tests/DiagnosticRedactionTests.swift"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to remove the local quality blocker while preserving privacy and integrity blockers.
3. Validate US1 independently with focused macOS tests.
4. Continue to US2 for automatic processing pickup.

### Incremental Delivery

1. US1: valid imperfect packages can upload.
2. US2: accepted uploads automatically start/reuse processing.
3. US3: results appear consistently in review surfaces.
4. US4: privacy/content boundaries are proven across the new flow.

### Validation Discipline

- Write failing tests before implementation for each story.
- Mark tasks `[X]` only after focused validation for that task/story passes.
- Do not commit raw audio, transcript text, private meeting content, credentials, signed URLs, or private local paths.
