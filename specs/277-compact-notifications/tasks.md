# Tasks: Единые компактные уведомления GRAF

**Input**: `specs/277-compact-notifications/` — spec, plan, research, data-model, contracts, quickstart.
**Lane**: `high-risk-product`; полный Spec Kit. Проверка требований 21/21 PASS перед генерацией. До кода обязательны analyze, GitHub issue sync и независимое повторное review с этим файлом.
**Tests**: сначала новые проверки и наблюдаемый отказ прежнего поведения, затем реализация. `[X]` ставится только после результата и проверки, не по обещанию агента.

## Phase 1: Setup

- [X] T001 Зафиксировать исходные тесты и точные границы удаления в `specs/277-compact-notifications/validation.md` и `specs/277-compact-notifications/cleanup-map.md`; сохранить чужие изменения основного checkout.

## Phase 2: Foundation

- [X] T002 Зафиксировать карту требований, зависимости и независимое разрешение начала реализации в `specs/277-compact-notifications/review-report.md`, `specs/277-compact-notifications/validation.md` и этом `tasks.md`; проверить отсутствие новых зависимостей и корректность существующего `.gitignore`.

**Checkpoint**: T001–T002 и все pre-implementation gates завершены перед изменением кода. Ни одно ревью требований не считается runtime-приёмкой.

## Phase 3: US1 — Компактная карточка (P1)

**Goal**: пять сценариев одного вида без пустой колонки закрытия и обязательных пустых строк.
**Independent test**: геометрия всех сценариев, 380pt, short 44–52pt при обычном тексте, светлая/тёмная тема, увеличенный текст; измерения настоящих AppKit views.

- [X] T003 [P] [US1] Сначала добавить падающие проверки новой геометрии, необязательных строк, порядка кнопок и текста без процентов в `apps/macos/Shared/Tests/DesktopNotificationCompactTests.swift` (FR-001–006, SC-001/004).
- [X] T004 [US1] Переработать `apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift`: ширина 380pt, padding12/icon18/gap8/radius12, close18/glyph9/hit28 вне текстовой колонки, short44–52, действия ниже и флажок отдельно, перенос без уменьшения шрифта, контраст4.5/3 и настройки доступности (зависит от T003).
- [ ] T005 [US1] Перевести короткую запись в `apps/macos/RecApp/App/TwoBrainRecApp.swift` на общий presenter, удалить `apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift` и заменить `apps/macos/Shared/Tests/ShortRecordingNoticeTests.swift` проверкой действующего пути без запасной карточки (FR-005/021, после T004/T010).

## Phase 4: US2 — Управление записью (P1)

**Goal**: сохранить восемь секунд и локальные правила, исключить потерю решения и невидимый запуск.
**Independent test**: start/skip/close/timeout × remember; double click/expiry; старый token; недоступный экран; sleep/lock/смена контекста.

