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
- Same-job recovery использует внешний job id или durable idempotency key.
  Неизвестный POST восстанавливается exact replay с тем же ключом; после
  получения external job id повторный multipart запрещён.
- Deadline workflow создавался через `DEFAULT_DEADLINE`, а не через
  `processing_recovery_deadline_seconds`.
- Manual upload dispatch запускает normalization и processing независимо;
  processing source для `manual_upload` выбирает original `media`.
- Single-source normalization выполняет полный strict source decode перед
  transcode, хотя tolerant FFmpeg-команда уже существует.
- MediaScribe v1 принимает M4A; отдельный persistent WAV не требуется.
- `archive_audio=false` сейчас не создаёт normalization job; существующий purge
  привязан к processing workflow и имеет publication/transition/crash race,
  поэтому не может быть переиспользован без fencing и journal-first semantics.
- `invalid_audio_payload/input_audio` сохраняется как `processed`, поэтому UI
  продолжает polling из-за отсутствующего transcript.
- MediaScribe client принимает arbitrary codec label как multipart MIME; при
  canonical submit это дало бы неверный Content-Type и `.bin` filename.

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
5. Только для manual uploads убрать preliminary full source decode: один
   bounded probe → один tolerant transcode с `-t 14401` → один output probe →
   один strict output decode. Остальные media paths не менять.
6. До первого provider job gate processing activity по durable normalization
   state; отправлять exact canonical M4A, а не original media.
7. Создавать normalization job и durable transient owner для no-archive;
   единым revision policy исключать storage reserve/commit и оба playback
   selectors, а purge выполнять journal-first с publication fences.
8. Reconcile `ProcessingWorkflow(starting/workflow_started)` с deterministic
   Temporal start и explicit `REJECT_DUPLICATE`; ambiguous start не считать
   failure.
9. Terminalize provider input-audio failure и прекращать frontend polling.
10. Allowlist/infer multipart MIME; canonical contract — `audio/mp4` +
    `manual-media.m4a`.
11. Для неизвестного результата POST использовать документированный контракт
    MediaScribe v0.5.3: повторять только exact multipart с тем же durable
    `Idempotency-Key`; изменившийся request fingerprint блокировать до egress.
    Локальная pre-egress job строка сама по себе canonical gate не обходит.
12. Не расходовать provider watchdog во время normalization; ждать durable
    next-attempt/fallback timer и ограничивать history через `continue_as_new`.

## Не выбранные варианты

- Новый idempotency key или изменённый multipart после неизвестного submit не
  используется: это создаёт вторую job либо `409 idempotency_conflict`.
- Изменение MediaScribe API не требуется: status/result endpoints уже есть.
- Увеличение production `processing_recovery_max_attempts` не решает смешение
  семантик и оставляет ложную terminal failure.
- Новый orchestration workflow type не нужен: readiness возвращается из уже
  существующей activity, а wait выполняется после её результата.
- Deferred processing start после normalization `READY` не выбран: он создаёт
  отдельный durable handoff/reconciler и оставляет no-archive lifecycle без
  ProcessingWorkflow во время подготовки.
- FFmpeg в processing worker не выбран: CPU-heavy media work остаётся в
  выделенном media worker.
- Persistent WAV не выбран: MediaScribe принимает M4A, а второй artifact
  увеличивает storage/upload latency и риск расхождения таймкодов.
- Новая retention таблица не выбрана: finalized UploadSession, существующие
  workflow/artifact records и PurgeJournal достаточны после фиксации lock order
  и точки линеаризации.
