# Tasks: Панель управления и уведомления 249

Реализация и автоматические проверки выполнены по сводке `implementation-evidence.md`; полная аппаратная приёмка T020 и исследование T021 остаются открытыми. Umbrella: https://github.com/yshishenya/graf/issues/6635. Независимый review и синхронизация child issues выполнены; дизайн сам по себе не закрывает umbrella.

## Phase 1 — Review and setup

- [X] T001 Рассмотреть `specs/249-notification-control-design/checklists/ux.md` и `checklists/security.md`, подтвердить область внедрения и критерии доступности 8-секундного запроса.
- [X] T002 Зафиксировать review/issue mapping в `specs/249-notification-control-design/tasks.md`, проверить фактические версии клиента/сервера перед внедрением и независимое происхождение ресурсов. [FR-018]

## Phase 2 — Shared contracts

- [X] T003 Добавить тесты lifecycle/scope/read-revision/повторной доставки в `apps/server/tests/unit/test_notification_inbox.py` по `data-model.md`: новая revision старой карточки во время read, две области, запрет local events в вебе и server events в нативной доставке. [FR-005/007/008/009]
- [X] T004 Реализовать additive schema и историю в `apps/server/src/twobrain_rec_server/notifications/inbox.py`; миграцию со свободным номером в `db/migrations/versions/`; сохранить mandatory outbox; ограничить видимость завершённых карточек 30 днями, очищать metadata в существующем maintenance path без изменения сроков доменных данных. [FR-007/008/016]

## Phase 3 — US1: control now

Проверка: готовность → старт → пауза → продолжение → Stop, включая скрытое окно и отсутствие сети.

- [X] T005 [US1] Дополнить `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift` и `CaptureControlV5Tests.swift` проверками совмещённой панели, независимых capture/upload статусов и действий. [FR-001/002/003/014]
- [X] T006 [US1] Расширить `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift` и внедрить текущие capture actions из `App/TwoBrainRecApp.swift`; сохранить safe calendar projection. [FR-001/002/014/017]
- [X] T007 [US1] Обеспечить постоянную видимую компактную панель и Stop при hidden menu/fullscreen в `apps/macos/RecApp/App/TwoBrainRecApp.swift`, не меняя countdown 214. [FR-003/004/013]
- [X] T008 [US1] Объединить точки входа настроек в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и маршруты `Sources/Cabinet/DesktopMeetingShellView.swift`, сохранив локальное владение автозаписью. [FR-017]

## Phase 4 — US2: timely messages

Проверка: одна встреча с напоминанием, ask/always/never, отсутствием сети, terminal failure и готовностью.

- [X] T009 [US2] Расширить `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift` и `MeetingDetectionRecordingLifecycleTests.swift`: истечение не запоминает, отказ, гонка Start/Stop, повторное событие. [FR-004]
- [ ] T010 [US2] Реализовать presenter только локальных событий/напоминаний и дедупликацию в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`, подключить через `App/TwoBrainRecApp.swift`; OS permission, Focus, возраст события и приоритет активной записи; получение/показ при закрытом окне и без загруженного WKWebView. [FR-005/006/011/012/019/020]
- [X] T011 [US2] Подключить реальные committed result/sharing producers к `apps/server/src/twobrain_rec_server/notifications/inbox.py`, покрыть end-to-end в `apps/server/tests/integration/test_notification_inbox_flow.py`; контракт источников/получателей/разрешения — `producer-contract.md`, N16/N17/N19 сохраняют существующий контекст без фиктивных producers; точки: `processing/store.py:persist_processing_result/set_workflow_status`, `outcomes/ai_service.py:_cas_summary_slot`, `cabinet/access.py:create_scoped_share_grant/accept_share_invitation`; транзакционные владельцы и ограничения — в `research.md`. [FR-005/007/016]

## Phase 5 — US3: inbox

Проверка: important/history, одной карточке read, revision race, stale cache, logout/revoke/delete и разделение областей.

- [X] T012 [US3] Реализовать HTTP/read/HTML fallback в `apps/server/src/twobrain_rec_server/cabinet/web_routes/notifications.py`, scoped auth/CSRF и safe actions, фильтрацию удаления/revoke, очистку при pageshow/scope change и bounded refresh 30 секунд; проверки в `apps/server/tests/contract/test_notification_inbox_routes.py`. [FR-008/009/012]
- [X] T013 [US3] Добавить общую кнопку и панель в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shell.html` и новом `components/notification_inbox.html`, текущие `cabinet.css`/`cabinet.js`; empty/error/stale/narrow/keyboard, возврат focus, ошибки read и навигации. [FR-007/008/013/017]
- [X] T014 [US3] Проверить разделение поверхностей в `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` и `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`: embedded сохраняет серверную ленту; local incidents не передаются в web inbox; server events не командуют capture и не вызывают нативный presenter. [FR-009/011/012/020]