- [ ] T006 [P] [US2] До реализации добавить проверки матрицы решений, стабильности окна/фокуса/отсчёта и reentrant callback в `apps/macos/Shared/Tests/DesktopNotificationPromptLifecycleTests.swift`; сохранить и явно запускать `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift`, `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`, `apps/macos/Shared/Tests/MeetingDetectionRecordingLifecycleTests.swift` и `apps/macos/Shared/Tests/CaptureControlV5Tests.swift` (FR-007–011/019/020, SC-002).
- [ ] T007 [US2] Обновлять содержимое и флажок на месте в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift`, выполнять terminal action один раз, снимать старое окно до callback, возвращать явный отказ показа; убрать progress и прежние необращаемые actions (после T004/T006).
- [ ] T008 [US2] Связать актуальный prompt/token с обработчиками в `apps/macos/RecApp/App/TwoBrainRecApp.swift`: close/Escape без сохранения, checkbox только явным start/skip, таймер8s после успешного показа, отмена без позднего запуска при sleep/lock/target/context change, indicator/Stop и все capture gates неизменны (после T007/T010).

## Phase 5: US3 — Один канал и настройки (P1)

**Goal**: один собственный показ в выбранное время, ноль новой системной доставки, полезные предпочтения сохраняются.
**Independent test**: 0/1/5min, absolute deadline, приоритеты всех пяти видов, миграция/повторы/смена владельца, реальный WebKit-контракт настроек.

- [X] T009 [P] [US3] Переписать сначала проверки нового канала в `apps/macos/Shared/Tests/DesktopNotificationControlTests.swift` и `apps/macos/Shared/Tests/DesktopLocalNotificationDeliveryTests.swift`: prefs decode, 0/1/5, дедупликация до показа, priority/tie/preemption, старые claims, context/quiet/sound и отказ размещения (FR-007/008/012–017/020/023/025).
- [ ] T010 [US3] Переработать `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`: единый scheduler и актуальные callbacks, prompt>problem>short>meeting>preview, равный приоритет не вытесняет, displaced не возвращается, максимум один ожидающий short до20s; due=startsAt-offset×60, deadline=min(due+120s,endsAt); обновление не меняет срок (после T009).
- [ ] T011 [US3] Вынести prefs/claims из `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift` в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPreferences.swift`, сохранив `reminders: Bool=true`, `offsetMinutes: Int=1` (0/1/5), `showTitles: Bool=false`, `sound: Bool=false`, добавив `quiet: Bool=false` с decoder default; изолировать выполняемую очистку своих старых OS requests в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationRetirement.swift`, перенести необходимые claims односторонне без rollback aliases и без потери session ownership (после T009/T010, FR-014/015/023, SC-003).
- [X] T012 [P] [US3] Добавить сначала version2/quiet/ошибочные поля/старый документ/epoch tests в `apps/macos/Shared/Tests/EmbeddedCabinetNotificationSettingsBridgeTests.swift`, `apps/server/tests/browser/settings-consistency.test.cjs`, `apps/server/tests/browser/settings-combobox.test.cjs` и `apps/server/tests/integration/test_settings_ia_flow.py` (FR-015/016/020/025).
- [ ] T013 [US3] Обновить `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift`, раздел уведомлений `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`: один version2, пять prefs, quiet, реальный preview, нет permission UI/actions, строгие поля/mainframe/origin/route/nonce/epoch и последовательное сохранение (после T011/T012).
- [ ] T014 [US3] Обновить живой `DesktopNotificationsSettingsView` в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; удалить старый `/desktop/settings/notifications/mac` и callback через `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`, `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`, `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, `apps/macos/RecApp/App/TwoBrainRecApp.swift`; обновить `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` и `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` (после T008/T013, FR-014/015/021).

## Phase 6: US4 — Доступность и повторный доступ (P2)

**Goal**: клавиатура без перехвата фокуса и нейтральная ограниченная история результатов.
**Independent test**: явный focus/Tab/ShiftTab/Space/Return/Escape, стабильное AX-дерево при tick, 20/6s hover/focus hold отдельно от8s, history/context/privacy.

- [ ] T015 [P] [US4] Сначала добавить проверки bounded history и lifecycle экрана/фокуса в `apps/macos/Shared/Tests/DesktopNotificationHistoryTests.swift` и `apps/macos/Shared/Tests/DesktopNotificationAccessibilityTests.swift` (FR-006/012/017–020, SC-004/007).
- [ ] T016 [US4] Реализовать history в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift` и пункты существующего меню в `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`: до50 entries newest-first, только UUID/Date/closed enum/нейтральный текст, память запуска/контекста, без meetingname/sessionpath/URL/participant/transcript/audio/replayaction, preview/tick не входят; очищать при смене контекста (после T010/T015).
- [ ] T017 [US4] Реализовать в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift` явный focus, first click, устойчивый AX, hold20/6s без изменения8s/calendar deadline, сохранение screenID, fullscreen/visibleFrame, перенос отключённого экрана без reset, доступную прокрутку и отказ невозможного размещения без перекрытия Stop; связать focus и сведения о собственном Stop в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (после T007/T008/T015).

## Phase 7: Cleanup and validation

- [X] T018 Удалить остатки и обновить действующие проверки по `specs/277-compact-notifications/cleanup-map.md`, включая `apps/macos/Shared/Tests/DesktopNotificationCardTests.swift`; добавить `scripts/check_notification_retirement.py` и его негативные тесты `apps/server/tests/contract/test_desktop_notification_retirement.py`, запретив старые scheduling/delegate/permission/wrapper/route и разрешив только выполняемый cleanup helper. Historical specs, server inbox/billing, CalendarPromptView и notificationContext сохраняются (FR-021–024, SC-006).
- [ ] T019 Выполнить все focused native/WebKit/browser/pytest проверки и builds/ContractValidation из `specs/277-compact-notifications/quickstart.md`; записать реальные результаты, число тестов, причины skips и точные команды в `specs/277-compact-notifications/validation.md`; исправить регрессии (после T005/T008/T014/T016/T017/T018).
- [ ] T020 Проверить новый интерфейс только через `/Applications/GRAF Dev.app` и `infra/scripts/dev-harness.sh` по `infra/dev/README.md`: синтетическая матрица5сценариев×темы/шрифт, клавиатура/VoiceOver, первый click, сроки, capture gates/Stop, сон/блокировка, два экрана/fullscreen; сохранить metadata-only evidence в `specs/277-compact-notifications/validation.md`, не объявлять непроверенное PASS (после T019 и clean tested commit).
- [ ] T021 Обновить `docs/current-product-status.md`, `changes/unreleased/F277.yaml` и `specs/277-compact-notifications/quickstart.md` по фактическому новому поведению; выполнить speckit-converge с append-only добавлением непокрытых задач, независимое code review и устранение замечаний (после T019; итог после T020).
- [ ] T022 Создать PR с русским описанием и `high-risk-product`, дождаться exact-SHA/base `governance-fast`, `macos-pr`, `pr-metadata` через `scripts/validate-pr-checks.py`; сверить `specs/277-compact-notifications/tasks.md` с live issues и closure evidence. Неполные merge/manual gates оставлять открытыми; публичный release/production вне задачи (после T020/T021).

