# Feature Specification: Meeting Content Regeneration Lifecycle

**Feature Branch**: `124-content-regeneration-lifecycle`

**Created**: 2026-07-23

**Status**: Ready for implementation after Spec Kit analysis

**Input**: User request: «Продумать всю бизнес-логику повторной генерации и версий транскрипта, диаризации и итогов, включая автоматические и ручные сценарии, сохранение/замену версий, пользовательские состояния, системную и техническую реализацию, затем доработать, провести повторные review и полный release/deploy closeout».

## Clarifications

### Session 2026-07-23

- Независимый business-аудит, system-аудит и UX-аудит проведены read-only до
  реализации. Все три вывода требуют единого контракта immutable source/result,
  candidate и published current, а также защиты от stale-accept и deletion race.
- Владелец результата получает read-only preview candidate перед принятием.
  Preview не публикуется shared viewers и не используется export/share до
  явного `Использовать`.
- История и явный пользовательский `Вернуть предыдущую версию` остаются
  отдельным UX-срезом; серверная lineage и безопасная возможность внутреннего
  rollback должны быть заложены уже в этом срезе.
- По конституционному gate уточнена retention boundary: завершённые
  Generation Call, Langfuse observations и Temporal History сохраняются как
  plaintext observability под операторской policy, а контролируемые GRAF-копии
  meeting content проходят deletion/purge journal; ни одна из этих категорий
  не маскируется под другую.

## User Scenarios & Testing

### User Story 1 - Получить первый достоверный результат (Priority: P1)

Как владелец встречи, я хочу получить первые транскрипт, диаризацию и итоги
после завершения обработки, чтобы результат появился один раз и не порождал
дубликаты при повторном открытии встречи или перезапуске worker.

**Why this priority**: Это базовая ценность продукта и главный источник риска
лишних расходов, stale-данных и непредсказуемых состояний.

**Independent Test**: Для одной завершённой встречи повторить refresh, два
одновременных запроса, restart worker и transient provider failure; в системе
остаётся одна активная генерация на один входной fingerprint, а пользователь
видит правдивое состояние и может вернуться к результату.

**Acceptance Scenarios**:

1. **Given** принят immutable media revision и доступный transcript result,
   **When** для default format ещё нет успешного или активного запуска,
   **Then** система создаёт один baseline outcome candidate для точного
   `(source revision, result fingerprint, template version, generator/config)`.
2. **Given** baseline уже доступен или находится в работе, **When** владелец
   открывает встречу или обновляет страницу, **Then** новый запуск не создаётся.
3. **Given** provider временно недоступен, **When** срабатывает автоматический
   retry, **Then** retry ограничен количеством/временем, использует тот же
   idempotency key и после исчерпания оставляет понятный manual retry без
   изменения принятого результата.
4. **Given** transcript отсутствует, заблокирован политикой или встреча
   удаляется, **When** запускается baseline flow, **Then** внешняя генерация не
   вызывается, причина и следующий шаг остаются правдивыми.

### User Story 2 - Запросить другой вариант итогов (Priority: P1)

Как владелец встречи, я хочу явно выбрать формат или попросить новый вариант,
чтобы сравнить его с текущими итогами и не потерять принятую версию.

**Independent Test**: Создать вариант другого формата, закрыть страницу,
дождаться готовности, открыть preview, оставить текущие итоги и отдельно
принять новый вариант; в каждом шаге current остаётся корректным.

**Acceptance Scenarios**:

1. **Given** transcript result доступен, **When** owner выбирает другой
   доступный формат, **Then** создаётся один candidate, pinned к source/result,
   template key/version и generator/config; current не меняется.
2. **Given** owner выбирает тот же формат, **When** он не нажал явную команду
   `Обновить итоги`, **Then** дорогая генерация не запускается.
3. **Given** candidate queued/generating, **When** owner уходит, обновляет
   страницу или закрывает приложение, **Then** durable generation не отменяется,
   а при возврате можно безопасно продолжить проверку состояния.
4. **Given** candidate готов, **When** owner открывает его preview, **Then** он
   видит название формата, источник и безопасный read-only текст варианта, а
   current accepted остаётся отдельно видимым.
5. **Given** owner выбирает `Оставить текущие`, dismiss или reject, **Then**
   candidate не публикуется, current не меняется, а lineage попытки сохраняется.
