# Feature Specification: Полноценная изолированная Dev-среда GRAF

**Feature Branch**: `codex/229-dev-runtime-full-stack`

**Created**: 2026-09-01

**Status**: Draft

**Input**: Issue [#6276](https://github.com/yshishenya/graf/issues/6276) и live blocker из Feature 227

**Risk / Validation Lane**: `high-risk-feature` — инфраструктура, Docker, Postgres, Temporal, workers, миграции, подписанное macOS-приложение и rollback.

## Контекст и цель

GRAF должен иметь одну воспроизводимую локальную Dev-среду, в которой можно
проверить связный пользовательский путь от подписанного `GRAF Dev.app` через
server-rendered frontend и backend до Temporal, processing worker, media worker,
Postgres и MinIO. Текущая локальная команда запускает только Postgres/MinIO и
backend с отключённой обработкой, поэтому live smoke не доказывает основной
processing-путь. Дополнительный риск создаёт старая локальная база с revision,
которой нет в текущем checkout.

Цель этой фичи — сделать такой runtime единственным активным Dev-кандидатом на
машине, привязать все его компоненты к одному exact Git SHA, безопасно отделить
его состояние от production и старого local state и обеспечить атомарные
promotion/rollback. Фича не меняет продуктовую семантику записи, приватности,
аутентификации или обработки встреч.

## User Scenarios & Testing

### User Story 1 — Проверить полный стек одной командой (Priority: P1)

Разработчик выбирает чистый checkout конкретного SHA и получает один Dev-
кандидат, в котором frontend, backend, Temporal, processing worker, media
worker, Postgres, MinIO и одна `GRAF Dev.app` собраны из одного источника. Он
может открыть локальный кабинет и выполнить smoke без ручного запуска
несвязанных сервисов.

**Why this priority**: без полного runtime невозможно честно тестировать фичи,
которые проходят через backend и workers; это прямой блокер Dev validation.

**Independent Test**: на чистом disposable Dev state выполнить `build`,
`promote`, затем `smoke`; все обязательные проверки должны пройти, а
production app и production data — остаться неизменными.

**Acceptance Scenarios**:

1. **Given** чистый checkout с exact SHA и доступными Docker/uv/signing
   identity, **When** оператор выполняет `build → promote → smoke`, **Then**
   поднимаются API, server-rendered frontend, Temporal и оба worker-пути, а
   smoke сообщает PASS для каждого обязательного компонента.
2. **Given** один активный Dev-кандидат, **When** разработчик открывает
   `http://127.0.0.1:<port>/login`, **Then** страница обслуживается тем же
   backend-origin и использует Dev-конфигурацию без production endpoint или
   credentials.
3. **Given** worker или Temporal не готов, **When** выполняется smoke, **Then**
   кандидат получает terminal blocked/fail результат и не становится active.

### User Story 2 — Безопасно изолировать состояние и миграции (Priority: P1)

Разработчик может запускать Dev независимо от production и исторического local
state. Если в выбранном состоянии нет совместимого migration graph, система
останавливается до запуска приложения и сообщает, как создать новый Dev
namespace; существующее состояние не удаляется и не исправляется ручным
изменением revision.

**Why this priority**: пересечение volume, портов, credentials или миграций с
production может привести к потере данных или ложному зелёному smoke.

**Independent Test**: направить Dev на фиктивный старый database state и
проверить, что preflight возвращает понятный fail-closed результат до запуска
API/workers, а production bundle, volumes и старый local state не меняются.

**Acceptance Scenarios**:

1. **Given** Dev state с migration revision, отсутствующей в текущем graph,
   **When** оператор запускает promotion, **Then** preflight блокирует запуск,
   указывает mismatch и безопасный путь к новому Dev namespace, не выполняя
   `alembic stamp`, не редактируя `alembic_version` и не удаляя старый state.
2. **Given** работающий production app или production-like environment variable,
   **When** оператор запускает Dev adapter, **Then** команда завершается до
   подключения к production origin, data root, volume или credential.
3. **Given** параллельно существующий старый local state, **When** создаётся
   новый Dev candidate, **Then** используются отдельные Compose project/volume
   names, loopback ports и data root, а старый state остаётся доступным для
   диагностики или ручного удаления владельцем.

### User Story 3 — Атомарно переключать и откатывать Dev-кандидата (Priority: P1)

Разработчик может безопасно заменить активный Dev SHA после проверки нового
кандидата. При ошибке установки, запуска или smoke предыдущие приложение,
runtime и active manifest сохраняются; при необходимости оператор выполняет
rollback к ранее проверенному кандидату.

**Why this priority**: одна Dev app и один loopback runtime требуют
сериализованного переключения; частичная promotion иначе оставит машину в
неопределённом состоянии.

**Independent Test**: подготовить два кандидата, внедрить ошибку на каждом
этапе promotion, затем проверить сохранность предыдущего active manifest и
успешный rollback с последующим smoke.

**Acceptance Scenarios**:

1. **Given** активный кандидат A и подготовленный кандидат B, **When** B
   проходит все проверки, **Then** active manifest, runtime и
   `/Applications/GRAF Dev.app` атомарно указывают на B.
2. **Given** promotion B завершилась ошибкой до smoke или во время smoke,
   **When** операция заканчивается, **Then** A остаётся active и его runtime
   может быть восстановлен без ручного удаления файлов.
3. **Given** активный B и сохранённый parent A, **When** оператор выполняет
   rollback, **Then** приложение и полный runtime возвращаются к A, после чего
   smoke подтверждает его exact SHA и identity.
4. **Given** два одновременных оператора promotion/rollback, **When** они
   используют один Dev state, **Then** lock сериализует операции и ни одна из
   них не перезаписывает чужой manifest или процесс.

## Edge Cases and Failure Handling

- Checkout грязный, detached или его `HEAD` не равен `source_sha`: build и
  promotion блокируются до исправления checkout.
- Один SHA собран в двух worktree с разными manifest parent: устаревший
  candidate отклоняется; повторная сборка выполняется от текущего active
  manifest.
- Compose config невалиден, image build не завершён, порт занят или health
  check истёк: active pointer не меняется, ошибка содержит компонент и
  безопасное следующее действие.
- Temporal готов, но processing/media worker не зарегистрировал обязательный
  task queue: readiness остаётся fail; частично рабочий runtime не считается
  smoke PASS.
- В старом Dev state отсутствует revision, несколько heads обнаружены либо
  migration command аварийно завершился: запуск блокируется; revision не
  угадывается.
- `/Applications/GRAF Dev.app` отсутствует, имеет другой bundle ID,
  designated requirement или signing identity: promotion блокируется до
  сохранения предыдущего приложения.
- Runtime record содержит чужой PID или не подтверждается command/start token:
  process не завершается автоматически; требуется ручная проверка владельца.
- Оператор пытается использовать public/production endpoint, secret, signed URL,
  raw audio или transcript в evidence: операция блокируется и сохраняет только
  metadata-only receipt.

## Requirements

### Functional Requirements

- **FR-001**: Dev adapter MUST orchestrate one documented local runtime that
  includes API, server-rendered frontend, Temporal, processing worker, media
  worker, Postgres, MinIO and migration/init steps; the Dev processing path MUST
  not inherit `processing_enabled=false`.
- **FR-002**: Build MUST require a clean checkout and bind manifest, backend,
  frontend, worker images/runtime and macOS app to the same full 40-character
  `source_sha`; a mismatch MUST fail closed before promotion.
- **FR-003**: Dev Compose project name, volume names, network names, ports and
  data root MUST be explicitly namespaced for the single Dev runtime and MUST
  be distinct from production and the historical local runtime.
- **FR-004**: Dev configuration MUST expose only loopback origins and MUST
  reject production/staging environment variables, origins, credentials,
  signed URLs and production app/data paths.
- **FR-005**: Migration preflight MUST compare the database revision and current
  migration graph before API or workers become ready; unknown, missing,
  divergent or multiple heads MUST produce a terminal blocked result with an
  actionable safe-new-state instruction.
- **FR-006**: Migration recovery MUST NOT call `alembic stamp`, directly edit
  `alembic_version`, use `docker compose down -v`, or delete an old Dev/local
  state as an implicit repair.
- **FR-007**: The only installed Dev app MUST be `/Applications/GRAF Dev.app`
  with bundle ID `pro.2brain.graf.dev`, channel `dev`, a stable designated
  requirement/signing identity, no production updater metadata and explicit
  loopback cabinet/upload origins.
- **FR-008**: Promotion MUST take the existing Dev lock, validate candidate
  parent and component identity, stage the app/runtime, run smoke, and update
  the active manifest only after all required checks pass.
- **FR-009**: A failed or cancelled promotion MUST leave the previous active
  manifest, app and owned runtime recoverable; compensation MUST refuse to
  signal unowned processes.
- **FR-010**: Rollback MUST select a previously validated parent or explicitly
  selected manifest, require checkout of its exact SHA, restore app and runtime
  atomically and run the same smoke checks before declaring success.
- **FR-011**: Live smoke MUST check API liveness/readiness, server-rendered
  `/login`, auth provider bootstrap, representative API route, database and
  storage readiness, migration readiness, Temporal readiness, processing
  worker readiness, media worker readiness, app bundle identity and exact
  source SHA. Aggregate worker health MUST NOT replace the named checks.
- **FR-012**: Dev receipts and logs MUST be metadata-only and MUST NOT contain
  secrets, credentials, raw audio, transcript text, signed URLs or private
  meeting content.
- **FR-013**: Build, promotion, smoke, status and rollback MUST be idempotent
  where the requested manifest is already active; stale parent or malformed
  manifest MUST be rejected without pointer mutation.
- **FR-014**: The feature MUST NOT execute production deploy/migration,
  change capture/privacy/auth semantics, publish a product release, or perform
  mass legacy deletion.

### Key Entities

- **Dev candidate manifest**: immutable metadata binding Feature ID, exact source
  SHA, component digests/versions, migration head, app identity, Dev boundary,
  parent manifest and health result.
- **Dev active pointer**: one atomic pointer to the active manifest and runtime
  mode for the machine-local Dev channel.
- **Dev runtime namespace**: Compose project, containers, networks, volumes,
  ports and data root owned by this feature's Dev adapter.
- **Migration preflight result**: metadata-only result containing expected graph
  head(s), observed database revision, comparison status and safe next action.
- **Runtime ownership record**: PID, exact launch command, start identity and
  source SHA sufficient to avoid signalling an unrelated process.
- **Promotion transaction**: staged app/runtime operation with previous-state
  snapshot, candidate smoke result, commit point and compensation result.

## Success Criteria

### Measurable Outcomes

- **SC-001**: On a clean supported macOS checkout and clean Dev state, one
  documented `build → promote → smoke` run reaches a PASS result for API,
  frontend, Temporal, processing worker, media worker, database/storage and app
  identity without a second manual service startup.
- **SC-002**: In 100% of contract and injected-failure tests, every component
  digest/source identity and the installed app metadata equal the requested
  full 40-character SHA; no mixed-SHA candidate is accepted.
- **SC-003**: In 100% of migration-mismatch tests, API/workers do not become
  ready, no manual revision mutation is performed, and the prior state digest
  is unchanged.
- **SC-004**: Across at least 10 repeated promotions of valid candidates, the
  machine has at most one installed `GRAF Dev.app`, exactly one active pointer,
  and stable bundle ID/designated requirement/signing identity.
- **SC-005**: Every injected failure before or during promotion leaves the
  previous active manifest and app recoverable; a valid rollback returns to a
  smoke-PASS state without production path access.
- **SC-006**: Two concurrent promotion attempts on one Dev state produce one
  serialized outcome, no pointer corruption and no signal to an unowned PID in
  100% of lock/ownership tests.
- **SC-007**: A repository governance check can prove that Dev evidence contains
  no secret, raw audio, transcript text, signed URL or production-looking path.

## Assumptions and Dependencies

- F227's generic manifest, lock and metadata-only harness remain the source of
  generic contracts; this feature owns the GRAF-specific Compose/runtime adapter.
- Server-rendered frontend remains on the backend origin for this slice; a
  second frontend server is not invented.
- Dev worker processes are started and readiness-tested locally, while calls to
  external MediaScribe/LiteLLM/Langfuse remain disabled or explicitly opt-in
  under existing secret custody rules.
- Docker, `uv`, Swift 6/macOS 14+, local signing identity and loopback ports are
  available on the developer Mac.
- A fresh isolated Dev namespace may require a one-time explicit operator action
  to initialize an empty database; this is not permission to erase old state.
- F227 PR #6275 and its workflow/operator gates may still be pending. This
  feature can be planned and validated locally before those gates are complete,
  but it must not claim remote merge-queue proof prematurely.

## Out of Scope

- Production deployment, production migration, backup/restore execution or
  public product release.
- Changes to recording, capture, privacy, auth, deletion or external provider
  product semantics.
- A second installed Dev application, per-worktree installed apps or a public
  staging environment.
- Mass legacy deletion; retirement remains a later controlled slice and new
  legacy additions remain forbidden by the existing process.
- Public notarization, Sparkle publication or changing production updater
  metadata.

## Legacy Impact

Classification: `retain-with-exception`

owner: `dev-runtime`

expiry: 2026-10-31

removal trigger: Feature 229 reaches clean-state smoke PASS; then a separate
reviewed retirement slice removes the old adapter only after rollback evidence

retirement task: Feature 228 issue #6238, task T000; this feature only makes
the old path non-active and must not delete its state

risk: preserving the old processing-disabled adapter would make tests appear
green while omitting the worker/Temporal path; reusing its state could cross
data boundaries

validation: contract tests, clean-state live smoke, migration mismatch fixture,
production-boundary scan, promotion failure injection and rollback smoke

reason: the superseded adapter is an incomplete Dev runtime path. It remains a
bounded, non-active compatibility exception until the isolated full-stack
adapter is proven; no new caller or fallback may be added.

## Clarifications

### Session 2026-09-01

- Q: Should the frontend be a second independently deployed local server? → A:
  No; retain the server-rendered frontend on the backend origin for this slice.
- Q: How should Dev state be isolated from the existing local state? → A: Use a
  dedicated Compose project, explicitly named volumes/networks/ports and a
  machine-local Dev data root; preserve old state without implicit deletion.
- Q: What should happen when the stored migration revision is not in the
  current graph? → A: Stop before application readiness, report the mismatch and
  offer a safe empty namespace; never stamp or edit the revision manually.
- Q: What app identity is allowed for the Dev channel? → A: Exactly one
  `/Applications/GRAF Dev.app` with bundle ID `pro.2brain.graf.dev`, stable
  designated requirement/signing identity and loopback-only origins.
  - Q: Should external provider calls be required for the first local smoke? → A:
  No; start and readiness-test the workers, while provider calls remain disabled
  or explicit opt-in under existing secret-custody rules.
