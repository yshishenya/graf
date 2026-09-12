> Текущий статус: визуальная приёмка НЕ пройдена. После проверки e964 пользователь отклонил вид раскрытых меню; T009–T011 обязательны. Ниже сохранена история проверок, прежние заключения о завершении относятся только к прежнему кандидату.

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


## Завершённая установленная приёмка — 2026-09-12
После ручной разблокировки Mac независимый проверяющий задачи `01a090a9-ac47-7893-a74d-e18f37e33986` проверил через CUA единственный `/Applications/GRAF Dev.app`, exact code SHA `e964bba55ed594f8bdccf94068d75fd07590c1b5`. Без новых сборок и замены кода:

- Focus/type в поле приложений открывает список; `zoom` даёт Zoom/Zoom Phone и две строки правил.
- Zoom: Down/Down/Escape и Down/Down/щелчок вне поля сохраняют исходное «Спрашивать».
- Down/Down/Return выбирает «Никогда», после Уведомления → Запись и повторного фильтра значение сохраняется. Щелчок по «Спрашивать» возвращает его; на снимке после проверки Zoom и Zoom Phone — «Спрашивать».
- Напоминание: «За минуту» → «За 5 минут» по Enter, сохранение подтверждено после переключения вкладок, затем возвращено «За минуту».
- AX показывает именованные combo boxes, действие Confirm, список вариантов, выбранные строки и кнопки вариантов. Явный expanded атрибут сериализатор CUA не отобразил; программная проверка expanded есть в native tests. Полная речевая проверка VoiceOver не проводилась.
- Снимки вкладок Запись и Уведомления одинакового размера 960×768 в выдаче CUA: окно не уменьшается, содержимое обеих вкладок видно целиком, строки компактны (около 38 px на масштабированном снимке). Эти пиксели не выданы за нативные points: 1040×800 — размер содержимого, заданный кодом и ограниченный экраном; прямое измерение points не проводилось.
- Закрытие и повторное открытие штатно возвращает резервное окно. Root отдельно прочитал AX и снимок повторно открытого окна: размер/компоновка сохранены, название Yandex Telemost и правило помещаются. Предыдущий обзор кода подтверждает перенос более длинных имён и прокрутку каталога.

После тестового восстановления CUA сообщил о внешнем изменении приложения; свежий AX показал другие пользовательские значения общего правила и фильтра Yandex. Оба проверяющих и ожидающая задача F6796 подтвердили, что не меняли их. Эти значения сохранены без отката; снимок Zoom/напоминания доказывает восстановление именно в момент завершения соответствующих тестов, а не последующее пользовательское состояние.

API приостанавливался только на ограниченное время для открытия fallback с гарантированным unpause. По завершении State.Paused=false; root final smoke 13/13 PASS на e964. Запись не запускалась, данные не удалялись. Локальные снимки/отчёт вне git: `.dev/validation/f6793-installed-cua/`. T006/T007 выполнены.

Финальная сверка spec/plan/tasks/constitution: 10 FR + 4 SC покрыты, T001–T008 выполнены, обязательных незавершённых задач нет. Новых convergence задач не требуется. High-risk-feature: browser/native/contract/harness, независимый review и установленная приёмка завершены. GitHub CI на последнем коммите документации проверяется отдельно; установленный code SHA остаётся e964, apps/infra/scripts не меняются. PR готовится к включению в релиз, merge/public release/production deploy не выполняются.

## Визуальное отклонение — 2026-09-12
Два пользовательских снимка показали указатель и тяжёлую округлую оболочку NSPopover, полную ширину списка приложений, вложенный фокус и обрезание последней строки. Исторический PASS мыши/клавиатуры и закрытых вкладок не покрывает эти дефекты. PR #6937 сохраняется draft; добавлены T009–T011. Новый установленный результат и exact-SHA CI пока ожидаются.

## Gate визуальной итерации — 2026-09-12
T009: первичные источники и официальные примеры записаны в research-ui-2026.md; интерактивный synthetic HTML макет проверен в Chromium и визуально (не доказательство AppKit). Независимый selector_inventory проверил CHK010/011 и повторный analyze: CRITICAL0/HIGH0/MEDIUM0, FR+SC16/16 покрыты11 задачами. Уточнены первоначальный focus, historical NSPopover, selected/active и actual geometry0/1/3/8/>8. Issue6924 синхронизирован T009–T011; canon ensure/validate300 PASS. Реализация T010 и установленная приёмка T011 следуют после этого gate.

## Локальная проверка web визуальной итерации
Общий CSS/DOM: ширина app-filter380, radius6, плотные строки, галочка сохранённого значения, отдельный active, focus без автоматического раскрытия, фактические высоты до8 целых строк. `settings-combobox.test.cjs`: Chromium PASS (600 вариантов0.8ms), WebKit PASS (1.0ms), включая short-menu viewport=scrollHeight и полную8-ю строку длинного каталога. `timezone-settings.test.cjs` PASS; `test_settings_ui_contract.py`25/25 PASS. Синтетические снимки светлой/тёмной темы просмотрены, длинная подпись переносится на375px. Изолированный Spec Kit governance PASS. Это локальная проверка; native и установленная приёмка T011 ещё не завершены.

