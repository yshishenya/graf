# Tasks: Надёжный переход локальной записи в кабинет

**Input**: Design documents from `/specs/231-local-recording-handoff/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required by the high-risk capture/deletion/UX lane.

## Phase 1: Focused RED tests

- [X] T001 [US3] Add failing AEC finite-overshoot and terminal-invalid-input checks in `apps/macos/Shared/Tests/RecordingEchoProcessorTests.swift` (FR-010–FR-012)
- [X] T002 [US1] Add failing UTF-8, accessible open action, duration and no-grafting contracts in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift` (FR-001–FR-005, FR-009)
- [X] T003 [US2] Add failing v5 local-resource migration and saved-duration checks in `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` (FR-005, FR-007–FR-009)

## Phase 2: Root-cause implementation

- [X] T004 [US3] Clamp finite frames at the shared AEC boundary and preserve exact terminal cause in `apps/macos/RecApp/Sources/Capture/RecordingEchoProcessor.swift`, `RecordingAudioTimeline.swift` and `V5LocalRecordingWriter.swift` (FR-010–FR-012)
- [X] T005 [US1] Correct v5 duration, failure category/reason and stale-item refresh in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (FR-005–FR-008)
- [X] T006 [US1] Implement UTF-8 payload decode and native local playback authorization in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` and `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-001, FR-003–FR-004)
- [X] T007 [US1] Render an accessible normal-icon local row without server-row grafting in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-002–FR-005, FR-009)

## Phase 3: User data cleanup

- [X] T008 [US4] Delete only the four approved valueless local packages through the queue service and prove preservation of meeting `876ca9ec-d065-43b8-a36a-e2020dc41151` (FR-013–FR-014)

## Phase 4: Validation and closeout

- [X] T009 Run the feature quickstart, focused XCTest, JavaScript syntax, accessibility/DOM and fresh dev-capture checks; record only metadata-safe results (SC-001–SC-005)
- [ ] T010 Run `infra/scripts/ci-local.sh --fast`, re-run Spec Kit convergence and record clean-SHA evidence for the high-risk lane without PR/release/deploy (SC-006)

## Phase 5: Convergence

- [X] T011 Require the local playback file to remain readable both when projecting the row action and when authorizing native open per FR-004 (partial)
- [X] T012 Make the existing feature-pointer and release-attestation governance tests independent of another active feature and already-published CalVer tags after clean-SHA fast-CI convergence

## Dependencies & Execution Order

- T001–T003 precede T004–T007.
- T004–T007 precede cleanup and end-to-end validation.
- T008 uses the existing queue service after target and preserved-record allowlists are rechecked.
- T009 precedes T010.
