# Data Model: MediaScribe polling recovery

Миграция не требуется. Используются существующие поля `ProcessingWorkflow`:

- `status` — lifecycle state, не смешивать с provider status;
- `retry_class` — `retryable`, `unknown_outcome`, `terminal` или `none`;
- `retry_count` — число плановых recovery checks;
- `next_attempt_at` и `next_attempt_source` — следующий durable check;
- `deadline_at` — watchdog boundary;
- `last_reason_code` — bounded machine reason для UI/API.

В `RetrySchedule` добавляется только in-memory `stop_reason`, чтобы вызывающий
код различал max-attempt stop и deadline stop без изменения БД.
