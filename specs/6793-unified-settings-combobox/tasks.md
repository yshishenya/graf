# Tasks: F6793

## Phase 1: Requirements
- [X] T001 Проверить требования и UX checklist в `specs/6793-unified-settings-combobox/checklists/ux.md`, выполнить analyze и синхронизацию GitHub.

## Phase 2: US1 / US2
- [X] T002 [US1] [US2] Сначала адаптировать `apps/server/tests/browser/timezone-settings.test.cjs` и добавить `apps/server/tests/browser/settings-combobox.test.cjs`, покрыть FR-001–FR-007/SC-001–SC-003.
- [X] T003 [US1] [US2] Реализовать общий выбор и фильтр в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`; проверить все settings surfaces.
- [X] T004 [US1] [US2] Реализовать такой же ввод/выбор в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; выполнить focused проверки `apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift`, `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`, `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

## Phase 3: Validation
- [X] T005 Выполнить проверки, независимый review/Ponytail и converge; записать `specs/6793-unified-settings-combobox/validation/receipt.md` и `changes/unreleased/F6793.yaml` (FR-008).
- [X] T006 После разрешённого коммита проверить единственный `/Applications/GRAF Dev.app` через harness и exact-SHA PR governance-fast, записать evidence в `specs/6793-unified-settings-combobox/validation/receipt.md` (FR-006, FR-008, SC-004).

- [X] T007 [US3] Увеличить и ограничить экраном резервное окно в `apps/macos/RecApp/App/TwoBrainRecApp.swift`, уплотнить строки в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; проверить обе вкладки и длинные названия в установленном GRAF Dev (FR-009).

GitHub owner T001–T007: https://github.com/yshishenya/graf/issues/6924

Dependencies: T001 → T002 → T003 → T004 → T005 → T007 → T006. Release/deploy вне текущего исполнения.

T004 implementation: `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`; tests: `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift`.

## Phase 4: Предпосылка установленной проверки
- [X] T008 Исправить загрузку датированных MinIO образов в `scripts/dev-harness.py`, описать политику в `infra/dev/README.md` и проверить cache/fail-closed в `tests/governance/test_graf_local_adapter.py` и `tests/governance/test_dev_harness.py` (FR-010).

T008 → T006; GitHub owner T008: https://github.com/yshishenya/graf/issues/6924.

## Phase 5: Визуальная итерация по замечаниям пользователя
Исторические T006/T007 фиксируют проверку прежнего кандидата; готовность PR вновь открыта до T009–T011.
- [X] T009 [US1] [US2] Проверить источники 2026 и примеры продуктов в `specs/6793-unified-settings-combobox/research-ui-2026.md`, определить `contracts/compact-dropdown.md`, выполнить независимый UX checklist/analyze и синхронизировать #6924 (FR-011).
- [X] T010 [US1] [US2] Исправить оболочку, фокус и расчёт строк в `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`, ограничить поле в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`, обновить раскрытие/геометрию в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и уплотнить общий web CSS `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; добавить focused проверки геометрии и состояния в `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift` и `apps/server/tests/browser/settings-combobox.test.cjs` (FR-011, SC-005).
- [ ] T011 [US3] Проверить установленный GRAF Dev с раскрытыми меню обеих вкладок, темы, длинные строки, край экрана и сохранение поведения; выполнить independent review/converge, обновить `specs/6793-unified-settings-combobox/validation/receipt.md` и `changes/unreleased/F6793.yaml`, exact-SHA PR checks (FR-008, FR-009, FR-011, SC-004, SC-005).

Dependencies: T009 → T010 → T011. GitHub owner T009–T011: https://github.com/yshishenya/graf/issues/6924.

## Phase 6: Convergence после установленной проверки
- [ ] T012 [US2] Исправить подтверждение щелчком в новой нативной панели в `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`, проверить доступность списка вариантов и добавить регрессионную проверку в `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift`; повторить установленную приёмку T011 (FR-004, FR-006, FR-011).

T012 → T011. GitHub owner T012: https://github.com/yshishenya/graf/issues/6924.

## Phase 7: Convergence по GitHub review
- [X] T013 [US2] Выделять подтверждённое название при начале редактирования нативной настройки в `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`, не сбрасывая уже введённый запрос или фильтр приложений; добавить регрессию в `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift` (FR-003, FR-004, review3997548962).
- [X] T014 [US1] Сохранять запрос приложений при повторном раскрытии и использовать одинаковое нормализованное сравнение для вариантов и строк в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`; применить тот же контракт сохранения запроса и поиска по имени в `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`, проверить в `apps/server/tests/browser/settings-combobox.test.cjs` и `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift` (FR-002, FR-003, review3997548965, review3997548968).

T013/T014 → T011. GitHub owner: https://github.com/yshishenya/graf/issues/6924.

## Phase 8: Convergence GitHub CI
- [ ] T015 Уточнить проверку единственного обработчика шкалы записи в `apps/server/tests/contract/test_cabinet_static_assets_contract.py`: допускать независимый resize обработчик списка настроек, сохранив проверки границ/повторного подключения; выполнить связанные проверки настроек и exact-SHA GitHub CI (FR-008, FR-011).

GitHub owner T015: https://github.com/yshishenya/graf/issues/6924.
