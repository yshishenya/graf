# Tasks: Automatic Meeting Detection

**Input**: Design documents from `/specs/092-automatic-meeting-detection/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[quickstart.md](./quickstart.md), [contracts/](./contracts/)

**Tests**: Required. This is a high-risk capture/privacy/admin/diagnostics slice.
Write focused tests before implementation within each user story.

**Organization**: Tasks are dependency ordered and grouped by independently
testable implementation stories.

## Phase 1: Setup

**Purpose**: Prepare shared contracts and imports without changing behavior.

- [X] T001 [P] Add meeting detection schema exports to `apps/server/src/twobrain_rec_server/api/schemas.py`.
- [X] T002 [P] Add server package scaffold in `apps/server/src/twobrain_rec_server/meeting_detection/__init__.py`.
- [X] T003 [P] Add macOS meeting detection source folders by creating placeholder module files under `apps/macos/Shared/Sources/MeetingDetection/` and `apps/macos/RecApp/Sources/MeetingDetection/`.
- [X] T004 [P] Add reviewed registry baseline data at `apps/server/src/twobrain_rec_server/db/migrations/data/0019_meeting_target_registry.json`.
- [X] T005 Add 092 validation notes to `CHANGELOG.md` under unreleased behavior/planning changes.

---

## Phase 2: Foundational Server Data And Safety

**Purpose**: DB schema, persistence, redaction, and shared validation that block
server/admin stories.

- [X] T006 [P] Add SQLAlchemy models for registry, telemetry, candidates, review actions, non-target rules, and rate limits in `apps/server/src/twobrain_rec_server/db/models/meeting_detection.py`.
- [X] T007 Export meeting detection models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`.
- [X] T008 [P] Add Alembic migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0017_meeting_detection_registry.py`.
- [X] T009 [P] Add migration tests in `apps/server/tests/integration/test_meeting_detection_migrations.py`.
- [X] T010 [P] Add metadata-only forbidden-content scanner tests in `apps/server/tests/unit/test_meeting_detection_redaction.py`.
- [X] T011 Implement forbidden-content scanner in `apps/server/src/twobrain_rec_server/meeting_detection/redaction.py`.
- [X] T012 [P] Add registry validation tests in `apps/server/tests/unit/test_meeting_detection_registry.py`.
- [X] T013 Implement registry document validation helpers in `apps/server/src/twobrain_rec_server/meeting_detection/registry.py`.
- [X] T014 [P] Add candidate scoring/aggregation tests in `apps/server/tests/unit/test_meeting_detection_candidates.py`.
- [X] T015 Implement candidate aggregation helpers in `apps/server/src/twobrain_rec_server/meeting_detection/candidates.py`.

**Checkpoint**: Server data and safety helpers are ready; no user-visible routes yet.

---

## Phase 3: User Story 1 - Receive Safe Telemetry (Priority: P1)

**Goal**: Desktop clients can submit bounded metadata-only meeting detection
rollups, and the server stores only safe known-target health and VKS candidates.

**Independent Test**: Contract and integration tests submit valid, duplicate,
unsafe, low-score, and rate-limited telemetry payloads.

### Tests

- [X] T016 [P] [US1] Add telemetry API contract tests in `apps/server/tests/contract/test_meeting_detection_api_contract.py`.
- [X] T017 [P] [US1] Add telemetry forbidden-content contract tests in `apps/server/tests/contract/test_meeting_detection_no_secret_content.py`.
- [X] T018 [P] [US1] Add telemetry integration tests in `apps/server/tests/integration/test_meeting_detection_telemetry.py`.

### Implementation

- [X] T019 [US1] Add Pydantic request/response models for telemetry and registry in `apps/server/src/twobrain_rec_server/api/schemas.py`.
- [X] T020 [US1] Implement telemetry persistence/idempotency/rate-limit service in `apps/server/src/twobrain_rec_server/meeting_detection/telemetry.py`.
- [X] T021 [US1] Add `POST /api/v1/desktop/meeting-detection/telemetry` route in `apps/server/src/twobrain_rec_server/api/meeting_detection.py`.
- [X] T022 [US1] Include meeting detection API router in `apps/server/src/twobrain_rec_server/main.py`.
- [X] T023 [US1] Add OpenAPI drift/route coverage updates in `apps/server/tests/contract/test_openapi_contract_drift.py`.

**Checkpoint**: Telemetry endpoint works independently and rejects unsafe payloads.

---

## Phase 4: User Story 2 - Review Candidates In Admin (Priority: P1)

**Goal**: Admins can see likely VKS candidates and known target health, then
mark non-target, merge, create diagnostic-only drafts, request validation, and
publish reviewed registry changes.

**Independent Test**: Synthetic candidate telemetry creates an admin review item;
admin actions update state and write audit without enabling prompt behavior.

### Tests

- [X] T024 [P] [US2] Add admin review API contract tests in `apps/server/tests/contract/test_meeting_detection_admin_contract.py`.
- [X] T025 [P] [US2] Add admin review integration tests in `apps/server/tests/integration/test_meeting_detection_admin_review.py`.
- [X] T026 [P] [US2] Add admin no-secret rendering checks in `apps/server/tests/contract/test_admin_no_secret_content_egress.py`.

### Implementation

- [X] T027 [US2] Implement admin review query/service logic in `apps/server/src/twobrain_rec_server/meeting_detection/admin_review.py`.
- [X] T028 [US2] Add admin view model builders in `apps/server/src/twobrain_rec_server/admin/meeting_detection.py`.
- [X] T029 [US2] Extend admin navigation/view models in `apps/server/src/twobrain_rec_server/admin/view_models.py`.
- [X] T030 [US2] Add `/admin/meeting-detection` route in `apps/server/src/twobrain_rec_server/admin/web.py`.
- [X] T031 [US2] Add admin template `apps/server/src/twobrain_rec_server/admin/templates/admin/meeting_detection.html`.
- [X] T032 [US2] Add admin action API routes under `/api/v1/admin/meeting-detection/...` in `apps/server/src/twobrain_rec_server/api/admin.py`.
- [X] T033 [US2] Ensure every admin action writes `AdminAuditEvent` from `apps/server/src/twobrain_rec_server/admin/audit.py`.

**Checkpoint**: Admin can review and classify candidates without changing capture behavior.

---

## Phase 5: User Story 3 - Publish And Fetch Registry (Priority: P1)

**Goal**: Server publishes validated registry versions and desktop clients fetch
them with ETag/cache fallback semantics.

**Independent Test**: Admin publishes a diagnostic-only draft; desktop registry
endpoint returns valid JSON and ETag; malformed draft cannot publish.

### Tests

- [X] T034 [P] [US3] Add registry endpoint tests in `apps/server/tests/integration/test_meeting_detection_registry.py`.
- [X] T035 [P] [US3] Add registry API contract coverage in `apps/server/tests/contract/test_meeting_detection_api_contract.py`.
- [X] T036 [P] [US3] Add RLS/tenant isolation coverage for registry and candidates in `apps/server/tests/contract/test_rls_table_inventory_contract.py`.

### Implementation

- [X] T037 [US3] Implement registry draft, publish, ETag, and latest-published lookup in `apps/server/src/twobrain_rec_server/meeting_detection/registry.py`.
- [X] T038 [US3] Add `GET /api/v1/desktop/meeting-detection/target-registry` route in `apps/server/src/twobrain_rec_server/api/meeting_detection.py`.
- [X] T039 [US3] Seed initial registry document from `specs/092-automatic-meeting-detection/native-allowlist.md` through migration or service fixture in `apps/server/src/twobrain_rec_server/db/migrations/versions/0017_meeting_detection_registry.py`.
- [X] T040 [US3] Add non-target rule export into registry documents in `apps/server/src/twobrain_rec_server/meeting_detection/registry.py`.

**Checkpoint**: Server/admin registry loop is independently usable before macOS uploader work.

---

## Phase 6: User Story 4 - macOS Registry, Filter, Rollups, Upload (Priority: P1)

**Goal**: macOS can load registry cache/seed, score likely VKS candidates, store
bounded local rollups, and upload only eligible candidate telemetry.

**Independent Test**: Swift tests prove bad registry fallback, low-score
redaction, non-target suppression, high-score candidate upload, retention, and
backoff.

### Tests

- [X] T041 [P] [US4] Add registry cache tests in `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift`.
- [X] T042 [P] [US4] Add VKS-candidate filter tests in `apps/macos/Shared/Tests/MeetingDetectionCandidateFilterTests.swift`.
- [X] T043 [P] [US4] Add telemetry rollup/uploader tests in `apps/macos/Shared/Tests/MeetingDetectionTelemetryTests.swift`.

### Implementation

- [X] T044 [US4] Implement shared Codable models in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`.
- [X] T045 [US4] Implement registry validation and last-good cache in `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift`.
- [X] T046 [US4] Implement VKS-candidate scoring and non-target suppression in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionCandidateFilter.swift`.
- [X] T047 [US4] Implement local rollup persistence/retention in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionTelemetryRollupStore.swift`.
- [X] T048 [US4] Implement telemetry uploader/backoff/policy in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionTelemetryUploader.swift`.
- [X] T049 [US4] Implement local detection/upload settings cache in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift`.

