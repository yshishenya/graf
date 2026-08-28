# Feature Specification: Надёжное ожидание результата MediaScribe

**Feature Branch**: `206-mediascribe-polling-recovery`
**Created**: 2026-08-26
**Status**: Implemented; production closeout pending

**Input**: Продолжать опрашивать существующую задачу MediaScribe, не считать
ожидающие статусы ошибкой и показывать пользователю ошибку только после
подтверждённого terminal failure провайдера либо локальной невозможности
обработки.

## Clarifications

### Session 2026-08-27

- Q: Можно ли показывать partial transcript до diarization? → A: Нет. Transcript
  становится видимым только после готовой diarization; summary независим.
- Q: Что показывать при временном сбое? → A: Countdown до автоматической
  попытки и ручное действие; ручной запуск сбрасывает текущий timer.
- Q: Как обрабатывать повреждённый manual-upload source? → A: С первого полного
  прохода tolerant transcode с пропуском декодируемых ошибок; preliminary full
  source decode не выполняется.
- Q: Какие байты отправлять в MediaScribe? → A: Exact strictly validated
  canonical M4A, тот же что используется playback при включённом архиве.
- Q: Что делать при `archive_audio=false`? → A: Использовать тот же canonical
  transiently без playback/storage quota и удалить bounded purge lifecycle.

## User Scenarios & Testing

### User Story 1 - Результат появляется после обычной задержки провайдера (Priority: P1)

Пользователь загружает запись и видит понятное состояние подготовки. GRAF
опрашивает ту же задачу MediaScribe до готовности результата; состояния
`uploaded`, `queued`, `processing`, `diarizing` и `409 result_not_ready` не
показываются как ошибка.

**Why this priority**: Это устраняет текущий тупик, когда MediaScribe успевает
обработать запись после того, как GRAF ошибочно завершает её.

**Independent Test**: Синтетический provider job остаётся pending несколько
проверок, затем становится ready; GRAF импортирует результат без новой загрузки
и без terminal failure.

**Acceptance Scenarios**:

1. **Given** provider job имеет pending-статус, **When** GRAF получает статус,
   **Then** workflow остаётся recoverable и планирует следующую проверку.
2. **Given** provider job стал `ready`, **When** GRAF выполняет следующую
   проверку, **Then** результат импортируется и transcript становится видимым
   только при готовой diarization.

### User Story 2 - Ошибка соответствует подтверждённой причине (Priority: P1)

Пользователь получает ошибку только если MediaScribe сообщил terminal `failed`
или GRAF обнаружил локальную неустранимую ошибку (например, отсутствующий
артефакт или некорректный ответ).

**Independent Test**: Проверить provider terminal failure, retryable HTTP
ошибку, malformed result и missing artifact в отдельных сценариях.

**Acceptance Scenarios**:

1. **Given** MediaScribe сообщил `failed`, **When** GRAF обновляет состояние,
   **Then** показываются понятная ошибка и доступное recovery-действие.
2. **Given** MediaScribe вернул 429/5xx/timeout или pending status, **When**
   GRAF обрабатывает ответ, **Then** запись остаётся временно ожидающей и не
   получает terminal failure.
3. **Given** ответ провайдера malformed или исходный артефакт недоступен,
   **When** GRAF проверяет его, **Then** локальная ошибка фиксируется отдельно
   и не маскируется под pending.

### User Story 3 - Пользователь может безопасно проверить позже (Priority: P2)

Если автоматическое ожидание достигло watchdog deadline, пользователь видит,
что результат ещё не подтверждён, может запустить ручную проверку, а GRAF
использует тот же MediaScribe job и не создаёт дубликат multipart-загрузки.

**Independent Test**: Довести workflow до watchdog deadline, проверить отдельное
recoverable состояние, ручную проверку и отсутствие новой provider job.

**Acceptance Scenarios**:

1. **Given** provider не сообщил ни ready, ни failed до watchdog deadline,
   **When** deadline достигнут, **Then** GRAF не утверждает provider failure,
   показывает состояние ожидания проверки и оставляет ручное действие.
2. **Given** пользователь нажал ручную проверку во время countdown, **When**
   запрос принят, **Then** countdown сбрасывается и выполняется проверка той же
   provider job.
3. **Given** старый workflow завершён terminal из-за прежнего poll limit,
   **When** есть сохранённый provider job, **Then** статусная проекция не
   возвращает ложное «Обрабатывается» рядом с ошибкой.
4. **Given** окно стало неактивным во время обработки, **When** MediaScribe
   позднее сообщает terminal `no_recognizable_speech`, **Then** фоновая
   проверка обновляет карточку без обязательного повторного входа во встречу.

### User Story 4 - Ручная загрузка подготавливается один раз для плеера и MediaScribe (Priority: P1)

Пользователь загружает поддерживаемый аудио- или видеофайл. GRAF сразу
выполняет tolerant-нормализацию, строго проверяет созданный canonical M4A и
только затем отправляет эти же байты в MediaScribe. Повреждённые декодируемые
фреймы не превращают восстановимую запись в тупик, а таймкоды результата
соответствуют воспроизводимому аудио.

