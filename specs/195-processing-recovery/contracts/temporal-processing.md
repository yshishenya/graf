# Contract: Temporal processing workflow

**Feature**: `195-processing-recovery`
**Статус**: recommended orchestration design; требует implementation review

## Workflow identity

Один workflow на активную GRAF `processing_attempt`, например:

```text
graf-processing/{workspace_id}/{media_revision_id}/{attempt_id}
```

ID не показывается пользователю. Повторный старт с тем же identity должен
возвращать/подхватывать существующий run, а не запускать новый provider job.

Input — только bounded identifiers и immutable request metadata:

```text
workspace_id, meeting_id, media_revision_id, processing_attempt_id,
source_fingerprint, deletion_epoch, request_mode, artifact policy
```

Не передавать в workflow input audio bytes, transcript, API key, password,
signed URLs или provider raw JSON.

## Deterministic state machine

```text
START
  -> load_attempt
  -> submit_or_reconcile
  -> poll_status/result
       -> ready -> import_result -> project_artifacts -> summary_projection -> DONE
       -> retryable -> workflow.sleep(next_attempt_at) -> poll_status/result
       -> terminal -> mark_terminal -> DONE
       -> unknown outcome -> reconcile_same_key -> ...
```

`workflow.sleep()` — единственный timer для processing retry. В workflow нельзя
использовать `asyncio.sleep`, current wall clock, random или network I/O.

## Activities

Activities должны быть маленькими, idempotent и иметь bounded timeout:

1. `load_processing_state` — читать Postgres; не возвращать content;
2. `submit_or_reconcile_provider_job` — POST same body/key при unknown outcome,
   сохранять headers/body mapping;
3. `get_provider_status` — GET job; сохранять status/queue/hints;
4. `get_provider_result` — GET result; 409 not-ready не считать исключением
   infrastructure retry;
5. `import_provider_result` — validate, hash, upsert result/segments,
   provenance, overlaps; проверить deletion epoch;
6. `project_processing_state` — обновить GRAF user projection и audit metadata;
7. `get_provider_summary`/GRAF summary stage — независимый summary path;
8. `request_provider_deletion` и `poll_provider_deletion` — durable receipt;
9. `emit_processing_metric` — allowlisted aggregate only.

Большие payloads должны проходить через owner-controlled object storage с
bounded reference или import activity; не возвращать их через Temporal result.

## Retry policy

Temporal SDK RetryPolicy — только для transient transport failures у конкретной
Activity, с bounded `schedule_to_close`, `start_to_close`, `heartbeat` и
maximum attempts. Provider business retry живёт в state machine:

- `result_not_ready` → state `waiting_retry`, `workflow.sleep` по hint;
- provider `retryable=true` → bounded schedule;
- `retryable=false`, invalid payload, idempotency conflict → terminal;
- POST timeout/502/504 → `unknown_outcome`, сначала reconciliation same key;
- exhausted deadline → explicit terminal/manual resolution, не бесконечный loop.

Activity должна возвращать typed safe outcome либо `ApplicationError` с
`non_retryable=True` для terminal business state. Не полагаться на общий retry
policy, который повторит multipart upload с новым key.

## Manual «Проверить обработку»

Рекомендуется Temporal Update `request_manual_check`, потому что UI получает
serialized acceptance/rejection и может передать client command id. Update:

1. validate access/attempt/deletion epoch на GRAF API до обращения к workflow;
2. внутри workflow атомарно проверить `schedule_generation` и
   `attempt_in_flight`;
3. если уже in-flight — вернуть `already_in_progress` с текущим state;
4. иначе увеличить generation, очистить timer и вызвать ровно одну
   `get_provider_status`/`get_provider_result` для того же job;
5. вернуть safe projection; новый `next_attempt_at` задаётся только результатом.

Postgres command row/unique fence остаётся обязательным: Update delivery и
HTTP retry сами по себе могут быть повторены.

Signal допустим как backward-compatible fallback только если текущий SDK/worker
не поддерживает Update. В таком режиме HTTP должен отвечать accepted и читать
projection после commit; нельзя обещать синхронный provider result.

## Cancellation, deletion и restart

- workflow cancellation не равна provider deletion;
- Delete command ставит GRAF deletion epoch и state `deleting`, затем ждёт
  provider receipt;
- каждая write Activity проверяет epoch/fence перед commit;
- worker crash после submit → workflow resumes at reconcile, same key/job;
- crash после import → result hash/version делает import idempotent;
- crash во время timer → Temporal возобновляет durable sleep;
- crash после manual command → generation/in-flight fence подавляет duplicate.

## Versioning

Изменения workflow shape совместимы через `workflow.patched`/versioning и
replay tests на snapshots старого и нового run. Нельзя просто переименовать
Activity или убрать старую ветку, пока старые histories ещё живы.

Переход со старого one-Activity workflow:

- новые attempts стартуют на новом workflow type/version;
- running legacy runs либо завершаются через compatibility adapter, либо
  мигрируются explicit patch point;
- миграция не создаёт новую provider job автоматически;
- любой manual action сначала ищет current DB attempt/job.

## Task queue и масштабирование

Начальная рекомендация — общий processing task queue с:

- admission по workspace quota и MediaScribe active-job limits;
- bounded concurrency, heartbeat и metrics;
- отдельной priority только если измерения показывают starvation;
- fairness dashboard по bounded workspace bucket, без raw tenant identifiers.

Не создавать queue per tenant до измеренного доказательства необходимости:
это усложняет deployment, worker routing и migration.

## Temporal validation

До rollout обязательны:

- time-skipping test durable sleep;
- replay test старой history после workflow change;
- Update/Signal duplicate and concurrent command test;
- heartbeat/cancellation test для long activity;
- failure injection после submit, status, result, import и deletion;
- payload-size/no-plaintext-history contract;
- worker restart test с сохранённым Postgres projection;
- test, что Temporal retry не меняет idempotency key.