## Phase 6 — US4: settings

Проверка: сохранение/отмена/error/conflict, старые false, разница account и Mac, запрет ОС.

- [X] T015 [US4] Расширить `apps/server/tests/unit/test_notification_preferences.py` и `tests/contract/test_settings_ui_contract.py` миграцией false, missing old form fields, mandatory delivery и version conflict. [FR-010/012]
- [X] T016 [US4] Расширить `apps/server/src/twobrain_rec_server/billing/notification_preferences.py`, `cabinet/web_routes/settings.py`, `templates/cabinet/pages/settings_notifications_content.html`, сохранив старые optional поля и отдельную серверную форму; не занимать `components/notifications.html`, где уже живёт форма, новым несовместимым назначением: новый inbox component `components/notification_inbox.html`. [FR-010/012]
- [ ] T017 [US4] Подключить Mac-owned preferences/permission/test notification к `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; owner+device storage, отмена pending/delivered при logout/scope/disable/calendar change; старую автозапись не дублировать. [FR-004/010/011/012]

## Phase 7 — US5: compatibility and cleanup

Проверка: old config + local queue + upgrade + fallback + rollback.

- [X] T018 [US5] Добавить upgrade/rollback/local-mode проверки в `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`; сохранить проверки `DesktopCabinetUploadLinkTests.swift`, `DesktopUploadQueueV5Tests.swift`, `DesktopMeetingShellWebViewBoundaryTests.swift`; зафиксировать все callers compact queue в `specs/249-notification-control-design/research.md`. [FR-015]
- [X] T019 [US5] После T018 удалить только доказанно недостижимую embedded queue ветку в `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` и уточнить footer в `Sources/Calendar/CalendarTray.swift`; сохранить decoder и автономный список. [FR-014/015/016]

## Phase 8 — Validation and closeout

- [ ] T020 Пройти `specs/249-notification-control-design/quickstart.md` на реальном Mac/web/WKWebView: hidden menu, full screen, multiple displays, permissions, offline, disk, no-speech, VoiceOver, theme, 200%; записать обезличенные результаты. [FR-001–020; SC-001/002/003/005/006]
- [ ] T021 Провести 5 пользовательских сценариев поиска настроек/понимания записи и замер local response p95, внести результаты в `specs/249-notification-control-design/quickstart.md`. [SC-004/006]
- [ ] T022 Выполнить converge, validation по high-risk lane, обновить `changes/unreleased/F249.yaml`, сверить tasks/issues и PR SHA; commit/release только с отдельной авторизацией. [FR-015/018]

## Dependencies and delivery

T001→T002 обязательны для всей реализации. T003→T004 для серверных историй; нативный US1 может готовиться независимо от server storage после T002. T005→T006→T007→T008. T009 до T010. T004 до T011–T014. T015 до T016–T017. T018 после работающего преемника; T019 только после успешного T018. T020–T022 после выбранных функций.

Разделение возможно по независимым файлам: нативный US1 и серверная Phase2; тесты настроек T015 и серверные producer tests T011. Внутри общего TwoBrainRecApp.swift/notifications.html — последовательные изменения одним владельцем. Первая полезная часть — US1 с безопасным календарём и видимым Stop; публиковать её отдельно можно только после её gates, не под видом полного завершения всех задач.

Уточнение дизайна перед реализацией: [разделение поверхностей](surface-separation.md). «На этом Mac» — локальное состояние без read-маркеров. Веб — important/history и точка нового важного, без read-all и системной доставки. T010/T014/T016/T017 обязаны соблюдать FR-020.

## GitHub ownership

- T001: https://github.com/yshishenya/graf/issues/6669
- T002: https://github.com/yshishenya/graf/issues/6670
- T003: https://github.com/yshishenya/graf/issues/6671
- T004: https://github.com/yshishenya/graf/issues/6672
- T005: https://github.com/yshishenya/graf/issues/6673
- T006: https://github.com/yshishenya/graf/issues/6674
- T007: https://github.com/yshishenya/graf/issues/6675
- T008: https://github.com/yshishenya/graf/issues/6676
- T009: https://github.com/yshishenya/graf/issues/6677
- T010: https://github.com/yshishenya/graf/issues/6678
- T011: https://github.com/yshishenya/graf/issues/6679
- T012: https://github.com/yshishenya/graf/issues/6680
- T013: https://github.com/yshishenya/graf/issues/6681
- T014: https://github.com/yshishenya/graf/issues/6682
- T015: https://github.com/yshishenya/graf/issues/6683
- T016: https://github.com/yshishenya/graf/issues/6685
- T017: https://github.com/yshishenya/graf/issues/6686
- T018: https://github.com/yshishenya/graf/issues/6687
- T019: https://github.com/yshishenya/graf/issues/6688
- T020: https://github.com/yshishenya/graf/issues/6689
- T021: https://github.com/yshishenya/graf/issues/6690
- T022: https://github.com/yshishenya/graf/issues/6691
- T023: https://github.com/yshishenya/graf/issues/6709
- T024: https://github.com/yshishenya/graf/issues/6711
- T025: https://github.com/yshishenya/graf/issues/6751

Setup evidence: independent UX 13/13 and security 9/9; analyze.md critical/high 0; base a389657e6; 22/22 tasks have open owners. Feature249 canon 23/23 PASS. Global canon hook failed only unrelated #6684 (feature253, area label and Spec tasks field); global sync success is not claimed.

## Уточнение процесса от пользователя, 2026-09-06

T022 включает устранение обходных путей установки: один GRAF Dev через harness,
обязательный маршрут в AGENTS.md, отключённые build-local-app/run-local-app и
сборщик макета, проверка отказа до создания app, обновление старых инструкций.
Имя сертификата и чтение старой конфигурации сохраняются ради совместимости;
исторические отчёты не переписываются как новые результаты.

T007/T018/T020 остаются открытыми до проверки установленного GRAF Dev:
конфигурация виджета и совместимость покрыты тестами, аппаратные сценарии этим
не подменяются. T009 опирается на неизменённые существующие countdown/lifecycle
тесты в полном наборе Swift. Новый общий файл проверок — DesktopNotificationControlTests.swift.

## Phase 9: Convergence

Runtime выявил HIGH/contradicts по FR-002/004, US1/AC4 и принципу II:
новый виджет ошибочно обещает остановку системного звука на паузе микрофона.
Независимый reviewer подтвердил сохранение семантики Feature 022.

- [X] T023 Исправить общие нативные подписи паузы микрофона, отображение обоих источников и непрерывный таймер; согласовать spec/experience/quickstart/макет с существующим V5LocalRecordingWriter, добавить тест времени и повторить GRAF Dev. [FR-002/004; US1/AC4; contradicts]


## Phase 10: Convergence

- [X] T024 Устранить обрезание кнопок и источников в `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift` и `Sources/Notifications/DesktopControlPanel.swift`; проверить реальный виджет GRAF Dev шириной 290 px в записи и паузе. [FR-013/017; SC-006; partial]

T010/T017: код и автоматические проверки выполнены, запрос принят macOS;
видимая системная доставка/полная матрица ещё не приняты. T019: удаление и
регрессии выполнены, окончательное закрытие зависит от upgrade/rollback T018.
Поэтому эти задачи возвращены в открытые, соответствующие issues остаются открытыми.


## Phase 11: Convergence

- [X] T025 Исправить path-dependent контрольную сумму разрешений в `scripts/dev-harness.py` и добавить регрессию в `tests/governance/test_dev_harness.py`; проверить одинаковые entitlement values двух реальных Dev artifacts без установки. [T022; process: stable Dev identity; contradicts]

## Phase 12: Convergence

- [ ] T026 Исправить повторную постановку отменённых будущих напоминаний без повторной доставки уже наступивших; на клике проверять актуальную ссылку и срок события; обновлять разрешение при возврате в окно настроек. Добавить регрессии и повторить GRAF Dev. [FR-006/011/012/019; T010/T017; contradicts]
- [X] T027 Выполнить запрошенные пользователем пять независимых экспертных проходов субагентами, устранить подтверждённые проблемы пути и записать ограничения: это не измерение времени пяти людей. [SC-004/006; T021; user clarification 2026-09-06]
- [X] T028 Сохранить виджет до подтверждённого освобождения capture при Stop/error, показать переход остановки и ненавязчивый итог с доступом к записи; добавить проверки состояний. [FR-002/003/013; US1; expert pass 2]
- [X] T029 Сохранить ошибку формата при непринятом повторе и подтверждать показанную revision только после успешного открытия встречи; добавить серверные/браузерные регрессии. [FR-007/008/009; C04/C05]


T026: https://github.com/yshishenya/graf/issues/6758
T027: https://github.com/yshishenya/graf/issues/6759
T028: https://github.com/yshishenya/graf/issues/6760
T029: https://github.com/yshishenya/graf/issues/6761

Пользователь уточнил метод T021: пять независимых субагентов вместо отсутствующих
наблюдений людей. Их выводы сведены в agent-study.md; p95 этим не измерен.

## Phase 13: Convergence

- [X] T030 Добавить штатный переход между версиями управляющего кода в `scripts/dev-harness.py`: проверять чистый checkout прежнего полного SHA и его runtime digest до любых изменений, восстанавливать прежний runtime прежним кодом при отказе, поддержать симметричный rollback через проверенный target checkout. Сохранить блокировку, единственный GRAF Dev, данные и проверки идентичности; добавить регрессии и выполнить живой переход. [T022; process: single GRAF Dev; partial]

T030: https://github.com/yshishenya/graf/issues/6763

- [X] T031 Устранить повторные сигналы одной записи при ошибке Stop и подавлять баннер поверх видимого результата; назвать переход в общий список «Открыть локальные записи» в `DesktopNotificationPresenter.swift` и `DesktopControlPanel.swift`, добавить регрессии. [FR-002/005/019; expert pass 5; contradicts]

T031: https://github.com/yshishenya/graf/issues/6764

## Phase 14: Convergence

- [X] T032 Исправить устаревший статус разрешения после повторного включения macOS: обновлять его в открытом активном разделе настроек, сверять перед тестовым уведомлением. Повторить OS off/on без закрытия раздела в единственном GRAF Dev. [FR-011/012; live eb9a8d517; contradicts]

T032: https://github.com/yshishenya/graf/issues/6765

## Сверка фактической приёмки на 57db9ba34, 2026-09-06

T007: живая запись47с, закрыто главное окно, Krisp переведён в полноэкранный
режим, виджет и однократный Stop доступны. T018/T019: upgrade → rollback на
3de3eec50 → возврат57db9ba34, 13/13 smoke на обоих переходах, запись47с и
настройки сохранены. Автономные decoder/queue проверки входят в Swift812.
T027: пять отдельных сценарных агентов, исправления T026–T032.
T028: короткая запись показала последовательно «Останавливаем запись…» и
«Запись остановлена / Отправляем запись / Локальная копия сохранена».
T029: сервер/Node9 PASS; живой веб возвращает «Важное» после закрытия истории,
не восстанавливает точку на старых результатах. Просмотр и отзыв доступа
проверены регрессиями предыдущего коммита, продуктовый код веба с тех пор не менялся.
T030: штатный живой cross-definition rollback и возврат PASS, общий lock,
полные13 проверок; временный checkout удалён после возврата.
T031: один инцидент с обратной совместимостью,12 targeted Swift; фактический
виджет результата показан. T032: OS off→on отражается в том же открытом
разделе на установленной57db9ba34; исходное разрешение on восстановлено.

T010/T017/T026 пока сохраняют обязательство полного сценария календарных
напоминаний/Focus; только реальная системная тестовая доставка подтверждена
журналом usernoted Delivering alert/notificationCenter и Presenting as banner.
T020/T021/T022 остаются открыты: полная аппаратная матрица, VoiceOver и нативный
p95 ещё не приняты. Mac заблокировался во время перехода к VoiceOver,
инструмент сообщил невозможность автоматического разблокирования. Продолжение
интерфейсных действий требует разблокированного Mac. Веб p95=33.7мс (40 открытий,
2 requestAnimationFrame), это не нативный p95 и не пользовательские секунды SC-004.


## Phase 15: Convergence

- [X] T033 Разделить доступные имена трёх действий автозаписи в `MeetingDetectionSettingsView.swift`: явная группа приложения и собственное имя каждой кнопки, сохранить выбранность/disabled и существующие правила. Дополнить регрессию `AppControlAccessibilityTests.swift` и проверить живое дерево доступности в GRAF Dev. [FR-013/017; T020; contradicts; HIGH]

T033: https://github.com/yshishenya/graf/issues/6767

T033 принят на eb4f5808292dde362b0fa9d89aa65845d06875ee: в живом дереве
доступности группа 8x8 Work содержит отдельные «Всегда», «Спрашивать»,
«Никогда». Последовательное нажатие каждого действия меняет выбранное
значение; исходное «Спрашивать» восстановлено. Swift40 PASS, Dev13/13 PASS,
governance-fast run34051940484 PASS на том же SHA.

## Phase 16: Convergence

- [ ] T034 Исправить нажатие календарного напоминания без ссылки: после проверки текущего события открыть существующее меню GRAF; отменённые, истёкшие и чужие события не выполняют действие. Уточнить текст и добавить регрессию. [FR-012/019; T010/T026; no-link click; HIGH]

T034: https://github.com/yshishenya/graf/issues/6779

- [ ] T035 Сохранить ручной старт в верхнем меню при календарном предложении записи: не использовать правило скрытия дубликата кнопки главного окна в controlPanelSnapshot. Сохранить permissions/start-stop guards, добавить регрессию и проверить живой GRAF Dev. [FR-002/003/019; T020; live calendar start; HIGH]

T035: https://github.com/yshishenya/graf/issues/6780

## Phase 17: Convergence — замечания пользователя по двум поверхностям

- [ ] T036 Ограничить всю нативную панель выбранным экраном, закрепить управление записью, сократить технический шум и перенести вторичный контент в прокрутку; сохранить правдивые источники, Stop и действия восстановления, проверить изменение содержимого/дисплея. [FR-002/003/012/013/017/019; user screenshots 2026-09-07; HIGH]
- [ ] T037 Перенести вход «Уведомления» из плавающей шапки в постоянное левое меню над профилем, переиспользовать стили навигации и панель «Важное / История», проверить широкое/узкое окно, свёрнутое меню, клавиатуру и обновление содержимого. [FR-007/008/013/017/020; user rejection of topbar 2026-09-07; HIGH]
