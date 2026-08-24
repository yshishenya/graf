# Data model: processing attempt, artifacts и recovery

**Feature**: `195-processing-recovery`
**Статус**: design contract; это не миграция и не инструкция выполнить DDL

## Принцип владения состоянием

PostgreSQL хранит user-facing processing truth и fences. Temporal хранит
исполнение workflow и timer history. MediaScribe хранит provider job/result.
Ни один из них не должен маскироваться под другой:

```text
Media revision (immutable source)
        |
        +--> Processing attempt (GRAF business attempt)
                 |
                 +--> Provider job (at most one per attempt)
                 +--> Artifact states (transcript/diarization/summary/...)
                 +--> Retry schedule / command fence
```

Все сущности workspace-scoped, привязаны к media revision и защищены текущими
RLS/authorization/deletion-epoch правилами.

## Сущности

### Media revision

Уже существующая immutable запись источника. Для этой feature используется как
граница содержания и удаления:

| Поле | Назначение |
|---|---|
| `id`, `workspace_id`, `meeting_id` | tenant и объект доступа |
| canonical track references | single/dual-track выбор upload |
| `source_fingerprint` | сравнение запроса при reconciliation |
| `deletion_epoch` | не дать позднему result воскресить удалённую встречу |
| source status | доступность исходного объекта для новой попытки |

Новая бизнес-попытка не меняет media revision. Если исходный revision
недоступен, UI не предлагает безопасный automatic retry.

### Processing attempt

Логическая попытка пользователя обработать один revision. Текущий
`ProcessingWorkflow` можно расширить или использовать как эту запись; отдельная
таблица нужна только если текущая история не позволяет хранить завершённые
попытки без нарушения active-workflow uniqueness.

Обязательные свойства:

| Поле | Тип/ограничение | Смысл |
|---|---|---|
| `id` | UUID | публично не показывается как provider id |
| `media_revision_id` | FK | неизменный источник |
| `attempt_ordinal` | integer | 1, 2, ... в рамках revision |
| `trigger` | enum | `initial`, `automatic_retry`, `manual_check`, `explicit_new_attempt`, `reconciliation`, `recovery` |
| `state` | enum | `created`, `submitting`, `submitted`, `waiting_retry`, `polling`, `importing`, `completed`, `failed_terminal`, `blocked_unknown`, `canceled` |
| `stage` | enum | `submit`, `reconcile`, `status`, `result`, `import`, `summary`, `deletion` |
| `retry_class` | enum/null | `retryable`, `unknown_outcome`, `terminal`, `none` |
| `retry_count` | integer | automatic schedule count, не число HTTP calls |
| `deadline_at` | timestamptz | абсолютный верхний предел обработки |
| `next_attempt_at` | timestamptz/null | durable server-owned next operation |
| `next_attempt_source` | enum/null | `provider_retry_after`, `provider_next_retry_at`, `server_fallback`, `manual_override` |
| `manual_command_version` | integer | fence для двух вкладок/двойного клика |
| `last_safe_code` | string/null | allowlisted machine reason |
| `last_request_id` | string/null | provider correlation, metadata-only |
| `deletion_epoch_at_start` | integer/null | late-write fence |
| `started_at`, `completed_at`, `updated_at` | timestamptz | lifecycle |

Invariant: для одного `workspace_id + media_revision_id` может быть только одна
активная attempt. Завершённые terminal attempts остаются для диагностики, но не
будят workflow и не считаются текущей user-facing truth.

### Provider job

Текущий `MediaScribeJob` — durable linkage. Сохраняются:

| Поле | Назначение |
|---|---|
| `processing_attempt_id`/workflow FK | связь с одной бизнес-попыткой |
| `external_job_id` | server-side opaque id; не показывать в обычном UI |
| `idempotency_key` | повтор identical POST и reconciliation |
| `request_mode` | `single` или `dual` |
| `diarize`, `summarize`, speaker options | exact request fingerprint |
| `source_fingerprint` и safe request fingerprint | доказать same-body replay |
| `provider_status` | raw known/unknown value |
| `provider_queue_state` | отдельная raw queue axis |
| `provider_attempt`, `provider_max_attempts` | provider diagnostics |
| `provider_next_retry_at`, `retry_after_seconds` | hint, не локальная истина |
| `result_available`, `summary_state` | provider projection |
| `last_error_code`, `last_error_origin` | allowlisted machine values |
| `last_request_id`, `api_contract_version`, `provider_build` | bounded diagnostics |
| `submitted_at`, `last_polled_at`, `ready_at`, `failed_at` | timings |

Unique constraints должны гарантировать:

- не более одного provider job на `processing_attempt_id`;
- `workspace_id + idempotency_key` уникален для active/tombstoned retention;
- `workspace_id + external_job_id` уникален;
- новый key возможен только для `explicit_new_attempt` после terminal evidence.

Raw provider values допускаются в server-side diagnostic columns/JSON только с
bounded size и redaction. Неизвестный будущий status не должен падать на enum
validation или превращаться в terminal failure.

