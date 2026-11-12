# Tasks: Исправления после ревью интерфейса

**Note**: T013 выполнена частично: новые поведения покрыты тестами, массовое удаление 437 source-text assertions оставлено отдельным долгом, чтобы не ослабить покрытие в этом релизе.

**Input**: `specs/294-interface-review-fixes/spec.md`, `plan.md`
**Tests**: high-risk lane; behavior tests first where practical.

## Phase 1: Корректность управления

- [X] T001 Add `DesktopCabinetNavigationShortcut` model; change «Домой» to a non-conflicting shortcut; add a test that navigation shortcuts are unique and do not collide with `WorkspaceZoomMenu`.
- [X] T002 Unify Stop/Pause visibility for `CaptureStatusItem`, titlebar, menu and accessibility; disable repeat Stop during `.stopping`.
- [X] T003 Fix saved-microphone restore: unavailable saved device falls back to the system default and is cleared from preferences.
- [X] T004 Handle disconnect of the effective system/default microphone, not only the explicitly selected one; add tests.

## Phase 2: Приватность и актуальность

- [X] T005 Await `WKWebsiteDataStore.removeData` before posting auth change/reloading the cabinet.
- [X] T006 Recompute local recording rows when the desktop time zone changes.
- [X] T007 Add recording/degraded/failed distinction to `GrafTrayRecordingState` and menu-bar labels.
- [X] T008 Fix settings fallback: «Все настройки GRAF» opens the general account route; sidebar lists all five sections.

## Phase 3: Упрощение

- [X] T009 Remove unused states/fields from `LocalRecordingPresentation`, `CaptureStatusPresentation`, `RecordingBlockerPresentation`.
- [X] T010 Remove `AccountSwitchResetPlan`/`AccountSwitchResetPolicy` unused flags and storage script; inline the single reset path.
- [X] T011 Consolidate local-recording copy in `SystemAudioStatusLabels`/`LocalRecordingPresentation`; remove unused labels.
- [X] T012 Remove unused `LocalSettingsFallbackView(notifications:)`, use `CaseIterable` for all sections, flush logs on termination.
- [X] T013 Replace brittle source-text checks touched by these changes with behavior tests where practical; keep the rest as documented debt.

## Phase 4: Проверки и выпуск

- [X] T014 Update `InterfacePreferencesStore` frame validation for minimum size and visible-screen intersection; add tests.
- [X] T015 Move microphone discovery off MainActor and make `resolveRecordingMicrophoneSelection` use the cached input list; add performance-contract tests.
- [X] T016 Run build, focused tests, full Swift suite, ContractValidation and `ci-local.sh --fast`; record evidence.
- [ ] T017 Create PR, run `governance-fast`, `macos-pr`, `pr-metadata` and `validate-pr-checks.py`.
- [ ] T018 Prepare CalVer release, freeze candidate, run `release-full`, build/notarize/staple/Gatekeeper/Sparkle.
- [ ] T019 Run `cd-remote.sh --dry-run`, deploy production, verify public health/runtime SHA, publish GitHub Release and appcast.
- [ ] T020 Close task issues/umbrella with Russian evidence comments.

## Dependencies

- T001–T013 before T014–T017.
- T018 only after T016/T017 pass.
- T019 only after T018 and explicit production approval.
- T020 after public artifacts and deploy evidence.
