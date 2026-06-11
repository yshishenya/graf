# Tasks: Desktop Upload Queue And Resilient Upload Behavior

**Input**: Design documents from `specs/014-desktop-upload-queue/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, completed checklists, and clean analyze pass.

**Tests**: Required. This feature touches persistence, upload truth,
server-mediated ingest, diagnostics, privacy boundaries, and user-facing
recovery UI.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Prepare feature evidence and validation scaffolding.

- [X] T001 Create desktop upload queue evidence file in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #512)
- [X] T002 [P] Add desktop upload validation script in `apps/macos/Scripts/validate-desktop-upload-queue.sh` (GH #513)
- [X] T003 [P] Add upload queue audit events in `apps/macos/Shared/Sources/Audit/AuditEvents.swift` (GH #514)

## Phase 2: Foundational

**Purpose**: Shared upload truth models, persistence, redaction, and role mapping.

- [X] T004 [P] Add upload queue state, failure, retry, artifact profile, retry record, server truth, retention decision, and queue item models in `apps/macos/Shared/Sources/Models/AudioModels.swift` (GH #515)
- [X] T005 [P] Extend upload state vocabulary for retrying, degraded, blocked, and terminal deleted in `apps/macos/Shared/Sources/Models/AudioStates.swift` (GH #516)
- [X] T006 [P] Add upload queue model and transition tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift` (GH #517)
- [X] T007 Add durable queue persistence, local package discovery, role mapping, and state transition logic in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (GH #518)
- [X] T008 Add diagnostic allowlist coverage for upload queue metadata in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift` (GH #519)
- [X] T009 [P] Add upload queue diagnostic redaction tests in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift` (GH #520)

## Phase 3: User Story 1 - Auto-queue Completed Recordings for Upload (Priority: P1)

**Goal**: Every completed local package is queued automatically on finalization or app launch.

**Independent Test**: Create a local package, relaunch app/service, and verify one durable queue item with the same package identity appears without deleting local artifacts.

- [X] T010 [P] [US1] Add local package discovery tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift` (GH #521)
- [X] T011 [US1] Hook app launch queue scan into `apps/macos/RecApp/App/TwoBrainRecApp.swift` (GH #522)
- [X] T012 [US1] Hook successful/degraded local recording finalization enqueue into `apps/macos/RecApp/App/TwoBrainRecApp.swift` (GH #523)

## Phase 4: User Story 2 - Expose Truthful Upload State and Retry Progress (Priority: P1)

**Goal**: Users see queued/uploading/retrying/uploaded/degraded/failed/blocked truth and retryability.

**Independent Test**: Simulate transient failure and verify state, reason, next retry, and local artifact retention.

- [X] T013 [P] [US2] Add retry and failure-classification tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift` (GH #524)
- [X] T014 [US2] Implement retry scheduler and failure classification in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (GH #525)
- [X] T015 [US2] Add compact upload queue status UI to `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift` (GH #526)
- [X] T016 [US2] Wire queue status, retry, and stop retry actions from app state in `apps/macos/RecApp/App/TwoBrainRecApp.swift` (GH #527)

## Phase 5: User Story 3 - Resume Without Duplication (Priority: P1)

**Goal**: Upload resumes from accepted/missing server truth without duplicate finalization.

**Independent Test**: Simulate partial accepted bytes, missing ranges, retry, and repeated finalize.

- [X] T017 [P] [US3] Add upload client request/mapping tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift` (GH #528)
- [X] T018 [US3] Implement `012` API client, SHA256 part evidence, idempotency keys, and missing-range reconciliation in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` (GH #529)
- [X] T019 [US3] Integrate uploader client into queue worker in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (GH #530)

## Phase 6: User Story 4 - Preserve Local Data Through Recovery Windows (Priority: P2)

**Goal**: Local artifacts remain while upload truth is recoverable or manual-only.

**Independent Test**: Expire retry window and verify manual-only blocked state with local artifacts retained.

- [X] T020 [P] [US4] Add retention-deadline and terminal-state tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift` (GH #531)
- [X] T021 [US4] Implement retry-expiry/manual-only retention decisions in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (GH #532)

## Phase 7: User Story 5 - Preserve Ownership and Security Boundaries (Priority: P2)

**Goal**: Queue behavior stays inside owner-controlled ingest and diagnostics remain secret-free.

**Independent Test**: Scan diagnostics and upload code for forbidden direct STT/object-store paths and secret leakage.

- [X] T022 [P] [US5] Add contract validation coverage for upload queue redaction and backend role mapping in `apps/macos/Shared/Tools/ContractValidation/main.swift` (GH #533)
- [X] T023 [US5] Ensure upload diagnostics and audit logs use safe queue metadata only in `apps/macos/RecApp/App/TwoBrainRecApp.swift` (GH #534)
- [X] T031 [US5] Add ephemeral bearer header support for production ingest in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` (GH #535)
- [X] T032 [P] [US5] Add bearer header tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift` (GH #536)
- [X] T034 [US5] Pass production smoke bearer credentials by token file path in `apps/server/scripts/upload_test_artifact.py` and `infra/scripts/run-production-smoke.sh` (GH #537)
- [X] T035 [P] [US5] Expand upload bearer redaction coverage in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift` (GH #538)
- [X] T036 [US5] Add production smoke AuthSession issuance helper in `apps/server/scripts/issue_smoke_auth_session.py` (GH #539)
- [X] T037 [US5] Update production smoke runner cleanup to mint a temporary AuthSession, read bearer only from a token file, and remove auth residue in `infra/scripts/run-production-smoke.sh` and `apps/server/scripts/cleanup_smoke_auth_session.py` (GH #540)
- [X] T038 [P] [US5] Add regression coverage for AuthSession-per-smoke runner behavior and auth cleanup ordering in `apps/server/tests/integration/test_production_smoke_boundary.py`, `apps/server/tests/integration/test_upload_helper_contract.py`, and `apps/server/tests/unit/test_smoke_cleanup.py` (GH #541)

## Phase 8: Final Validation And Audit

**Purpose**: Run quality gates and record evidence.

- [X] T024 Run `swift build` from `apps/macos` and record result in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #542)
- [X] T025 Run `swift test` from `apps/macos` and record result in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #543)
- [X] T026 Run `swift run ContractValidation` from `apps/macos` and record result in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #544)
- [X] T027 Run forbidden-content scan and record result in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #545)
- [X] T028 Run `apps/macos/Scripts/validate-desktop-upload-queue.sh` and record result in `specs/014-desktop-upload-queue/evidence/test-results.md` (GH #546)
- [X] T029 Perform final feature audit against spec, plan, tasks, contracts, and quickstart in `specs/014-desktop-upload-queue/analysis.md` (GH #547)
- [X] T030 Update `[Unreleased]` changelog entry for feature `014` in `CHANGELOG.md` (GH #548)
- [X] T033 Record production URL, smoke identity, and bearer handling in `specs/014-desktop-upload-queue/quickstart.md` (GH #549)

## Dependencies & Execution Order

- Phase 1 setup has no dependencies.
- Phase 2 foundational tasks block all user stories.
- US1 must complete before user-visible queue status is meaningful.
- US2 can run after US1 and foundational state model.
- US3 depends on role mapping and queue worker state from US1/US2.
- US4 depends on retry state and retention fields from Phase 2.
- US5 can proceed once diagnostics and upload client metadata exist.
- Final validation depends on all implementation tasks.

## Parallel Opportunities

- T002 and T003 can run in parallel.
- T004, T005, T006, and T009 can run in parallel.
- T010 can run in parallel with T011 after T007 exists.
- T013 and T017 can run in parallel after foundational models.
- T020 and T022 can run in parallel after core queue metadata exists.

## Implementation Strategy

1. Complete metadata and persistence first.
2. Make local package discovery and enqueue independently testable.
3. Add retry truth and UI before live server upload.
4. Add server-mediated client with role mapping and idempotency.
5. Finish retention/security boundaries, then run validation and audit.
