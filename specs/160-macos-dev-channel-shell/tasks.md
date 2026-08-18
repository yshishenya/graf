---
description: "Dependency-ordered implementation tasks for macOS Dev Channel and Native Home"
---

# Tasks: macOS Dev Channel and Native Home

**Risk lane**: `high-risk-feature`; no public release/deploy.

## Phase 1: Contract-first coverage

- [X] T001 [P] [US1] Add Dev bundle/origin/no-feed/stable-signer static contract tests for `apps/macos/Scripts/build-dev-app.sh` and `apps/macos/Scripts/install-dev-app.sh` in `apps/macos/Shared/Tests/DevChannelPackagingTests.swift`.
- [X] T002 [P] [US2] Add channel-aware application-support path tests for recordings, upload queue, meeting detection, and telemetry in `apps/macos/Shared/Tests/DevChannelStorageTests.swift` and existing store test files.
- [X] T003 [P] [US3] Add Home identifier and safe canonical-route/native control assertions to `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

## Phase 2: Channel and storage implementation

- [X] T004 [US1] Add explicit channel parsing and stable names in `apps/macos/RecApp/Sources/Support/GrafAppChannel.swift`.
- [X] T005 [US2] Route local recordings and upload queue storage through the channel helper in `apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T006 [US2] Route meeting-detection settings/cache/telemetry through the same channel namespace in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionAppModule.swift` and `MeetingDetectionTelemetryRollupStore.swift`.

## Phase 3: Dev build/install

- [X] T007 [US1] Add the loopback-only signed Dev builder in `apps/macos/Scripts/build-dev-app.sh`, including stable `GRAF Dev` metadata, separate bundle ID, no Sparkle feed, usage descriptions, and a visibly distinct DEV icon treatment.
- [X] T008 [US1] Add atomic build/install/update command `apps/macos/Scripts/install-dev-app.sh` that verifies signing identity, designated requirement, bundle ID, origin, storage namespace, and production app non-interference before replacing only `/Applications/GRAF Dev.app`.
- [X] T009 [US2] Add fail-closed signer/origin/feed/storage assertions and metadata-only validation to `apps/macos/Shared/Tests/DevChannelPackagingTests.swift`; never add TCC reset/workaround commands.

## Phase 4: Native Home

- [X] T010 [US3] Add Home capability and safe `goHome()` loading to `EmbeddedCabinetNavigationController`, including attach/detach/session-expiry state handling, without changing existing Back/Forward/Reload guards.
- [X] T011 [US3] Add labeled Home control, keyboard shortcut, disabled state, tooltip, and accessibility identifier to `DesktopCabinetNavigationControls` in `DesktopCabinetWorkspaceView.swift` and `DesktopCabinetState.swift`.

## Phase 5: Validation and review

- [X] T012 Run Swift focused tests, shell syntax checks, Dev metadata checks, and the feature quickstart; fix findings with one regression check per root cause.
- [X] T013 Review permissions, signing, updater, storage isolation, external navigation, auth/session recovery, accessibility, and Ponytail simplification; record `specs/160-macos-dev-channel-shell/analysis.md`.
- [X] T014 Run native computer-use smoke when the Mac is unlocked, run `infra/scripts/ci-local.sh --fast`, and record metadata-only evidence and limitations in `quickstart.md`.

## Dependency order

T001–T003 precede T004–T011. T004–T006 precede T007–T009. T010–T011 are
sequential within the native navigation file. T012 precedes T013 and T014.
