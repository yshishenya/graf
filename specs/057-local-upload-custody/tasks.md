# Tasks: Local Upload Custody

**Input**: Design documents from `specs/057-local-upload-custody/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Tests are required because the spec covers data loss prevention,
upload/retry semantics, deletion truth, privacy, accessibility, and server
contract boundaries.

**Organization**: Tasks are grouped by user story to enable independent
implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete
  tasks)
- **[Story]**: Maps the task to a user story from `spec.md`
- Each task includes exact repository paths

## Phase 1: Setup

**Purpose**: Add shared fixtures and validation scaffolding used by multiple
stories.

- [X] T001 [P] Add macOS custody fixture helpers in `apps/macos/Shared/Tests/DesktopUploadCustodyFixtures.swift`
- [X] T002 [P] Add server custody fixture helpers in `apps/server/tests/fixtures/local_upload_custody.py`
- [X] T003 [P] Add metadata-only validation notes in `specs/057-local-upload-custody/validation/README.md`

---

## Phase 2: Foundational

**Purpose**: Core projection, contracts, and boundary guards that block user
story work.

**Critical**: No user story work starts until this phase is complete.

- [X] T004 [P] Add custody projection failing tests in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T007 [P] Add server custody enum/schema failing tests in `apps/server/tests/contract/test_desktop_status_contract.py`
- [X] T024 Add pre-implementation 057-to-058 handoff fixture tests in `apps/server/tests/contract/test_desktop_status_contract.py`
- [X] T005 Implement `DesktopUploadCustodyProjection` in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T006 Wire projection creation into `DesktopUploadQueueService` in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T008 Add custody owner/action/retry-class schemas, including `Problem` custody extension fields, in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T009 Add stable custody/problem enum values in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [X] T010 Add 057/058 write-scope guard to implementation notes in `specs/057-local-upload-custody/quickstart.md`

**Checkpoint**: Projection, copy keys, and contract field names are stable
enough for all stories and feature `058` handoff. The T024 handoff fixtures must
exist before user story implementation starts, even if they fail until the
corresponding server fields are implemented.

---

## Phase 3: User Story 1 - Valid Local Recording Is Never Lost Silently (Priority: P1) MVP

**Goal**: Valid stopped recordings remain locally accounted for until delivered
or terminalized with truthful lifecycle evidence.

**Independent Test**: Offline, restart, server outage, malformed queue, and 404
server-unknown scenarios preserve custody state and do not report all-synced or
lost.

### Tests for User Story 1

- [X] T011 [P] [US1] Add malformed queue quarantine and encrypted-at-rest custody tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T012 [P] [US1] Add 404 server-unknown preservation and registration/session/finalize-response loss tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T013 [US1] Add background trigger and crash/relaunch duplicate-prevention tests for custody runner scheduling in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T014 [US1] Add server `recording_not_found` contract coverage in `apps/server/tests/contract/test_desktop_status_contract.py`

### Implementation for User Story 1

- [X] T015 [US1] Preserve malformed queue documents as metadata-safe blocked custody and enforce encrypted-at-rest custody ledger/artifact handling in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` and `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T016 [US1] Map sync-state 404 to `server_unknown_local_saved` custody and preserve registration/session/finalize truth after response loss in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T017 [US1] Add launch, activation, auth, network, wake, and scheduled retry triggers in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T018 [US1] Add retention warning and terminal undelivered projection rules in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T019 [US1] Ensure local custody audit logging is metadata-only in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T020 [US1] Expose `recording_not_found` as stable server-unknown problem truth in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [X] T021 [US1] Update US1 validation steps in `specs/057-local-upload-custody/quickstart.md`

**Checkpoint**: US1 proves the MVP custody promise without requiring server web
presentation changes.

---

## Phase 4: User Story 2 - Server Meeting List Stays Authoritative (Priority: P1)

**Goal**: The WebView server list remains the only meeting list; native custody
does not duplicate server-known or server-unknown recordings as rows.

**Independent Test**: Online, offline, expired-auth, and server-conflict states
produce server read-model truth or native aggregate custody only, never two
meeting rows.

### Tests for User Story 2

- [X] T022 [P] [US2] Add no-native-duplicate-list tests in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`
- [X] T023 [P] [US2] Add route-availability tests for server-known-only review links in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 2

