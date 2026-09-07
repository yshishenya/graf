# Tasks: Автозапись в общих настройках

Input: spec.md, plan.md, research.md, data-model.md, contracts/recording-settings.md.
Lane: high-risk-feature. Tests required by spec. Owner: текущий агент реализации.

## Phase 1 — Foundation
- [x] T001 Добавить проверки и атомарный patch настроек в apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift; подключить writers в MeetingDetectionSettingsView.swift и apps/macos/RecApp/App/TwoBrainRecApp.swift. FR-003–005.

## Phase 2 — US1
- [x] T002 [US1] Проверить и реализовать узкий native bridge в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetRecordingSettingsBridge.swift и EmbeddedCabinetWebView.swift, тесты в apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift. FR-001–005, FR-007.
- [x] T003 [US1] Перенести форму в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html и cabinet/static/cabinet/cabinet.js, проверки в apps/server/tests/contract/test_settings_ui_contract.py. FR-001–005, FR-008–009.

## Phase 3 — US2
- [x] T004 [US2] Перенаправить входы настроек с сохранением локального резерва в apps/macos/RecApp/App/TwoBrainRecApp.swift; проверить routes/build и неизменность панели. FR-006, FR-008, FR-010.

## Phase 4 — Validation
- [x] T005 Выполнить quickstart и convergence, записать evidence в specs/245-web-recording-settings/validation.md и changes/unreleased/245-web-recording-settings.md. SC-001–004.

## Dependencies & Strategy
T001 → T002 → T003 → T004 → T005. Тесты каждого блока пишутся перед кодом.
US1 проверяется через синтетический store/WebKit, US2 через navigation/fallback.
МVP — оба сценария с неизменными захватом и панелью. Независимые Swift/pytest
проверки можно запускать одновременно; реализация выполняется последовательно.
Внешнее закрытие требует PR и соответствующих gate; до этого GitHub issues остаются
открытыми с локальным evidence, даже если код проверен.

- T001: https://github.com/yshishenya/graf/issues/6591

- T002: https://github.com/yshishenya/graf/issues/6592

- T003: https://github.com/yshishenya/graf/issues/6593

- T004: https://github.com/yshishenya/graf/issues/6594

- T005: https://github.com/yshishenya/graf/issues/6595

Локальная реализация и проверки завершены: [validation.md](validation.md). PR/release evidence остаётся открытым внешним gate.
