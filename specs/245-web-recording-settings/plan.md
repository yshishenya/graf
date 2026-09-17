# Implementation Plan: Автозапись в общих настройках

**Branch**: `codex/245-web-recording-settings` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary
Один существующий экран записи, локальный исполнитель через WebKit.
Существующая нативная форма остаётся резервной. Панель и захват не меняются.

## Technical Context
- Swift 6/macOS 14+, WebKit, SwiftUI; Python/Jinja и существующий cabinet.js.
- Storage: прежний MeetingDetectionSettingsStore, без миграции или серверной БД.
- Dependencies: только уже используемые системные API и зависимости.
- Risk / Validation Lane: high-risk-feature, граница WebView и предпочтения записи.
- Release Gate: no deploy; commit/push/PR разрешены пользователем 2026-09-06; merge/release не входят.
- Tests: XCTest, pytest, синтетическая страница и нативная WebKit проверка.
- Scale: текущий проверенный реестр, одна форма; нет опроса сервера или новой службы.

## Constitution Check
До исследования и после дизайна: PASS. Локальное хранение и резервная форма
позволяют читать/менять правила без сервера; автозапись и 8 секунд не меняются.
Нативные Record/Stop/permissions/индикаторы остаются вне этой работы.
Никаких аудио, секретов и содержимого встреч в новых сообщениях или evidence.

## Design
- MeetingDetectionSettingsStore: последовательное load/patch/atomic-save,
  общая очередь для экземпляров в одном процессе. Existing UI и remembered
  choice используют тот же patch, не сохраняют устаревший снимок.
- Новый EmbeddedCabinetRecordingSettingsBridge в Cabinet: WebKit message handler
  with reply, фиксированный version=1 и короткий список read/set/setAll.
  Каждый document получает новый nonce; navigation start инвалидирует старый.
  Доверенные source/current URL, main frame, attached active view и nonce
  проверяются до доступа к store. Реестр читается нативно.
- Ответ содержит только id/name/rule, success/error. Native notifications
  обновляют форму после remembered choice и обновления реестра.
- Шаблон settings_recording_content.html: подпись «На этом Mac», раздел автозаписи,
  native select с тремя значениями, массовый select со смешанным состоянием.
  Элементы скрыты до успешного чтения. Локальная ссылка сохраняется всегда.
- cabinet.js: загрузка/сохранение/ошибка/повтор, обновление без потери фокуса,
  поддержка HTMX и защиты от позднего ответа на уже закрытую форму.
- TwoBrainRecApp: общий вход меню отправляет notification в существующее главное
  окно; готовый кабинет выбирает /desktop/settings/recording. Иначе открывается
  прежняя локальная форма. Перехваченный legacy URL всегда открывает именно её.

## Validation Plan
Сфокусированные проверки из quickstart. Локальная проверка схемы/Swift build/UI.
Перед PR требуется governance-fast на его точном SHA; перед release полный gate,
notarization и CD. Эти внешние этапы не объявляются выполненными локальными тестами.

## Project Structure
- apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetRecordingSettingsBridge.swift
- apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
- apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift
- apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift
- apps/macos/RecApp/App/TwoBrainRecApp.swift
- apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html
- apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
- apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift
- apps/server/tests/contract/test_settings_ui_contract.py
- changes/unreleased/F245.yaml