- [X] T025 [US2] Remove server-unknown local rows from the primary workspace surface in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T026 [US2] Keep local custody details outside WebView meeting content in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T027 [US2] Gate review destinations on server-known identity and review availability in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T028 [US2] Add explicit structured `custody` read-model fields for 058 handoff in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T029 [US2] Populate handoff custody fields without relying on `status_label`, `status_reason`, or `primary_action` in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- [X] T030 [US2] Update `contracts/057-to-058-handoff-contract.md` if final field names differ in `specs/057-local-upload-custody/contracts/057-to-058-handoff-contract.md`

**Checkpoint**: US2 proves one authority boundary: server-known rows are server
truth; server-unknown items are native aggregate custody only.

---

## Phase 5: User Story 3 - User Sees Only Real Actions (Priority: P1)

**Goal**: Normal users see only actions they can actually perform; transport
retry mechanics are product-owned.

**Independent Test**: Network outage, expired auth, wrong workspace, quota,
policy, deletion, stale device, corruption, and processing failure all map to
the correct owner/action policy without Retry or Stop retry controls.

### Tests for User Story 3

- [X] T031 [US3] Add action-policy and destructive local-delete confirmation mapping tests in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T032 [P] [US3] Add UI no-retry-control tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [X] T033 [US3] Add HTTP status/problem mapping tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T034 [P] [US3] Add server problem-code mapping tests that reject legacy UI actions such as `manual_review`, `stop_upload`, `retry_later`, `retry_future`, and `open_desktop_queue` as 057/058 contract values in `apps/server/tests/integration/test_ingest_failure_truth.py`

### Implementation for User Story 3

- [X] T035 [US3] Remove normal-user Retry and Stop retry button wiring from `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T036 [US3] Remove normal-user manual retry and stop-retry handlers from `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T037 [US3] Implement owner/action/retry-class mapping in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T038 [US3] Normalize desktop client failure categories from stable problem codes in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T039 [US3] Return stable owner/action/problem fields from server ingest failures, using `Problem` custody extension fields or the agreed nested equivalent, in `apps/server/src/twobrain_rec_server/api/ingest.py`

**Checkpoint**: US3 proves the user is not asked to manage transport mechanics.

---

## Phase 6: User Story 4 - Custody Status Is Calm, Compact, And Honest (Priority: P2)

**Goal**: Local custody is visible and trustworthy without dominating the
meeting workspace.

**Independent Test**: Zero, one, and many custody items show compact aggregate
status, highest-risk priority, readable Russian copy, keyboard access, and
VoiceOver labels.

### Tests for User Story 4

- [X] T040 [US4] Add aggregate summary priority tests, including disk-pressure priority, in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T041 [US4] Add compact right/control surface tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [X] T042 [US4] Add accessibility label coverage for custody status in `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation for User Story 4

- [X] T043 [US4] Replace technical upload summary copy with the contracted custody copy-key catalog in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T044 [US4] Render the single compact aggregate custody status owner in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T045 [US4] Add secondary custody details disclosure outside WebView content, including destructive local-delete confirmation copy, in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T046 [US4] Add VoiceOver-readable labels and non-color-only status text in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T047 [US4] Update UX checklist evidence notes in `specs/057-local-upload-custody/checklists/ux.md`

**Checkpoint**: US4 proves custody status is calm, compact, and accessible.

---

## Phase 7: User Story 5 - Admin And Support Can See Safe Incident Truth (Priority: P2)

**Goal**: Non-user-resolvable blockers have metadata-safe incident truth for
admins/support without leaking content.

**Independent Test**: Each admin/support blocker produces safe reason category,
owner, timestamps, lifecycle state, and safe identity with no audio, transcript,
tokens, signed URLs, or private paths.

### Tests for User Story 5

- [X] T048 [US5] Add safe incident projection tests in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T049 [US5] Add safe report redaction tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [X] T050 [US5] Add server incident/read-model metadata tests in `apps/server/tests/contract/test_desktop_status_contract.py`

### Implementation for User Story 5

- [X] T051 [US5] Add safe report payload builder in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T052 [US5] Route diagnostics/copy-safe-report actions from custody UI in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T053 [US5] Add metadata-safe incident fields to server schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T054 [US5] Populate incident owner/action state in server sync/read-model code in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`

**Checkpoint**: US5 proves support gets safe truth without content leakage.

---

## Phase 8: User Story 6 - Upload, Processing, And Deletion Truth Stay Separate (Priority: P2)

**Goal**: Upload success, processing success, server deletion, local purge, and
local custody never collapse into a generic success/failure state.

**Independent Test**: Upload-finalized/processing-failed, server-deleted/local
artifacts remain, local purge success/failure, and ready review states remain
distinct.

### Tests for User Story 6

