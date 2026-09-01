# Feature Specification: Управляемое поэтапное retirement legacy

**Feature Branch**: `codex/228-legacy-retirement-process`
**Created**: 2026-08-31
**Status**: Draft — planning only; no runtime removal is authorized by this feature.

**Input**: После настройки общего Dev/CI/release процесса GRAF должен прекращать
накапливать legacy и безопасно уменьшать уже существующий долг. Владелец работает
параллельно с агентами в нескольких worktree; правила должны быть точными, но
контекст агента не должен содержать весь реестр или историю решений.

## Problem Statement

В репозитории уже есть обязательная декларация `Legacy Impact`, но нет принятого
реестра всех существующих compatibility-контуров, доказуемого срока их жизни и
единого способа выделить один контур в безопасный removal slice. Массовое
удаление сейчас небезопасно: часть контуров относится к миграциям, Temporal
history, историческим MediaScribe-данным, macOS/Sparkle update continuity или
production rollback. Одновременно рискованно помещать реестр и текущую задачу в
корневой `AGENTS.md`: это создаёт конфликт и тратит контекст каждой сессии.

## Actors and Goals

- **Владелец продукта** видит конечный список контуров, их риск, срок и
  последовательность безопасного retirement.
- **Feature agent** получает только контекст одного contour/slice и не может
  удалить чужую совместимость, данные или историю «заодно».
- **Reviewer** подтверждает классификацию, cutover/rollback и checklist quality;
  его отметки не меняются агентом.
- **Release operator** включает только готовые slices в замороженный release
  train и проводит один authoritative Full CI для точного candidate SHA.
- **Dev operator** репетирует только изолированные Dev/local операции и не
  изменяет production state, volumes или TCC.

## User Scenarios & Testing

### User Story 1 — Получить доказуемый реестр (Priority: P1)

Владелец получает детерминированный metadata-only реестр candidate legacy
контуров. У каждой записи есть происхождение, классификация, владелец, риск,
подтверждающая ссылка и состояние решения; поиск кандидата не означает, что его
разрешено удалять.

**Independent Test**: на одном exact SHA два запуска discovery/validation
выдают одинаковый отсортированный набор contour ID и digest; отчёт не содержит
секретов, raw audio, transcript или пользовательского текста.

### User Story 2 — Не создавать новое неучтённое legacy (Priority: P1)

Перед началом feature агент выбирает ровно одну декларацию `remove`,
`retain-with-exception` или `untouched`. Новая compatibility-ветка разрешена
только как узкое исключение с owner, expiry, removal trigger, риском, проверкой
и task/issue будущего удаления.

**Independent Test**: синтетический changed-path с alias/fallback/flag/fixture
или documentation path без полной декларации блокируется; валидное конечное
исключение проходит; просроченное — нет.

### User Story 3 — Подготовить независимый retirement slice (Priority: P1)

Для утверждённого `remove` contour создаётся отдельная небольшая Feature с
собственными Spec Kit artifacts, issue/PR, возможностью тестировать в Dev,
явной границей compatibility window, abort conditions и rollback target. Один
slice не редактирует соседние contours и не меняет root `CHANGELOG.md`.

**Independent Test**: template/validator отклоняет slice без contour ID,
exact-SHA evidence, migration/replay/signing condition (когда она применима),
rollback target или независимого validation command.

### User Story 4 — Сохранять контекст агентов ограниченным (Priority: P2)

Агент перед работой читает корневой routing, активные `spec.md`, `plan.md`,
`tasks.md`, `quickstart.md` и только scoped legacy guidance/registry record,
которые относятся к выбранному contour. Корневой `AGENTS.md` не содержит
активный feature, список всех legacy или детальные runbooks.

**Independent Test**: context validator принимает feature с path-scoped
ссылкой; он отклоняет mutable active-feature pointer в root `AGENTS.md` и
отсутствующую связь task → contour → issue.

### User Story 5 — Выпускать retirement только train-ом (Priority: P2)

Release operator может включить несколько уже смёрженных готовых slices в
редкий release train, но Full CI запускается один раз только после freeze
точного candidate SHA. Fast CI individual PR не признаётся release evidence.