### Processing artifact

Артефакт — не одно boolean поле результата. Минимальный набор:

| Artifact | Состояния | Граница готовности |
|---|---|---|
| `transcript` | `not_requested`, `processing`, `available`, `unavailable`, `failed` | есть непустые сегменты и подтверждена diarization той же attempt для UI |
| `diarization` | `not_requested`, `processing`, `available`, `unavailable`, `failed` | импортированы валидные speaker turns для того же result revision |
| `summary` | `not_requested`, `queued`, `running`, `available`, `failed`, `unavailable` | собственная GRAF/provider summary policy |
| `playback` | `processing`, `available`, `unavailable`, `failed` | GRAF playback gate |
| `export` | `not_ready`, `available`, `failed` | политика конкретного export |
| `deletion` | `not_requested`, `requested`, `pending_provider`, `confirmed`, `failed` | provider receipt + GRAF fence |

`ProcessingResult` сохраняет `result_version`, hash, language, counts,
`transcript_status`, `diarization_status`, `summary_status`, failure metadata и
import timestamp. `TranscriptSegment` и `DiarizationSegment` остаются
revision-pinned. В result import дополнительно нужно предусмотреть (в текущих
таблицах или bounded JSON artifact):

- source role и original role;
- overlap intervals;
- acoustic speaker turns;
- provenance/model/build information;
- provider download capabilities, но не provider URL как пользовательский
  абсолютный egress.

Необязательные provider fields могут быть `null`/`unknown`; их отсутствие не
ломает import.

### Retry schedule

Можно хранить в `ProcessingWorkflow`/attempt, не создавая отдельный retry
service:

```text
next_attempt_at       timestamptz nullable
retry_class           retryable | unknown_outcome | terminal | none
retry_count           non-negative int
schedule_source       provider_retry_after | provider_next_retry_at |
                       server_fallback | manual_override
schedule_generation   monotonically increasing int
manual_claimed_at     timestamptz nullable
manual_claimed_by     enum user | automatic | reconciliation
```

`schedule_generation` участвует в workflow sleep wake-up: проснувшийся timer
сначала атомарно сравнивает generation и state. Старый timer при несовпадении
становится no-op.

Правила расчёта:

1. валидный `Retry-After` или provider `next_retry_at` имеет приоритет;
2. применяются minimum/maximum bounds, deadline и bounded jitter;
3. плохой/отсутствующий hint использует server fallback и UI не показывает
   ложное точное обещание;
4. ручной check увеличивает generation, очищает pending `next_attempt_at` и
   ставит `manual_claimed_by=user`; новый schedule создаётся только ответом
   операции;
5. local/browser countdown пересчитывает `max(0, next_attempt_at - server_now)`
   после refresh, а не накапливает локальный drift.

### Deletion receipt

Текущий deletion workflow переиспользуется. Для MediaScribe сохраняются:

- provider job reference server-side;
- GRAF deletion request id и deletion epoch;
- provider receipt id/state/status URL;
- `requested_at`, `last_checked_at`, `confirmed_at`;
- `cancelling` vs `completed` и safe error code.

Поздний import проверяет deletion epoch/row fence до каждой записи. После
`completed` provider receipt обычные status/result/download URL не возвращаются
в user projection.

## User-facing projection

`ProcessingStatusResponse` и `ProcessingReviewState` должны быть additive
проекциями, а не прямым provider DTO:

```json
{
  "state": "waiting_retry",
  "stage": "result",
  "retry_class": "retryable",
  "reason_code": "provider_unavailable",
  "next_attempt_at": "2026-08-23T10:03:00Z",
  "manual_action": "check_now",
  "attempt_in_flight": false,
  "artifacts": {
    "transcript": {"state": "available", "visible": true},
    "diarization": {"state": "available", "visible": true},
    "summary": {"state": "running", "visible": false}
  }
}
```

Это пример формы, а не готовый API. Обязательные UI invariants:

- `transcript.visible=true` только при `transcript=available` и
  `diarization=available` одной attempt;
- `summary=failed/running` не меняет transcript visibility;
- `manual_action=check_now` только для safe same-job retry;
- terminal failure не получает countdown;
- provider job id, idempotency key, signed URL и raw error не попадают в
  projection для обычного пользователя.

## State transition rules

```text
created -> submitting
submitting --202--> submitted -> polling
submitting --unknown POST outcome--> blocked_unknown -> reconcile
polling --409 result_not_ready--> waiting_retry -> polling
polling --ready--> importing -> completed
importing --transcript+diarization--> transcript_visible
completed --summary running/failed--> completed (summary independent)
any active --retryable--> waiting_retry
any active --terminal--> failed_terminal
any active --delete--> deleting -> canceled/confirmed deletion
```

Запрещено:

- `waiting_retry -> submitting` с новым key;
- `blocked_unknown -> submitting` до same-key reconciliation;
- `failed_terminal -> automatic retry`;
- `deleting -> completed` без deletion fence;
- `transcript visible` при неподтверждённой diarization.