**Checkpoint**: macOS can safely fetch registry and upload only filtered telemetry, with no detector yet.

---

## Phase 7: User Story 5 - Native macOS Detector, Prompt Policy, And Settings (Priority: P1)

**Goal**: macOS detects verified native meeting app activity through Gilb-style
`AudioHAL` app ownership, debounces candidates, ignores non-targets, and routes
prompt or target-scoped auto-record decisions through existing gates.

**Independent Test**: Synthetic parser/state-machine tests cover Zoom,
Telemost, unknown, Krisp/audio utility, browser ownership, malformed logs,
short tests, start debounce, end grace, and policy decisions.

### Tests

- [X] T050 [P] [US5] Add parser fixture tests in `apps/macos/Shared/Tests/MacOSAudioOwnershipParserTests.swift`.
- [X] T051 [P] [US5] Add prompt/auto-record policy tests in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T052 [P] [US5] Add capture prerequisite regression tests in `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`.

### Implementation

- [X] T053 [US5] Implement `AudioHAL` primary parser in `apps/macos/Shared/Sources/MeetingDetection/MacOSAudioOwnershipParser.swift`.
- [X] T054 [US5] Implement detector state machine/process wrapper in `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`.
- [X] T055 [US5] Implement prompt eligibility and target-scoped auto-record policy in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift`.
- [X] T056 [US5] Integrate detector-assisted approvals with `apps/macos/RecApp/Sources/Capture/CaptureScopeApprovalService.swift`.
- [X] T057 [US5] Integrate prompt/visible recording gate with `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [X] T058 [US5] Add metadata-only detector evidence to `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T059 [P] [US5] Add meeting detection settings/health accessibility coverage in `apps/macos/Shared/Tests/CaptureControlTests.swift` and `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.
- [X] T060 [US5] Integrate detection mode, health, and target-scoped auto-record revocation affordances in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T061 [US5] Add desktop meeting-detection settings route policy support in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`.

**Checkpoint**: Verified native app candidates can prompt safely; unknown apps still never prompt; user-visible settings can disable detection, switch detect-only, and revoke target-scoped auto-record.

---

## Phase 8: User Story 6 - Browser Metadata And Calendar/Join Intent Foundation (Priority: P2)

**Goal**: Browser meetings are evaluated through service-specific metadata plus
calendar/join intent, not generic browser audio ownership.

**Independent Test**: Browser fixtures distinguish Telemost/Meet joined pages
from landing/new/settings/device-test/media/voice-search pages and fail closed
when metadata is unavailable.

### Tests

- [X] T062 [P] [US6] Add browser target evidence tests in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [X] T063 [P] [US6] Add calendar/join-intent detector tests in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`.

