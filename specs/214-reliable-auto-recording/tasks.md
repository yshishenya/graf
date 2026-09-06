# Задачи: надёжный полный цикл автоматической записи

**Входные документы**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Полоса риска**: высокий риск — запуск и остановка записи, локальное хранение,
восстановление, отправка и пользовательские состояния.

**Правило реализации**: использовать существующие настройки, writer, manifest,
восстановление, очередь и общий список. Не добавлять вторую службу, очередь,
базу или отдельную историю встреч.

## Формат

- `[P]` — можно выполнять параллельно с другими отмеченными задачами фазы,
  потому что файлы не пересекаются.
- `[US#]` — пользовательский путь из `spec.md`.
- Проверки каждой фазы выполняются до изменения поведения этой фазы.

## Фаза 1 — Проверочная опора встроенного реестра

**Цель**: до реализации зафиксировать требования к упаковке и проверке
встроенного списка приложений без сети.

- [X] T001 Добавить проверку наличия, упаковки и общей валидации встроенного реестра в `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` (FR-040)

---

## Фаза 2 — Общее состояние сохранения

**Цель**: подготовить один существующий элемент очереди к раннему показу записи.

- [X] T002 Добавить проверки обратимого декодирования, сортировки и запрета отправки состояния `saving` в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` (FR-030–FR-032)
- [X] T003 Добавить `saving` в существующий `UploadItemState` и его пользовательское имя в `apps/macos/Shared/Sources/Models/AudioModelCore.swift`, сохранив совместимость старых документов очереди (FR-031)

**Проверка фазы**: старые документы очереди читаются как раньше; `saving` виден,
но не допускается к отправке.

---

## Фаза 3 — User Story 1: ровно три локальных состояния (P1)

**Цель**: `Всегда`, `Спрашивать`, `Никогда` становятся единственным локальным
решением для каждого проверенного приложения.

**Независимая проверка**: чистая установка, старый файл настроек и работа без
сети дают редактируемую трёхпозиционную карту; новые приложения получают
`Спрашивать`.

- [X] T004 [P] [US1] Расширить матрицу политики для `always`/`ask`/`never` без глобальных и серверных разрешений в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` (FR-001–FR-003, FR-013, FR-016)
- [X] T005 [P] [US1] Добавить проверки чистой установки, безопасного чтения старых полей и записи только трёхпозиционной карты в `apps/macos/Shared/Tests/MeetingDetectionTelemetryTests.swift` (FR-001–FR-003)
- [X] T006 [P] [US1] Добавить проверки порядка действующий сервер → кэш → встроенный реестр и значения `ask` для новых целей в `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` (FR-002, FR-040)
- [X] T007 [US1] Упростить модель и сохранение настроек до `automaticRecordingRules` с однократным безопасным чтением старых значений в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift` (FR-001–FR-003, FR-016)
- [X] T008 [US1] Удалить скрытые глобальные и серверные условия из решения о записи в `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift` (FR-013, FR-015–FR-016)
- [X] T009 [US1] Добавить бессрочный `apps/macos/RecApp/Resources/meeting-target-registry-baseline.json`, включить его в `apps/macos/Package.swift`, добавить источник `bundled` и подключить как последний проверенный источник в `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift`, `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionAppModule.swift` (FR-002, FR-040)
- [X] T010 [US1] Оставить в настройках только общий и построчный выбор трёх состояний, значение `Разные` и доступные подписи в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и обновить проверки в `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` (FR-004–FR-006, SC-008)

---

## Фаза 4 — User Story 2: вопрос и запуск через 8 секунд (P1)

**Цель**: сохранить восьмисекундный запуск, но менять постоянную настройку только
после явной кнопки с галочкой.

**Независимая проверка**: четыре сочетания кнопок и галочки, таймер, окончание
встречи и одновременные события дают ровно один ожидаемый исход.

- [X] T011 [P] [US2] Дополнить матрицу отсчёта явными решениями, галочкой, окончанием встречи и повторными событиями в `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift` (FR-007–FR-012, FR-014)
- [X] T012 [US2] Сделать решение окна одноразовым, сохранить `always`/`never` только после явной кнопки с галочкой и не сохранять выбор по таймеру в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-007–FR-014)
- [X] T013 [US2] Обновить видимые и доступные подписи окна `Записать`, `Не записывать`, `Запомнить выбор` и отсчёта в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и проверки в `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` (FR-007, FR-012, SC-008)

---

## Фаза 5 — User Story 3: запись точно останавливается (P1)

**Цель**: не терять окончание встречи во время запуска, после сна или разрыва
наблюдения.

**Независимая проверка**: обычное окончание, окончание во время запуска,
повторные сигналы, сон/пробуждение, 10 минут без подтверждения и ручная остановка
дают не больше одного старта и одно завершение связанной записи.

- [X] T014 [P] [US3] Добавить искусственную матрицу запуска и остановки в новый `apps/macos/Shared/Tests/MeetingDetectionRecordingLifecycleTests.swift` без звука и частных данных (FR-017–FR-023)
- [X] T015 [US3] Сохранять одно требование остановки при гонке с `recordingStartInProgress` и исполнять его после выхода из запуска в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-019–FR-020)
- [X] T016 [US3] Связать автоматическую запись с точным приложением и непрерывной встречей, не затрагивая ручную запись, в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-017–FR-018, FR-023)
- [X] T017 [US3] После свежего снимка/пробуждения сверять detector-запись с текущей встречей и использовать существующий секундный цикл для остановки после 10 минут без подтверждения в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-021–FR-022)

---

## Фаза 6 — User Story 4: запись переживает сбой (P1)

**Цель**: до первого звука создать устойчивую личность записи, ограничить потерю
хвоста десятью секундами и классифицировать каждый незавершённый пакет.

**Независимая проверка**: принудительное прерывание на каждой стадии даёт после
запуска готовую, ограниченно пригодную или повреждённую строку без дублей.

- [X] T018 [P] [US4] Добавить проверки раннего `active` manifest, окончательного атомарного перехода и безопасного кода повреждения в `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift` (FR-024, FR-027–FR-029)
- [X] T019 [P] [US4] Добавить проверки закрепления WAV, восстановления заголовка и потери хвоста не более 10 секунд в `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift` (FR-025–FR-026, SC-004)
- [X] T020 [P] [US4] Добавить матрицу повторного восстановления незавершённых папок в новый `apps/macos/Shared/Tests/CaptureRecoveryServiceTests.swift` (FR-027–FR-029)
- [X] T021 [US4] Создавать и атомарно записывать `active` manifest до приёма звука в `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift` и `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift` (FR-024)
- [X] T022 [US4] Закреплять текущий заголовок и данные WAV не реже одного раза в 10 секунд в существующем writer в `apps/macos/RecApp/Sources/Capture/CanonicalRecordingWriter.swift` (FR-025–FR-026)
- [X] T023 [US4] Восстанавливать длину/заголовок WAV, производный файл и окончательный manifest либо ставить безопасный код повреждения в `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift` (FR-027–FR-029)
- [X] T024 [US4] Запускать восстановление при старте приложения и объединять каждый найденный пакет с существующей очередью в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (FR-027–FR-030)

---

## Фаза 7 — User Story 5: неотправленная запись в общем списке (P1)

**Цель**: показывать запись с начала сохранения, автоматически повторять
отправку и дать действие `Отправить` в той же строке.

**Независимая проверка**: сеть, перезапуск, временная/постоянная ошибка, ручная
отправка, повреждение и успешное согласование не скрывают строку и не создают
дублей.

- [X] T025 [P] [US5] Расширить проверки очереди для раннего `saving`, обновления тем же `id`, автоматического повтора, `Отправить` и повреждения в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` (FR-030–FR-034)
- [X] T026 [P] [US5] Добавить проверки ограниченной модели локальной строки, разрешённых сообщений и объединения с серверной строкой в `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift` (FR-030–FR-036, FR-041)
- [X] T027 [US5] Добавить в существующую очередь создание/обновление элемента `saving` и сохранить `retry(itemId:)` единственным ручным путём в `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` (FR-030–FR-034)
- [X] T028 [US5] Создавать `saving` при начале остановки, обновлять тот же элемент после manifest и передавать действие `Отправить` в `apps/macos/RecApp/App/TwoBrainRecApp.swift` (FR-030–FR-034)
- [X] T029 [US5] Передавать ограниченные локальные строки и принимать только допустимые действия по `id` через существующий мост в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` (FR-030–FR-035, FR-041)
- [X] T030 [US5] Вставлять локальные состояния и действие `Отправить` в существующий общий список, объединяя строку по серверной личности, в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-031–FR-035)
- [X] T031 [US5] Удалить отдельные панели локальной сохранности после переноса состояний и сохранить местный ряд только для оболочки без кабинета в `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` и обновить `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` (FR-036, SC-008)

---

## Фаза 8 — User Story 6: удалить серверную зависимость (P2)

**Цель**: сначала доказать независимость нового клиента, затем удалить только
серверное разрешение автозапуска, сохранив реестр и его защиту.

**Независимая проверка**: новый клиент одинаково проходит локальную матрицу со
старым ответом, ответом без поля и без сети; сервер больше не публикует поле, но
реестр, исключения, ETag и вход работают.

- [X] T032 [P] [US6] Добавить клиентские проверки документов с `assistedAutoStartPolicy`, без него и без сети в `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` и `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` (FR-037, SC-009)
- [X] T033 [US6] Удалить клиентские модели, проверку и подтверждение серверного разрешения из `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`, `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift` (FR-016, FR-037)
- [X] T034 [P] [US6] Переписать серверные договорные проверки на отсутствие поля при сохранении реестра, исключений и ETag в `apps/server/tests/contract/test_meeting_detection_api_contract.py`, `apps/server/tests/contract/test_openapi_contract_drift.py` и `apps/server/tests/unit/test_config_validation.py` (FR-038–FR-039)
- [X] T035 [US6] Удалить поле, построитель и настройки серверного разрешения из `apps/server/src/twobrain_rec_server/api/meeting_detection.py`, `apps/server/src/twobrain_rec_server/api/schemas.py` и `apps/server/src/twobrain_rec_server/config.py` (FR-038–FR-039)
- [X] T036 [US6] Удалить связанные переменные из `infra/docker-compose.yml` и `infra/env/rec.production.env.example`, а поле из `specs/012-server-ingest-foundation/contracts/openapi.yaml`, не меняя остальные договоры реестра (FR-038–FR-039)

---

## Фаза 9 — Сквозная проверка и завершение

- [X] T037 [P] Выполнить точечные Swift-проверки политики, отсчёта, остановки, writer, восстановления, очереди и WebView по командам из `specs/214-reliable-auto-recording/quickstart.md` и записать только безопасные результаты в `specs/214-reliable-auto-recording/quickstart.md` (SC-001–SC-008)
- [X] T038 Выполнить точечные pytest/OpenAPI/JavaScript-проверки серверной очистки по `specs/214-reliable-auto-recording/quickstart.md` и записать безопасные результаты в `specs/214-reliable-auto-recording/quickstart.md` (SC-009–SC-010)
- [X] T039 Пройти искусственный полный путь чистая установка → встреча → остановка → сбой/восстановление → отправка → согласование по `specs/214-reliable-auto-recording/quickstart.md` без частного содержимого (SC-001–SC-010)
- [X] T040 Выполнить проверку на переусложнение через `@ponytail-review`, устранить необязательные новые слои и сохранить доказательство в `specs/214-reliable-auto-recording/quickstart.md` (FR-042)
- [X] T041 Обновить итоговые пользовательские и совместимые изменения в `CHANGELOG.md`, выполнить согласованный быстрый составной набор без полного CI и записать безопасный итог и причину отклонения от `infra/scripts/ci-local.sh --fast` в `specs/214-reliable-auto-recording/quickstart.md` (SC-010)

Один `infra/scripts/ci-local.sh --full` выполняется позже на точном кандидате
релиза. Выпуск, нотариальное подтверждение и развёртывание не входят в эту
реализацию без отдельного разрешения.

---

## Зависимости

```text
Фаза 1 -> US1
Фаза 2 -> US4 и US5
US1 -> US2 -> US3
US3 -> US4 -> US5
US1 -> US6
US1 + US2 + US3 + US4 + US5 + US6 -> Фаза 9
```

- US1 отдельно доказывает локальный источник правды и работу без сети.
- US2 зависит от правил US1, но не от хранения и отправки.
- US3 зависит от единственного решения US2 и не зависит от серверной очистки.
- US4 использует завершение US3 и общее состояние `saving`.
- US5 использует устойчивый пакет US4 и существующую очередь.
- Серверную часть US6 выпускать можно только после совместимого клиентского
  шага; в коде ветки порядок всё равно подтверждается отдельными проверками.

## Возможная параллельная работа

- После T003 проверки T004–T006 можно писать параллельно в разных файлах.
- В US4 задачи T018–T020 можно писать параллельно до реализации T021–T024.
- В US5 задачи T025 и T026 можно писать параллельно до реализации очереди и
  моста.
- Клиентскую совместимость T032 и серверные проверки T034 можно готовить
  параллельно; удаление T035–T036 выполняется только после обеих проверок.
- T037 и T038 выполняются последовательно, потому что записывают доказательства
  в один файл.

## Стратегия поставки

1. Сначала клиентская часть US1–US5: локальные настройки, надёжная остановка,
   восстановление и общий список.
2. Доказать независимость клиента от старого серверного поля.
3. Затем выполнить серверную очистку US6.
4. После точечных проверок пройти полный искусственный путь и быстрые ворота.
5. Отдельный выпуск: новый клиент первым; серверная очистка после условия
   минимальной поддерживаемой версии.

**Первый минимальный полезный разрез**: US1 + US2 + US3. Он делает выбор и
остановку предсказуемыми, но не считается полным решением до US4–US5, потому что
надёжность записи включает сохранение, восстановление и отправку.
