# Tasks: F6793

## Phase 1: Requirements
- [X] T001 Проверить требования и UX checklist в `specs/6793-unified-settings-combobox/checklists/ux.md`, выполнить analyze и синхронизацию GitHub.

## Phase 2: US1 / US2
- [X] T002 [US1] [US2] Сначала адаптировать `apps/server/tests/browser/timezone-settings.test.cjs` и добавить `apps/server/tests/browser/settings-combobox.test.cjs`, покрыть FR-001–FR-007/SC-001–SC-003.
- [X] T003 [US1] [US2] Реализовать общий выбор и фильтр в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`; проверить все settings surfaces.
- [X] T004 [US1] [US2] Реализовать такой же ввод/выбор в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; выполнить focused проверки `apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift`, `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`, `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

## Phase 3: Validation
- [X] T005 Выполнить проверки, независимый review/Ponytail и converge; записать `specs/6793-unified-settings-combobox/validation/receipt.md` и `changes/unreleased/F6793.yaml` (FR-008).
- [ ] T006 После разрешённого коммита проверить единственный `/Applications/GRAF Dev.app` через harness и exact-SHA PR governance-fast, записать evidence в `specs/6793-unified-settings-combobox/validation/receipt.md` (FR-006, FR-008, SC-004).

- [ ] T007 [US3] Увеличить и ограничить экраном резервное окно в `apps/macos/RecApp/App/TwoBrainRecApp.swift`, уплотнить строки в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; проверить обе вкладки и длинные названия в установленном GRAF Dev (FR-009).

GitHub owner T001–T007: https://github.com/yshishenya/graf/issues/6924

Dependencies: T001 → T002 → T003 → T004 → T005 → T007 → T006. Release/deploy вне текущего исполнения.

T004 implementation: `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`; tests: `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift`.