## Dependencies and parallel work

T001 → T002 → независимые тестовые ветви T003/T006/T009/T012/T015. Падающие проверки выполняются до соответствующего нового кода. Единственный владелец `.build` — основной агент; рабочие агенты не запускают конкурентные сборки.

- US1: T003 → T004; T005 ждёт T010 и интеграцию приложения.
- US2: T006 → T007 после T004 → T008 после T010.
- US3: T009 → T010 → T011; T012 → T013 после T011; T014 после T008/T013.
- US4: T015 → T016 после T010 и T017 после T007/T008.
- Общие файлы `DesktopNotificationCardPresenter.swift`, `DesktopNotificationPresenter.swift`, `TwoBrainRecApp.swift` имеют по одному владельцу; пересекающиеся задачи не выполняются параллельно.
- Пример параллельной работы: автор card выполняет T004/T007, автор scheduler — T010/T011, автор bridge готовит T012. Основной агент затем интегрирует приложение/меню. Независимые тестовые файлы позволяют не перезаписывать работу друг друга.

## Requirement coverage

| Требования | Задачи |
|---|---|
| FR-001–006 / SC-001 | T003–T005, T015, T017, T020 |
| FR-007–008 | T006–T010, T019–T020 |
| FR-009–011 / SC-002 | T006–T008, T017, T019–T020 |
| FR-012 | T009–T010, T015, T017, T019–T020 |
| FR-013 / SC-005 | T009–T010, T019–T020 |
| FR-014–015 / SC-003 | T009–T014, T018–T020 |
| FR-016 | T009–T014, T016, T019–T020 |
| FR-017–018 / SC-007 | T009–T011, T015–T016, T019–T020 |
| FR-019 / SC-004 | T003–T004, T006–T008, T015, T017, T020 |
| FR-020 | T006–T017, T019–T020 |
| FR-021–023 / SC-006 | T005, T011, T014, T018–T022 |
| FR-024 | T018, T020–T021 |
| FR-025 | T009–T013, T019–T020 |

## Implementation strategy

## GitHub ownership

Каждая строка ниже назначает единственного владельца задачи; все issues открыты до полной проверки закрытия. T022 использует исходную umbrella reservation #7276, без дублирования.