**Independent Test**: release manifest связывает Feature IDs, contour IDs,
merged PRs, fragment digest, exact SHA и единственную authoritative Full CI
receipt; stale/cancelled/synthetic merge receipt отклоняется.

## Edge Cases and Failure States

- Один обнаруженный путь обслуживает текущий продукт и старую запись: он
  классифицируется `retain-with-exception` или сначала получает boundary slice,
  а не удаляется.
- Миграция, Temporal history, Sparkle/update trust или production rollback
  требует отдельного domain slice; inventory не даёт права на `stamp`, reset,
  удаление history, volume или deploy.
- GitHub, remote или local discovery недоступны: snapshot получает `blocked`;
  неполный отчёт не закрывает contour и не разрешает release.
- Изменился source SHA либо registry digest после validation: evidence stale и
  должно быть пересобрано.
- Истекло исключение или исчез owner/task: merge/release block fail-closed.
- В metadata попали content-bearing данные: запись исключается, отчёт признаётся
  unsafe и нуждается в исправлении generator/fixture.
- Ретirement нужен, но rollback отсутствует: contour остаётся blocked; это не
  основание продлить исключение без нового reviewer decision.

## Functional Requirements

- **FR-001**: Система MUST вести versioned metadata-only legacy registry на
  exact source SHA; кандидат и подтверждённый contour различаются статусом.
- **FR-002**: Каждая подтверждённая запись MUST иметь immutable contour ID,
  category, repository-relative source evidence, owner, risk rationale,
  classification, status, linked task/issue и validation evidence.
- **FR-003**: Registry MUST запрещать content-bearing поля: credentials,
  tokens, signed URLs, raw audio, transcript, logs с private meeting content и
  сырые database rows.
- **FR-004**: Повторный inventory на неизменном SHA MUST давать одинаковые
  ordering и digest; изменённый SHA/digest MUST помечать старое evidence stale.
- **FR-005**: Каждая feature/PR MUST содержать ровно одну Legacy Impact
  classification: `remove`, `retain-with-exception` или `untouched`.
- **FR-006**: `retain-with-exception` MUST иметь owner, ISO expiry в будущем,
  reason, exact compatibility boundary, removal trigger, risk, validation и
  linked retirement Feature/task/issue; неявное и бессрочное исключение MUST
  fail closed.
- **FR-007**: Изменение legacy-sensitive path MUST быть сопоставлено с Legacy
  Impact; scanner MUST отличать историческую документацию/evidence от новой
  активной compatibility-поверхности и не требовать false-positive cleanup.
- **FR-008**: Каждый `remove` contour MUST стать ровно одним primary retirement
  slice либо явно `blocked` с причиной; один slice MAY объединять контуры только
  при общей boundary, rollback и независимой проверке.
- **FR-009**: Retirement slice MUST иметь scope fence, owner, risk lane,
  compatible-client/data boundary, Dev rehearsal, abort conditions, rollback
  target, exact validation commands, known limitations и links на GitHub issue,
  PR и release evidence.
- **FR-010**: Slice для migrations MUST использовать отдельный
  expand/contract + isolated backup/restore contract; запрещены manual
  `alembic_version` edits, blind stamp/reset и production volume operations.
- **FR-011**: Slice для Temporal MUST иметь deterministic replay/idempotency
  evidence и history-retention decision; он не удаляет существующую history.
- **FR-012**: Slice для macOS/Sparkle MUST сохранять bundle identifier,
  Developer ID trust/designated requirement, notarized rollback и appcast
  continuity; он не публикует release без отдельного approved gate.
- **FR-013**: Legacy-compatible code, tests, fixtures и documentation MUST
  удаляться/обновляться в одном slice только после доказательства, что
  supported data/client boundary пройдена; новая feature не добавляет fallback
  «на всякий случай».
- **FR-014**: Root `AGENTS.md` MUST оставаться коротким routing surface;
  detailed policy живёт в one scoped guidance file, active ownership — в
  ignored `.specify/feature.json`, а task-specific contour context — в active
  Feature artifacts.
