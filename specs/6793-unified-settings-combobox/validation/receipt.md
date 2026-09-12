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

## Текущий результат — 2026-09-11 15:32 UTC
Установлен `dev-cb87d4a4d716`, source SHA `cb87d4a4d716e3e2653f25e8c36cfe4ddc95f38d`, promote15:30:46Z. Build/promote/status/smoke через штатный harness: PASS, 13/13 health checks. Последние NativeSettingsComboBoxTests + AppLifecycleWindowRegressionTests:13/13 PASS. GitHub governance-fast https://github.com/yshishenya/graf/actions/runs/34615620046 и pr-metadata https://github.com/yshishenya/graf/actions/runs/34615620142 — PASS на этом exact SHA.

T006 и T007 не закрыты: CUA исчез из callable tools root, native reviewer и соседней задачи. Последние изменения DidChange event guard и setContentSize после hostingController ещё не перепроверены в живом UI. Нельзя объявлять устранение установленного native failure доказанным только по unit tests. Подтверждено до этих последних двух исправлений: общий web/embedded выбор/фильтр; native строки≈41px, стабильность окна при смене вкладок, полный показ уведомлений, notification Return persistence. Непроверены повторные ArrowDown/Escape/outside-click, mouse native выбор и начальный увеличенный размер; VoiceOver speech не проверялся.

Все исходные настройки после тестов восстановлены: Zoom и Zoom Phone — Спрашивать, напоминание — За минуту. API healthy/unpaused. PR#6937 остаётся draft, issue#6924 открыт, release/merge/production deploy не выполнялись. Последующее изменение этого отчёта является документацией: установленный SHA указан отдельно, код приложений в нём не меняется.

## Повторная приёмка cb87 — 2026-09-12
CUA снова доступен. В установленном GRAF Dev подтверждены две ошибки прежнего NSComboBox: AXShowMenu открывает контекстное меню текста (Cut/Copy/Paste), а ArrowDown/Return может показывать «Никогда» без сохранения после смены вкладок. ArrowDown/Escape на этом кандидате сохранил прежнее «Спрашивать». Zoom/Zoom Phone не изменены. Увеличение окна после назначения hosting controller и компактность строк видны; окончательные размеры и повторное открытие проверяются на следующем кандидате.

По результатам установленной проверки общий native helper переводится на публичные NSTextField/NSPopover с явными действиями подтверждения. Отсутствие ошибок в предыдущих delegate unit tests не является доказательством исправления этих пользовательских сценариев. T006/T007 остаются открытыми до проверки нового установленного кода; прежние упоминания недоступности CUA описывают исторический checkpoint.

## Исправление нативного поля и сборки — 2026-09-12
Общий native helper заменён на NSTextField/NSPopover с явными действиями: стрелки выделяют, click/AXPress/Return подтверждают, Escape/Tab/blur/outside отменяют. Контекстное AXShowMenu и предположения о currentEvent удалены. Убрана внешняя AX value, скрывавшая ввод; повторное открытие резервного окна сохраняет его frame. Independent native review PASS; NativeSettingsComboBox/Accessibility/Window/оба Embedded bridge: 48/48 PASS, включая 13 проверок нового helper. Эти тесты не заменяют установленную приёмку popup event loop.

Для необходимой Dev-приёмки FR-010/T008 добавлены в ту же фичу и issue #6924. Минимальное изменение штатного builder использует `pull --policy missing` только для двух датированных MinIO образов; Postgres/Temporal продолжают загружаться. Отсутствие локального образа с отказом registry останавливает сборку; измерение ID, архив, подпись и checks не изменены. Требования infra CHK008/009 и independent code review PASS. Новые проверки сначала упали на прежнем коде; итоговый `test_graf_local_adapter.py + test_dev_harness.py`: 60/60 PASS. Live cache/build и promote с previous-checkout остаются следующей частью T006/T008.

Повторный analyze требований/плана/задач: 10 FR + 4 SC имеют покрытие T001–T008, несвязанных задач нет, блокирующих противоречий/неоднозначностей нет. High-risk-feature и ограничения constitution сохранены. Custom UX/infra checklist: 9/9 PASS, владельцы независимые reviewers. Новая реализация не добавляет сторонних библиотек, private API, альтернативного пути установки или правил записи. Ponytail review: лишних абстракций/зависимостей не найдено.


## Кандидат e964: сборка, установка и GitHub — 2026-09-12
Source SHA `e964bba55ed594f8bdccf94068d75fd07590c1b5`, manifest `dev-e964bba55ed5`; штатный build PASS и promote 10:31:31Z PASS с `--previous-checkout` чистого активного `7dbcce5f56faaeac8efbc604fddc780e045594f2`. Никакие runtime-definition/SHA/signing guards не отключались. Promote health 13/13 PASS. MinIO storage `sha256:460b46057cbcf8d01c2f7ceae9209290334b75dc1912235b10ad9bd35de056db` и storage_init `sha256:b0211e8b39d1818f2bb5dd4ff1a44e781a196e60e692dc19f46b463ef07a1e41` совпадают с предыдущим принятым manifest; повторная сборка действительно использовала кеш. T008 выполнена.

GitHub `governance-fast` [34688568398](https://github.com/yshishenya/graf/actions/runs/34688568398) и `pr-metadata` [34688568378](https://github.com/yshishenya/graf/actions/runs/34688568378) PASS на exact SHA e964. Локальный governance validator PASS с изолированным specify-cli 1.0.1, установленным по закреплённому ref; глобальный CLI/lock не менялся.

Повторная сверка speckit-converge: новых задач по реализации нет, 10 FR и 4 SC покрыты T001–T008; T006/T007 сохраняются для обязательной фактической приёмки. Ponytail-review: новых зависимостей и лишних общих слоёв нет. Установленная проверка нового AppKit popup ещё не подтверждена; зелёные CI/build/handler tests не закрывают этот остаток.
