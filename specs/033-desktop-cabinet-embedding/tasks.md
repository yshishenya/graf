# Tasks: Desktop Cabinet Embedding

**Input**: Design documents from `/specs/033-desktop-cabinet-embedding/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are required because this feature touches the macOS native shell, embedded route trust boundary, auth/config state, accessibility, no-secret evidence, and upload-to-review continuity.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Establish feature files and validation placeholders.

- [X] T001 Create the desktop cabinet source directory marker in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`
- [X] T002 [P] Add the feature validation evidence placeholder in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`
- [X] T003 [P] Create the screenshot evidence directory marker in `specs/033-desktop-cabinet-embedding/validation/screenshots/.gitkeep`

---

## Phase 2: Foundational

**Purpose**: Shared route, configuration, and state models that all stories depend on.

**Critical**: No user story implementation begins until this phase is complete.

### Tests

- [X] T004 [P] Add desktop cabinet configuration tests in `apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift`
- [X] T005 [P] Add desktop cabinet route policy tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- [X] T006 [P] Add desktop cabinet state and shell-invariant tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation

- [X] T007 Implement `DesktopCabinetConfiguration`, URL building, and sanitized header handling in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`
- [X] T008 Implement `DesktopCabinetRoutePolicy` and route decisions in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T009 Implement `DesktopCabinetState`, bounded unavailable copy, and native shell invariant helpers in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`

**Checkpoint**: Route/config/state models pass focused tests and can be used by user stories.

---

## Phase 3: User Story 1 - Open Meetings In The Desktop Shell (Priority: P1)

**Goal**: The desktop app exposes a meetings workspace that hosts the server-owned `/desktop/meetings` list and detail routes while staying inside native app context.

**Independent Test**: Build the app core with a configured development server URL and assert the workspace builds the correct embedded list/detail URLs and shows a first-class meetings destination.

### Tests for User Story 1

- [X] T010 [P] [US1] Add workspace URL and default destination tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T011 [P] [US1] Add app accessibility label tests for the meetings workspace in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation for User Story 1

- [X] T012 [US1] Implement the WebKit bridge wrapper in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- [X] T013 [US1] Implement `DesktopCabinetWorkspaceView` with native heading, route status, and embedded list/detail hosting in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T014 [US1] Integrate the meetings workspace into the root macOS app layout in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T015 [US1] Update validation evidence for desktop list/detail entry points in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`

**Checkpoint**: User Story 1 is independently functional with a configured server route.

---

## Phase 4: User Story 2 - Preserve Native Capture Authority (Priority: P1)

**Goal**: Native Record, active indicator, Stop, upload truth, and diagnostics remain outside the embedded cabinet and are not duplicated by web content.

**Independent Test**: Simulate idle, preparing, active, stopping, failed, and unavailable cabinet states; assert native shell invariants keep capture controls and Stop reachable.

### Tests for User Story 2

- [X] T016 [P] [US2] Add native shell invariant assertions for active recording and cabinet states in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T017 [P] [US2] Add forbidden embedded control copy tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 2

- [X] T018 [US2] Keep `CaptureControlView` and native upload status outside the embedded cabinet region in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T019 [US2] Add explicit native-shell accessibility identifiers and labels for cabinet/capture regions in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T020 [US2] Update validation evidence for active recording and native Stop preservation in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`

**Checkpoint**: User Story 2 proves embedded review cannot hide or own capture authority.

---

## Phase 5: User Story 3 - Show Bounded Unavailable And Auth States (Priority: P1)

**Goal**: Not configured, offline, timeout, malformed, expired-session, denied, and not-found states are truthful and do not affect local capture/upload truth.

**Independent Test**: Feed each cabinet state into the workspace model/view helpers and assert bounded messages, privacy-preserving copy, and native shell invariants.

### Tests for User Story 3

- [X] T021 [P] [US3] Add unavailable/auth state copy tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T022 [P] [US3] Add no-secret/no-live-path tests for cabinet state messages in `apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift`

### Implementation for User Story 3

- [X] T023 [US3] Render bounded unavailable/auth states in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T024 [US3] Ensure configuration and error copy stays metadata-only in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`
- [X] T025 [US3] Update validation evidence for unavailable/auth states in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`

**Checkpoint**: User Story 3 is independently functional without a reachable server.

---

## Phase 6: User Story 4 - Connect Local Upload Outcomes To Review (Priority: P2)

**Goal**: Uploaded/server-identified local queue items can open embedded review while queued/failed/local-only items keep truthful upload guidance.

**Independent Test**: Build queue items with and without server meeting identifiers; verify review destinations are available only when server identity exists.

### Tests for User Story 4

- [X] T026 [P] [US4] Add upload review link tests in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`
- [X] T027 [P] [US4] Extend upload summary tests for review availability in `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation for User Story 4

- [X] T028 [US4] Implement upload review destination helpers in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`
- [X] T029 [US4] Add review action plumbing for uploaded queue items in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T030 [US4] Wire upload review action to the embedded meeting detail in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T031 [US4] Update validation evidence for upload-to-review continuity in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`

**Checkpoint**: User Story 4 connects local upload outcome to review without overpromising local-only items.

---

## Phase 7: User Story 5 - Maintain Clean-Room Desktop/Web UX Consistency (Priority: P2)

**Goal**: The implemented app aligns with V8/Krisp IA gates without copying Krisp visuals/copy/assets and without regressions in accessibility or layout.

**Independent Test**: Capture sanitized screenshots and compare against the V8/Krisp clean-room gates, feature `016` web screenshots, and no-secret/no-private-content evidence rules.

### Tests for User Story 5

- [X] T032 [P] [US5] Add no-Krisp-copy/no-private-content evidence scan notes in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`
- [X] T033 [P] [US5] Add UI copy/accessibility regression assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation for User Story 5