**Why this priority**: Параллельный запуск playback-нормализации и provider
submit позволяет отправить повреждённый оригинал, даже когда GRAF успешно
создаёт исправный M4A.

**Independent Test**: Загрузить файл с повреждённым, но восстанавливаемым
фреймом; доказать один tolerant transcode, строгую проверку результата, один
MediaScribe POST canonical M4A и совпадение SHA отправленного файла с playback
artifact при включённом архиве.

**Acceptance Scenarios**:

1. **Given** ручная загрузка ещё нормализуется, **When** processing workflow
   проверяет readiness, **Then** provider job не создаётся, а workflow ждёт
   через bounded durable timer.
2. **Given** canonical M4A строго проверен и опубликован, **When** processing
   продолжает работу, **Then** MediaScribe получает exact canonical artifact с
   `Content-Type: audio/mp4` и именем `manual-media.m4a` ровно один раз.
3. **Given** пользователь выбрал обработку без сохранения аудио, **When**
   canonical M4A готов, **Then** он используется как transient provider input,
   не показывается в плеере, не расходует storage quota и удаляется существующим
   transient purge lifecycle.
4. **Given** нормализация временно не удалась, **When** назначен retry, **Then**
   пользователь видит countdown и может нажать «Повторить подготовку»; команда
   идемпотентно сбрасывает таймер и не создаёт параллельный transcode.
5. **Given** нормализация завершилась terminal либо встреча удалена/заменена,
   **When** processing проверяет readiness, **Then** MediaScribe не получает
   исходный или canonical файл и UI прекращает polling с понятным действием.

### Edge Cases

- Provider прислал неизвестный будущий pending-статус: сохранить job
  recoverable и не создавать новую загрузку.
- Ответ на submit неизвестен: выполнять только same-key reconciliation.
- `Retry-After`/`next_retry_at` отсутствуют или некорректны: применять bounded
  backoff без busy polling.
- Provider terminal failure с partial artifacts: сохранить доступные артефакты,
  но не показывать transcript без подтверждённой diarization.
- Temporal worker перезапустился во время ожидания: timer и повторная проверка
  должны восстановиться из истории workflow.
- Окно кабинета скрыто в момент плановой проверки: low-frequency polling не
  теряется и останавливается после terminal projection.
- Worker упал после сохранения `ProcessingWorkflow(status=starting)`, но до
  Temporal start: reconciler повторяет deterministic start и не создаёт новый
  workflow/provider job.
- Worker упал после публикации canonical M4A, но до следующей processing
  activity: durable gate обнаруживает `READY` после перезапуска.
- Уже существует подтверждённый provider `external_job_id`: дальнейшее polling
  не зависит от normalization и никогда не меняет отправленный source; локальная
  pre-egress строка без external id не обходит canonical gate.
- Storage quota заполнена: архивная публикация получает понятный policy block,
  а `archive_audio=false` transient canonical не начисляет storage usage.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST treat MediaScribe pending statuses and `409
  result_not_ready` as recoverable provider states.
- **FR-002**: GRAF MUST poll the existing provider job until ready, confirmed
  terminal failure, or a separate bounded watchdog outcome.
- **FR-003**: Provider polling MUST NOT be limited by the short generic recovery
  attempt limit; the watchdog deadline remains the upper bound.
- **FR-004**: GRAF MUST use provider `Retry-After` and `next_retry_at` when valid,
  with bounded fallback delay and no busy loop.
- **FR-005**: GRAF MUST distinguish provider terminal failure, retryable
  technical failure, watchdog timeout/stuck state, and local processing failure
  in durable reason/status projection.
- **FR-006**: Manual check MUST reconcile the same provider job or idempotency
  key and MUST NOT issue a duplicate multipart upload.
- **FR-007**: The UI MUST show transcript only when diarization is available;
  summary readiness remains independently represented.
- **FR-008**: The UI MUST show a clear pending/retry/watchdog state, countdown
  when a next check is scheduled, and a manual check action when available.
- **FR-009**: Terminal status projections MUST be consistent between detail,
  list, API status endpoint, and recovery controls.
- **FR-010**: Temporal workflow waiting MUST use durable timers/signals and
  remain deterministic on replay.
- **FR-011**: Every supported manual upload MUST use bounded metadata probing,
  one tolerant transcode to canonical M4A, and strict full validation of the
  generated output; GRAF MUST NOT perform a preliminary full decode of the
  source. This tolerant-first path MUST NOT alter capture, other single-source,
  dual-source, copy or remux paths.
- **FR-012**: GRAF MUST NOT create a MediaScribe job or submit manual-upload
  bytes until the matching normalization job is `ready` with an exact validated
  canonical artifact.
- **FR-013**: MediaScribe and archived playback MUST consume the same canonical
  M4A bytes and timeline for a manual upload; the original upload MUST NOT be
  submitted once this contract applies.
