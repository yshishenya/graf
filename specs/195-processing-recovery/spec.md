# Feature Specification: Восстановление обработки и ранняя расшифровка встречи

**Feature Branch**: `195-processing-recovery`

**Created**: 2026-08-23

**Status**: Draft

**Input**: Перевести взаимодействие GRAF с MediaScribe на расширенный API v1, использовать его асинхронный жизненный цикл и сделать обработку встречи понятной и восстанавливаемой: показывать расшифровку после готовой диаризации независимо от summary, автоматически повторять временные сбои, показывать обратный отсчёт до следующей попытки и дать пользователю кнопку ручного запуска без создания дублей provider jobs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Посмотреть расшифровку до готовности итогов (Priority: P1)

Пользователь открывает встречу и получает полезный текст с репликами и спикерами сразу после завершения диаризации. Ему не нужно ждать генерации итогов или готовности второстепенных артефактов.

**Why this priority**: Расшифровка — основной результат записи. Блокировка текста из-за summary увеличивает time-to-value и создаёт впечатление, что встреча потеряна.

**Independent Test**: Подать в обработку запись, для которой расшифровка и диаризация готовы, а summary ещё выполняется или завершилось сбоем; убедиться, что вкладка «Расшифровка» доступна и содержит текст, а summary показывает собственное состояние.

**Acceptance Scenarios**:

1. **Given** текстовые сегменты уже получены, но диаризация ещё не завершена, **When** пользователь открывает встречу, **Then** GRAF не показывает эти сегменты как пользовательскую расшифровку и явно сообщает, что обработка продолжается.
2. **Given** расшифровка и диаризация готовы, а summary находится в состоянии выполнения, **When** пользователь открывает встречу, **Then** вкладка «Расшифровка» доступна с таймингами и атрибуцией спикеров, а вкладка «Итоги» показывает «готовится» независимо от текста.
3. **Given** расшифровка и диаризация готовы, а summary завершилось ошибкой, **When** пользователь открывает встречу, **Then** расшифровка остаётся доступной, ошибка summary не переводит всю встречу в блокирующую ошибку и предлагает действие только для итогов.
4. **Given** диаризация недоступна или не подтверждена, **When** пользователь открывает встречу, **Then** GRAF не показывает частичный текст без спикеров в обычной вкладке расшифровки и объясняет, что сначала нужно завершить или восстановить диаризацию.

### User Story 2 - Понятно дождаться и запустить повторную попытку (Priority: P1)

Пользователь видит, что сбой временный, знает, когда GRAF попробует снова, и может не ждать — запустить проверку/повторную попытку вручную. После ручного действия старый таймер не должен неожиданно запустить ещё одну попытку.

**Why this priority**: Сейчас сообщение «обработка требует проверки» не объясняет, потеряна ли запись и что делать. Прозрачное восстановление снижает тревогу и предотвращает повторные загрузки пользователем.

**Independent Test**: Смоделировать ответ с временной ошибкой и временем следующей попытки, дождаться отображения countdown, нажать ручную кнопку и проверить, что запрос запускается немедленно, отсчёт сбрасывается, а параллельной автоматической попытки не происходит.

**Acceptance Scenarios**:

1. **Given** MediaScribe или импорт вернули временно повторяемую ошибку, **When** GRAF переводит встречу в состояние ожидания восстановления, **Then** пользователь видит понятное объяснение, время следующей автоматической попытки и обратный отсчёт до неё.
2. **Given** обратный отсчёт активен, **When** пользователь нажимает «Проверить обработку», **Then** текущий таймер отменяется/сбрасывается, запускается одна ручная попытка, кнопка защищена от повторного нажатия, а после ответа показывается актуальное состояние и новый countdown только при необходимости.
3. **Given** сервер не сообщил точное время следующей попытки, **When** GRAF отображает временный сбой, **Then** интерфейс не придумывает точную дату; он показывает безопасное окно ожидания или текст «попробуйте сейчас» с доступной ручной кнопкой.
4. **Given** автоматическая попытка уже началась, **When** пользователь нажимает ручную кнопку, **Then** GRAF не создаёт параллельную попытку, а предлагает дождаться текущей или обновляет её статус.
5. **Given** временный сбой восстановился, **When** повторная попытка получает результат, **Then** countdown и кнопка исчезают, а интерфейс переходит к независимым статусам расшифровки, диаризации, summary и playback.

### User Story 3 - Безопасно восстановить неопределённую или окончательно неудачную обработку (Priority: P1)

Пользователь не создаёт дубликаты и не оплачивает повторную обработку из-за сетевого сбоя. GRAF различает «мы не знаем, принял ли провайдер запрос» и «провайдер подтвердил окончательный отказ», предлагает соответствующее действие и сохраняет уже готовые артефакты.