| Task | Issue |
|---|---|
| T001 | [#7287](https://github.com/yshishenya/graf/issues/7287) |
| T002 | [#7288](https://github.com/yshishenya/graf/issues/7288) |
| T003 | [#7289](https://github.com/yshishenya/graf/issues/7289) |
| T004 | [#7286](https://github.com/yshishenya/graf/issues/7286) |
| T005 | [#7290](https://github.com/yshishenya/graf/issues/7290) |
| T006 | [#7293](https://github.com/yshishenya/graf/issues/7293) |
| T007 | [#7291](https://github.com/yshishenya/graf/issues/7291) |
| T008 | [#7292](https://github.com/yshishenya/graf/issues/7292) |
| T009 | [#7294](https://github.com/yshishenya/graf/issues/7294) |
| T010 | [#7295](https://github.com/yshishenya/graf/issues/7295) |
| T011 | [#7297](https://github.com/yshishenya/graf/issues/7297) |
| T012 | [#7296](https://github.com/yshishenya/graf/issues/7296) |
| T013 | [#7298](https://github.com/yshishenya/graf/issues/7298) |
| T014 | [#7300](https://github.com/yshishenya/graf/issues/7300) |
| T015 | [#7301](https://github.com/yshishenya/graf/issues/7301) |
| T016 | [#7299](https://github.com/yshishenya/graf/issues/7299) |
| T017 | [#7302](https://github.com/yshishenya/graf/issues/7302) |
| T018 | [#7304](https://github.com/yshishenya/graf/issues/7304) |
| T019 | [#7303](https://github.com/yshishenya/graf/issues/7303) |
| T020 | [#7305](https://github.com/yshishenya/graf/issues/7305) |
| T021 | [#7306](https://github.com/yshishenya/graf/issues/7306) |
| T022 | [#7276](https://github.com/yshishenya/graf/issues/7276) |

### Порядок реализации

Сначала компактный компонент и его доказуемые переходы, затем доменная интеграция и единственный канал, затем доступность/история и полное удаление. US1 — первый проверяемый результат, но не сокращение полного объёма. Ни временная успешная сборка, ни красивый скриншот не завершают фичу без всех требований и проверок. Issue mapping добавляется после analyze; повторная проверка gate после добавления ссылок не меняет реализацию.

## Phase 8: US2 — разрешённая защита отменённого запуска (2026-09-27)

Согласие пользователя: «разрешаю» на узкое исправление P1; reviewer requirements gate 26/26 в `scope-review.md`. FR-026–028 / SC-008. Дополняет T008, выполняется **до** завершения T019–T022. Прежние результаты уведомлений не являются проверкой этого расширения.

- [X] T023 [US2] Сначала воспроизвести запрет pending/recovery и cached queue/runtime transport отрицательными проверками в `apps/macos/Shared/Tests/RecordingStartAcceptanceTests.swift`, `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` и `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`; затем дополнить матрицу начальный/before-commit/финальный отказ, restart, scan/retry, чужая/завершённая сессия, неизвестный enum, identity/read error, старый nil/manual/accepted и старое чтение без нового поля. Ноль transport calls/attemptCount/serverCreationAttempted при локальном запрете; runtime не заменяется source scan.
- [X] T024 [US2] После RED T023 добавить optional `startAcceptance` с закрытым enum pending/accepted (nil исторический; unknown decode error) в `apps/macos/Shared/Sources/Models/AudioModelCore.swift`; в `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift` защитить staging/sync/atomic commit без fallible post-commit и before-commit failure hook; в `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift` сохранять pending со scopeApproval=nil до timer, синхронно принимать только текущую sessionID с памятью после диска и сохранять признак при stop; в `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift` не ремонтировать/удалять pending и сохранять признак accepted; в `apps/macos/RecApp/App/TwoBrainRecApp.swift` после await проверять decision → markCapturing → acceptStart без await до публикации успеха. Изменение сэмплов/таймера/прав/Stop запрещено.
- [X] T025 [US2] После RED T023 и согласованной модели T024 защитить `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` и `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`: pending запрещён независимо от cached profile; живой manifest с правильными sessionId/directoryId обязателен до transport/reconcile и после существующих приостановок; ошибки чтения/неизвестный enum — отказ, nil снимает только новый барьер. Не увеличивать сетевые счётчики при локальном отказе; не менять протокол и расписание повторов. Добавить общий узкий helper `apps/macos/RecApp/Sources/Upload/RecordingStartAcceptanceGate.swift` при необходимости единой проверки двух потребителей.
- [X] T026 [US2] После T024/T025 выполнить матрицу `RecordingStartAcceptanceTests`, writer/recovery/queue/client/capture и общий F277 набор из `specs/277-compact-notifications/quickstart.md`; измерить принятие с целью ≤100ms на исправном локальном хранилище, получить независимое review кода; записать реальные результаты/ограничения в `specs/277-compact-notifications/validation.md`, обновить `docs/current-product-status.md` и `changes/unreleased/F277.yaml`. Только после устранения P1 продолжить T019–T022; ручные и PR gates не заменять автоматическими тестами.

Зависимости: T023 RED → T024/T025 → T026 → незавершённая общая приёмка T019–T022. T024 — MAIN; T025 — отдельный владелец queue/client/helper и соответствующих тестов. Тесты T023 делятся по этим непересекающимся файлам, единственный владелец Swift `.build` — MAIN. Параллельная правка queue допустима после фиксации интерфейса модели, не до RED. Сопоставление: FR-026 → T023/T024/T026; FR-027 → T023–T026; FR-028/SC-008 → T023–T026.

Владелец T023, T024, T025, T026 в GitHub: [#7336](https://github.com/yshishenya/graf/issues/7336), одна связанная задача исправления P1; все четыре IDs явно перечислены в body. Остальные T001–T022 сохраняют прежних владельцев. Ни одна issue этим дополнением не закрывается.