6. **Given** owner выбирает `Использовать`, **Then** система атомарно проверяет
   ожидаемый current/source fence, публикует candidate, помечает прежний
   accepted outcome как superseded и возвращает новый current.

### User Story 3 - Безопасно пережить конкуренцию и stale candidate (Priority: P1)

Как владелец или участник, я хочу, чтобы параллельные вкладки, новый transcript
или новый accept не приводили к тихой замене старых итогов.

**Independent Test**: Запустить два candidate, принять один в другой вкладке,
изменить source result до accept второго и проверить, что stale action получает
409/понятное обновление без мутации данных.

**Acceptance Scenarios**:

1. **Given** candidate pinned к старому source/result hash, **When** source
   result или media revision меняется до accept, **Then** accept отклоняется
   без мутации current и предлагает обновить страницу.
2. **Given** другая вкладка уже приняла новый outcome, **When** текущая вкладка
   принимает старый candidate, **Then** действие отклоняется optimistic conflict,
   current остаётся новым.
3. **Given** два одинаковых запроса приходят одновременно, **Then** один
   idempotent candidate переиспользуется, а не создаются две оплачиваемые
   генерации.
4. **Given** поздний callback старого workflow, **When** его source/revision
   fence не совпадает с актуальным, **Then** callback не меняет meeting status,
   current result или outcome.

### User Story 4 - Обработать новый audio/transcript source (Priority: P1)

Как владелец встречи, я хочу повторно обработать новую или исправленную запись,
не теряя доказуемую историю предыдущего результата.

**Independent Test**: Создать новую immutable media revision и новый processing
run, проверить отдельные lineage/workflow/job/result, затем сравнить current до
и после явного принятия нового outcome.

**Acceptance Scenarios**:

1. **Given** новая media revision или подтверждённый reprocess request, **Then**
   создаются revision-scoped processing workflow/job/result records; старые
   records immutable и не переиспользуют external job другого source.
2. **Given** новый transcript result импортирован, **Then** старые transcript,
   diarization и outcomes остаются историческими, а новый baseline — отдельным
   candidate до политики публикации.
3. **Given** новый source появился после ручной правки/явного accept, **Then**
   автоматический процесс не переписывает current; пользователь видит новый
   вариант и явно принимает его.
4. **Given** reprocess повторно доставил тот же provider result hash, **Then**
   импорт идемпотентен и не создаёт дополнительные segments/outcomes.

### User Story 5 - Сохранить корректную lineage шаблонов и генераторов (Priority: P1)

Как владелец и оператор, я хочу понимать, каким источником, форматом и версией
генератора создан каждый вариант, чтобы старые итоги оставались воспроизводимыми.

**Independent Test**: Изменить personal template, обновить generator/config и
проверить, что старый outcome продолжает ссылаться на старую immutable версию,
а новый запрос использует новую.

**Acceptance Scenarios**:

1. **Given** personal template изменён, **Then** создаётся новая immutable
   template version; принятые outputs не regener­ate автоматически.
2. **Given** built-in template обновлён, **Then** старая версия остаётся
   доступной для исторического outcome, а новые requests используют новую
   версию по явной policy.
3. **Given** prompt/model/config deployment изменён, **Then** открытие или
   просмотр встречи не запускает silent regeneration; нужен новый source или
   явное действие/policy.
4. **Given** candidate status ready, **Then** visible и accessible copy называет
   формат варианта, а не только безличное `Новый вариант готов`.

### User Story 6 - Сохранить trust boundaries для shared, export и deletion (Priority: P1)

Как владелец продукта, я хочу, чтобы новые варианты не утекали через shared
просмотр, экспорт, observability или удаление и не возвращались после tombstone.

**Independent Test**: Проверить owner/shared access, export/share во время
candidate, delete-vs-generate race и post-delete worker callback на metadata-only
fixture.

**Acceptance Scenarios**:

1. **Given** candidate ещё не принят, **When** shared viewer открывает встречу,
   **Then** он видит только accepted current в пределах ACL, без candidate,
   template settings, raw prompt или internal error details.
2. **Given** export/share запущен во время candidate, **Then** он читает
   current pointer в момент действия и никогда не публикует candidate сам по
   себе.
3. **Given** deletion/retention/access revoke начались, **Then** generation,
   polling, accept и late import прекращаются или безопасно блокируются; deletion
   wins race.
