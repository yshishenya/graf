# Research: MediaScribe polling recovery

## Проверенные факты

- `processing/submit.py` уже вызывает `poll_job` и считает pending provider
  statuses recoverable.
- `workflows/processing_workflow.py` уже выполняет один provider check на
  activity и ждёт через durable Temporal timer.
- `processing/recovery.py` одновременно ограничивает scheduler по
  `processing_recovery_max_attempts` и provider polling. При production settings
  `12` это завершает обычный polling примерно через минуту.
- `workflows/worker.py` трактует любой `RetrySchedule` без следующей даты как
  `processing_retry_deadline_exceeded`, не различая лимит попыток и deadline.
- MediaScribe v1 client уже сохраняет `status`, `retry_after_seconds` и
  `next_retry_at` из job status response.
- Same-job recovery уже использует внешний job id или idempotency key и не
  должен повторять multipart upload.
- Deadline workflow создавался через `DEFAULT_DEADLINE`, а не через
  `processing_recovery_deadline_seconds`.

## Решение

1. Добавить в scheduler явное основание остановки (`max_attempts_exceeded` или
   `deadline_exceeded`) и параметр, отключающий generic max-attempt limit для
   provider polling.
2. В provider polling использовать deadline как watchdog, не выдавая
   `FAILED_TERMINAL` только потому, что закончился короткий poll budget.
3. Оставить terminal provider `failed`, malformed response и local artifact
   failures terminal; transient HTTP/timeout/pending — recoverable.
4. Сохранить Temporal loop без wall-clock/asyncio.sleep в workflow definition;
   watchdog должен ждать manual signal/update без busy loop.

## Не выбранные варианты

- Повторная multipart-загрузка после неизвестного submit не используется:
  это может создать дубликат.
- Изменение MediaScribe API не требуется: status/result endpoints уже есть.
- Увеличение production `processing_recovery_max_attempts` не решает смешение
  семантик и оставляет ложную terminal failure.