### Implementation

- [X] T064 [US6] Extend browser target evidence models in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T065 [US6] Add browser meeting service pattern matching in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`.
- [X] T066 [US6] Integrate safe calendar/join-intent hints from `apps/macos/RecApp/Sources/Calendar/DesktopCalendarReminderService.swift`.
- [X] T067 [US6] Ensure unsupported browser metadata states remain manual-only in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift`.

**Checkpoint**: Browser path can classify safe service-family evidence without an extension.

---

## Spec User Story Coverage

Implementation phases are dependency-oriented so the server/admin registry safety
surface lands before macOS upload and detector rollout. This table maps every
product user story from [spec.md](./spec.md) to executable tasks.

| Spec Story | Covered By |
| --- | --- |
| US1 Detect and ask for a new meeting | T051, T055-T060, T070-T071 |
| US2 Detect native apps with Gilb-style audio ownership | T050, T053-T058, T070-T071 |
| US3 Detect browser meetings safely | T062-T067, T071 |
| US4 Cover Russian VKS targets | T004, T012-T013, T034-T040, T068-T071 |
| US5 Block false positives from non-meeting activity | T010-T015, T042, T046, T050-T055, T062-T067, T072 |
| US6 Preserve visible capture control | T051-T052, T055-T060, T070-T071 |
| US7 Let users and admins control detection | T024-T040, T049, T055, T059-T061, T070-T071 |
| US8 Use calendar context without overclaiming | T063, T066, T071 |
| US9 Record metadata-only detector evidence | T006-T023, T041-T048, T058, T070-T072 |
| US10 End or suppress recordings safely | T051, T055-T057, T067, T071 |
| US11 Target-scoped auto-record after user opt-in | T049, T051, T055-T060, T070-T071 |