- [X] T034 [US5] Capture sanitized desktop screenshots into `specs/033-desktop-cabinet-embedding/validation/screenshots/`
- [X] T035 [US5] Compare implemented screenshots against V8 and feature `016` evidence in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`
- [X] T036 [US5] Update `CHANGELOG.md` with feature `033` behavior and validation references
- [X] T037 [US5] Update `docs/current-product-status.md` so `016` is no longer listed as the next product slice after 033 implementation

**Checkpoint**: User Story 5 records clean-room UI evidence and status updates.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Final validation, docs, issue traceability, and release-readiness evidence.

- [X] T038 Run focused macOS tests from `specs/033-desktop-cabinet-embedding/quickstart.md`
- [X] T039 Run macOS release build from `specs/033-desktop-cabinet-embedding/quickstart.md`
- [X] T040 Run server cabinet regression tests from `specs/033-desktop-cabinet-embedding/quickstart.md`
- [X] T041 Scan tracked feature evidence for secrets, signed URLs, raw audio, transcript text, private Krisp content, private account identifiers, and live local paths in `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md`
- [X] T042 Reconcile completed tasks and validation evidence in `specs/033-desktop-cabinet-embedding/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1, US2, US3 (P1)**: Depend on Foundational. US2 and US3 can proceed once workspace state helpers exist.
- **US4 (P2)**: Depends on Foundational and US1 route opening behavior.
- **US5 (P2)**: Depends on the implemented desktop workspace from US1-US4.
- **Polish**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1**: MVP start after Foundational.
- **US2**: Starts after Foundational and validates native shell authority with US1 workspace integration.
- **US3**: Starts after Foundational and can be implemented alongside US1 shell work.
- **US4**: Starts after US1 because review links need an embedded detail opener.
- **US5**: Starts after US1-US4 because it validates the full visual/product loop.

### Within Each User Story

- Tests are written first and must fail before implementation when practical.
- Model/policy helpers precede SwiftUI composition.
- Native shell composition precedes visual evidence.
- Validation evidence is updated after each story checkpoint.

## Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T004, T005, and T006 can run in parallel.
- T010 and T011 can run in parallel.
- T016 and T017 can run in parallel.
- T021 and T022 can run in parallel.
- T026 and T027 can run in parallel.
- T032 and T033 can run in parallel.

## Parallel Example: Foundational Tests

```bash
Task: "T004 [P] Add desktop cabinet configuration tests in apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift"
Task: "T005 [P] Add desktop cabinet route policy tests in apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift"
Task: "T006 [P] Add desktop cabinet state and shell-invariant tests in apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 to expose the meetings workspace in the app.
3. Complete US2 and US3 before any demo because capture safety and bounded unavailable states are constitutional gates.
4. Complete US4 to connect upload outcomes to review.
5. Complete US5 and Polish before claiming MVP-readiness movement.

### Validation Rhythm

1. Run focused Swift tests after foundational helpers and after each story checkpoint.
2. Update `specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md` after each checkpoint.
3. Run macOS release build and server cabinet regression before claiming implementation complete.
4. Capture sanitized screenshots only after private content and secret leakage risk is controlled.