4. **Given** generation/observability хранит transcript или provider payload,
   **Then** controlled GRAF copies follow the deletion workflow, while completed
   Generation Call, Langfuse and Temporal observability content remains retained
   under the operator-approved retention policy; the report names this boundary
   and never promises universal erasure outside GRAF control.

### User Story 7 - Понятно восстановиться после сбоя (Priority: P2)

Как владелец, я хочу получить один понятный следующий шаг после сетевого,
workflow или provider сбоя, не получая бесконечного polling и дубликатов.

**Independent Test**: Имитировать Temporal dispatch failure, worker restart,
provider timeout, hidden tab и expired candidate; проверить durable recovery и
bounded UI polling.

**Acceptance Scenarios**:

1. **Given** DB candidate committed, но Temporal start не удался, **Then** durable
   reconciler/outbox повторяет dispatch или переводит attempt в bounded failed;
   queued candidate не остаётся навсегда без workflow id.
2. **Given** worker перезапущен, **Then** существующий attempt resumes/retries по
   idempotency key, а current не меняется.
3. **Given** foreground polling достиг deadline или вкладка скрыта, **Then** UI
   останавливает частые запросы, оставляет `Проверить ещё`/`Обновить страницу`,
   а durable server generation продолжает жить.
4. **Given** candidate expired/failed, **Then** owner видит `Повторить` с
   bounded retry и не теряет current.

## Edge Cases

- Нет transcript, пустой transcript или только недостоверные segments.
- Две media revisions принимаются почти одновременно.
- Provider возвращает тот же result version с другим hash или другой version с
  тем же hash.
- Callback старого workflow приходит после нового workflow и после deletion.
- Candidate готов, но template archived/deleted или доступ к workspace отозван.
- Manual regeneration превышает quota/cost budget или provider недоступен.
- Один и тот же owner открывает несколько вкладок и принимает разные candidates.
- Shared viewer получает ссылку на candidate id или старый poll URL.
- Export/share запущен между optimistic check и commit accept.
- Delete storage purge частично завершён, DB transaction откатилась, или
  observability delivery задержалась.
- Восстановление после backup/restore должно сохранить lineage и current fence.
- Разные timezone/locale не должны менять идентичность revision или hash.

## Functional Requirements

### Source and result lineage

- **FR-001**: Каждая принятая media revision MUST быть immutable и иметь
  стабильный идентификатор, номер и fingerprint содержимого.
- **FR-002**: Каждый processing run MUST быть однозначно связан с одной
  `media_revision` и создавать отдельный immutable result identity; повторный
  run MUST NOT переписывать segments/result старого run in place.
- **FR-003**: Provider job, workflow, callback и retry MUST быть scoped к source
  revision/result fence; callback со старым fence MUST be ignored safely.
- **FR-004**: Result identity MUST include content/source hash and distinguish
  same provider version with changed payload from a true idempotent duplicate.
- **FR-005**: The published meeting state MUST use one authoritative current
  accepted pointer; list, detail, export, share and review MUST resolve the same
  pointer and MUST exclude queued/generating/rejected/superseded candidates.

### Regeneration and candidates

- **FR-006**: Automatic baseline generation MUST run only once per unique
  `(meeting, source revision, processing result fingerprint, default template
  version, generator/config fingerprint)` and MUST be idempotent.
- **FR-007**: Automatic retries MUST be bounded, classified by retryability and
  reuse the same candidate/idempotency key; permission, deletion, missing input,
  policy and invalid template errors MUST NOT auto-retry.
- **FR-008**: Viewing, reopening, refresh, prompt/model deployment or a transient
  UI error MUST NOT trigger silent regeneration or current replacement.
- **FR-009**: Manual regeneration MUST require owner authorization and an explicit
  format or `Обновить итоги` command; shared viewers MUST never dispatch it.
- **FR-010**: Every candidate MUST pin source revision/result hash, template
  identity/version, generator/config provenance, actor, creation time and
  lifecycle state.
- **FR-011**: Candidate preview MUST be read-only, owner-only, safe to render and
  clearly separated from current accepted content.
- **FR-012**: Accept MUST perform an optimistic source/current/deletion fence check
  and atomically publish exactly one candidate; stale accept MUST return a
  conflict without mutation.
- **FR-013**: Reject, dismiss, cancel or failed generation MUST preserve current
  accepted content and retain metadata-only lineage needed for audit/diagnostics.
