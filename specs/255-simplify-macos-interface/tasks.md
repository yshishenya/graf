# Tasks: Единая и простая оболочка GRAF

## Решение владельца от 2026-09-08: проверка macOS 14

Владелец сообщил: «У меня нет макос 14. Давай без него если невозможно так протестировать. Доводи до готовности к мерджу и релизу».
Для F255 отсутствие ручной проверки на macOS 14.5 принимается как явное ограничение выпуска, а не блокирующий пункт и не PASS. Минимальная поддерживаемая версия не повышается; сохраняются deployment target и проверки совместимости API при сборке. Матрица на доступной macOS 26.5, доступность, совместимость и остальные проверки остаются обязательными. Это решение не отменяет Full CI, подписывание, нотариализацию или контроль точного SHA.


## Решение владельца от 2026-09-07 — действующий приоритет

Владелец отверг замену левой панели системным списком и замену меню профиля: вернуть исходные навигацию, состав, порядок и подменю по нажатию на пользователя из `c6bbcf376`. Это явно отменяет прежнее требование удаления десяти disabled-команд и передачи управления в native. Такие команды возвращаются в исходном недоступном состоянии; подключение новых действий не входит в откат. Не превращать основное окно в системные настройки.

T019 выполняет точечный возврат, T020 — повторное исследование реального Krisp и согласованной геометрии всех областей. Компактная автозапись T018 сохраняется. Liquid Glass и матовый вариант остаются предметом проектирования; новая композиция не считается реализованной или принятой. Старые требования native bridge и его runtime-проверки ниже являются историей отвергнутого варианта, а не основанием повторно его внедрять. Reviewer-owned отметки прежнего варианта не означают приёмку нового решения.


**Input**: spec.md, plan.md, research.md, data-model.md, contracts/interface.md, journeys.md, inventory.md, quickstart.md.
**Lane**: high-risk-feature. Незавершённые задачи остаются открытыми; выполненные отмечаются по evidence. Custom checklist оценивает рецензент; реализация его не отмечает.

## Phase 1: Допуск и исходная точка

