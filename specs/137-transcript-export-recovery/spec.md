# Feature Specification: Восстановление выгрузки транскрипта и саммари

**Feature Branch**: `codex/137-transcript-export-recovery`

**Created**: 2026-08-03

**Status**: Draft

**Input**: Пользовательская проблема: для готовой записи «3 авг, 16:40» нельзя скачать транскрипт и саммари; нужно устранить корневые причины для этой записи и новых обработанных записей.

## User Scenarios & Testing

### User Story 1 - Владелец скачивает готовый транскрипт (Priority: P1)

Как владелец встречи, я хочу скачать готовый транскрипт после успешной обработки,
чтобы использовать результат за пределами кабинета без отдельной настройки для
каждой записи.

**Why this priority**: Транскрипт уже существует, но текущая неявная политика
блокирует его на общей границе выгрузки.

**Independent Test**: Создать синтетическую обработанную встречу без явной
политики, открыть capability и выполнить выгрузку от владельца; получить
непустой транскрипт, не раскрывая содержимое в capability или audit.

**Acceptance Scenarios**:

1. **Given** транскрипт импортирован и содержит сегменты, а явное решение об
   ограничении выгрузки отсутствует, **When** владелец запрашивает транскрипт,
   **Then** capability и прямой server-mediated маршрут разрешают выгрузку.
2. **Given** встреча доступна permitted non-owner viewer, **When** viewer
   запрашивает транскрипт при owner-default, **Then** сервер отклоняет выдачу
   байтов и не раскрывает содержимое.
3. **Given** явный per-meeting deny, **When** владелец повторяет запрос,
   **Then** deny сохраняется и имеет приоритет над default.

---

### User Story 2 - Владелец получает готовое саммари (Priority: P1)

Как владелец встречи, я хочу видеть и скачивать валидное саммари после обработки,
чтобы готовая запись не оставалась без доступного результата из-за незаполненного
указателя или неявной политики.

**Why this priority**: Для записи уже создан детерминированный результат, но он
остался кандидатом, а текущий указатель результата не был установлен.

**Independent Test**: Создать синтетическую встречу с доступным транскриптом,
запустить baseline без принятого результата, проверить, что валидный baseline
становится текущим и саммари экспортируется владельцем.

**Acceptance Scenarios**:

1. **Given** для текущего результата нет принятого outcome, а детерминированный
   baseline успешно сформирован и привязан к текущей ревизии, **When** baseline
   завершается, **Then** он публикуется как текущий outcome и становится доступен
   для owner-only выгрузки.
2. **Given** уже существует принятый outcome, **When** появляется новый baseline
   или ручной AI-кандидат, **Then** принятый результат не заменяется без явного
   решения владельца.
3. **Given** саммари отсутствует, неполно или устарело относительно транскрипта,
   **When** владелец запрашивает экспорт, **Then** capability сообщает bounded
   недоступность и не выдаёт пустой или устаревший файл.

---

### User Story 3 - Ошибка AI не ломает готовый результат (Priority: P1)

Как владелец встречи, я хочу, чтобы ошибка нового AI-кандидата не скрывала уже
готовный транскрипт или саммари, а корректная ссылка на сегмент восстанавливалась
по каноническому источнику.

**Why this priority**: Ручное обновление саммари уже завершалось с ошибкой
валидации пары `segment_id/sequence`, хотя сам транскрипт был готов.

**Independent Test**: Передать валидный segment ID с неверным sequence и отдельно
неизвестный ID; первый случай нормализовать до канонической пары, второй —
отклонить, сохранив предыдущий результат.

**Acceptance Scenarios**:

1. **Given** AI вернул существующий segment ID с неверным sequence, **When** ответ
   проходит локальную проверку, **Then** сохранённая ссылка использует sequence
   из pinned transcript и кандидат может завершиться.
2. **Given** AI вернул неизвестный ID, недопустимую структуру или ссылку вне
   pinned transcript, **When** ответ проверяется, **Then** кандидат завершается
   bounded validation failure и не публикуется.
3. **Given** новый AI-кандидат упал, **When** владелец открывает текущую встречу,
   **Then** доступные транскрипт и принятый baseline остаются без изменений, а
   ошибка отображается как повторяемое действие без raw model content.

---

### User Story 4 - Статус обработки остаётся понятным (Priority: P2)

Как пользователь, я хочу видеть готовность по фактическому статусу обработки,
чтобы технический статус жизненного цикла загрузки не выглядел как продолжающаяся
обработка уже готовой встречи.

**Why this priority**: У записи одновременно присутствовали lifecycle-статус
`ingested_pending_processing` и завершённый `processing_status=processed`.

**Independent Test**: Для синтетической встречи с импортированным результатом
проверить API и web view: readiness определяется завершённой обработкой, а
жизненный статус загрузки не блокирует выгрузку.

**Acceptance Scenarios**:

1. **Given** workflow завершён и результат импортирован, **When** пользователь
   открывает встречу, **Then** processing/readiness показывает готовность и не
   требует повторной отправки в очередь.
2. **Given** workflow ещё выполняется или завершился ошибкой, **When** пользователь
   открывает встречу, **Then** readiness показывает соответствующее bounded
   состояние и выгрузка остаётся закрыта.

