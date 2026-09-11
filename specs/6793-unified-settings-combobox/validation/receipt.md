# F6793 validation — 2026-09-11

Base: `ad71f2ce4db68d846d7c333213961c5f5f7d5e89`, branch `6793-unified-settings-combobox`.
Lane: high-risk-feature (shared UX/accessibility); no production deploy.

## Requirements
Spec/clarify/plan/checklist/tasks выполнены. Clarify 0 questions, решение ограничено существующими настройками. Independent UX reviewer 6/6 PASS. Analyze initial C1 (неполные пути задач) исправлен; повторный analyze PASS, FR/SC coverage 12/12. GitHub owner всех T001–T006: #6924; issue canon validation PASS.

## Functional evidence
- `node apps/server/tests/browser/timezone-settings.test.cjs`: PASS. Реальная форма/отправка, поиск русский/IANA/UTC, выбор, preview, Cancel, network/422 retry, redirect, no-JS.
- `node apps/server/tests/browser/settings-combobox.test.cjs`: Chromium PASS и WebKit PASS. Actual recording/notification templates + synthetic bridges; actual summary editor dialog/default selection; app filter, массовое правило скрытым строкам, клавиатура/IME, no-match, reset, disabled/catalog, pending refresh, narrow viewport, 600 вариантов ≤1 мс.
- `uv run --project apps/server --extra dev pytest apps/server/tests/contract/test_settings_ui_contract.py -q`: 25 passed (2 upstream warnings).
- `swift test --package-path apps/macos --filter 'NativeSettingsComboBoxTests|CaptureControlV5Tests|AppControlAccessibilityTests|DesktopNotificationControlTests'`: 51/51 PASS, в том числе 7 новых native handler checks.
- `swift test --package-path apps/macos --filter EmbeddedCabinetRecordingSettingsBridgeTests`: 5/5 PASS, настоящий WKWebView и локальное хранилище правил.
- `node --check .../cabinet.js`, `git diff --check`: PASS.
- `scripts/check_spec_kit_governance.py`: PASS с изолированным specify-cli 1.0.1 на закреплённом ref из lock; глобальный CLI другой версии не менялся.

- Финальный совместный Swift запуск: `swift test --package-path apps/macos --filter 'NativeSettingsComboBoxTests|CaptureControlV5Tests|AppControlAccessibilityTests|DesktopNotificationControlTests|EmbeddedCabinetRecordingSettingsBridgeTests|EmbeddedCabinetNotificationSettingsBridgeTests'`: 61/61 PASS.
- Скриншоты из автоматической синтетической проверки проверены визуально: одно поле приложений, варианты под ним, перенос длинных строк, отсутствие горизонтального выхода на ширине 375; светлая/тёмная темы. Скриншоты вне git.

## Scope inventory
Аккаунт: пояс. Запись: приложение, общее и индивидуальное правило. Итоги: шаблон, язык и подробность. Уведомления: время напоминания. Offline macOS: приложения/правила/напоминание. Календари (флажки), пространство (карточки), тема (radio) и billing (кнопки) не имеют раздельного search/select; сохранены. Сквозной source scan всех settings templates не находит немаркированных select/старого timezone-search.

## Review / limitations
Независимый web review нашёл P2: refresh(read) стирал активный ввод; исправлено отложенным read до завершения выбора/ухода фокуса, добавлен regression scenario. Меню вынесено в поддерживаемый браузером popover top layer с fixed fallback, ограничено видимой областью, закрывается при прокрутке внешней страницы. Повторный независимый review PASS: P2 воспроизведением снят, новых замечаний нет; Ponytail-review — без лишних зависимостей/абстракций.
Native tests проверяют AppKit delegate/action, а не реальный popup event loop или VoiceOver. Установленный GRAF Dev/визуальная native приёмка и exact-SHA PR governance-fast остаются T006. Никакого публичного release/deploy.

## Converge checkpoint
Проверены spec/plan/tasks/constitution и текущий код. Новых обязательных работ по реализации не обнаружено; все найденные требования имеют реализацию/локальные проверки. T005 завершён, T006 остаётся открытой задачей приёмки: коммит после отдельного разрешения, установка GRAF Dev через harness, системное меню/VoiceOver, затем exact-SHA PR governance-fast. Полная приёмка фичи и release не объявляются. Существующая T006 покрывает остаток, дублирующая convergence task не создаётся.

Shared Dev status (read-only): active feature 6792, SHA `d73d9087f609e6c0e33de8238174e49e242218ad`, manifest `dev-d73d9087f609`; эта версия не содержит F6793. До разрешения коммита стенд не обновлялся.
