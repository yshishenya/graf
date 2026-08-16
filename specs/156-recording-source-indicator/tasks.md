# Tasks: Источник системного звука в индикаторе записи

**Input**: Design documents from `/specs/156-recording-source-indicator/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Risk lane**: `high-risk-feature` — capture UX and accessibility; no capture-route or data-contract change.

## Phase 1: Setup

**Purpose**: Confirm the existing native package and keep the change dependency-free.

- [X] T001 Review `apps/macos/Package.swift` and confirm the feature uses existing SwiftUI/XCTest dependencies without adding a package

---

## Phase 2: Foundational

**Purpose**: Establish the shared copy and accessibility contract before the view consumes it.

- [X] T002 Add source-row labels and `systemAudio.status.source` identifier in `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`

**Checkpoint**: Shared copy and identifier are defined; no audio or storage behavior changes.

---

## Phase 3: User Story 1 - Понять источник активной записи (Priority: P1) 🎯 MVP

**Goal**: Show the verified source name in the existing upper recording status card while preserving the primary status and Stop action.

**Independent Test**: A session with `sourceDisplayName = "Zoom"` exposes «Источник: Zoom» in the active status surface and keeps the existing stop/pause/resume affordances.

### Tests for User Story 1

- [X] T003 [US1] Add focused source-display and active-lifecycle assertions to `apps/macos/Shared/Tests/CaptureIndicatorTests.swift` before implementation

### Implementation for User Story 1

- [X] T004 [US1] Add normalized source presentation helpers and the compact informational source row in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`

**Checkpoint**: Known verified app names are visible in active, paused, degraded, and stopping states without moving capture controls.

---

## Phase 4: User Story 2 - Доверять нейтральному состоянию источника (Priority: P1)

**Goal**: Keep manual and unavailable attribution truthful instead of guessing an application.

**Independent Test**: A manual sentinel produces «Системный звук»; missing, blank, and unknown evidence produce «Источник не определён».

### Tests for User Story 2

- [X] T005 [US2] Add manual-sentinel, missing-value, whitespace, and post-stop visibility assertions to `apps/macos/Shared/Tests/CaptureIndicatorTests.swift` before fallback implementation

### Implementation for User Story 2

- [X] T006 [US2] Complete the fallback mapping and active-session visibility boundary in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`

**Checkpoint**: Manual and unknown states are explicit, stable, and never inferred from frontmost applications or audio levels.

---

## Phase 5: User Story 3 - Быстро проверить источник с клавиатурой и VoiceOver (Priority: P2)

**Goal**: Make long source names and the new informational row accessible without affecting existing actions.

**Independent Test**: The source row has a stable identifier, full accessible label/help text, single-line truncation, and existing actions remain separate.

### Tests for User Story 3

- [X] T007 [US3] Add source identifier, full-name accessibility, truncation, contrast, and preserved-action contract assertions to `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation for User Story 3

- [X] T008 [US3] Add the source row accessibility label, identifier, help text, and single-line layout in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`

**Checkpoint**: The source is understandable through VoiceOver/help and remains visually compact at narrow widths.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Record the user-visible change and close with the required evidence.

- [X] T009 Update the Russian user-facing entry in `CHANGELOG.md` for the recording-source indicator behavior
- [X] T010 Run the feature validation in `specs/156-recording-source-indicator/quickstart.md`, including focused XCTest, local macOS build, and `infra/scripts/ci-local.sh --fast`; record results in the final handoff

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) precedes the shared contract.
- Foundational (Phase 2) precedes all user-story work.
- US1 (Phase 3) provides the source row used by US2 and US3.
- US2 (Phase 4) hardens the same helper against manual/unknown values before accessibility polish.
- US3 (Phase 5) follows the final source presentation shape.
- Polish (Phase 6) depends on all story tasks and focused validation.

### Parallel Opportunities

- T001 can be completed independently before T002.
- T003 and T007 are test-only tasks, but T007 must follow the final source-row shape; do not edit `CaptureIndicatorTests.swift` concurrently with T005 because they touch the same file.
- T009 is independent of the Swift implementation and can be prepared in parallel after the user-visible copy is settled.

## Implementation Strategy

1. Complete T001–T002 and establish the shared contract.
2. Deliver US1 as the MVP with tests before implementation.
3. Add truthful manual/unknown fallbacks in US2.
4. Add accessibility and layout protection in US3.
5. Update changelog, run quickstart, then run the fast repository lane.

## Notes

- No task adds a new dependency, persisted field, capture callback, process observer, route, permission, telemetry event, or server API.
- Mark tasks `[X]` only after the implementation and its named validation pass.
