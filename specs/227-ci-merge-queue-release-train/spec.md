# CI merge queue и provenance release train

**Feature ID**: `F227`

**Feature Branch**: `codex/227-ci-merge-queue-release-train`

**Created**: 2026-08-31

**Status**: Завершающая сверка принятого объёма; закрытие трекера ожидает PR

**Umbrella issue**: [#6207](https://github.com/yshishenya/graf/issues/6207)

## Цель

Сделать проверку параллельных PR и выпусков достоверной: устаревший CI не
может считаться успешным, merge queue проверяет synthetic merge commit, а
release train связывает фактический SHA `master` с PR, Feature ID, CI receipt и
единственным authoritative Full CI.

## Уточнения

### Завершающий объём — 28.10.2026

Это решение заменяет прежнее намерение внедрить native merge queue в нынешнем
репозитории. `yshishenya/graf` — публичный репозиторий личного аккаунта
(`owner.type=User`); GitHub предоставляет merge queues репозиториям организаций.
Источник и точная цитата сохранены в research §R9. Отсутствие событий очереди
само по себе не является основанием решения.

- T015/#6222: подтвердить исходную гарантию stale/superseded через действующие
  producer/consumer пути. Добавить только недостающую отрицательную проверку
  `validate-pr-checks.py`: при успешных совпадающих run/job/head/base/attempt
  валидный по схеме non-passed receipt отвергается именно конечным потребителем.
  Положительный passed остаётся успешным. Производственный код менять не нужно.
- T016/#6223: отменить дополнительное ручное дублирование URL/base/receipt в
  описании PR. Обязательный Exact source SHA, trusted metadata, существующий
  шаблон и проверка настоящих артефактов общим consumer сохраняются.
- T028/#6235: тот же `ci-local.sh --fast` на GitHub runner с event base выполняет
  исходный функциональный результат exact-SHA fast. Нужны focused, workflow lint
  и настоящие обязательные checks. Непроведённый повтор на Mac не заявляется.
- T029/#6236 и T031/#6274: отменить оставшиеся подготовку и настоящую приёмку
  native queue для нынешнего личного MVP. Действующий последовательный PR путь,
  fail-closed mapping и все условные требования merge_group сохраняются.
  Fixtures не считаются живой приёмкой. Вернуться к этому объёму только при
  подтверждённой доступности очереди и конкретной потребности; перед включением
  нужны новый актуальный план, настоящие положительные/отрицательные сценарии,
  authoritative membership, expected-state, полномочия и проверенный откат.
- T030/#6237 остаётся обязательной: полная сверка всех исходных задач и детей,
  converge без скрытого обязательного дефекта. Общая #6207 закрывается последней
  как NOT_PLANNED смешанного исходного плана, а не как реализованная очередь.

Все 33 исходные строки и владельцы сохраняются. Отменённые T016/T029/T031
остаются `[ ]`; для COMPLETED нужны индивидуальные live-closeout проверки.
Решение вступает в силу после независимого ревью и принятия PR; до этого
перечисленные задачи и закрытие общей issue не объявляются принятыми.

### Идентичность общей issue — 29.10.2026

При итоговой сверке найден отдельный остаток трекера: #6207 всё ещё обозначена
временной T000, которой нет в tasks.md. T030 регистрирует этот остаток;
новая T034 исправляет только заголовок и поле `Spec tasks` существующей #6207.
Исходные заголовок и поле T000 сохраняются в датированном комментарии, остальные
критерии и история — без изменений. Владельцы исходных задач не меняются;
#6237 остаётся единственным владельцем T030. Новая issue не создаётся.
T034 не выполняет отменённую очередь и не повторяет сверку детей T030.
Общая #6207 остаётся открытой до принятия результата и закрытия всех детей,
затем закрывается NOT_PLANNED по смешанному решению выше.

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

### Уточнение T014 / #6221 — 28.10.2026

Известный шагу формирования квитанции `job.status=failure` или `cancelled`
имеет приоритет над уже сохранённым локальным PASS. При `success` сохраняется
фактический локальный статус, включая `stale`, `superseded` и другие отказы;
отсутствие evidence или неизвестный статус задания не разрешают PASS.
Поля `conclusion`, `cancellation_state`, `supersession_state` формирует уже
существующий `scripts/emit-ci-receipt.py`: переносить или дублировать их ради
старого пути T014 не требуется. Исходная задача и её владелец сохраняются.

Квитанция описывает известное состояние при её формировании. Отмена или ошибка
последующего шага может произойти позже; перед принятием результата общий
`validate-pr-checks.py` обязан отдельно подтвердить фактические успешные run/job
GitHub, точные SHA/base и попытку запуска. Синтетическая проверка workflow не
заменяет настоящий GitHub run, native queue rehearsal или выпуск.

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
4. **Given** готовое локальное evidence с PASS, **When** шаг формирования
   квитанции уже знает `failure`/`cancelled`, **Then** evidence квитанции и её
   `status`/`conclusion` показывают соответственно `failed`/`cancelled`,
   исходный локальный файл не перезаписывается, и PASS не публикуется.

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
- Известная при формировании квитанции отмена перекрывает промежуточный PASS.
  Более поздняя отмена отклоняется доверенной проверкой фактических run/job
  GitHub; файл из предыдущего шага не доказывает окончательный успех workflow.
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
  queue is outside the accepted personal-repository scope; before any future
  activation all required workflows and
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
