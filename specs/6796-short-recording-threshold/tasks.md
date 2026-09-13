# Tasks: Единый порог сохранения

Feature: 6796. Lane: high-risk-feature. Source: [spec.md](spec.md), [plan.md](plan.md).

## Phase 1: Setup and foundation

- [X] T001 Проверить согласованность требований и независимый review в `specs/6796-short-recording-threshold/checklists/safety.md` и `review.md`; привязать GitHub issues до кода. (Issue #6944)

## Phase 2: US1 — единое штатное завершение

Independent test: точные границы обеих штатных причин; сохранность аварийных фрагментов.

- [X] T002 [US1] Добавить синтетические проверки границы и причин остановки в `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`, затем durable признак и предикат в `apps/macos/Shared/Sources/Models/AudioModelCore.swift`, фиксацию в `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`. FR-001–004/008. (Issue #6945)
- [X] T003 [US1] Подключить правило в общем Stop `apps/macos/RecApp/App/TwoBrainRecApp.swift`, показать нейтральное сообщение в `apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift`; проверить свойства и время жизни в `apps/macos/Shared/Tests/ShortRecordingNoticeTests.swift`. FR-002/007/009. (Issue #6946)

## Phase 3: US2 — очистка и восстановление

Independent test: crash после маркера, повторный scanner, cleanup failure, старые записи и symlink не приводят к неверному удалению/отправке.

- [X] T004 [US2] Добавить проверки в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` и защиту scan/enqueue/upload плюс повторяемую очистку в `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`; проверить `CaptureRecoveryServiceTests.swift` и совместимость. FR-004–006/008/009. (Issue #6947)

## Phase 4: Validation and closeout

- [X] T005 Проверить локальную матрицу `specs/6796-short-recording-threshold/quickstart.md`, провести code review/converge, записать результаты в `validation.md` и фрагмент `changes/unreleased/F6796.yaml`. (Issue #6948)
- [X] T006 После разрешённого коммита проверить штатный GRAF Dev по `specs/6796-short-recording-threshold/quickstart.md`, GitHub governance-fast на exact PR SHA; сверить tracker и evidence в `validation.md`. Без подтверждения результата не закрывать feature issues. (Issue #6949)

## Dependencies and implementation strategy

T001 → T002 → T004 → T003 → T005 → T006. Ветка US1/US2 поставляется вместе: UI не должен отбрасывать запись до durable защиты. [P] задач нет из-за общей границы. Независимый review может выполняться параллельно чтению test helpers; runtime edits после PASS.

Перед отправкой: processDueItems явно исключает .saving и помеченные manifest; upload повторно проверяет текущее состояние до перехода/создания server ID. Очистка допускает отсутствие строки или только pristine .saving: совпадают sessionId/directoryId/пути, attemptCount=0, serverCreationAttempted=false, отсутствуют meeting/upload/revision/server truth IDs и lifecycle/deletion конфликт. Неоднозначность запрещает purge и upload, оставляет безопасную диагностику/повтор. Проверки включают устаревший saving snapshot и частично начатую отправку.

## GitHub owners

- T001: https://github.com/yshishenya/graf/issues/6944
- T002: https://github.com/yshishenya/graf/issues/6945
- T003: https://github.com/yshishenya/graf/issues/6946
- T004: https://github.com/yshishenya/graf/issues/6947
- T005: https://github.com/yshishenya/graf/issues/6948
- T006: https://github.com/yshishenya/graf/issues/6949

## Phase 5: Штатный стенд

- [X] T007 Перенести проверенное исправление MinIO pull из F6793 только в `scripts/dev-harness.py`, `tests/governance/test_graf_local_adapter.py`, `infra/dev/README.md`; сохранить fail-closed сборку, проверить pytest, независимый review и повторный CI. Зависимость T006 → сначала T007; product scope не расширяется. (Issue #6951)

T007: https://github.com/yshishenya/graf/issues/6951

T006: установленная матрица завершена: ручные normal Stop по обе стороны
порога, меню, начало аудио, выключенный микрофон, уведомление/новый Start,
светлая/тёмная панели, настоящий автоматический Start/Stop и перезапуск
после discard. Каталог, строка очереди и серверная встреча отсутствуют.
Независимый итоговый review Approved. VoiceOver: code-reviewed post и
тестируемая панель; доставка/озвучивание native-unverified, ручная процедура
отменена пользователем. Это явное исключение, не PASS. Подробности validation.md.
Текущий CI PASS; после финального документационного коммита обязательны
новые checks на точном SHA перед слиянием и закрытием issues.

## Phase 6: Диагностика блокера приёмки

- [X] T008 Зафиксировать первую техническую аномалию источника в `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift` и разрыв в `RecordingAudioTimeline.swift`, подключить существующий AppLog через `V5LocalRecordingWriter.swift` и `App/TwoBrainRecApp.swift`, проверить сохранение префикса в `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`, выполнить профильные проверки/review/CI и получить метаданные штатного GRAF Dev для классификации `render_reference_missing`; записать результат в `validation.md`. Сопоставить raw/output PTS, duration/outputDuration и интервалы callbacks; проверить синтетические CoreMedia метки в `apps/macos/Shared/Tests/SystemAudioSampleExtractorTests.swift`. До изменения механизма захвата установить причину. Зависит от T007, предшествует завершению T006. (Issue #6954)

T008: https://github.com/yshishenya/graf/issues/6954


T008: классификация подтверждена на installed5c7350e84 и независимым review.
Входной разрыв PTS не создан преобразованием; физическая потеря PCM или
изменение меток не различены. Первопричина вынесена в открытую #6958
(Feature177, T000 triage); защита не ослаблена. Обязательные сценарии T006 завершены отдельно, см. validation.md;
ссылка на прежний дефект не подменяла их приёмку.


## Phase 7: Convergence — замечания GitHub review

- [X] T009 Исправить точную границу FR-003 в `AudioModelCore.swift` по каноническим48k кадрам без округления16k/AAC padding; проверить реальный writer/converter1_439_999/1_440_000/1_440_001 для обоих штатныхStop, durable marker, начало и неизвестную длительность в `LocalRecordingWriterSystemAudioTests.swift` (partial, HIGH). (Issue #6976)
- [X] T010 Запретить очистку FR-006 при ссылке другой строки очереди на любой удаляемый artifact path в `DesktopUploadQueueService.swift`; проверить все поля путей/нормализацию/соседнийprefix, сохранность байтов/обеихстрок/маркера и повторныйscan в `DesktopUploadQueueV5Tests.swift` (partial, HIGH). (Issue #6977)

T009/T010 завершены и приняты независимым review. Новый runtime47b6d
прошёл короткий/длинный Stop и настоящий restart; T006 завершена.
Предыдущая матрица5c применяется только к неизменённым маршрутам/presenter.
Перед merge обязательны checks финального документационного SHA.

T009: https://github.com/yshishenya/graf/issues/6976

T010: https://github.com/yshishenya/graf/issues/6977
