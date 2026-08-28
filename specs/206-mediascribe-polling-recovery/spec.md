# Feature Specification: Надёжное ожидание результата MediaScribe

**Feature Branch**: `206-mediascribe-polling-recovery`
**Created**: 2026-08-26
**Status**: Draft

**Input**: Продолжать опрашивать существующую задачу MediaScribe, не считать
ожидающие статусы ошибкой и показывать пользователю ошибку только после
подтверждённого terminal failure провайдера либо локальной невозможности
обработки.

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

## Assumptions

- MediaScribe v1 job status and result endpoints remain the source of provider
  truth; no MediaScribe service changes are part of this slice.
- Existing GRAF database fields for retry schedule and deadlines are reused;
  no new status is required. A bounded data migration may fill an already
  existing lineage field when historical rows have one exact source mapping.
- The existing server-side MediaScribe credential boundary is preserved.
- Production deployment and reprocessing are out of scope for this coding
  slice; they require a separately approved release gate.