- **FR-015**: Feature agents MUST писать только `changes/unreleased/F<id>.yaml`;
  root `CHANGELOG.md` собирает только release operator на frozen candidate.
- **FR-016**: Release manifest MUST связывать inclusion contour/slice с
  exact merged SHA, PR/issue/task, changelog fragment digest и одной
  authoritative Full CI receipt; individual fast receipts не заменяют её.
- **FR-017**: Checklists остаются reviewer-owned; automation/agents MUST NOT
  отмечать требования checked и MUST NOT закрывать issue без evidence.
- **FR-018**: Feature 228 MUST NOT удалять runtime code, migrations, Temporal
  histories, customer data, volumes или legacy files; это program-planning
  slice, который создаёт только contracts, validators, guidance, fixtures и
  future task backlog после review.

## Success Criteria

- **SC-001**: 100% approved registry records содержат все обязательные поля
  FR-002, а их source paths contained и metadata-only.
- **SC-002**: Два inventory запуска на одном SHA дают идентичный digest и
  contour ordering; любые SHA/digest mismatch помечаются stale.
- **SC-003**: 100% synthetic incomplete/expired exceptions и unowned active
  legacy additions блокируются validator'ом; валидная finite exception проходит.
- **SC-004**: 100% approved `remove` contours имеют один linked retirement
  slice или machine-readable blocked reason; нет broad "cleanup all" task.
- **SC-005**: 100% migration/Temporal/macOS candidate contours имеют выбранную
  protected-domain category и не допускают generic deletion lane.
- **SC-006**: Проверка agent context доказывает, что root `AGENTS.md` не
  содержит active feature/registry list, а active Feature содержит точные
  path-scoped references.
- **SC-007**: Release candidate, включающий retirement slices, отклоняется без
  immutable Full CI evidence на exact candidate SHA и fragment manifest digest.
- **SC-008**: По завершении Feature 228 отсутствует удаление legacy runtime,
  production mutation или изменение reviewer-owned checkbox state.

## Scope

### In Scope

- Read-only inventory baseline, registry/exception/slice schemas, governance
  validators, fixtures, documentation, Spec Kit templates and issue backlog.
- Превращение предыдущего Feature 220 draft в актуальный, scoped и
  implementation-ready program, совместимый с Feature 216/222/227 process.
- Категоризация реальных observed candidates, включая historical MediaScribe
  compatibility, processing/normalization backfill, migration, Temporal и
  Sparkle/deploy boundaries, без решения удалить их заранее.
- Bounded agent-context routing и release-train traceability для future slices.

### Out of Scope

- Любое массовое или конкретное удаление legacy сейчас.
- Production deploy, database/volume reset, `alembic stamp`, Temporal history
  deletion, TCC reset, publication или изменение Apple signing trust.
- Изменение capture, auth, billing, transcription, deletion или user-visible
  product behavior без отдельного approved Feature.
- Закрытие GitHub issues, reviewer checklists или implementation commits.

## Assumptions

- Feature 216 Legacy Impact contract и текущие `release-and-validation.md`
  являются обязательной базой; Feature 228 усиливает, а не отменяет их.
- Feature 220 — полезный historical draft, но он не merged в текущую base и
  не является доказательством реального inventory или выполненного cleanup.
- `codex/206-legacy-cleanup` не содержит уникальных commits относительно
  текущей base; Feature 206 polling/recovery содержит protected historical
  compatibility и требует отдельной классификации, не revival старой ветки.
- Final removal decisions принадлежат owner/reviewer после inventory; отсутствие
  решения означает `blocked`, а не автоматическое удаление или продление.

## Legacy Impact

- **Classification**: `untouched`
- **Evidence**: Feature 228 меняет только process/specification surfaces;
  runtime legacy, data and supported compatibility paths не удаляются.
- **New legacy**: запрещён; любые новые compatibility paths требуют finite
  exception по FR-006.
- **Protected boundaries**: migrations, Temporal history, MediaScribe historical
  records, Sparkle/update continuity, Developer ID signing и production rollback
  остаются отдельными approved slices.