- [X] T055 [US6] Add upload-vs-processing projection tests in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T056 [P] [US6] Add verified local purge ack tests in `apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift`
- [X] T057 [P] [US6] Add server local purge ack failure tests in `apps/server/tests/integration/test_local_purge_coordination.py`
- [X] T058 [P] [US6] Add processing/deletion separation tests in `apps/server/tests/integration/test_recording_sync_processing.py`

### Implementation for User Story 6

- [X] T059 [US6] Separate upload, processing, deletion, and purge projection fields in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T060 [US6] Verify local deletion/tombstone/unrecoverability before purge ack and reconcile before upload, finalize, terminal decision, and purge ack in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T061 [US6] Send failed or unverified local purge acknowledgements safely in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T062 [US6] Enforce local purge ack validation in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T063 [US6] Keep processing failure separate from local upload failure in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`

**Checkpoint**: US6 proves lifecycle truth is precise and not overclaimed.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Validation, docs, release notes, and boundary proof after selected
stories are implemented.

- [X] T064 [P] Update `CHANGELOG.md` with 057 behavior, UX, contract, and validation impact
- [X] T065 [P] Update `docs/current-product-status.md` with 057 status after validation
- [X] T066 [P] Run focused macOS validation from `specs/057-local-upload-custody/quickstart.md`
- [X] T067 [P] Run focused server validation from `specs/057-local-upload-custody/quickstart.md`
- [X] T068 Run `infra/scripts/ci-local.sh`
- [X] T069 Run forbidden-content scans over 057 docs, diagnostics, logs, and evidence paths referenced by `specs/057-local-upload-custody/quickstart.md`, including `specs/057-local-upload-custody/validation/`
- [X] T070 Confirm `git diff --name-only` has no 057 writes to `apps/server/src/twobrain_rec_server/cabinet/web.py`, server cabinet templates, server cabinet CSS/static, or meeting-list/detail HTML markup

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all stories.
- **User Stories**: Depend on Foundational completion.
- **Final Phase**: Depends on all selected stories.

### User Story Dependencies

- **US1 (P1)**: MVP custody safety. Start first after Foundation.
- **US2 (P1)**: Can start after Foundation; safest after US1 projection fields
  are stable.
- **US3 (P1)**: Can start after Foundation; should be completed before broad
  UI polish so action policy is stable.
- **US4 (P2)**: Depends on US3 action policy and projection copy keys.
- **US5 (P2)**: Can start after Foundation; benefits from US3 owner/action
  mappings.
- **US6 (P2)**: Can start after Foundation; coordinates with US1/US5 lifecycle
  evidence.

### Parallel Opportunities

- Setup fixture tasks T001-T003 can run in parallel.
- Foundational tests T004 and T007 can run in parallel.
- Server contract work T007-T009 can run in parallel with macOS projection work
  T004-T006 after field names are agreed.
- Tests within each user story marked `[P]` can be written in parallel before
  implementation.
- US2 server handoff tasks can run in parallel with US3 native UI tasks after
  Foundation.
- Final validation tasks T066-T067 can run in parallel before the full local CI.

---

## Parallel Example: US3

```text
Task: "T031 [P] [US3] Add action-policy mapping tests in apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift"
Task: "T032 [P] [US3] Add UI no-retry-control tests in apps/macos/Shared/Tests/CaptureControlTests.swift"
Task: "T033 [P] [US3] Add HTTP status/problem mapping tests in apps/macos/Shared/Tests/DesktopUploadClientTests.swift"
Task: "T034 [P] [US3] Add server problem-code mapping tests in apps/server/tests/integration/test_ingest_failure_truth.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1.
3. Stop and validate: valid local recordings are never lost silently across
   offline/restart/server-unknown scenarios.

### P1 Completion

1. Complete US2 to protect the server-owned meeting list.
2. Complete US3 to remove fake user tasks and transport retry controls.
3. Validate P1 as a coherent custody experience before P2 polish.

### P2 Completion

1. Complete US4 compact/accessibility behavior.
2. Complete US5 safe incident truth.
3. Complete US6 lifecycle separation and purge-before-ack.
4. Run focused validation, forbidden-content scans, boundary guard, and full
   local CI.

## Notes

- Do not modify `apps/server/src/twobrain_rec_server/cabinet/web.py`, server
  cabinet templates, server cabinet CSS/static, or meeting-list/detail HTML
  markup in 057.
- Keep test tasks before implementation tasks inside each story.
- Mark tasks `[X]` only after the corresponding validation passes.
- Implementation commits require explicit user approval after validation.