**Why this priority**: Повторная отправка неизвестного upload новым ключом может создать две provider jobs. С другой стороны, бесконечное ожидание окончательно повреждённого файла не помогает пользователю.

**Independent Test**: Прервать ответ после отправки upload, восстановить соединение и проверить reconciliation с тем же ключом; отдельно подать terminal failure и убедиться, что автоматических повторов нет и показывается корректное следующее действие.

**Acceptance Scenarios**:

1. **Given** результат отправки неизвестен, **When** GRAF восстанавливает соединение, **Then** он сначала проверяет ранее созданную provider job с тем же ключом и тем же содержимым, а не создаёт новый логический upload.
2. **Given** провайдер подтвердил окончательную ошибку входного файла или невозможность распознавания речи, **When** пользователь открывает встречу, **Then** countdown не показывается, причина объясняется человеческим языком, а действие ведёт к исправлению/новой записи или обращению за помощью.
3. **Given** провайдер подтвердил terminal failure после того, как transcript или diarization уже были импортированы, **When** пользователь открывает встречу, **Then** готовые артефакты сохраняются, а недоступный артефакт имеет отдельное состояние.
4. **Given** пользователь явно попросил повторить окончательно неудачную обработку, **When** GRAF создаёт новую бизнес-попытку, **Then** она имеет новый идентификатор попытки и новый ключ провайдера, а старая попытка остаётся доступной для диагностики и не запускается повторно.

### User Story 4 - Получить полный и восстанавливаемый результат MediaScribe (Priority: P2)

Пользователь получает результат через GRAF, не взаимодействуя с MediaScribe напрямую. GRAF корректно использует доступные режимы single/dual-track, диаризацию, summary, статусы очереди, результаты, загрузки и удаление, а после перезапуска worker продолжает обработку с сохранённой стадии.

**Why this priority**: Расширенный контракт MediaScribe даёт данные и lifecycle, необходимые для надёжной обработки и восстановления старых задач, но не должен превращаться в новую пользовательскую систему управления провайдером.

**Independent Test**: Проверить создание, polling, result/import, summary, authenticated downloads, cancellation/deletion и восстановление по списку jobs на тестовом окружении с API v1; остановить worker между стадиями и убедиться, что обработка продолжается без повторной отправки.

**Acceptance Scenarios**:

1. **Given** запись имеет один или два канонических аудиотрека, **When** GRAF отправляет её на обработку, **Then** выбирается соответствующий поддерживаемый режим, а параметры диаризации и summary передаются согласно настройкам GRAF и runtime capabilities провайдера.
2. **Given** provider result готов, **When** GRAF импортирует его, **Then** сохраняются доступные сегменты, роли треков, акустические повороты, overlap-интервалы, provenance и состояния артефактов без раскрытия provider job id пользователю.
3. **Given** результат ещё не готов, **When** GRAF опрашивает provider status/result, **Then** используется рекомендованная провайдером задержка с bounded jitter и deadline, а не бесконечный частый polling.
4. **Given** удаление встречи или записи запрошено пользователем, **When** MediaScribe принимает отмену асинхронно, **Then** GRAF показывает состояние удаления, опрашивает receipt до подтверждения и не заявляет об окончательном удалении раньше provider confirmation.
5. **Given** worker или процесс GRAF перезапущен, **When** workflow возобновляется, **Then** пользовательский статус, next-attempt time, provider job linkage и idempotency state восстанавливаются из durable state, а внешняя job не дублируется.

## Edge Cases

