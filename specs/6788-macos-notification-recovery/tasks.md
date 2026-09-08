# Tasks: F6788 — запись из меню и уведомления

Источник: spec.md/plan.md/contracts/experience.md. Lane: high-risk-product.
Ветка от выпущенного e81b412; одна сессия и один PR. Reviewer checklists
проверяет независимый reviewer, а не исполнитель.

## Phase 1: Setup

- [X] T001 Зафиксировать объединённые требования и независимую проверку в specs/6788-macos-notification-recovery/checklists/ и requirements-review.md.

## Phase 2: Foundation

- [X] T002 Завершить analyze и синхронизировать tasks/issue ownership в specs/6788-macos-notification-recovery/analysis.md и issues.md до реализации.

## Phase 3: US1 — надёжные команды без постоянного окна

Independent Test: закрытый кабинет/календарная карточка → Start/Mute/Unmute/Stop,
одна реальная запись, ни одного постоянного окна. FR001–003/009, SC001–002.

- [X] T003 [US1] Добавить регрессию общей доставки и transition guards в apps/macos/Shared/Tests/CaptureControlV5Tests.swift и DesktopNotificationControlTests.swift.
- [X] T004 [US1] Исправить четыре tray-команды через существующий dispatcher без подъёма кабинета и проверить готовность handler в apps/macos/RecApp/App/TwoBrainRecApp.swift.
- [X] T005 [US1] Удалить постоянный widget и его неиспользуемые зависимости, сохранив меню/очередь/F214, в apps/macos/RecApp/Sources/Notifications/DesktopControlPanel.swift и Calendar/CalendarTray.swift; обновить AppControlAccessibilityTests.swift.

## Phase 4: US2 — доступные настройки

Independent Test: оба общих входа и прямой локальный вход открывают нужную
вкладку без потери черновика; обычный браузер не управляет Mac. FR004/007/010.

- [X] T006 [US2] Покрыть доверенный маршрут вкладки уведомлений и отказ чужому origin в apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift.
- [X] T007 [US2] Добавить выбор существующей нативной вкладки и безопасный embedded-переход в apps/macos/RecApp/App/TwoBrainRecApp.swift и apps/macos/RecApp/Sources/Cabinet/.
- [X] T008 [US2] Разделить Mac/кабинет/письма в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html и проверить существующим тестом настроек в apps/server/tests/.

## Phase 5: US3 — редкие полезные сигналы

Independent Test: календарь со ссылкой/без, отключение/включение, старый
контекст, Focus; действий захвата и повторных сигналов нет. FR005–007, SC004–005.

- [X] T009 [US3] Добавить регрессии действий/дедупликации/восстановления в apps/macos/Shared/Tests/DesktopNotificationControlTests.swift и DesktopCalendarReminderTests.swift.
- [X] T010 [US3] Реализовать штатные OS-действия и правдивый календарный текст с проверкой контекста в apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift.
- [X] T011 [US3] Исправить подтверждённые разрывы disable/enable/переноса, сохранив один сигнал, в apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift и существующем reminder service.

## Phase 6: US4 — состояние у своей записи

Independent Test: offline/retry/local recovery и server blocked/terminal/ready;
read отдельно от resolved. FR008–009, SC004–005.

- [X] T012 [US4] Проверить и восстановить адресный переход локальной ошибки к записи и тихую отправку в apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift и Cabinet/; покрыть существующими тестами.
- [X] T013 [US4] Проверить blocked_config/terminal/ready через существующие серверные представления apps/server/src/twobrain_rec_server/cabinet/ и tests/; исправить доказанные тексты/действия без новых producers inbox.

## Phase 7: Validation and closeout

- [ ] T014 Выполнить quickstart в единственном GRAF Dev и записать точный SHA/результаты/исключённый VoiceOver в specs/6788-macos-notification-recovery/validation.md.
- [ ] T015 Завершить независимый code/Ponytail review, convergence, changes/unreleased/F6788.yaml и готовый PR с governance-fast и точным source SHA; записать evidence в specs/6788-macos-notification-recovery/validation.md.

## Dependencies and strategy

