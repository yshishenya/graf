# Tasks: Сквозное укрепление интерфейса GRAF

**Input**: Design documents from `specs/293-interface-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: High-risk lane; write/adjust focused tests before implementation where practical.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1..US5
- Exact file paths are included.

## Phase 1: Setup

- [X] T001 [P] Add owned release fragment `changes/unreleased/F293.yaml` with planned changes and validation placeholders.
- [X] T002 [P] Create `apps/macos/RecApp/Sources/AppShell/`, `apps/macos/Shared/Tests/AppShellBehaviorTests.swift` and `apps/macos/Shared/Tests/CaptureStatusPresentationTests.swift` skeletons importing `@testable TwoBrainRecAppCore`.

---

## Phase 2: Foundational (blocking)

- [X] T003 Move `ContentView`, `AppContentRoot`, `MeetingDetectionPrompt`, `AppLifecycleDelegate`, `AppLog` and prompt types from `apps/macos/RecApp/App/TwoBrainRecApp.swift` to `apps/macos/RecApp/Sources/AppShell/ContentView.swift`, `AppLifecycleDelegate.swift` and `AppLog.swift`; leave only the `@main` shim in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T004 Create `apps/macos/RecApp/Sources/AppShell/AppMenuBuilder.swift` with testable `makeMenu` and move `installMainMenu`/selector logic out of the executable target.
- [X] T005 Add `CaptureStatusPresentation.swift`, `RecordingBlockerPresentation.swift`, `LocalRecordingPresentation.swift` under `apps/macos/RecApp/Sources/Capture/`, `InterfacePreferences.swift` and `AccountSwitchResetPolicy.swift` under `apps/macos/RecApp/Sources/AppShell/`/`Cabinet/` per `data-model.md`.
- [X] T006 Add `apps/macos/Shared/Tests/DesktopDesignTokenContractTests.swift` parsing `cabinet.css` core variables and comparing `DesktopDesignTokens`.
- [ ] T007 Move `DesktopDesignTokens.swift`, `DesktopWebButtonStyle` and `DesktopMeetingShellChrome` into `apps/macos/RecApp/Sources/DesignSystem/`; update imports and source-text test paths so Capture does not depend on Cabinet for design primitives.
- [X] T008 Add `apps/macos/Shared/Tests/InterfacePerformanceContractTests.swift` skeleton and update existing source-text tests in `Shared/Tests/AppControlAccessibilityTests.swift`/`DesktopNotificationAppIntegrationTests.swift` to the new AppShell paths or replace them with behavior tests.

**Checkpoint**: app-shell is testable, presentation/reset/preferences models exist, project builds.

---

## Phase 3: US1 — Доверять состоянию записи (P1)

- [X] T009 [P] [US1] Add failing matrix tests in `apps/macos/Shared/Tests/CaptureStatusPresentationTests.swift` for capture, local-custody and blocker states, actions, tones, forbidden strings and partial-upload/expired copy.
- [X] T010 [US1] Implement `CaptureStatusPresentation`, `RecordingBlockerPresentation` and `LocalRecordingPresentation` per `data-model.md`, including `saving/active/saved/degraded/blocked/failed/terminal/deleting/corrupted/uploading/expired`.
- [X] T011 [US1] Wire the shared status presentation into `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`, `CaptureStatusItem.swift`, `Cabinet/DesktopMeetingShellView.swift` titlebar HUD and `Calendar/CalendarTray.swift`; remove duplicate state switches.
- [ ] T012 [US1] Add `PermissionPresentation` in `apps/macos/RecApp/Sources/Capture/PermissionPresentation.swift`; use it in `DesktopPermissionOnboardingView.swift`, `CaptureControlViewCore.swift` and `SystemAudioPermissionGate.swift`.
- [X] T013 [US1] Remove raw failure codes from `SystemAudioStatusLabels.captureFailureDetail` in `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`; map codes to human copy and update `CaptureControlV5Tests`/`DesktopUploadQueueV5Tests`.
- [X] T014 [US1] Replace `recordingBlocker: String?`/`localRecordingStatus: String?` in `apps/macos/RecApp/Sources/AppShell/ContentView.swift` with typed models; remove `contains`-based decisions and add regression tests in `AppShellBehaviorTests.swift`/`CaptureStatusPresentationTests.swift`.

**Checkpoint**: status/blocker/custody/permission logic is typed; no raw codes or text-dependent behavior.

**Deferred note**: T012 не добавляет параллельный `PermissionPresentation`, чтобы не дублировать существующий типизированный `SystemAudioPermissionGate`/`SystemAudioPermissionPresentation`, который остаётся источником для стартового гейта. Унификация текстов онбординга с этим гейтом — отдельная задача.

---

## Phase 4: US2 — Не терять контекст и управление (P1)

- [X] T015 [P] [US2] Add failing `AccountSwitchResetTests` in `apps/macos/Shared/Tests/AccountSwitchResetTests.swift` for route, prompt, player, selection, bridges and in-flight responses.
- [X] T016 [US2] Implement `AccountSwitchResetPolicy` and wire it from the auth-change handler in `ContentView.swift`; reset route to meetings, prompts, pending/failed state, player, selection and web bridges; clear cabinet-origin `localStorage`/`sessionStorage` or isolate per account.
- [X] T017 [US2] Add application-menu «Остановить запись» with `⌘⇧S` in `AppMenuBuilder.swift`/`AppLifecycleDelegate.swift`, validated by the control snapshot; localize menu items, remove duplicate `Zoom In`, resolve `⌘0`, scope zoom to the cabinet and fix the hidden-window update alert.
- [X] T018 [US2] Make `LocalSettingsFallbackView` section-aware for «Аккаунт», «Запись», «Уведомления», «Календарь», «Биллинг» in `MeetingDetectionSettingsView.swift`/`ContentView.swift`; add distinct cabinet empty/loading/error states in `DesktopCabinetWorkspaceView.swift`/`EmbeddedCabinetWebView.swift`.
- [X] T019 [US2] Persist window frame, inspector expansion and microphone via `InterfacePreferences` in `AppLifecycleDelegate.swift`/`DesktopMeetingShellView.swift`/`ContentView.swift`; implement mic disconnect/reconnect, quit-during-save and notification-card overlay rules.
- [X] T020 [US2] Add behavior tests for account reset, stop availability, settings sections, preferences, mic reconnect, quit-during-save and overlay in `AppShellBehaviorTests.swift`/`AccountSwitchResetTests.swift`.

**Checkpoint**: account switch, global stop, settings fallback and preferences work and are tested.

---

## Phase 5: US3 — Работать без подтормаживаний (P1)

- [X] T021 [US3] Cache available microphone inputs in `MicrophoneCaptureService.swift` with connect/disconnect refresh; move `EmbeddedCabinetLocalRecordingRow.rows` out of `ContentView.body` into detached queue-change computation.
- [X] T022 [US3] Add bounded `DateFormatter` cache in `apps/macos/Shared/Sources/UserTime.swift`; move `loadItems`/`applyRetentionExpiry`/`currentDeletionOperations` off MainActor; make `AppLog` asynchronous/batched with cached ISO8601 and cheaper `BoundedLogFileWriter` append.
- [ ] T023 [US3] Pause 30-second refresh loops while inactive; add `os_signpost` around capture actions; run the 60-minute/100-item measurement and record `specs/293-interface-hardening/validation/performance.md`.

**Checkpoint**: render path has no blocking I/O/device work; latency budget is measured.

---

## Phase 6: US4 — Цельный и доступный интерфейс (P2)

- [X] T024 [US4] Update `SystemAudioStatusLabels` and all surfaces to canonical «Остановить запись», «Выключить микрофон», «Включить микрофон»; remove visible `Mute`; add menu/copy tests in `AppMenuBuilderTests.swift`/`SystemAudioLocalizationTests.swift`.
- [ ] T025 [US4] Add `accessibilitySortPriority` for capture region, reduce-motion handling in `EqualizerBars`, increased-contrast handling in settings/onboarding, `@ScaledMetric`/adaptive widths in shell/onboarding/settings and long-string tests.
- [X] T026 [US4] Add «Скопировано» feedback to `DesktopSupportIncidentActionStrip.swift`; use `DesktopUserTimeContext.shared.timeZone` in `DesktopNotificationPresenter.swift` and `EmbeddedCabinetLocalRecordingRow.rows`; add accessibility tree tests in `AppShellBehaviorTests.swift`.

**Checkpoint**: menus/copy/accessibility are consistent; critical actions work with keyboard/VoiceOver and long strings.

**Partial note**: T025 выполнил `accessibilitySortPriority`, reduce-motion и адаптивные `@ScaledMetric`-ширины. Отдельная матрица increased-contrast и длинных строк не добавлена; существующие accessibility-проверки меню, панели и карточки находятся в `AppControlAccessibilityTests` и `DesktopNotificationAccessibilityTests`.

---

## Phase 7: US5 — Безопасно развивать и выпускать (P2)

- [X] T027 [US5] Remove confirmed dead types/constants/methods (`CaptureFinalizationService`, `DebugClipCleanupService`, dead enums, unused status/menu constants) and update `AppControlAccessibilityTests`/`DesktopDesignTokensTests`/other affected tests.
- [ ] T028 [US5] Remove confirmed dead CSS classes from `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and update/add `apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py`.
- [ ] T029 [US5] Extract shared `TitlebarAccessoryHost` and `CaptureTransportControls`; fix `EmbeddedCabinetWebView.swift` compiler warnings without behavior change; add tests.
- [X] T030 [US5] Run `swift build`, focused tests, full `apps/macos/Scripts/run-swift-tests.sh`, `ci-local.sh --fast`; update `specs/293-interface-hardening/validation.md`, `docs/current-product-status.md` and `changes/unreleased/F293.yaml`.

