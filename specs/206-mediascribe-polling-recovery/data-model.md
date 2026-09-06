# Data Model: MediaScribe polling recovery

Новые сущности и lifecycle-поля не требуются. Используются существующие поля
`ProcessingWorkflow`:

- `status` — lifecycle state, не смешивать с provider status;
- `retry_class` — `retryable`, `unknown_outcome`, `terminal` или `none`;
- `retry_count` — число плановых recovery checks;
- `next_attempt_at` и `next_attempt_source` — следующий durable check;
- `deadline_at` — watchdog boundary;
- `last_reason_code` — bounded machine reason для UI/API.

В `RetrySchedule` добавляется только in-memory `stop_reason`, чтобы вызывающий
код различал max-attempt stop и deadline stop без изменения БД.

Для manual-upload canonical gate используются существующие сущности:

- `PlaybackNormalizationJob.state` — `queued/running/publishing/retry_wait`
  означает внутреннее ожидание; `ready` требует exact
  `canonical_track_artifact_id`; `terminal/cancelled` запрещает provider egress;
- `TrackArtifact` canonical M4A — единственный manual-upload provider source;
  при `archive_audio=true` это также playback source, при `false` — transient и
  скрытый от playback/storage quota;
- `ProcessingWorkflow` — business-attempt и Temporal-execution lineage;
  создаётся сразу после accepted commit и сохраняет transient lifecycle,
  processing quota reservation, deterministic workflow id и manual command
  generation. Replacement Temporal execution не означает новую provider
  operation;
- `MediaScribeJob` — local pre-egress row может существовать до POST, но не
  обходит gate; только `external_job_id` либо explicit same-key unknown-outcome
  reconciliation подтверждает provider submission. Canonical artifact identity,
  SHA, size, profile, validation, request fingerprint и idempotency key входят в
  неизменный provider-operation contract. Один provider job может пережить
  несколько Temporal executions и несколько exact same-key HTTP attempts;
- finalized `UploadSession.archive_audio` — revision-scoped policy source;
  любой конфликтующий `false` трактуется fail-closed как no-archive, отсутствие
  session сохраняет legacy archival behavior;
- `TemporaryUploadObject`, `ProcessingWorkflow.transient_*` и существующий
  `PurgeJournal` — custody/purge contract. Purge intent/fences фиксируются до
  object deletion; earliest hard deadline среди revision attempts сохраняется.

Audit добавляет allowlisted `normalization_mode=tolerant` только как policy fact.
Persisted artifact derivation остаётся существующим `single_source_transcode`,
a `recovered_source=false`, пока фактическое recovery не доказано. Новое enum
значение не требуется.

Миграция `0083_result_workflow_lineage` не меняет публичную модель данных. Она
консервативно заполняет существующий `ProcessingResult.processing_workflow_id`
только через доказанную цепочку result → MediaScribe job → workflow и не
угадывает конфликтующую lineage. Следующая миграция `0084_processing_recovery`
идёт строго после уже применяемого production head `0083_result_workflow_lineage`
и добавляет только индексы/внешний ключ для bounded transient purge и recovery;
второй migration head не создаётся. Если реализация потребует
новый public status, artifact role или retention entity, работа останавливается
и plan пересматривается.
