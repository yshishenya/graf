# Feature Specification: Повторная обработка результата без распознанной речи

**Feature Branch**: `204-terminal-no-speech-recovery`
**Created**: 2026-08-25
**Status**: Ready for implementation

## User Scenarios & Testing

### User Story 1 - Пользователь может безопасно повторить terminal no-speech (Priority: P1)

Пользователь открывает запись, для которой MediaScribe завершил обработку, но
не нашёл распознаваемую речь. GRAF честно показывает причину и предлагает
начать новую бизнес-попытку. Нажатие кнопки создаёт ровно одну новую попытку,
не изменяя старый результат и не создавая дубликат автоматически.

**Independent Test**: На записи с импортированным `no_recognizable_speech`
проверить статус, POST новой попытки, новый ordinal/workflow и отсутствие
изменений старого result/job.

### User Story 2 - Новая попытка сразу отображается как активная

После принятия новой попытки пользователь видит текущую обработку, а старый
no-speech result не перекрывает её статус. При повторной загрузке страницы
отображаются тот же workflow и понятное состояние ожидания.

**Independent Test**: После создания новой попытки получить status API до
завершения worker и убедиться, что состояние active, `attempt_in_flight=true`,
а `manual_action` не возвращает пользователя к старому terminal состоянию.

### User Story 3 - Ограничения безопасности остаются неизменными (Priority: P1)

Повторная попытка по-прежнему требует той же рабочей области, доступного
исходного артефакта, неизменённой deletion epoch и quota admission. Сбой
Temporal dispatch не оставляет пользователя в тупике.

**Independent Test**: Regression matrix для no-speech, quota, deletion fence,
missing source, in-flight и Temporal dispatch failure.

## Requirements

- **FR-001**: Импортированный result с `status=imported` и
  `failure_reason=no_recognizable_speech`, связанный с текущим workflow и
  revision, MUST считаться безопасным terminal business outcome для явного
  действия пользователя «Начать обработку заново».
- **FR-002**: Admission новой попытки MUST сохранять существующие проверки
  tenant, source fingerprint, deletion epoch, quota и active-attempt fence.
- **FR-003**: После создания новой попытки старый result MUST NOT переводить
  status projection обратно в `failed_terminal`, если текущий workflow уже
  активен и result относится к предыдущей попытке.
- **FR-004**: Новая попытка MUST получать новый ordinal/workflow identity и
  использовать существующий Temporal dispatch/idempotency flow.
- **FR-005**: Terminal outcomes, отличные от `no_recognizable_speech`, MUST
  сохранить текущую политику admission и понятный user-facing response.
- **FR-006**: Regression coverage MUST включать API/store projection и
  production-safe metadata assertions; raw audio, transcript, provider payload
  и credentials не должны появляться в evidence.

## Edge Cases

- Повторный клик во время активной новой попытки возвращает idempotent
  `already_in_flight`, а не создаёт третью попытку.
- Старый no-speech result остаётся доступным как исторический terminal artifact,
  но не является текущим статусом во время новой попытки.
- При удалении встречи, изменении revision или нехватке quota новая попытка
  отклоняется без изменения старых артефактов.
- Если Temporal недоступен после admission, существующий компенсационный путь
  переводит новую попытку в terminal infrastructure state, доступный для
  повторного явного запуска после восстановления.

## Success Criteria

- **SC-001**: На 100% проверенных no-speech записей кнопка приводит к принятию
  новой попытки или к объяснимому, проверяемому ограничению; silent dead-end
  отсутствует.
- **SC-002**: Один пользовательский клик создаёт не более одного нового
  workflow и provider job для business attempt.
- **SC-003**: До завершения новой попытки status API и UI показывают активное
  состояние, а не старый terminal result.
- **SC-004**: Все существующие tenant, deletion, source, quota и idempotency
  regression tests продолжают проходить.
- **SC-005**: Production smoke на существующей записи подтверждает полный
  путь: terminal no-speech → явная новая попытка → active/recovered outcome →
  честный финальный статус без дубликатов.

## Assumptions

- `no_recognizable_speech` — подтверждённый business outcome MediaScribe, а не
  временная ошибка провайдера.
- Новый upload/job создаётся только после явного действия пользователя;
  Temporal и существующие v1 idempotency primitives переиспользуются.
- Production deployment и smoke выполняются только после прохождения exact-SHA
  validation и отдельного release approval.

## Out of Scope

- Изменение MediaScribe, его моделей или API-контракта.
- Автоматическое повторение no-speech без действия пользователя.
- Новый retry service, webhook или отдельная UI-подсистема.
- Редизайн остальных processing states.
