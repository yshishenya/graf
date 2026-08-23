# Tasks: Деликатный индикатор источника записи

**Input**: Design documents from `/specs/197-recording-indicator-polish/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/recording-indicator-polish.md`, `quickstart.md`

**Validation lane**: high-risk UX change inside an active Spec Kit slice;
focused XCTest, native macOS build, metadata-only visual smoke, then
`infra/scripts/ci-local.sh --fast`. No deploy or release work.

## Phase 1: Setup

**Purpose**: Reuse the existing native capture surface and session evidence.

- [X] T001 Confirm the implementation uses the existing SwiftUI package, `CaptureSession.triggerEvidence`, shared source labels, and no new dependency in `apps/macos/Package.swift`, `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`, and `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`.

## Phase 2: Foundational contracts

**Purpose**: Lock the user-visible source and accessibility contracts before
changing the titlebar layout.

- [X] T002 [P] [US1] Add focused known-app, manual-system-audio, unknown-source, and lifecycle expectations for the quiet titlebar label in `apps/macos/Shared/Tests/CaptureIndicatorTests.swift`.
- [X] T003 [P] [US2] Add titlebar source identifier, full-label/help, single-surface, and preserved action assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

**Checkpoint**: Contract tests describe the requested outcome and are ready to
fail before the SwiftUI implementation changes.

## Phase 3: User Story 1 — Сразу понять, что записывается (Priority: P1) 🎯 MVP

**Goal**: Show the confirmed app in the existing upper recording indicator.

**Independent test**: With active synthetic evidence `Zoom`, focused tests and
the local HUD show `Источник · Zoom` without opening the sidebar.

- [X] T004 [US1] Add the shared quiet source presentation label helper and remove the duplicate sidebar source row while preserving `sourceDisplayName` and `sourceAccessibilityLabel` in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`.
- [X] T005 [US1] Render the non-interactive, secondary, single-line source text inside the existing status group of `RecordingTitlebarHUD` in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.

**Checkpoint**: Known app, manual-system-audio, unknown-source, and lifecycle
states remain source-truthful in the upper indicator.

## Phase 4: User Story 2 — Не спутать информацию с новой плашкой (Priority: P1)

**Goal**: Keep one outer capsule and preserve the current Pause/Resume/Stop
hierarchy and geometry.

**Independent test**: The source has no background, border, icon or click action;
the existing controls remain separate and reachable in active and paused states.

- [X] T006 [US2] Apply bounded width, tail truncation, secondary GRAF typography,
  no new surface, and existing spacing/tokens to the source child in
  `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.
- [X] T007 [US2] Keep the source label inside the existing HUD accessibility
  container while leaving Pause/Resume/Stop as independent accessible actions in
  `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.

**Checkpoint**: The titlebar remains a single calm recording capsule with the
source subordinate to status and controls.

## Phase 5: User Story 3 — Сохранить честные и доступные состояния (Priority: P2)

**Goal**: Preserve truthful fallbacks, full semantic names and disappearance
after active capture.

**Independent test**: Focused XCTest covers fallback values, lifecycle removal,
long-name truncation contract, VoiceOver label and native help.

- [X] T008 [US3] Add focused `sourceIndicatorLabel(for:)` assertions for known-app
  context copy, exact manual/unknown fallback copy, and stopped-session removal
  in `apps/macos/Shared/Tests/CaptureIndicatorTests.swift`.
- [X] T009 [US3] Verify the source child uses `systemAudio.status.source`, the
  full `Источник: <name>` label and help text, while the sidebar no longer owns a
  duplicate source presentation, in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

**Checkpoint**: Source truth and accessibility remain stable across active,
paused, degraded and stopping states and are absent after finalization.

## Phase 6: Polish and validation

**Purpose**: Document the behavior and run the selected validation lane.

- [X] T010 [P] Update the Unreleased section with the single-surface source-label
  behavior in `CHANGELOG.md`.
- [X] T011 Run `swift test --package-path apps/macos --filter CaptureIndicatorTests`
  and `swift test --package-path apps/macos --filter AppControlAccessibilityTests`
  from `specs/197-recording-indicator-polish/quickstart.md`.
- [X] T012 Build the native macOS app and perform metadata-only visual smoke for
  active, paused, degraded, narrow and finalized states using
  `specs/197-recording-indicator-polish/quickstart.md`.
- [X] T013 Run the selected macOS repository gate, inspect the final diff, and
  record the server-CI skip when no server paths are changed. Release/deploy
  was initially out of scope and was later explicitly authorized by the owner;
  its evidence is recorded in the release note.

## Dependencies & Execution Order

- T001 precedes all implementation work.
- T002 and T003 can run in parallel after T001 and must precede T004–T007.
- T004 precedes T005; T006–T007 refine T005 in the same file.
- T008–T009 run after T004–T007 because they cover the new helper and the moved
  titlebar ownership rather than duplicating the existing source mapping tests.
- T010 can run in parallel with T004–T009 because it touches a separate file.
- T011–T013 run after implementation and documentation tasks.

> T012 evidence: native build passed; live smoke covered active, paused, narrow,
> and finalized states. The degraded path remains covered by focused state and
> accessibility tests rather than forcing a permission failure in the local app.

## Parallel Opportunities

```text
T002  apps/macos/Shared/Tests/CaptureIndicatorTests.swift
T003  apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
T010  CHANGELOG.md
```

These tasks have disjoint write sets. SwiftUI implementation tasks T004–T007
remain sequential because they intentionally move one presentation contract
between two related surfaces.

## Implementation Strategy

1. Lock the source/accessibility contract.
2. Move the existing source presentation to the upper HUD with the smallest
   native SwiftUI diff.
3. Validate each user story independently, then run the fast repository gate.
4. Leave production, release, notarization, Sparkle and appcast state untouched.