### Edge Cases

- Явные `meeting_override` запреты для transcript, summary и package имеют
  приоритет над owner-default.
- `workspace_default` и отсутствие строки политики считаются неявным default;
  владелец получает owner-only, permitted non-owner — отказ.
- Удаление, stale source revision, неполный transcript, нулевое число сегментов
  и отсутствие текущего outcome должны оставаться fail-closed.
- Для уже существующего готового automatic baseline требуется идемпотентное
  восстановление указателя; повторная reconcile-операция не создаёт второй
  результат и не меняет принятые ручные итоги.
- Audit, diagnostics, evidence и UI metadata не содержат transcript text,
  summary text, storage keys, signed URLs, credentials или raw model response.

## Requirements

### Functional Requirements

- **FR-001**: Система MUST применять owner-only default к transcript, summary и
  package export, если per-meeting policy отсутствует или пришла из неявного
  `meeting_default`/`workspace_default` источника.
- **FR-002**: Система MUST сохранять явный `meeting_override` deny или owner-only
  режим и MUST не расширять доступ permitted non-owner viewer.
- **FR-003**: Capability endpoint, web cabinet и прямой content-export маршрут
  MUST использовать одну и ту же эффективную policy/readiness decision.
- **FR-004**: Система MUST публиковать успешно сформированный детерминированный
  baseline как текущий outcome только когда для актуального результата нет
  принятого outcome; существующий accepted outcome MUST оставаться неизменным.
- **FR-005**: Система MUST привязывать опубликованный outcome к текущим
  processing result, media revision и source hash; stale или mismatched result
  MUST быть недоступен для выгрузки.
- **FR-006**: Система MUST проверять AI source references по pinned transcript и
  нормализовать sequence по валидному segment ID; неизвестные ID и иные
  нарушения границы MUST завершаться bounded validation failure.
- **FR-007**: Ошибка AI-кандидата MUST сохраняться с безопасным reason code и не
  MUST заменять либо скрывать доступный accepted outcome или transcript.
- **FR-008**: Processing/readiness projections MUST отражать завершённый
  `processed` result независимо от того, что immutable meeting lifecycle status
  остаётся `ingested_pending_processing` до отдельного lifecycle transition.
- **FR-009**: Все внешние выгрузки MUST сохранять текущие authorization, deletion,
  revision, server-mediated и metadata-only audit gates.
- **FR-010**: Повторная reconcile/acceptance для одного result MUST быть
  идемпотентной, не создавать дубликаты outcome и не менять явно принятые
  результаты.

### Key Entities

- **MeetingArtifactPolicy**: эффективные owner-only/explicit egress decisions и
  их источник.
- **ProcessingResult**: импортированный provider-neutral результат с transcript
  availability, revision и source hash.
- **MeetingOutcomeSet**: deterministic baseline или AI candidate и текущий
  accepted pointer.
- **TranscriptSegment**: pinned canonical segment ID/sequence, используемый как
  источник evidence.
- **ProcessingWorkflow**: revision-scoped processing lifecycle и terminal status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: В 100% синтетических сценариев с доступным transcript владелец без
  policy row получает capability `available` и успешный server-mediated export.
- **SC-002**: В 100% синтетических сценариев с валидным initial baseline и без
  accepted outcome владелец получает доступное summary и summary export после
  одной reconcile-операции.
- **SC-003**: В 100% сценариев с explicit deny, non-owner viewer, deletion или
  stale revision содержимое и байты не выдаются.
- **SC-004**: В 100% сценариев с неверным sequence при валидном segment ID
  сохранённая evidence-ссылка соответствует pinned transcript; неизвестные IDs
  не принимаются.
- **SC-005**: Повторный запуск reconcile для уже исправленного результата не
  создаёт новых outcome или generation attempts.
- **SC-006**: Focused tests, `git diff --check` и `infra/scripts/ci-local.sh
  --fast` проходят; production deployment не заявляется без отдельного release
  gate и approval.

## Assumptions

- Owner-only является безопасным default для личного owner workflow; explicit
  policy остаётся источником истины для privacy decisions.
- Детерминированный baseline считается достаточно доверенным для первой
  публикации, когда нет принятой истории; новые ревизии и ручные AI-форматы
  сохраняют review-before-replace lifecycle.
- Existing endpoints, access decisions, storage boundary, export formats,
  Temporal/Langfuse retention policy and server-rendered cabinet переиспользуются.
- Ремонт текущих production rows выполняется отдельным одобренным rollout или
  идемпотентной reconcile-операцией после валидации кода; этот slice не содержит
  несанкционированной production mutation.

## Out of Scope

- Удаление или редактирование transcript, Generation Call, Langfuse или Temporal
  History и изменение plaintext observability policy.
- Новый endpoint, storage URL, direct provider credential или MediaScribe path.
- Автоматическая публикация replacement/AI-кандидата поверх accepted outcome.
- Изменение capture/routing, macOS recording UX или immutable meeting lifecycle
  semantics.
- Production deploy, миграция/ручная правка production без отдельного approval.