- Сегменты появились раньше диаризации: они остаются внутренним промежуточным результатом и не показываются пользователю до подтверждения готовности диаризации.
- Диаризация готова, но transcript пуст из-за `no_recognizable_speech`: пользователь видит честное состояние «речь не распознана», а не пустую расшифровку или бесконечный spinner.
- Summary выполняется, отключён runtime-конфигурацией или завершился ошибкой: transcript и diarization не блокируются; для summary показывается отдельное состояние.
- Ответ upload потерян после фактического принятия провайдером: новый ключ запрещён до reconciliation; повторяется тот же запрос только в рамках безопасного same-key контракта.
- Повторное нажатие ручной кнопки, двойной клик или два браузерных окна: действует одна логическая ручная попытка, остальные получают актуальный статус.
- Ответ `Retry-After` отсутствует, некорректен или слишком велик: используется серверное bounded fallback-окно; интерфейс не показывает ложное точное обещание.
- Provider возвращает неизвестный будущий status или queue state: GRAF сохраняет raw machine value для диагностики, не ломает пользовательский экран и не трактует неизвестное состояние как terminal failure без безопасного основания.
- Polling получает `404`, `410`, deletion state или неповторяемую ошибку: workflow прекращает неподходящие повторы и показывает соответствующее действие.
- Provider временно недоступен после импорта одного артефакта: уже сохранённые артефакты остаются доступными, а восстановление относится только к недостающему этапу.
- Удаление локальной встречи происходит во время polling/import: поздний результат не должен воскресить удалённую встречу или вернуть удалённый артефакт в UI.
- Пользователь использует браузерную и desktop-поверхность одновременно: обе показывают одну authoritative processing state и не создают независимые retries.
- Медленная сеть, вкладка в background или закрытый desktop-клиент: countdown рассчитывается по серверному времени/next-attempt timestamp после обновления, а не по накопленной локальной секунде.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST model transcript, diarization, summary, playback, export and deletion as independently observable artifact states; readiness of one artifact MUST NOT be inferred solely from readiness of another.
- **FR-002**: GRAF MUST keep transcript content hidden from the ordinary user-facing transcript view until diarization is confirmed ready for the same processing attempt and revision.
- **FR-003**: Once transcript and diarization are ready, GRAF MUST make the transcript available even when summary is running, unavailable, disabled or failed, and MUST preserve the transcript while summary recovers.
- **FR-004**: GRAF MUST distinguish retryable, terminal and unknown-outcome processing states using machine-readable provider semantics and local evidence; free-form provider detail MUST NOT be the only classifier.
- **FR-005**: For retryable states, GRAF MUST persist the next automatic-attempt time or bounded fallback schedule and expose a localized explanation, countdown and a manual action when a retry is safe.
- **FR-006**: Manual retry MUST cancel or supersede the pending automatic timer for the same logical attempt, start at most one immediate operation, disable duplicate clicks while it is in flight and recalculate the next state from the response.
- **FR-007**: An automatic timer MUST NOT start a second operation after a manual action has already claimed the same logical retry slot.
- **FR-008**: GRAF MUST use the provider's retry hints, including `Retry-After` when available, while applying a bounded deadline, jitter and a safe fallback when hints are missing or invalid.
- **FR-009**: GRAF MUST preserve the provider job identifier, idempotency key, processing-attempt identity and request/correlation metadata in server-side durable state without exposing secrets, signed URLs or provider identifiers in ordinary UI copy.
- **FR-010**: If upload outcome is unknown, GRAF MUST reconcile the original request using the same idempotency key and equivalent request body before allowing a new provider job; a new key MUST NOT be used as a blind recovery action.
- **FR-011**: A new idempotency key and provider job MUST be created only for an explicit new business attempt after the previous attempt is confirmed terminal or otherwise safely closed.
- **FR-012**: GRAF MUST migrate processing requests and lifecycle reads to the supported MediaScribe v1 contract, including single/dual-track upload, job status, result, summary, authenticated artifact downloads, cancellation/deletion status and cursor-based recovery where applicable.
- **FR-013**: GRAF MUST obtain environment-dependent limits and capabilities at runtime, including supported media, speaker-count modes, active-job limits, retry/backoff hints and summary availability, and MUST degrade safely when an optional capability is unavailable.
- **FR-014**: GRAF MUST preserve transcript segment timing and, when present, track roles, speaker attribution, acoustic turns, overlap intervals and provenance; unknown fields MUST be tolerated for forward compatibility.
- **FR-015**: GRAF MUST keep MediaScribe credentials and direct provider communication server-side; desktop and browser clients MUST use GRAF-owned authorization and result endpoints.
- **FR-016**: GRAF MUST persist stage transitions, retry classification, next-attempt time, manual/automatic trigger, provider status and import outcome as metadata suitable for diagnostics and aggregate analytics without storing raw audio or transcript content in ordinary logs.
- **FR-017**: The durable processing coordinator MUST resume after worker/process restart from the last confirmed stage and MUST NOT duplicate an external provider job or re-import a result in a way that regresses already available artifacts.
- **FR-018**: GRAF MUST reconcile provider deletion/cancellation states and MUST not present provider-side deletion as complete before a confirmed deletion receipt or equivalent terminal evidence.
- **FR-019**: User-facing recovery copy MUST explain what is happening, whether user action is needed, what action is available now and whether already prepared artifacts remain safe; raw HTTP status, provider error detail and job identifiers MUST not be the primary copy.
- **FR-020**: Browser and embedded desktop meeting surfaces MUST expose the same artifact/recovery truth; surfaces MAY differ in native capture/offline affordances but MUST NOT launch independent processing attempts.
- **FR-021**: Recovery controls and countdown MUST be keyboard accessible, screen-reader understandable, localizable and resilient to refresh, background tabs, reduced motion and forced-colors mode.
- **FR-022**: GRAF MUST emit allowlisted aggregate events for processing state changes, first usable result, retry request, retry outcome, export outcome and support handoff, excluding meeting identifiers, titles, filenames, provider job IDs, transcript/audio content and free text.

### Key Entities