T001 → T002 → US1 → US2 → US3 → US4; расширение T017 → US5/T018–T020 → T014/T021 → T015.
В каждой истории регрессия до исправления; после шага — её focused check.
US2/US3 делят App/Presenter, поэтому реализация последовательная. Независимо
можно читать/проверять серверные шаблоны и Swift-тесты; runtime Dev один.
Первые рабочие команды — внутренний checkpoint, итог включает все пять историй.
Новые обнаруженные обязательные задачи дописываются при convergence.

Связанные старые F249 gaps: #6780 (T035 меню), #6779 (T034 no-link), #6758
(T026 recovery). Эти упоминания не устанавливают повторное владение старой задачей
и не означают её завершение. Собственные issue-связи — issues.md.

## Added from prerequisite check

- [X] T016 Исправить усечение номера фичи/задачи длиннее трёх цифр в .specify/extensions/github-issue-canon/scripts/issue_canon_common.py и normalize_issue_canon.py и его upstream source; добавить регрессию, сохранив полную проверку canon. Требуется перед T002, обнаружено при обязательном issue sync.

## Объединение F258 (обязательный объём до T014/T015)

- [X] T017 Повторить независимый affected review/analyze и синхронизировать перенос F258 в specs/6788-macos-notification-recovery/{requirements-review,analysis,issues}.md; FR011–014, SC007–008. До T018–T020.
- [X] T018 [US5] Перенести и проверить audio revision, общую summary projection и узкую media role из PR6824 в apps/server/src/twobrain_rec_server/{cabinet,processing,outcomes,normalization,ingest,api}/ и apps/server/scripts/bootstrap_runtime_database_roles.py с исходными регрессиями; FR011/014, SC007–008.
- [X] T019 [US5] Перенести и проверить автообновление без потери player/format/focus/title draft в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js и apps/server/tests/unit/test_meeting_progress_ui.py; FR012, SC007.
- [X] T020 [US4] Совместить owner/epoch/incident и правдивый sync из F258 в apps/macos/RecApp/Sources/{Notifications,Upload}/ и apps/macos/Shared/Sources/Models/AudioModelCore.swift; убрать неиспользуемую ветку recap и сохранить полезные регрессии; FR008/013, SC004–005/008.
- [ ] T021 [US5] Проверить объединённые server/Node/Swift, media role и первый embedded вход, автоматическое появление итогов с сохранением player/draft в единственном GRAF Dev после F257; evidence в specs/6788-macos-notification-recovery/validation.md. FR010–014, SC006–008; installed часть вместе с T014, до T015.

F258 T002–T005 → T018/T019; T006–T010 → T018/T020; T011/T012 → T014/T015/T021.
F258 native recap и widget superseded решением владельца, а не отмечены выполненными.
Исходные #6818–#6823/PR6824 остаются связанными до сверки итогового PR.

## Phase 8: Convergence

- [X] T022 [US5] Исправить самоотмену уже запрошенного native Reload в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift и добавить apps/macos/Shared/Tests/EmbeddedCabinetReloadRegressionTests.swift с настоящим WebKit/loopback HTTP; сохранить проверки текущего документа, origin и истёкшей сессии. FR012/SC007, восстановление при временной сети (partial, HIGH); доказательство передано из диагностики F257, её продуктовый объём не переносится.

## Phase 9: Convergence

- [X] T023 [US5] Согласовать частичную готовность итогов в шкале этапов, динамической строке и серверном списке в apps/server/src/twobrain_rec_server/cabinet/{static/cabinet/cabinet.js,view_models.py}; проверить реальными Node-функциями и серверной регрессией в apps/server/tests/{unit/test_meeting_progress_ui.py,integration/test_meeting_summary_slots.py}. FR011/SC007 (partial, MEDIUM), подтверждённый P2 итогового независимого code review.

T023 использует nullable summary_status в существующем MeetingListItem
(apps/server/src/twobrain_rec_server/api/schemas.py): ту же проверенную проекцию,
что processing/desktop sync. Это метаданные состояния, не новый источник
готовности или изменение прав; отсутствие поля у старого ответа допустимо.