- **FR-014**: An active equivalent candidate MUST be reused/deduplicated; a same
  format request MUST require explicit refresh intent and MUST NOT be launched by
  selector focus or page load.
- **FR-015**: Candidate lifecycle MUST have bounded expiry and a recoverable
  terminal state; a queued attempt MUST NOT remain indefinitely without a durable
  dispatch/reconciliation path.

### Version and template policy

- **FR-016**: Source revision, processing result, outcome variant, template
  version, prompt version and generator/config version MUST be represented as
  separate lineage axes; one version number MUST NOT ambiguously represent all.
- **FR-017**: Previous accepted outcomes MUST become `superseded` only after a
  new candidate is atomically accepted; no silent destructive overwrite is
  allowed.
- **FR-018**: Personal template edits MUST create immutable versions; built-in
  template versions MUST remain resolvable for historical outputs.
- **FR-019**: Historical outcomes MUST remain pinned to their source/template/
  generator provenance even when a template is archived or current policy changes.
- **FR-020**: User-facing history/compare/revert UI is out of scope for this
  slice, but server lineage MUST support a later history/revert slice without
  data migration that discards accepted outputs.

### Recovery and concurrency

- **FR-021**: External dispatch MUST be durable relative to the candidate commit;
  an outbox/reconciler or equivalent MUST recover the DB-committed request after
  Temporal/provider start failure.
- **FR-022**: Import, generation, accept and delete MUST use a shared deletion
  tombstone/epoch fence before and after external egress; late work MUST be
  idempotently discarded.
- **FR-023**: Concurrent creation of active workflow/job/candidate records MUST
  be protected by database-level uniqueness/locking scoped to the correct source
  identity, not a pre-check alone.
- **FR-024**: Upload parts and active upload sessions MUST preserve quotas and
  non-overlap under concurrent requests; this slice MUST either fix or explicitly
  exclude unrelated upload-storage races with a linked follow-up.
- **FR-025**: Foreground polling MUST be bounded, back off, pause while hidden and
  expose a manual recovery action without cancelling durable server work.

### Privacy, deletion and observability

- **FR-026**: Content-bearing Generation Call payloads, Langfuse observations
  and Temporal History MUST be explicitly classified as retained plaintext
  observability under the operator-approved retention policy for the internal
  MVP; they MUST NOT be mislabeled as metadata-only or silently deleted by
  meeting deletion. Ordinary logs, audit rows and committed evidence remain
  metadata-only.
- **FR-027**: Deletion status MUST distinguish controlled GRAF purge, backup
  expiry, retained Generation Call/Langfuse/Temporal content, external provider
  limits and metadata-only audit retention; copy MUST not promise universal
  erasure.
- **FR-028**: Shared/export/public paths MUST never expose candidate content,
  private prompt/config, provider credentials, signed URLs or raw diagnostic
  payloads.

### UX and accessibility

- **FR-029**: Candidate states MUST expose understandable labels: preparing,
  ready with format name, failed with next action, stale/conflict, expired and
  blocked; accepted current remains stable while candidate changes.
- **FR-030**: Stale/conflict resolution MUST offer an explicit `Обновить`
  action; an error-only state without recovery action is insufficient.
- **FR-031**: Owner candidate actions MUST be keyboard/VoiceOver reachable, use
  polite live updates, avoid focus theft and preserve focus on refresh.
- **FR-032**: Shared viewers MUST not receive controls or status that imply they
  can generate, preview or accept.

## Non-Functional Requirements

- **NFR-001**: No raw audio, transcript text, credentials, signed URLs, or private
  meeting content may enter committed specs, logs, screenshots or validation
  evidence.
- **NFR-002**: New behavior MUST preserve macOS system-audio-first capture,
  manual start/stop, local visibility, and the desktop/server credential boundary.
- **NFR-003**: All state transitions MUST be auditable with metadata-only event
  fields and stable problem codes.
- **NFR-004**: The implementation MUST add no new client framework or runtime
  dependency unless the plan proves the existing stack cannot satisfy the
  contract.
- **NFR-005**: Every external egress and destructive action MUST have a bounded
  timeout, retry classification, idempotency key and rollback/stop condition.
- **NFR-006**: Browser and embedded cabinet surfaces MUST remain behaviorally
  equivalent for owner/shared access and recovery states.

## Key Entities

- **Media revision**: immutable accepted source package with provenance,
  fingerprint, source kind and lifecycle state.
