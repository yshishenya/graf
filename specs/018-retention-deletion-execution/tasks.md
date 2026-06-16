# Tasks: Retention And Deletion Execution

**Input**: Design documents from `specs/018-retention-deletion-execution/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included before implementation because this feature touches deletion, retention, audit, local purge, dependency truth, and launch-readiness gates.

**Organization**: Tasks are grouped by user story so each increment can be independently implemented, validated, reviewed, and closed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when touching different files with no dependency on incomplete tasks.
- **[Story]**: Maps to the user stories in `spec.md`.
- Every task includes an exact repository path.

## Phase 1: Setup

**Purpose**: Add feature scaffolding and fixtures without changing behavior yet.

- [ ] T001 Create deletion domain package skeleton in `apps/server/src/twobrain_rec_server/deletion/__init__.py`
- [ ] T002 [P] Create deletion test fixture skeleton in `apps/server/tests/fixtures/deletion_lifecycle.py`
- [ ] T003 [P] Create desktop local purge Swift test skeleton in `apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift`

---

## Phase 2: Foundational

**Purpose**: Shared persistence, schemas, lifecycle enums, RLS, audit, and report plumbing that block all user stories.

- [ ] T004 Add deletion lifecycle, artifact, retention, local purge, and audit enums in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [ ] T005 Add deletion SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/deletion.py`
- [ ] T006 Export deletion models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T007 Add meeting deletion and retention lifecycle columns in `apps/server/src/twobrain_rec_server/db/models/meeting.py`
- [ ] T008 Create retention/deletion migration in `apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py`
- [ ] T009 Update RLS validation table inventory for lifecycle tables in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [ ] T010 Add lifecycle/report/retention/local-purge Pydantic schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T011 Implement metadata-only lifecycle audit helpers in `apps/server/src/twobrain_rec_server/deletion/audit.py`
- [ ] T012 Implement lifecycle report row composition primitives in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [ ] T013 [P] Add migration and RLS coverage in `apps/server/tests/integration/test_retention_deletion_migrations.py`
- [ ] T014 [P] Add schema and no-secret contract coverage in `apps/server/tests/contract/test_deletion_no_secret_leakage.py`
- [ ] T015 [P] Add audit metadata unit tests in `apps/server/tests/unit/test_deletion_audit_metadata.py`

**Checkpoint**: Shared deletion/retention entities, lifecycle schemas, audit helpers, and RLS expectations are ready before story work starts.

---

## Phase 3: User Story 1 - Delete A Whole Meeting With Truthful Scope (Priority: P1) MVP

**Goal**: Owners/admins can delete a whole meeting, access is blocked as soon as deletion starts, active server purge is accounted for, and a truthful report replaces original content.

**Independent Test**: Create a ready meeting with MVP artifacts, request deletion as owner, verify lifecycle enters deleting, normal review/share/download/export content is blocked, controlled server artifacts are purged or explicitly failed, and the report explains covered and uncovered classes.

### Tests for User Story 1

- [ ] T016 [P] [US1] Add deletion request/report API contract tests in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T017 [P] [US1] Add manual deletion workflow integration tests in `apps/server/tests/integration/test_meeting_deletion_workflow.py`
- [ ] T018 [P] [US1] Add lifecycle access-blocking integration tests in `apps/server/tests/integration/test_deletion_lifecycle_blocks_access.py`
- [ ] T019 [P] [US1] Add deletion report view-model unit tests in `apps/server/tests/unit/test_deletion_report_view_models.py`

### Implementation for User Story 1

- [ ] T020 [US1] Implement deletion request validation and fail-closed audit ordering in `apps/server/src/twobrain_rec_server/deletion/service.py`
- [ ] T021 [US1] Implement active server purge accounting for meeting artifacts in `apps/server/src/twobrain_rec_server/deletion/service.py`
- [ ] T022 [US1] Implement deletion verification report assembly in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [ ] T023 [US1] Add deletion request, lifecycle, report, and retry routes in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T024 [US1] Block deleted/deleting meetings in effective access decisions in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [ ] T025 [US1] Hide deleted/deleting meetings from normal list queries by default in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T026 [US1] Block artifact egress for deleting/deleted meetings in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [ ] T027 [US1] Map deletion lifecycle and governance states in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T028 [US1] Render bounded delete confirmation and report states in `apps/server/src/twobrain_rec_server/cabinet/web.py`

**Checkpoint**: User Story 1 is independently functional and prevents content access after deletion starts.

---

## Phase 4: User Story 2 - Run Retention Jobs Without Surprises (Priority: P1)

**Goal**: Retention scans evaluate policy snapshots, create deletion lifecycle actions only for eligible meetings, and skip or block unsafe states with metadata-only audit.

**Independent Test**: Seed retained, expired, processing, already deleting, already deleted, policy-blocked, and unsafe-policy meetings; run retention scan; verify only eligible meetings receive lifecycle actions and all skips/blocks are auditable.