- **FR-014**: Manual uploads with `archive_audio=false` MUST use the same
  validated canonical input transiently, without playback egress or storage
  quota charging, and MUST purge original/canonical audio through the existing
  bounded transient lifecycle.
- **FR-015**: Temporary normalization failures MUST expose the durable next
  attempt, countdown, and idempotent manual retry; terminal normalization,
  deletion, and supersession MUST prevent provider egress.
- **FR-016**: A persisted processing start intent MUST be reconciled after a
  crash before Temporal start by reusing the deterministic workflow id with an
  explicit no-duplicate reuse policy; ambiguous starts MUST remain recoverable.
- **FR-017**: Provider `invalid_audio_payload` with `error_origin=input_audio`
  MUST project as terminal across DB, API, list, detail, controls, and frontend
  polling, including historical `processed` rows whose current workflow lineage
  was proven by migration.
- **FR-018**: Canonical M4A multipart metadata MUST be `audio/mp4` and
  `manual-media.m4a`; arbitrary codec labels MUST NOT be accepted as MIME types.
- **FR-019**: Normalization waiting MUST use durable `next_attempt_at`/bounded
  timers, MUST NOT consume the provider watchdog, and MUST bound Temporal history
  with `continue_as_new` without changing pre-existing history commands.
- **FR-020**: No-archive purge MUST be race-safe and crash-recoverable: committed
  purge intent/fences precede object deletion; only transient source/playback
  media is deleted; DB states are reconciled afterward under a stable lock order.
- **FR-021**: Manual-upload source duration MUST be finite, positive, known and
  at most four hours before transcode. Detectable stream/container/revision
  duration mismatch or output tail loss beyond the explicit small tolerance MUST
  fail closed; GRAF does not promise to detect truncation absent any evidence.
- **FR-022**: Meeting-detail status polling MUST continue at low frequency while
  the window is hidden until a terminal projection is received; a hidden-window
  timer MUST NOT leave the user on a stale processing screen.

### Key Entities

- **MediaScribe provider job**: Existing external job identity, provider status,
  retry hints, and terminal error evidence.
- **Processing workflow**: GRAF durable lifecycle, retry schedule, watchdog
  deadline, and user-facing reason projection.
- **Processing status projection**: Content-safe API/UI representation of
  readiness, recovery action, countdown, and terminal state.

## Success Criteria

- **SC-001**: A provider job that becomes ready within the watchdog window is
  imported without a duplicate provider job and without a false terminal error.
- **SC-002**: Pending provider states remain recoverable through at least 12
  checks and until the configured watchdog deadline.
- **SC-003**: For terminal provider failures, the API and detail UI show the same
  terminal recovery state in 100% of covered contract scenarios.
- **SC-004**: Transcript is never user-visible in covered scenarios before
  diarization is available.
- **SC-005**: Temporal replay tests pass for timer wait, manual check signal or
  update, and workflow restart behavior.
- **SC-006**: Covered manual-upload scenarios perform exactly one source probe,
  zero preliminary full source decodes, one tolerant transcode with `-t 14401`,
  one output probe, and one strict generated-output decode; non-manual paths keep
  their existing pass counts.
- **SC-007**: In covered manual-upload scenarios, MediaScribe creates exactly one
  provider job whose bytes and SHA match the validated canonical artifact. A
  lost POST response may cause multiple exact same-key HTTP attempts; the
  original source is never submitted.
- **SC-008**: Crash tests at normalization publication, processing start, and
  provider submission boundaries recover without a duplicate provider job.
- **SC-009**: `archive_audio=false` scenarios expose no player, consume no
  retained storage quota, and purge both source and canonical audio within the
  existing transient deadlines.
- **SC-010**: Terminal input-audio projections schedule no frontend polling
  timer in 100% of covered contract scenarios.
- **SC-011**: Canonical submission contract tests observe `audio/mp4` and
  `manual-media.m4a`.
- **SC-012**: Normalization metrics expose queue age, execution duration, and
  outcome without meeting content; initial worker concurrency remains unchanged
  until production evidence shows backlog.
- **SC-013**: Replay/current-history tests cover normalization timers,
  `continue_as_new`, cancellation and manual wake; duplicate/ambiguous Temporal
  starts and concurrent reconcilers do not create a second execution.
- **SC-014**: A covered pending → `no_recognizable_speech` result uses one
  provider submission and updates the detail terminal recovery state without a
  required page re-entry.

## Assumptions

- MediaScribe v1 job status and result endpoints remain the source of provider
  truth; no MediaScribe service changes are part of this slice.
- Existing normalization, artifact, processing, retry, and transient lifecycle
  entities are reused; no new workflow type, queue, or retained WAV is required.
- The internal `normalization_pending` activity result is orchestration metadata,
  not a new public lifecycle status.
- The existing server-side MediaScribe credential boundary is preserved.
- Production deployment and E2E are in scope under the user's current approval;
  Full CI is not repeated, while scoped/current-SHA validation and deployment
  gates remain mandatory.