- [X] T001 Завершить review требований в `specs/255-simplify-macos-interface/checklists/ux.md` и `checklists/security.md`, проверить analyze и владельцев зависимостей в `inventory.md`, закрепить допуск в `validation/readiness.md`. FR-013/FR-016; это review рецензента, не самоодобрение реализации. (Issue #6752)

## Phase 2: Проверяемая основа

- [ ] T002 Подтвердить системную sidebar со стабильным WebView и текущим titlebar в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`; записать нативный прототип macOS 26, minimum window и matte в `specs/255-simplify-macos-interface/validation/native-prototype.md`. FR-003/FR-004/FR-015. До расширения интеграции материал должен быть доказан. (Issue #6753)
- [ ] T003 Добавить сначала падающие проверки допуска версии/origin/main frame/payload/поколения/сессии и стабильности navigation в `apps/macos/Shared/Tests/EmbeddedCabinetShellBridgeTests.swift` и `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`. FR-008/FR-015; не подменять runtime компоновку source-string assertions. (Issue #6753)

## Phase 3: US1 — короткая и рабочая навигация (P1)

**Independent Test**: journeys.md для основных разделов/профиля; ноль заглушек и пустых подменю; HTML fallback и формы работают без native.

- [ ] T004 [US1] Обновить сначала падающие контракты меню и форм в `apps/server/tests/unit/test_cabinet_navigation_model.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/contract/test_cabinet_shell_response_contract.py`: основные разделы в настройках, отсутствие постоянных заглушек, сохранение рабочих команд и no-JS. FR-001/FR-002/FR-007/FR-011. (Issue #6754)
- [ ] T005 [US1] Реализовать ограниченный desktop-shell/v1 в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetShellBridge.swift`, подключить в `EmbeddedCabinetWebView.swift` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`; сохранить route controller, поколение, fallback и формы/CSRF. FR-005/FR-008/FR-015. (Issue #6754)
- [ ] T006 [US1] Согласовать источник меню и профиль в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` и при необходимости `cabinet/view_models.py`: удалить 10 заглушек/2 пустых подменю, сохранить рабочие входы, основные разделы в настройках; связать native snapshot в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`. FR-001/FR-002/FR-007/FR-008. (Issue #6754)

## Phase 4: US2 — два материала с одинаковым поведением (P1)

**Independent Test**: macOS 14.5/26, темы/доступность, system glass и matte; одинаковые команды и identity WebView/capture. US2 использует контракт US1, но имеет отдельную матрицу приёмки.

- [ ] T007 [US2] Дополнить `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` и `DesktopMeetingShellWebViewBoundaryTests.swift` проверками темы/system, очистки snapshot и неизменности существующей границы записи при смене оболочки; ожидания runtime закрепить в `specs/255-simplify-macos-interface/validation/acceptance.md`. FR-004/FR-005/FR-009/FR-015. (Issue #6755)
- [ ] T008 [US2] Встроить системный материал и непрозрачное исполнение, синхронизацию темы и семантические цвета в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, `DesktopMeetingShellView.swift`, `EmbeddedCabinetWebView.swift`; при необходимости передать существующее предпочтение из `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`. FR-003/FR-004/FR-005/FR-009/FR-015; без нового хранения и capture изменений. (Issue #6755)
- [ ] T009 [US2] Применить матовую геометрию и роли границ в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; обеспечить профиль/навигацию, фокус и 200% в `cabinet.js` и native workspace без второго набора контролов. FR-003/FR-006/FR-010/FR-011. (Issue #6755)

## Phase 5: US3 — согласованность и адресная чистка (P2)

**Independent Test**: inventory.md покрыт результатами; для каждого удаления найден весь круг потребителей и есть профильная проверка, рабочий local mode сохранён.

- [X] T010 [US3] Повторно найти все потребители и убрать только перекрытые CSS декларации и доказанно недостижимую queue-ветку в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`; обновить затронутые проверки и `specs/255-simplify-macos-interface/validation/cleanup.md`. По решению владельца от 2026-09-08 также убрать привязку `scripts/validate-dev-runtime.py` к закрытой F229 и заменить пропускаемый тест в `tests/governance/test_dev_runtime.py` регрессиями общего валидатора, сохранив защитные ограничения. FR-012/SC-005; .card и local mode не удалять без отдельного доказательства. (Issue #6756)
- [X] T011 [US3] Завершить общие роли заголовков/действий/состояний в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и согласовать реальные F245–F253, admin/public/no-JS, ресурсы и отклонения reference в `specs/255-simplify-macos-interface/inventory.md` и `validation/acceptance.md`. FR-010/FR-011/FR-013/FR-014. (Issue #6756)

## Phase 6: Приёмка, PR и выпуск

- [X] T012 Выполнить всю матрицу `specs/255-simplify-macos-interface/quickstart.md`, записать версии/SHA, сценарии/контраст/снимки и ограничения в `validation/acceptance.md`. FR-001–FR-016/SC-001–SC-006. Реальное native evidence и смешанные версии обязательны; незакрытые строки блокируют готовность. (Issue #6757)
- [ ] T013 Провести converge и review простоты, обновить `specs/255-simplify-macos-interface/tasks.md`, записать `validation/convergence.md`, подготовить `changes/unreleased/F255.yaml`; после разрешения владельца на коммит оформить PR с exact-SHA governance-fast и согласовать закрытие выполненных issues. FR-012/FR-013/FR-014/FR-016. (Issue #6757)
- [ ] T014 После допуска к выпуску пройти frozen candidate/Full CI/CD dry-run и релизные проверки, Developer ID/notarization/stapling/Gatekeeper/Sparkle/live appcast, smoke и русский CalVer release по `docs/agent-guidance/release-and-validation.md` и `docs/agent-guidance/macos-notarization.md`; сохранить evidence в `specs/255-simplify-macos-interface/validation/release.md`. FR-016/SC-006; без разрешения/gates не публиковать. (Issue #6752)

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014.

Тесты T003/T004/T007 сначала фиксируют ожидаемое новое поведение, затем соответствующая реализация. Связанные пути существующих тестов расширяются, а не создают параллельную тестовую систему. US1 — первый полезный этап; затем два материала, затем зачистка и общая приёмка. Частичный этап не считается выполнением запроса о двух материалах.

## Parallel opportunities

У задач нет [P]: изменения затрагивают одни shell/CSS/JS файлы, последовательность уменьшает конфликты. После реализации можно независимо прогнать Swift и pytest; внутри US1 сравнить web/native сценарии, US2 — матрицы обеих ОС, US3 — web/admin потребителей. Параллельные прогоны не означают разрешение делегировать implementation review.

## GitHub ownership

Umbrella/reservation: #6752. Task ownership синхронизировано 2026-09-06; T001 завершена отдельным рецензентом; runtime этим review не одобрен. Открытые задачи не закрываются за наличие документа. Чужие F245–F253 и #5804 не присваиваются F255.


| Spec tasks | GitHub issue |
|---|---|
| T001, T014 | [#6752](https://github.com/yshishenya/graf/issues/6752) |
| T002, T003 | [#6753](https://github.com/yshishenya/graf/issues/6753) |
| T004, T005, T006 | [#6754](https://github.com/yshishenya/graf/issues/6754) |
| T007, T008, T009 | [#6755](https://github.com/yshishenya/graf/issues/6755) |
| T010, T011 | [#6756](https://github.com/yshishenya/graf/issues/6756) |
| T012, T013 | [#6757](https://github.com/yshishenya/graf/issues/6757) |

#6752 сохраняет reservation/umbrella и не закрывается после одного T001: владеет также T014. Остальные issues закрываются только после выполнения всей группы и closure evidence.

## Phase 7: Convergence

- [ ] T015 Повторить нативный прототип и передачу меню в штатном установленном GRAF Dev через build/promote/status/smoke на чистом согласованном SHA; записать manifest, app presentation и реальные смешанные версии в `validation/native-prototype.md` и `validation/acceptance.md` per FR-004/FR-016 (partial, HIGH). Владелец #6753; уточняет незавершённые T002/T012, диагностический GRAF Local не засчитывается. (Issue #6753)
- [X] T016 Завершить матрицу macOS 14.5/26, темы/system, прозрачности/движения/контраста, VoiceOver, минимального окна/200% и активной записи/Stop в `validation/acceptance.md`; исправить выявленные дефекты в разрешённых native/CSS/JS файлах per FR-005/FR-006/FR-009, SC-003/SC-004 (partial, HIGH). Владелец #6755; уточняет T008/T009/T012. (Issue #6755)
- [X] T017 Проверить согласованную объединённую ревизию F245–F253 и все оставшиеся admin/public/no-JS/account-save сценарии, обновить `inventory.md` и `validation/acceptance.md` per FR-010/FR-011/FR-013, SC-006 (partial, HIGH). Владелец #6756; уточняет T011/T012, открытый соседний PR не считается внедрённым. (Issue #6756)

## Промежуточное состояние реализации

Код T003–T010 реализован и прошёл профильные проверки, но задачи с обязательной runtime приёмкой сохраняют `[ ]` до полного evidence. См. `validation/acceptance.md`, `validation/cleanup.md` и `validation/convergence.md`. Коммит `c6bbcf3` содержит документы; реализация закоммичена в `1614e6787`, создан draft PR #6766 и штатный Dev-кандидат. Установлен GRAF Dev `dev-e8193d7ba850`, live smoke 13/13 PASS; выпуск ещё не выполнен. Это отдельное evidence установленной ревизии; см. `validation/dev-preparation.md`.

- [X] T018 [US3] По запросу владельца от 2026-09-07 убрать одинаковые заглушки приложений и уменьшить высоту кнопок автозаписи до 28 pt, радиус до 6 pt в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`; согласовать существующий контракт `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`, сохранить три правила, выбор/disabled/клавиатуру и изменения F249 при совместной приёмке. FR-003/FR-006; владелец #6755. Профильные проверки и фактический результат — `validation/settings-density.md`. (Issue #6755)

## Phase 8: возврат по решению владельца

- [X] T019 [US1] Вернуть исходные sidebar/profile из `c6bbcf376` в `DesktopCabinetWorkspaceView.swift`, `EmbeddedCabinetWebView.swift`, `sections.html`, `cabinet.css`, `cabinet.js`; удалить bridge и его тесты, восстановить существующие контракты; проверить совместно с F249 и установить штатный GRAF Dev. Владелец #6754. Evidence: `validation/navigation-restore.md`. (Issue #6754)
- [X] T020 [US3] Провести свежий UI-аудит установленного Krisp и GRAF, изучить Apple HIG; описать детали меню, общую геометрию и варианты материалов без изменения привычных путей в `validation/krisp-review.md`. Владелец #6756. Старые T002–T009/T015 в части native sidebar/bridge отменены владельцем, а не выполнены. Evidence: свежий CUA-проход Krisp Account/Shared with me и GRAF Dev на синтетическом кабинете 2026-09-07; настройки не изменялись. (Issue #6756)

- [X] T021 [US1] По скриншоту владельца от 2026-09-07 исправить профиль в `cabinet.js`/`cabinet.css`: hover открывает только одно подменю, переход в другое/уход закрывает старое, зазор не мешает перейти внутрь; keyboard/touch/Escape сохраняются. Убрать отдельные рамки вариантов темы, смягчить общий контур и радиусы. Состав/порядок прежний. Регрессия в существующем `CabinetSidebarRuntimeTests.swift`; штатный совместный Dev после передачи стенда от F249. Владелец #6754. Evidence: `validation/profile-hover.md`; установлен `dev-51fd80f6f069`, 13/13 PASS. (Issue #6754)

- [X] T022 [US1] Исправить выявленный видеоотзывом дефект T021: внутренний padding между summary и submenu не закрывает раскрытый пункт. Проверить реальный hit target и остановку указателя в этом отступе, дополнить существующую WKWebView регрессию и передать адресный коммит F249 для следующей общей установки Dev. Владелец #6754. Evidence: `validation/profile-hover.md`; факт следующей установки и её SHA фиксируются отдельно в PR #6766/issue #6754. (Issue #6754)

- [X] T023 [US2] Применить согласованную матовую композицию всех трёх областей в `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, устранить дублирующий минимум содержимого в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и роли декоративных границ в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, сохранив навигацию, профиль, фокус и независимый Stop. Проверить существующие boundary/WK/server контракты, темы/масштаб и штатный совместимый GRAF Dev; записать `validation/matte-shell.md`. FR-003/FR-006/FR-009; владелец #6755. Не заменяет полную матрицу T016 и проверку Liquid Glass. (Issue #6755)

- [X] T024 [US2] Убрать тяжёлую тень вокруг закреплённого плеера и перевести декоративные разделители экрана встречи на `--line-soft` в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, сохранив цветные состояния предупреждений, фокус, вкладки и управление записью. Проверить светлую/тёмную тему на экране встречи и плеере; записать результат в `validation/detail-surface.md`. FR-003/FR-006/FR-009; владелец #6755. (Issue #6755)

- [X] T025 [US1] Сохранить текущий экран после выбора темы в меню профиля: отправлять автосохранение без навигации, вернуть выбор при ошибке и принимать только безопасный локальный `return_to` в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` и `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`. Не менять обычную форму настроек, состав меню и CSRF; проверить серверный маршрут и существующий WKWebView сценарий, записать `validation/profile-autosave.md`. FR-001/FR-006/FR-008; владелец #6754. (Issue #6754)

## Phase 9: дефект, обнаруженный при разрешённой записи

- [X] T026 [US2] Исправить отклонение корректной короткой записи из-за ceil-длительности в `apps/server/src/twobrain_rec_server/normalization/service.py`; расширить существующие `apps/server/tests/integration/test_playback_normalization_media_matrix.py` и `test_playback_normalization_finalize.py` границами допустимого округления, сохранить hash/byte-length/decode и manual-upload проверки. FR-009/SC-004; продолжение T016 после фактической записи/Stop, владелец #6755. Проверить публичные контракты плеера и установленный Dev; evidence в `validation/acceptance.md`. (Issue #6755)

- [X] T027 [US2] Синхронизировать light/dark/system из текущего разрешённого документа с NSApplication.appearance в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`; расширить `apps/macos/Shared/Tests/CabinetSidebarRuntimeTests.swift` реальным WKWebView-проходом и отказами чужого origin/iframe/invalid/detach. FR-005/FR-006, продолжение T016; владелец #6755. Не возвращать отменённую нативную навигацию и не создавать второе предпочтение темы. (Issue #6755)

- [X] T028 [US2] По отзыву владельца от 2026-09-08 закрывать меню строки macOS при внешнем клике, сохранить внутренние кнопки/повторный клик/Escape и удалять наблюдатели при закрытии в `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`. Применить существующий фиолетовый цвет GRAF и обеспечить контраст подписей, включая выбранные кнопки автозаписи в `MeetingDetectionSettingsView.swift`; расширить существующие `DesktopCalendarReminderTests.swift`. FR-003/FR-006, владелец #6755; проверить установленный Dev. (Issue #6755)

## Актуальная сверка задач перед финальной установкой

T011/T017 подтверждены совместными PostgreSQL/browser и установленными маршрутами списка/настроек/аккаунта/плеера. Историческая матрица desktop-shell/v1 снята вместе с отменённым протоколом; нет отдельного нового серверного протокола, требующего установки старого клиента. Действующие старые адреса, no-JS, origin/session и route контракты сохраняются в общих тестах. Не заявляется фактическая установка старой версии или PASS отменённого bridge. F249 не включается. T018/T023/T024/T025/T026/T027 имеют установленное evidence в acceptance.md; T016/T012/T013 сохраняют финальную проверку T028, converge и exact-SHA PR. Публичный выпуск T014 не выполнен.

- [X] T029 [US2] По решению владельца от 2026-09-08 превратить верхний календарный вход в компактное меню GRAF: использовать имеющуюся AppIcon.icns максимально читаемо в высоте строки macOS, сохранять знак GRAF при доступном обновлении, полностью скрывать заголовок/период/блок при пустом календаре. Сохранить вход в GRAF, настройки календаря, реальные встречи/ссылки и уведомление об обновлении; по последующему уточнению убрать индикатор загрузки, ошибку/повтор и ручное обновление, оставить восстановление подключения в настройках календаря. Изменить `CalendarTray.swift`, расширить существующие `DesktopCalendarReminderTests.swift`, проверить light/dark, пустое состояние/ошибки/обновление, закрытие и геометрию в установленном Dev. FR-002/FR-003/FR-006/FR-009; владелец #6755. (Issue #6755)


## Приёмка T028/T029 на установленном Dev, 2026-09-08

T012/T016/T028/T029 подтверждены совокупностью acceptance.md и установленного dev-38831bb4cc29: обе темы, компактное меню без раздела встреч, прямые действия, Enter и внешний клик. 69 Swift PASS, live smoke 13/13 PASS, governance-fast 34169129854 PASS на точном source SHA 38831bb4cc2972078765e64ec5973a59ba04f5b1. Проверка самого значка в строке опирается на ресурс/размер в XCTest: CUA не отдаёт системную строку и не засчитывается как её визуальная проверка. AppUpdate/ошибки/восстановление проверены автоматикой; календарный источник в Dev не подключался. macOS 14.5 и VoiceOver — not_run_owner_accepted. T013 сохраняет итоговую сверку review/tasks/issues; T014 — будущий публичный выпуск.

- [X] T030 [US2] Перерисовать собственный знак GRAF для строки macOS как нативный template-вектор; подключить фактическую запись/паузу/завершение к значку, подсказке и доступному тексту меню в `CalendarTray.swift` и `TwoBrainRecApp.swift`. Сохранить различимость обновления приложения и отсутствие пустого календарного раздела. Расширить `DesktopCalendarReminderTests.swift` переходами и raster-проверкой прозрачности/геометрии; проверить короткую реальную запись и Stop в штатном Dev, обе темы. FR-003/FR-005/FR-006/FR-009, уточнение владельца 2026-09-08. (Issue #6755)

- [X] T031 [US2] Добавить прямой ручной Start/Stop и контекстный минимальный NSMenu вместо popover в `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`, подключить прежние защищённые команды в `apps/macos/RecApp/App/TwoBrainRecApp.swift`; сохранить тихий календарь/HTTPS/privacy/обновление, стабильный знак записи и проверить состояния/устаревшие команды в `DesktopCalendarReminderTests.swift`, затем фактический старт и Stop из меню в штатном Dev. Требования и сценарии — уточнение spec от 2026-09-08; evidence в `validation/acceptance.md`. (Issue #6755)

- [ ] T032 [US2] По пяти замечаниям владельца встроить состояние записи в сам знак GRAF, явно закрывать меню по внешним кликам/потере активности без вложенного tracking, заменить календарные настройки общими и добавить безопасный выход; удалить мёртвую модель состояний, convenience и старые календарные callbacks в `CalendarTray.swift`/`TwoBrainRecApp.swift`, расширить `DesktopCalendarReminderTests.swift`, проверить официальный Dev и записать evidence в `validation/acceptance.md`. (Issue #6755)

- [X] T033 [US2] По подтверждению владельца сохранить mic-only pause, добавить «Mute микрофона»/«Включить микрофон» в `CalendarTray.swift`/`TwoBrainRecApp.swift`, согласовать shared подписи и capture HUD, встроить красный индикатор с Reduce Motion и графикой Mute в знак; проверить переходы/устаревшие команды/графику и установленный Dev, записать evidence в `validation/acceptance.md`. (Issue #6755)

- [ ] T034 [US2] Устранить удержание главной очереди запасным showMenu в `CalendarTray.swift`: после source-menu tracking использовать механизм цикла событий AppKit; проверить штатный Quit/cleanup и обработку внешних кликов/доступности на установленном Dev, записать metadata-only evidence в `validation/acceptance.md`. (Issue #6755)

## Подготовка merge и граница F249, 2026-09-08

T013 включает live fetch и пробный merge-tree F249/F255; результат и обязательный порядок переноса описаны в `validation/f249-compatibility.md`. Владелец подтвердил: верхнее меню полностью остаётся из F255. F249 не включается автоматически: её текущая ревизия конфликтует в 15 файлах, требует переноса на master после F255 и самостоятельной совместной приёмки.

T002–T009/T015 — отменённые задачи первоначального native-прототипа. Их `[ ]` сохраняет честную историю: они не выполнены и не являются открытой реализацией принятого варианта. Активные замены: T019/T021/T022/T025 (#6754), T016/T018/T023/T024/T027–T034 (#6755). Текущие issue ownership fields должны перечислять эти действующие задачи; первоначальные задачи остаются в исторических ссылках. T014 — отдельный будущий выпуск; его не закрывать при подготовке PR.
