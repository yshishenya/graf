# Tasks: Единый порог сохранения

Feature: 6796. Lane: high-risk-feature. Source: [spec.md](spec.md), [plan.md](plan.md).

## Phase 1: Setup and foundation

- [X] T001 Проверить согласованность требований и независимый review в `specs/6796-short-recording-threshold/checklists/safety.md` и `review.md`; привязать GitHub issues до кода.

## Phase 2: US1 — единое штатное завершение

Independent test: точные границы обеих штатных причин; сохранность аварийных фрагментов.

- [X] T002 [US1] Добавить синтетические проверки границы и причин остановки в `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`, затем durable признак и предикат в `apps/macos/Shared/Sources/Models/AudioModelCore.swift`, фиксацию в `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`. FR-001–004/008.
- [X] T003 [US1] Подключить правило в общем Stop `apps/macos/RecApp/App/TwoBrainRecApp.swift`, показать нейтральное сообщение в `apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift`; проверить свойства и время жизни в `apps/macos/Shared/Tests/ShortRecordingNoticeTests.swift`. FR-002/007/009.

## Phase 3: US2 — очистка и восстановление

Independent test: crash после маркера, повторный scanner, cleanup failure, старые записи и symlink не приводят к неверному удалению/отправке.

- [X] T004 [US2] Добавить проверки в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` и защиту scan/enqueue/upload плюс повторяемую очистку в `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`; проверить `CaptureRecoveryServiceTests.swift` и совместимость. FR-004–006/008/009.

## Phase 4: Validation and closeout

- [X] T005 Проверить локальную матрицу `specs/6796-short-recording-threshold/quickstart.md`, провести code review/converge, записать результаты в `validation.md` и фрагмент `changes/unreleased/F6796.yaml`.
- [ ] T006 После разрешённого коммита проверить штатный GRAF Dev по `specs/6796-short-recording-threshold/quickstart.md`, GitHub governance-fast на exact PR SHA; сверить tracker и evidence в `validation.md`. Без подтверждения результата не закрывать feature issues.

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

- [X] T007 Перенести проверенное исправление MinIO pull из F6793 только в `scripts/dev-harness.py`, `tests/governance/test_graf_local_adapter.py`, `infra/dev/README.md`; сохранить fail-closed сборку, проверить pytest, независимый review и повторный CI. Зависимость T006 → сначала T007; product scope не расширяется.

T007: https://github.com/yshishenya/graf/issues/6951

T006: exact-SHA CI и установка выполнены для 8f68e8697497; штатная native приёмка блокируется `render_reference_missing` в существующем коде захвата. Подробности и следующий диагностический шаг — `validation.md`. Задача не закрыта.

## Phase 6: Диагностика блокера приёмки

- [ ] T008 Зафиксировать первую техническую аномалию источника в `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift` и разрыв в `RecordingAudioTimeline.swift`, подключить существующий AppLog через `V5LocalRecordingWriter.swift` и `App/TwoBrainRecApp.swift`, проверить сохранение префикса в `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`, выполнить профильные проверки/review/CI и получить метаданные штатного GRAF Dev для классификации `render_reference_missing`; записать результат в `validation.md`. До изменения механизма захвата установить причину. Зависит от T007, предшествует завершению T006.

T008: https://github.com/yshishenya/graf/issues/6954
