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
- [ ] T007 [US1] Обеспечить постоянную видимую компактную панель и Stop при hidden menu/fullscreen в `apps/macos/RecApp/App/TwoBrainRecApp.swift`, не меняя countdown 214. [FR-003/004/013]
- [X] T008 [US1] Объединить точки входа настроек в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и маршруты `Sources/Cabinet/DesktopMeetingShellView.swift`, сохранив локальное владение автозаписью. [FR-017]

## Phase 4 — US2: timely messages

Проверка: одна встреча с напоминанием, ask/always/never, отсутствием сети, terminal failure и готовностью.

- [X] T009 [US2] Расширить `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift` и `MeetingDetectionRecordingLifecycleTests.swift`: истечение не запоминает, отказ, гонка Start/Stop, повторное событие. [FR-004]
- [X] T010 [US2] Реализовать presenter только локальных событий/напоминаний и дедупликацию в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`, подключить через `App/TwoBrainRecApp.swift`; OS permission, Focus, возраст события и приоритет активной записи; получение/показ при закрытом окне и без загруженного WKWebView. [FR-005/006/011/012/019/020]
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
- [X] T017 [US4] Подключить Mac-owned preferences/permission/test notification к `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; owner+device storage, отмена pending/delivered при logout/scope/disable/calendar change; старую автозапись не дублировать. [FR-004/010/011/012]

## Phase 7 — US5: compatibility and cleanup

Проверка: old config + local queue + upgrade + fallback + rollback.

- [ ] T018 [US5] Добавить upgrade/rollback/local-mode проверки в `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`; сохранить проверки `DesktopCabinetUploadLinkTests.swift`, `DesktopUploadQueueV5Tests.swift`, `DesktopMeetingShellWebViewBoundaryTests.swift`; зафиксировать все callers compact queue в `specs/249-notification-control-design/research.md`. [FR-015]
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