### Tests for User Story 2

- [ ] T029 [P] [US2] Add retention run API contract tests in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T030 [P] [US2] Add retention policy execution integration tests in `apps/server/tests/integration/test_retention_policy_execution.py`
- [ ] T031 [P] [US2] Add retention policy snapshot unit tests in `apps/server/tests/unit/test_retention_policy_snapshot.py`

### Implementation for User Story 2

- [ ] T032 [US2] Implement default/deployment retention policy snapshot resolution in `apps/server/src/twobrain_rec_server/deletion/policy.py`
- [ ] T033 [US2] Implement retention eligibility scan and skip/block reasons in `apps/server/src/twobrain_rec_server/deletion/retention.py`
- [ ] T034 [US2] Reuse deletion request workflow for retention-triggered actions in `apps/server/src/twobrain_rec_server/deletion/retention.py`
- [ ] T035 [US2] Add internal retention run route in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T036 [US2] Add retention lifecycle activity rows to report assembly in `apps/server/src/twobrain_rec_server/deletion/report.py`

**Checkpoint**: User Story 2 is independently functional and retention cannot mutate unsafe or ineligible meetings.

---

## Phase 5: User Story 3 - Coordinate Local Desktop Purge (Priority: P1)

**Goal**: Server deletion creates local purge tasks for relevant devices, desktop clients can acknowledge metadata-only purge outcomes, and reports distinguish server purge from local purge truth.

**Independent Test**: Create deletion reports with acknowledged, pending, unreachable, failed, and local-expiry-relied-upon device states; verify report truth and device-scoped API behavior.

### Tests for User Story 3

- [ ] T037 [P] [US3] Add local purge API contract tests in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T038 [P] [US3] Add local purge coordination integration tests in `apps/server/tests/integration/test_local_purge_coordination.py`
- [ ] T039 [P] [US3] Add desktop local purge Swift client tests in `apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift`

### Implementation for User Story 3

- [ ] T040 [US3] Implement local purge task creation and report state mapping in `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
- [ ] T041 [US3] Add desktop local purge task list and ack routes in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T042 [US3] Reject private/local-path acknowledgement payloads in `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
- [ ] T043 [US3] Add local purge task models to desktop upload client in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T044 [US3] Add local purge acknowledgement coordination in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T045 [US3] Render local purge pending/acknowledged/unreachable states in `apps/server/src/twobrain_rec_server/cabinet/web.py`

**Checkpoint**: User Story 3 is independently functional and local purge truth is visible without private proof uploads.

---

## Phase 6: User Story 4 - Report External Dependency And Backup Limits (Priority: P1)

**Goal**: Deletion reports show MediaScribe, Langfuse, workflow/temp, diagnostics, backup expiry, exports, integrations, and post-egress limits without overstating deletion.

**Independent Test**: Delete meetings with dependency states including not submitted, delete requested, confirmed, unsupported, unknown, metadata-only, content-bearing trace required, backup pending expiry, and backup expiry complete; verify bounded report wording.

### Tests for User Story 4

- [ ] T046 [P] [US4] Add dependency and backup state contract tests in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T047 [P] [US4] Add dependency deletion state unit tests in `apps/server/tests/unit/test_dependency_deletion_states.py`
- [ ] T048 [P] [US4] Add post-egress and backup report integration tests in `apps/server/tests/integration/test_meeting_deletion_workflow.py`

### Implementation for User Story 4

- [ ] T049 [US4] Implement dependency state mapping for MediaScribe, Langfuse, workflow/temp, diagnostics, and backups in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [ ] T050 [US4] Persist post-egress limits from share/download/export audit data in deletion report rows in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [ ] T051 [US4] Add backup expiry policy state to retention policy snapshots in `apps/server/src/twobrain_rec_server/deletion/policy.py`
- [ ] T052 [US4] Render backup, dependency, and post-egress limit rows in `apps/server/src/twobrain_rec_server/cabinet/web.py`

**Checkpoint**: User Story 4 is independently functional and reports do not claim full external purge unless confirmed.

---

## Phase 7: User Story 5 - Preserve Audit And Review History Safely (Priority: P2)

**Goal**: Owners/admins can review metadata-only deletion and retention activity after private content is purged, without turning audit logs into hidden content storage.

**Independent Test**: Execute manual deletion, retention deletion, denied deletion, retryable failure, terminal failure, and local purge acknowledgement flows; verify activity/report events contain metadata only.

### Tests for User Story 5

- [ ] T053 [P] [US5] Add lifecycle activity contract tests in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T054 [P] [US5] Add metadata-only activity integration tests in `apps/server/tests/integration/test_meeting_deletion_workflow.py`
- [ ] T055 [P] [US5] Extend no-secret audit tests in `apps/server/tests/unit/test_deletion_audit_metadata.py`

### Implementation for User Story 5

