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

## Установленная проверка кандидата 65dccbaa567e
Коммит/push и promote выполнены по разрешению пользователя «делай». GRAF Dev manifest dev-65dccbaa567e, SHA `65dccbaa567ee26a7d1c6ffb430bcc5de9d45af5`, promote 2026-09-11T13:52:08Z, harness health 13/13 PASS. GitHub governance-fast run 34606466186 и pr-metadata 34606466213 — PASS на этом SHA (первый metadata run требовал исправления формата SHA в PR body).

В установленном WKWebView: timezone Москва → Escape вернул Екатеринбург; приложения zoom → две строки, mouse/Enter выбор, очистка вернула каталог; Ник → Никогда в правиле Zoom, Escape отменил; шаблон Протокол фильтруется; язык no-match/очистка, подробность Кратко выбрана Enter в отменённом черновике; напоминание начал → В момент начала, Escape отменил. Доступные имена/expanded состояния видны через AX.

Для штатного fallback на 45 секунд приостановлен только graf-dev-api-1 с гарантированным unpause; API восстановлен и healthy, кабинет снова открылся. Установленная native проверка нашла ошибки: Enter не закрывал редактируемое меню, выбор через стрелку мог не сохраняться, фокус не раскрывал список. Эти ошибки исправлены в последующем diff; T006 остаётся открытым до повторной установленной проверки. Независимый native review не нашёл новых замечаний, но подтверждение реальных событий остаётся за установленным тестом. VoiceOver speech пока не проверялся.

## Повторные проверки после native исправления и дополнения размера
NSComboBox использует AXShowMenu у cell; Return/Escape передаются AppKit; завершённый выбор DidChange отделён от промежуточного IsChanging, programmatic selection защищён. Native focused regression 60/60 PASS, дополнительный итоговый набор NativeSettingsComboBox/AppLifecycleWindowRegression/AppControlAccessibility/оба EmbeddedCabinet bridge — 46/46 PASS. WebKit settings-combobox PASS после изменения плотности строк. Размер/отступы пока требуют установленной проверки T007 вместе с T006.

## Повторная установленная проверка 6d5623421776
SHA `6d562342177628263c98a1d71fda79a5997d9a7c`, promote 14:21:42Z, health 13/13 PASS; final smoke PASS; governance-fast https://github.com/yshishenya/graf/actions/runs/34609377399 и pr-metadata 34609377359 PASS. Код принят не полностью: установленная проверка agent задачи 01a090a9-ac47-7893-a74d-e18f37e33986 через CUA выявила, что реальный DidChange также приходит при ArrowDown. Down+Escape сохранял Всегда; последующий Return игнорировался как повторное подтверждение. Zoom восстановлен в Спрашивать через embedded и проверен после reload; Zoom Phone также Спрашивать. Offset За5мин по Return сохранялся; исходное За минуту восстановлено и проверено после вкладок. Search zoom фильтрует2строки, Return закрывает меню. Mouse native выбор инструментом подтвердить не удалось.

Фактическое резервное окно820×680 сохранялось между вкладками; уведомления помещались, строки≈41px. NSHostingController уменьшал окно при назначении содержимого: желаемый размер теперь задаётся повторно через setContentSize после contentViewController и до ограничения экраном. DidChange теперь направлен через тот же существующий event guard, что target/action; не-Return клавиши не подтверждают. T006/T007 ждут новой установленной проверки этих исправлений.
