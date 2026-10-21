# CI merge queue и provenance release train

**Feature ID**: `F227`

**Feature Branch**: `codex/227-ci-merge-queue-release-train`

**Created**: 2026-08-31

**Status**: Draft

**Umbrella issue**: [#6207](https://github.com/yshishenya/graf/issues/6207)

## Цель

Сделать проверку параллельных PR и выпусков достоверной: устаревший CI не
может считаться успешным, merge queue проверяет synthetic merge commit, а
release train связывает фактический SHA `master` с PR, Feature ID, CI receipt и
единственным authoritative Full CI.

## Уточнения

### Проверка применимости 2026-10-17

- Вопрос: нужен ли native merge queue для действующего выпуска? Ответ:
  действующая инструкция требует последовательных слияний с тремя обязательными
  проверками PR. Очередь — отдельный будущий этап; исходные T029/T031 остаются
  открытыми до настоящей проверки GitHub. Ни локальные тесты, ни служебный
  коммит выпуска не подтверждают этот этап.
- Вопрос: откуда берётся synthetic SHA при последовательном выпуске? Ответ:
  `scripts/release.sh` создаёт настоящий отдельный Git-коммит с деревом source
  и родителями base/source. Это метаданные происхождения, не событие очереди.
  При отсутствии очереди обе коллекции merge-group остаются пустыми.
- Вопрос: может ли происхождение synthetic заменить происхождение source?
  Ответ: нет; base обязательно является предком фактического source независимо
  от служебного коммита. Неполная история Git блокирует заморозку.
- Вопрос: нужна ли новая матрица Python? Ответ: закреплённый harness v0.1.13
  проверен на Python 3.9/3.12; проверка других версий здесь не заявляется.

## User Scenarios & Testing

### US1 — Проверить PR или merge queue на правильном SHA (P0)

Разработчик получает быстрый CI для PR, а merge queue получает отдельную
проверку synthetic merge SHA. Каждая проверка явно показывает событие, target
SHA, base SHA и принадлежность к PR/merge group.

**Why this priority**: без этого зелёный результат может относиться к другой
версии кода и блокирует безопасное слияние.

**Independent Test**: contract tests и GitHub workflow validation моделируют PR,
manual и `merge_group` события и проверяют checkout exact SHA и metadata-only
receipt.

**Acceptance Scenarios**:

1. **Given** PR с head SHA, **When** запускается PR workflow, **Then** checkout и
   evidence содержат только этот SHA и соответствующий base SHA.
2. **Given** merge queue synthetic SHA, **When** приходит `merge_group`, **Then**
   workflow проверяет synthetic SHA и сохраняет merge group ID и список PR.
3. **Given** отсутствующий или неподдержанный target SHA, **When** workflow
   стартует, **Then** он завершается fail-closed без успешного evidence.

### US2 — Не принять устаревший или дрейфующий CI (P0)

Разработчик видит, что новый commit отменяет старый запуск того же target, а
изменение дерева после тестов делает receipt stale/ambiguous.

**Why this priority**: устраняет гонку, при которой CI заканчивается после
появления нового коммита и его результат ошибочно используется дальше.

**Independent Test**: negative tests проверяют superseding run, cancellation,
изменение SHA и появление tracked/untracked файлов после последнего stage.

**Acceptance Scenarios**:

1. **Given** два запуска одного PR, **When** второй получает новый commit,
   **Then** старый run отменяется и не считается успешным evidence.
2. **Given** рабочее дерево изменилось после тестов, **When** формируется receipt,
   **Then** итог имеет `stale` или `ambiguous` и не проходит release validator.
3. **Given** повторный запуск того же target, **When** он использует canonical
   concurrency key, **Then** он отменяет только предыдущий запуск этого target.

### US3 — Выпустить редкий release train с одной полной проверкой (P0)

Release operator собирает несколько одобренных PR в train, фиксирует фактический
post-merge SHA `master`, запускает один authoritative Full CI и получает
воспроизводимый tag/Release decision.

**Why this priority**: Full CI должен запускаться редко, но результат должен
покрывать ровно то, что будет выпущено.

**Independent Test**: schema/validator tests и release-candidate rehearsal
проверяют train manifest, receipts, changelog digest, Full CI и stale SHA.

**Acceptance Scenarios**:

1. **Given** merged train с несколькими PR, **When** operator freezes candidate,
   **Then** manifest содержит train ID, PR, Feature ID, base/synthetic SHA и
   фактический SHA `master`.
2. **Given** Full CI evidence другого SHA или второго запуска того же candidate,
   **When** выполняется `decide`, **Then** решение — `no-go`.
3. **Given** approved immutable decision, **When** создаётся release, **Then** tag,
   GitHub Release, русские notes и rollback target связаны с одним SHA.

## Edge Cases

- GitHub Actions отключены или workflow ещё не попал в `master`: merge enforcement
  остаётся выключенным, локальный receipt не объявляется required check.
- `merge_group` не содержит PR mapping или base SHA: run блокируется.
- Новый commit появляется во время Full CI: candidate становится stale, создаётся
  новый candidate; старое evidence не переиспользуется.
- Отмена workflow завершается после записи промежуточного файла: receipt имеет
  terminal non-success status и не проходит validator.
- Генерация evidence оставляет untracked файл: final cleanliness gate блокирует
  release receipt, кроме явно разрешённых metadata-only paths.
- Synthetic merge SHA отличается от post-merge SHA `master`: оба сохраняются,
  но production release разрешён только для фактического post-merge SHA.

## Requirements

- **FR-001**: Workflow MUST resolve target SHA from the event type: PR head SHA,
  merge-group synthetic SHA или явно переданный manual SHA; unknown values MUST
  fail closed.
- **FR-002**: Workflow MUST checkout and verify the exact target SHA and record
  event name, workflow, run ID, run attempt, URL, target SHA and base SHA.
- **FR-003**: `merge_group` validation MUST preserve merge-group ID and resolve
  the complete PR mapping through an authoritative GitHub API; missing or
  ambiguous mapping MUST fail closed without treating synthetic SHA as the
  eventual release SHA.
- **FR-004**: PR, manual and merge-group runs MUST use deterministic concurrency
  keys; superseded/cancelled runs MUST never yield successful evidence.
- **FR-005**: CI MUST perform a final tracked and untracked cleanliness check
  after all tests and artifact generation, allowing only documented temporary
  metadata paths.
- **FR-006**: CI receipt MUST be metadata-only and include terminal conclusion,
  supersession/cancellation state and local evidence digest.
- **FR-007**: Release-train manifest MUST bind train ID, actual post-merge SHA,
  base/synthetic SHA, included PRs, Feature IDs, receipts, changelog digest,
  authoritative Full CI and rollback target.
- **FR-008**: `release-candidate.sh` MUST reject missing, stale, mismatched or
  duplicate authoritative evidence and MUST create a new candidate after SHA
  drift.
- **FR-009**: Required GitHub checks MUST be enabled only after the workflow
  is present on `master` and its stable check names are verified. Native merge
  queue is a separate operator-owned future gate: all required workflows and
  authoritative PR mapping MUST pass a real `merge_group` rehearsal first.
  Serial merges remain the current operating mode.
- **FR-010**: Generic event/receipt schemas and validators MUST be portable to
  `graf-development-harness`; GRAF-specific capture, privacy, signing, Temporal
  and production gates MUST remain project-local.

- **FR-011**: Release freeze MUST require `base_sha` to be an ancestor of actual
  `source_sha`; an ancestor relationship to `synthetic_merge_sha` alone MUST NOT
  satisfy this gate. All three SHAs MUST resolve to local commits; source and
  synthetic MUST remain distinct. Serial trains MUST use empty merge-group
  collections without inventing queue evidence.

## Success Criteria

- **SC-001**: 100% of PR and merge-group receipts contain matching requested,
  checked-out and final target SHA; mismatch rate is zero in regression tests.
- **SC-002**: Every superseded or cancelled run is rejected by the release
  validator and cannot satisfy a required check.
- **SC-003**: A worktree drift introduced after tests is detected before receipt
  publication in 100% of injected-failure tests.
- **SC-004**: One release train can include at least 3 approved PRs while running
  exactly one authoritative Full CI for the frozen post-merge candidate.
- **SC-005**: A release decision is reproducible from its immutable manifest,
  receipts, changelog digest and exact tag commit without private data.
- **SC-006**: Generic harness self-tests pass on supported Python versions and
  contain no GRAF-specific secrets, private paths, audio or transcript content.

- **SC-007**: An isolated Git rehearsal accepts the real serial operator flow
  with three PRs and empty queue collections; an unrelated base is rejected even
  when it is an ancestor of the synthetic commit. Rejection creates no train or
  immutable identity record.

## Assumptions

- GitHub Actions and three strict required PR checks are active. Native merge
  queue is not active; its platform availability must be established separately
  before any operator-owned activation. Empty API history is not proof of
  platform unavailability.
- PR titles, issue labels and Spec Kit pointers carry the existing Feature ID
  canon.
- A release train records synthetic merge SHA and final `master` SHA separately.
- Full CI remains the release-only gate; fast CI remains bounded PR feedback.
- No production deployment, migration mutation or legacy deletion is part of
  this feature.

## Out of Scope

- Production deployment execution and Apple notarization changes.
- Capture, privacy, auth, storage, Temporal or worker behavior changes.
- Deleting legacy paths; retirement remains in Feature 220 and later slices.
- Enabling branch protection before the workflow is merged and verified.

## Legacy Impact

Classification: `untouched`

owner: platform

expiry: none

removal trigger: not applicable; no legacy path is preserved or added

retirement task: not applicable

risk: governance-only change could accidentally preserve stale CI behavior

validation: exact-SHA, stale-run, final-cleanliness and release-train tests

reason: the feature changes process metadata and gates without adding product
fallbacks, aliases or compatibility paths.