## Независимая проверка визуального кода
Native reviewer build_recovery: PASS после удаления мёртвого suppressFocus и добавления публичного AXSharedFocusElements для активной ячейки с очисткой no-match/close/detach. NativeSettingsComboBoxTests19/19 PASS; accessibility/window/оба embedded bridge35/35 PASS. Публичный nonactivating child NSPanel, фактические row rects и освобождение observers проверены по коду. Установленная доставка мыши/кольцо фокуса остаются T011.

Web reviewer selector_inventory нашёл2 P2: non-overlay scrollbar меняет перенос после измерения; window deactivation не вызывает input.blur. Исправление резервирует ширину scrollbar до измерений и закрывает на window.blur/document.hidden без сохранения настройки; app query сохраняется. Добавлены воспроизводящие сценарии в существующий browser suite.

Повторные Chromium/WebKit и timezone PASS после2 web P2 исправлений. Native каталог не резервирует пустые24pt под отсутствующую галочку: текст/расчёт переноса используют поля10pt, правила сохраняют место галочки; Native19/19 PASS повторно.

Повторная сверка реализации: FR-001–FR-010 сохраняют прежние доказательства; FR-011/SC-005 имеют новое browser/native покрытие и независимый review. Локальная реализация T010 завершена; T011 требует нового установленного результата и exact-SHA PR CI. Общий Dev возвращён от F6796: активный8f68e8697497582dc33d6d7148d84844057686ca; штатная смена выполняется через проверенный previous-checkout.

## Кандидат faa7: точный SHA, установка и остановка приёмки
Source SHA `faa7e1f5fe428efe9508cb5a3a26f5327c817057`; build PASS, manifest `dev-faa7e1f5fe42`. Штатный promote 2026-09-12T13:26:09Z с проверенным предыдущим checkout активного8f68e869 PASS; здоровье 13/13 PASS. Политики подписи, образов, чистого SHA и runtime digest сохранены.

GitHub governance-fast [34696402559](https://github.com/yshishenya/graf/actions/runs/34696402559) и pr-metadata [34696402474](https://github.com/yshishenya/graf/actions/runs/34696402474): PASS на exact faa7. Первые два запуска после push упали на ожидаемом старом exact source SHA в прежнем описании; после обновления описания новые успешные runs относятся к текущему SHA. PR MERGEABLE/CLEAN, остаётся draft.

Финальный независимый web reviewer повторил оба P2 в Chromium/WebKit: обычная полоса18px учтена до измерений (WebKit viewport410px, восьмая строка полностью видима, отклонение0px); window blur и document hidden закрывают без сохранения. Web/Ponytail PASS. Native reviewer: PASS, AX активного/сохранённого разделён,19 focused tests;35 regression tests также PASS.

Независимый установленный проверяющий задачи `01a090a9-ac47-7893-a74d-e18f37e33986` подтвердил actual manifest faa7, затем CUA отказал: Mac locked, automatic unlock failed, требуется ручная разблокировка. Проверяющий UI/runtime не менял, API не приостанавливал. Ранее root делал два ограниченных45s pause для открытия fallback; оба автоматически восстановились, новый fallback не был открыт. Реальная новая приёмка раскрытых меню НЕ проведена; T011 остаётся открытой. Пользователю отправлен запрос разблокировки. Прежний e964 behavioral PASS не подменяет новую приёмку.

## Продолжение после разблокировки
Установленный reviewer подтвердил на faa7 полные8 строк каталога и3 строки правил/напоминаний, отсутствие указателя и вложенного фокуса. Обнаружен обязательный дефект: щелчок по «За5минут» в новой NSPanel дважды не подтверждает выбор, тогда как Down/Return сохраняет. Полное CUA AX дерево открытой панели не содержит списка/опций; причина требует проверки. T011 не завершена, по converge добавлена T012. Новый код не признаётся готовым по одним unit tests.

## T012: причина щелчка и локальная регрессия
До исправления фактический hit target строки — NSTextField с needsPanelToBecomeKey=true; nonactivating NSPanel по контракту не получает key focus. Строка заменена на плоскую NSButton: штатный target/action, единая область нажатия, acceptsFirstMouse=true и needsPanelToBecomeKey=false. Ручной tracking событий не добавлен. Поле предоставляет публичную AX иерархию раскрытого списка и реальных кнопок; обратные parent согласованы, close удаляет связь.

NativeSettingsComboBoxTests21/21 PASS: разные области строки, сохранение ровно один раз, рекурсивная AX достижимость, AXPress и очистка. Accessibility/window/оба embedded bridge35/35 PASS. Изолированный Spec Kit governance PASS. Установленный тест T011 требуется на новом SHA: этот локальный результат не отменяет failure кандидата faa7.

Независимый build_recovery code/Ponytail review T012: PASS, блокирующих замечаний нет. Проверены стабильный ID, guard закрытого/disabled/IME, пустая выдача, AX parent/cleanup и отсутствие цикла владения. Реальный щелчок и установленная AX иерархия остаются gate T011.
