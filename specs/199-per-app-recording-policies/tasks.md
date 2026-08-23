# Tasks: Политики автозаписи по приложениям

**Input**: Design documents from `/specs/199-per-app-recording-policies/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/automatic-recording-policy.md`, `quickstart.md` and completed
high-risk checklists.

## Phase 1: Model and migration (US1/US2)

- [X] T001 [P] [US1] Add `AutomaticRecordingRule` and state-transition tests in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T002 [P] [US2] Add Codable round-trip, legacy migration and atomic bulk-rule tests in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T003 [US1] Add the target-scoped rule map and migration helpers to `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift`.
- [X] T004 [US1] Extend `MeetingDetectionSettingsSnapshot` and policy resolution inputs in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` and `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`.

## Phase 2: Policy and prompt semantics (US1)

- [X] T005 [P] [US1] Add timeout/button/checkbox outcome tests, including timeout with checkbox on, in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` and `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift`.
- [X] T006 [US1] Resolve `always`, `ask` and `never` in `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` while retaining all capture gates.
- [X] T007 [US1] Update prompt decision persistence and final current-start rechecks in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T008 [US1] Update `MeetingDetectionPromptView` copy, callback semantics and timeout handling in `apps/macos/RecApp/App/TwoBrainRecApp.swift`; remove timeout persistence/suppression and technical inline rows.

## Phase 3: Settings UI (US2/US3/US4)

- [X] T009 [P] [US2] Add source-contract/accessibility assertions for labels, hints and removed bundle IDs in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.
- [X] T010 [US2] Replace binary target checkboxes with theme-style three-state radio cards in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.
- [X] T011 [US3] Add the mixed-state bulk radio control and apply-all behavior in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.
- [X] T012 [US4] Keep technical switches with short labels and pointer/keyboard/VoiceOver hints in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.

## Phase 4: Validation and documentation

- [X] T013 [P] [US1] Update Russian `CHANGELOG.md` and `docs/current-product-status.md` with the three-state prompt contract and migration boundary.
- [X] T014 [P] [US1] Add focused regression tests for active indicator/one-action Stop preservation in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.
- [X] T015 [US1] Run the focused Swift suite and synthetic UI/accessibility smoke from `specs/199-per-app-recording-policies/quickstart.md`; record metadata-only evidence in `specs/199-per-app-recording-policies/validation/implementation-evidence.md`.
- [X] T016 [US1] Build a separate GRAF Dev app for prompt/settings smoke without replacing `/Applications/GRAF.app`.

## Dependencies

- T001–T002 before T003–T004.
- T005 before T006–T008.
- T009 before T010–T012.
- T013–T016 after the behavior and UI phases.

## Definition of Done

- Every task is checked only after implementation and evidence.
- Focused tests pass for all state combinations and migration paths.
- No raw meeting content or credentials enter logs/evidence.
- Full CI, commit, push, release and deploy remain explicitly reported as not run
  unless separately requested.