- **Media Revision**: The immutable audio revision being processed; identifies the source, canonical tracks, ownership and deletion epoch.
- **Processing Attempt**: One user-visible business attempt for a media revision; records lifecycle state, trigger, retry classification, stage, timestamps and relation to imported artifacts.
- **Provider Job**: The single MediaScribe job belonging to one processing attempt; records provider job id, idempotency key, mode, provider status, queue state and safe correlation metadata.
- **Processing Artifact**: A revision-pinned transcript, diarization, summary, playback, export or deletion artifact with independent availability, freshness and failure state.
- **Retry Schedule**: Durable next-attempt timestamp, source of schedule, retry count/deadline, manual override state and the rule that prevents timer/manual races.
- **Provider Capability Snapshot**: Runtime-supported limits, formats, speaker modes, queue behavior, summary support and retry/cancellation hints used to validate requests and explain degraded states.
- **Deletion Receipt**: Provider and GRAF evidence describing requested, accepted, in-progress or confirmed deletion, including the state needed to avoid claiming completion too early.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance tests, 100% of meetings with confirmed transcript and diarization show the transcript even when summary is still running, unavailable or failed.
- **SC-002**: In acceptance tests, 100% of transcript segments remain hidden from the ordinary transcript view until the matching diarization-ready condition is confirmed.
- **SC-003**: For every retryable failure with a valid provider retry hint, the user-facing next-attempt countdown is based on that hint and becomes visible within 5 seconds of the failure state being displayed; invalid or missing hints never produce a false exact promise.
- **SC-004**: In concurrency and refresh tests, 100% of manual retry clicks cancel/supersede the pending countdown for that logical attempt and result in no duplicate provider job or parallel retry operation.
- **SC-005**: In fault-injection tests covering lost upload responses, worker restarts and duplicate delivery, 0 new provider jobs are created before same-key reconciliation completes, and at most one provider job is linked to each logical processing attempt.
- **SC-006**: At least 95% of recoverable transient failures in the acceptance workload reach a usable result without a support handoff or user re-upload; the remaining cases end in an explicit actionable state within the configured processing deadline.
- **SC-007**: At least 95% of meetings in the acceptance workload reach a first usable result defined as transcript plus confirmed diarization, while summary and playback continue on their own timelines.
- **SC-008**: After a worker/process restart at every defined stage boundary, 100% of in-flight attempts resume from durable state without losing already imported artifacts or exposing stale countdown state after refresh.
- **SC-009**: In API contract tests, GRAF handles documented v1 success, retryable, terminal, deletion and forward-compatible unknown-field cases without exposing provider credentials, signed URLs, raw provider payloads or provider job identifiers in ordinary user-facing responses.
- **SC-010**: Aggregate analytics can report retryable failure rate, manual retry rate, recovery rate, time to first usable result and artifact availability by surface and bounded media-size bucket without any prohibited meeting or content identifier.

## Assumptions

- The product definition of a first usable transcript for this feature is transcript plus confirmed diarization; raw ASR segments before diarization are not user-visible.
- Summary is a separate value stream. Existing GRAF summary generation remains the canonical user-facing summary unless a later approved decision enables a provider summary as a stored GRAF artifact.
- MediaScribe v1 is the authoritative external contract for new integration work; runtime capabilities and version endpoints are more authoritative than static examples in migration documents.
- The external API does not provide a documented webhook or streaming result channel, so the user experience can use durable polling and refresh without promising push completion.
- Retryable failure policy uses provider hints and a bounded server-owned fallback. Exact delay caps, attempt budgets and queue fairness are implementation/operations decisions to be fixed in the plan and validated against runtime capabilities.
- A manual action during an existing provider job means “check/continue this same job now”; it does not mean “upload a second copy”. A new business attempt is a separate explicit action after confirmed terminal failure.
- MediaScribe credentials, raw provider payloads and private meeting content remain server-side and follow existing GRAF privacy, deletion and observability gates.
- Existing capture, canonical audio preparation, ownership authorization, quota reservation and GRAF export policy are reused; audio capture and upload throughput are outside this feature.
- Historical failed meetings may be recovered only when their source revision and safe provider linkage are still available; otherwise the UI must state why a new user-confirmed attempt is needed.

## Out of Scope

- Changing macOS recording, system-audio capture, microphone permissions or the canonical audio preparation contract.
- Adding webhooks, SSE, WebSocket or provider-side push infrastructure that is not present in the MediaScribe v1 contract.
- Exposing MediaScribe as a second user-facing meeting cabinet, provider job console or direct download surface.
- Replacing GRAF's canonical summary workflow with provider-generated summary content without a separate product decision and quality gate.
- Blindly re-uploading an unknown-outcome request under a new idempotency key.
- Resumable/chunked media upload or direct desktop-to-MediaScribe communication.
- Production deployment, release versioning, issue creation, implementation code and migration execution in this planning slice.