**Checkpoint**: dead code removed, warnings reduced, validation evidence recorded.

---

## Phase 8: Release

- [X] T031 Create PR, run required GitHub checks and `scripts/validate-pr-checks.py`; record URLs/IDs in `specs/293-interface-hardening/validation.md`.
- [ ] T032 Prepare release `v2026.11.10.3` with `GRAF_RELEASE_OPERATOR` and `./scripts/prepare-release.sh 2026.11.10.3`; run `infra/scripts/cd-remote.sh --dry-run`.
- [ ] T033 Build/notarize/staple with `release-app-update.sh --phase prepare`; publish tag/GitHub Release and run `--phase publish --verify-feed 2026.11.10.3`.
- [ ] T034 Re-download public artifacts and verify appcast version/URL/length/XML/SHA-256, Sparkle signature and Gatekeeper in `specs/293-interface-hardening/validation/release.md`; close issue #7967 and task issues with Russian closure comments.

## Dependencies & Execution Order

- Phase 2 blocks all user stories.
- US1 and US2 can proceed after Phase 2; US3 depends on stable state shapes; US4 after US1/US2; US5 before release.
- Release only after T030/T031 and all checklist/analyze gates.

## Implementation Strategy

1. Foundational move + typed models + tests.
2. US1/US2 behavior fixes.
3. US3 performance.
4. US4 accessibility/copy.
5. US5 cleanup and release.