- [ ] T056 [US5] Add lifecycle audit activity response mapping in `apps/server/src/twobrain_rec_server/deletion/report.py`
- [ ] T057 [US5] Include lifecycle events in cabinet activity surfaces in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T058 [US5] Render metadata-only lifecycle activity in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T059 [US5] Add safe retry guidance for retryable and terminal failures in `apps/server/src/twobrain_rec_server/deletion/service.py`

**Checkpoint**: User Story 5 is independently functional and audit/report evidence remains metadata-only.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Evidence, documentation, release-readiness, and full validation across all stories.

- [ ] T060 [P] Update feature status and launch-readiness notes in `docs/current-product-status.md`
- [ ] T061 [P] Add Unreleased changelog entry for feature 018 in `CHANGELOG.md`
- [ ] T062 [P] Add sanitized screenshot/evidence index in `docs/evidence/018-retention-deletion-execution/README.md`
- [ ] T063 Run focused quickstart validation and record commands/results in `docs/evidence/018-retention-deletion-execution/README.md`
- [ ] T064 Run browser screenshot validation for delete/report states and record sanitized evidence in `docs/evidence/018-retention-deletion-execution/README.md`
- [ ] T065 Run `./infra/scripts/ci-local.sh` and record the result in `docs/evidence/018-retention-deletion-execution/README.md`
- [ ] T066 Review tracked evidence for private content, credentials, signed URLs, object keys, provider payloads, and local paths in `docs/evidence/018-retention-deletion-execution/README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on foundational lifecycle/schema/persistence/audit.
- **User Story 2 (Phase 4)**: Depends on foundational and reuses US1 deletion workflow service.
- **User Story 3 (Phase 5)**: Depends on foundational and report primitives; desktop client work depends on local purge API contract.
- **User Story 4 (Phase 6)**: Depends on foundational report primitives and can complete after US1 report assembly exists.
- **User Story 5 (Phase 7)**: Depends on lifecycle audit and report assembly from prior stories.
- **Polish (Phase 8)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 Delete Whole Meeting**: MVP gate. Must complete before reports can be considered launch-ready.
- **US2 Retention Jobs**: P1 launch gate and must reuse US1 deletion workflow semantics.
- **US3 Local Desktop Purge**: P1 launch gate for deletion truth; can proceed in parallel with US4 after foundational report state exists.
- **US4 Dependency And Backup Limits**: P1 launch gate for deletion truth; can proceed in parallel with US3.
- **US5 Safe Audit History**: P2 enhancement, but no-secret audit rules from foundational and US1 remain mandatory.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T013, T014, and T015 can run in parallel with schema/model work after draft entities exist.
- US1 tests T016, T017, T018, and T019 can run in parallel before US1 implementation.
- US2 tests T029, T030, and T031 can run in parallel.
- US3 tests T037, T038, and T039 can run in parallel.
- US4 tests T046, T047, and T048 can run in parallel.
- US5 tests T053, T054, and T055 can run in parallel.
- Polish documentation tasks T060, T061, and T062 can run in parallel after implementation evidence exists.

## Parallel Examples

### User Story 1

```text
Task: "T016 [US1] Add deletion request/report API contract tests in apps/server/tests/contract/test_retention_deletion_contract.py"
Task: "T017 [US1] Add manual deletion workflow integration tests in apps/server/tests/integration/test_meeting_deletion_workflow.py"
Task: "T018 [US1] Add lifecycle access-blocking integration tests in apps/server/tests/integration/test_deletion_lifecycle_blocks_access.py"
Task: "T019 [US1] Add deletion report view-model unit tests in apps/server/tests/unit/test_deletion_report_view_models.py"
```

### User Story 3

```text
Task: "T037 [US3] Add local purge API contract tests in apps/server/tests/contract/test_retention_deletion_contract.py"
Task: "T038 [US3] Add local purge coordination integration tests in apps/server/tests/integration/test_local_purge_coordination.py"
Task: "T039 [US3] Add desktop local purge Swift client tests in apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 whole-meeting deletion and access blocking.
3. Complete US2 retention job execution using the same lifecycle model.
4. Complete US3 local purge task/acknowledgement truth.
5. Complete US4 dependency and backup report truth.
6. Stop for review if US5 admin/audit polish should be deferred.

### Full 018 Scope

1. Complete all P1 launch gates: US1, US2, US3, and US4.
2. Complete US5 metadata-only audit/retry/report polish.
3. Finish evidence, changelog, current status, focused validation, browser screenshots, full local CI, and screenshot/evidence review.

### Quality Rules

- Tests for each story come before implementation and should fail before the story code is added.
- Do not start implementation while `$speckit-analyze` reports critical blockers.
- Do not broaden into public links, external recipient invitations, partial deletion, legal hold management, admin retention editing, billing, or desktop-owned deletion policy.
- Keep generated screenshots and evidence synthetic and no-secret.