- **Processing run**: revision-scoped attempt to obtain a provider result.
- **Processing result**: immutable transcript/diarization/summary input with
  content hash, status and import provenance.
- **Outcome candidate**: a generated, not-yet-published result pinned to one
  processing result and template/generator configuration.
- **Accepted outcome**: the one published outcome selected by the authoritative
  meeting current pointer.
- **Template version**: immutable built-in or personal format definition.
- **Generation attempt/call**: retryable provider execution plus a retained
  plaintext Generation Call ledger entry for completed calls, governed by the
  operator retention policy; surrounding logs and evidence remain metadata-only.
- **Deletion fence**: monotonic lifecycle/tombstone marker invalidating late
  processing, generation, accept and export work.
- **Dispatch record**: durable handoff state between DB intent and external
  workflow/provider start.

## Assumptions

- The default initial generation remains deterministic/extractive until a later
  approved provider policy changes it.
- New source revisions may automatically prepare a candidate only when the
  workspace policy allows it; they never silently replace current accepted
  content. Manual regeneration is always available to the owner.
- A candidate preview is an owner-only read-only projection. The later history/
  compare/revert UI is a separate feature, not a reason to discard lineage now.
- Existing media, processing, outcome and deletion records are migrated
  forward; no destructive data reset is acceptable.
- The work begins from the current Feature 122 implementation but is a separate
  Spec Kit slice so the meeting-list contract is not silently broadened.

## Out of Scope

- Native capture/routing redesign or reintroduction of removed audio-driver
  architecture.
- A full history/compare/revert user interface.
- New provider integrations, model selection UI, billing/quota product, or
  organization-wide prompt optimization UX.
- Rewriting the entire cabinet or replacing HTMX/vanilla JavaScript.
- Universal deletion outside GRAF-controlled systems or provider guarantees that
  the product cannot verify.
- Production deployment before the implementation, review and release gates
  are green.

## Dependencies and Risks

- Existing Feature 121 recording-workflow contracts and Feature 122 meeting-list
  presentation contract must remain compatible.
- Postgres migrations and RLS policies must preserve workspace isolation and
  historical lineage.
- Temporal/MediaScribe failure semantics and deletion races are high-risk
  boundaries requiring focused integration tests and production rehearsal.
- Existing generation observability tables may contain content-bearing payloads;
  migration and retention decisions need explicit privacy review before code.

## Success Criteria

- **SC-001**: For every accepted source/result fingerprint, repeated opens,
  refreshes, worker restarts and duplicate requests create at most one active
  baseline candidate and one immutable result identity.
- **SC-002**: 100% of processing workflows/jobs/results and outcome candidates in
  the supported reprocess path have source revision/result fences and complete
  provenance sufficient to explain which output is current.
- **SC-003**: In concurrency tests, zero stale candidate accepts mutate current;
  every stale attempt returns a deterministic conflict and leaves accepted data
  unchanged.
- **SC-004**: In dispatch-failure and worker-restart tests, no committed queued
  candidate remains without a reconciled terminal/active state after the defined
  recovery window.
- **SC-005**: In delete-vs-generate race tests, no transcript/outcome/content
  reappears after tombstone; controlled content is purged or explicitly reported
  under the approved retention boundary.
- **SC-006**: Shared/export/public tests expose only accepted current content and
  never candidate preview or private generation provenance.
- **SC-007**: Owner UX tests achieve 100% completion for initial generation,
  manual format selection, candidate preview/accept, stale refresh and retry
  recovery using keyboard and VoiceOver-compatible controls.
- **SC-008**: Foreground polling stops by the bounded deadline/attempt budget and
  does not issue requests while the document is hidden.
- **SC-009**: Existing meeting-list, capture, upload, deletion, export and full
  repository validation suites remain green; no raw/private data appears in
  committed evidence.
- **SC-010**: Release closeout records migration compatibility, backup/restore
  rehearsal, rollback plan, production smoke and installed-app/server version
  evidence; no deployment is claimed without command output.

## Risk / Validation Lane

High-risk architecture and user-facing workflow. Full Spec Kit
specify→clarify→plan→checklist→tasks→analyze→taskstoissues→implement is
required. Mandatory gates cover privacy/security, deletion/retention, UX/accessibility,
Postgres/RLS, Temporal/MediaScribe, and release/deploy.