---

## Phase 9: Polish, Validation, And Closeout

**Purpose**: Run gates, update docs, and reconcile implementation evidence with
already-created GitHub issues.

- [X] T068 [P] Update `docs/current-product-status.md` with implementation status and limitations after validation.
- [X] T069 [P] Update `CHANGELOG.md` with behavior, telemetry/admin, validation, and compatibility notes.
- [X] T070 Run server focused validation from `specs/092-automatic-meeting-detection/quickstart.md`.
- [X] T071 Run macOS focused validation from `specs/092-automatic-meeting-detection/quickstart.md`.
- [X] T072 Run forbidden-content scans listed in `specs/092-automatic-meeting-detection/quickstart.md` for telemetry/admin/diagnostics evidence.
- [X] T073 Run `infra/scripts/ci-local.sh`.
- [X] T074 Record high-risk validation lane, evidence, known limitations, and release/deploy exclusion in `specs/092-automatic-meeting-detection/quickstart.md`.
- [X] T075 Reconcile completed task checkboxes, validation evidence, and linked GitHub issue closeout state in `specs/092-automatic-meeting-detection/quickstart.md`.

---

## Dependencies & Execution Order

1. Phase 1 setup has no dependencies.
2. Phase 2 foundation blocks all server/admin stories.
3. Phase 3 telemetry blocks admin candidate review and macOS upload.
4. Phase 4 admin review and Phase 5 registry publishing together block macOS
   uploader rollout.
5. Phase 6 macOS registry/filter/upload blocks detector telemetry upload.
6. Phase 7 native detector/settings depends on Phase 6 and existing capture gates.
7. Phase 8 browser metadata can start after shared registry/policy models exist,
   but must not block native server/admin MVP if deferred.
8. Phase 9 closeout depends on selected implementation stories being complete.
9. `$speckit-taskstoissues` is a pre-implementation gate after a clean
   `$speckit-analyze` pass and before T001 starts.

## Parallel Opportunities

- T001-T004 can run in parallel.
- T006, T008, T010, T012, and T014 can run in parallel after setup.
- Tests within each user story can be written in parallel.
- Server admin rendering work can proceed after T027 while registry publish work
  proceeds after T037 if migrations are complete.
- macOS registry/filter tests and models can proceed in parallel with uploader
  tests after server contracts stabilize.

## MVP Implementation Strategy

1. Complete Phases 1-5 first: server telemetry, admin review, registry publishing,
   and registry fetch.
2. Validate server/admin quickstart and stop for review.
3. Complete Phase 6: macOS registry/filter/rollup/uploader.
4. Complete Phase 7 native detector for Zoom and Yandex Telemost.
5. Decide whether Phase 8 browser foundation is included in the first PR or kept
   as the next implementation slice under the same spec.
6. Run Phase 9 gates before PR/closeout.

## Phase 10: Convergence

- [X] T076 CRITICAL: Wire detector prompt and auto-record eligibility to real recording prerequisite and workspace policy state instead of hard-coded allow values per Constitution II and FR-007 (contradicts)
- [X] T077 Add safe prompt state and copy for target label, capture mode, capture sources, workspace policy state, and user choices without raw meeting metadata per FR-022 (partial)
- [X] T078 Add explicit non-Chromium browser support-state decision evidence as prompt-capable, detect-only, or manual-only per SC-005 (partial)
- [X] T079 Complete or explicitly close Microsoft Teams native AudioHAL validation evidence before final feature closeout per SC-006 (partial)
- [X] T080 Run and record detector resource gate measurements for CPU, RSS, disk writes, registry fetch cadence, and telemetry upload cadence per SC-009 (partial)
- [X] T081 Run and record the manual local admin browser smoke from the quickstart or document why it is outside this feature closeout per plan: quickstart validation (partial)
