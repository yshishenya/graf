# Tasks: Единый процесс разработки и переносимый harness

**Input**: Design documents from `specs/216-development-governance-harness/`

**Prerequisites**: `spec.md`, `research.md`, `plan.md`, `data-model.md`,
`contracts/`, reviewer-owned checklists

**Risk / Validation Lane**: `significant-feature`; no product deploy

**Umbrella**: GitHub issue #6090

## Phase 1 — Setup and source-of-truth boundaries

**Purpose**: создать безопасный каркас, не меняя продуктовый runtime и чужие
worktree.

- [ ] T001 Провести preflight Feature 216: проверить `origin/master`, ветку,
  чистоту worktree, `.specify/feature.json`, umbrella issue #6090 и отсутствие
  коллизий ID в `scripts/claim-feature.py` (FR-001–FR-003).
- [ ] T002 Зафиксировать в `docs/agent-guidance/development-process.md` роли,
  ownership matrix, полный Spec Kit/Ponytail порядок, risk lanes и правило
  explicit approval для implementation commit (FR-033–FR-036).
- [ ] T003 [P] Добавить в `changes/unreleased/README.md` schema, namespace,
  ownership и lifecycle changelog fragments без изменения корневого
  `CHANGELOG.md` (FR-009).
- [ ] T004 [P] Добавить project-local `harness/README.md` с границей generic
  core и GRAF adapter, запретом секретов и правилами контекста (FR-030–FR-031).

## Phase 2 — Feature identity and bounded agent context

**Purpose**: устранить повторные номера и неправильную загрузку контекста.

- [ ] T005 [US4] Написать `scripts/claim-feature.py` на stdlib: сканировать specs,
  local/remote refs, GitHub reservation input, проверять collision и выдавать
  immutable claim manifest (FR-001, FR-002, FR-003).
- [ ] T006 [US4] Добавить self-test к `scripts/claim-feature.py` для параллельных
  claims, занятого remote номера, повторного claim и offline draft (SC-001).
- [ ] T007 [US7] Обновить `.specify/feature.json` contract и
  `docs/agent-guidance/codex-worktrees.md`: active pointer обязателен,
  mtime fallback запрещён, owner/branch/spec/SHA проверяются preflight,
  один worktree принадлежит одной feature и одному owner (FR-005, FR-006,
  FR-007, FR-008).
- [ ] T008 [P] [US7] Добавить `scripts/validate-agent-context.py` и negative fixtures
  для отсутствующего pointer, чужого feature directory и dynamic root plan
  pointer (FR-004–FR-006, SC-008).
- [ ] T009 [US7] Обновить managed guidance в `AGENTS.md` и
  `docs/agent-guidance/spec-kit-flow.md`, оставив только стабильные правила,
  ссылки на active pointer и короткий bounded-context protocol (FR-004–FR-006).
- [ ] T010 [P] [US4] Расширить `.github/pull_request_template.md` и issue template
  обязательными Feature ID, umbrella issue, task IDs, lane, exact SHA и
  Legacy Impact; использовать русские формулировки (FR-010, FR-032).

## Phase 3 — Changelog fragments and legacy DoD

**Purpose**: убрать общие конфликтные файлы и не создавать новый legacy.

- [ ] T011 [US6] Написать `scripts/validate-changelog-fragments.py` с проверкой schema,
  уникального Feature ID, категорий, русской записи, ссылок и запрета
  machine-specific/secret content (FR-009, FR-031).
- [ ] T012 [US6] Добавить fragment template
  `changes/unreleased/F216.yaml` только для этой фичи и metadata-only запись
  governance; root `CHANGELOG.md` остаётся неизменённым до release train.
- [ ] T013 [US6] Написать `scripts/validate-legacy-impact.py` для обязательного
  раздела в spec/PR и проверки exception fields owner/expiry/trigger/task
  (FR-026–FR-029).
- [ ] T014 [P] [US6] Добавить reusable `Legacy Impact` секцию в Spec Kit templates и
  issue/PR forms, не меняя исторические specs (FR-026, FR-028).
- [ ] T015 [US6] Добавить в `docs/agent-guidance/release-and-validation.md` DoD:
  `legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0`, и правило
  отдельных retirement slices (FR-027–FR-029).

## Phase 4 — Single Dev manifest and app identity

**Purpose**: обеспечить один полноценный backend/frontend/macOS Dev target.

- [ ] T016 [US2] Описать `infra/dev/manifest.schema.json` и
  `infra/dev/README.md` по контракту `contracts/dev-manifest.md` с
  metadata-only полями и schema version.
- [ ] T017 [US2] Реализовать `scripts/dev-harness.py build/status` для existing
  compose, server, frontend boundary и macOS build scripts; не добавлять
  второй runtime/DB (FR-011–FR-014).
- [ ] T018 [US2] Реализовать lock-protected `promote` с atomic active pointer,
  component SHA/digest checks, migration-head check и dry-run
  `infra/scripts/dev-harness.sh` (FR-012–FR-013).
- [ ] T019 [US2] Реализовать `rollback` и `reset-data` с parent manifest, explicit
  Dev-only confirmation и fail-closed production endpoint/path checks
  (FR-017, FR-036).
- [ ] T020 [US2] Реализовать `smoke --json`: backend health, frontend reachability,
  auth bootstrap, representative API, worker/dependency health и app origin
  (FR-016).
- [ ] T021 [P] [US2] Расширить `apps/macos/Scripts/build-dev-app.sh` записью source
  SHA/manifest metadata без изменения bundle ID `pro.2brain.graf.dev`.
- [ ] T022 [P] [US2] Усилить `apps/macos/Scripts/install-dev-app.sh` проверками
  designated requirement, signing identity, atomic replacement и сохранения
  permissions; не трогать `/Applications/GRAF.app` (FR-014–FR-015).
- [ ] T023 [US2] Добавить Dev manifest concurrent promote, partial failure, mismatch
  SHA, rollback и production-boundary tests в `tests/governance/` (SC-003).

## Phase 5 — SHA-bound CI and release train

**Purpose**: устранить гонку длинного CI и отделить частый feedback от релиза.

- [ ] T024 [US3] Реализовать `scripts/validate-ci-evidence.py` с requested/observed
  SHA, stale/cancelled/ambiguous states, artifact digests и skipped gates
  (FR-018–FR-022).
- [ ] T025 [US3] Добавить stale-SHA cancellation/invalidating guard в
  `infra/scripts/ci-local.sh`, не перезапуская Full CI для frozen candidate;
  сохранить текущие product gates (FR-019, FR-022).
- [ ] T026 [US3] Добавить self-test для CI evidence: changed SHA, interrupted run,
  mismatched component и один authoritative full identity (FR-019, FR-021,
  SC-004, SC-005).
- [ ] T027 [US5] Описать `infra/release/candidate.schema.json` и
  `infra/scripts/release-candidate.sh` для freeze, digest и go/no-go, не
  создавая product tag автоматически (FR-020–FR-023).
- [ ] T028 [US5] Обновить `scripts/prepare-release.sh`/release guidance сборкой
  fragments в root `CHANGELOG.md` только release operator и проверкой CalVer,
  Russian notes, compatibility, limitations и rollback (FR-023, FR-024,
  FR-025).
- [ ] T029 [P] [US5] Добавить release-train checklist в
  `docs/agent-guidance/release-and-validation.md` и PR template с окнами,
  hotfix exception и exact-SHA evidence.

## Phase 6 — Spec Kit/Ponytail integration and portable extraction

**Purpose**: сделать процесс обязательным для агентов и пригодным для других
проектов, не переполняя их контекст.

- [ ] T030 [US7] Изменить `.specify/extensions.yml` и git extension config так, чтобы
  read-only context/issue-canon hooks оставались автоматическими, а auto-commit
  hooks были выключены по умолчанию; сохранить explicit approval rule (FR-033).
- [ ] T031 [US7] Добавить `scripts/check-development-process.py` как единый bounded
  preflight, вызывающий validators без дублирования bootstrap doctor
  (FR-004–FR-006, FR-032–FR-035).
- [ ] T032 [US8] Добавить `harness/` portable core: templates, schemas, validators,
  context protocol, CI/release contracts и self-tests; GRAF product gates
  подключаются только через adapter (FR-030).
- [ ] T033 [US8] Подготовить отдельный публичный репозиторий
  `graf-development-harness` через GitHub, проверить доступность имени,
  provenance, license, README и pinned bootstrap/Spec Kit refs (FR-030–FR-031).
- [ ] T034 [US8] Установить harness в чистый sample project, пройти self-test,
  secret/path scan и migration/rollback upgrade; сохранить metadata-only
  evidence (SC-007, SC-009).
- [ ] T035 [US8] Запустить Ponytail review для всех новых layers и удалить
  необязательные abstraction/dependency, если это не ломает gates и evidence.

## Phase 7 — Validation, follow-up and closeout

**Purpose**: завершить governance без product release и подготовить legacy
retirement отдельно.

- [ ] T036 Выполнить reviewer-owned checklists из
  `checklists/requirements.md` и `checklists/governance.md`; implementation
  agent не меняет checkbox state (FR-034).
- [ ] T037 Запустить `$speckit-analyze`, устранить все Critical/High и повторить
  до чистого результата; проверить покрытие FR/SC задачами.
- [ ] T038 Запустить `$speckit-taskstoissues`, создать child issues по canon,
  связать их с #6090, проверить labels и заменить временный T000 umbrella на
  реальный основной task ID.
- [ ] T039 Выполнить quickstart Feature 216, governance self-tests и
  `infra/scripts/ci-local.sh --fast` на PR-ready SHA; записать exact SHA,
  skipped gates и metadata-only evidence (SC-002, SC-006, SC-009).
- [ ] T040 Выполнить `$speckit-converge`: добавлять найденные задачи append-only,
  повторять issue sync/implementation/validation до отсутствия обязательных
  пунктов.
- [ ] T041 Создать следующую collision-free Feature 217+ для legacy retirement:
  inventory aliases/fallbacks/old states/migrations/Temporal/Sparkle paths,
  owners, risk classes, cutover and separate issues; не удалять legacy здесь
  (SC-006, SC-010).
- [ ] T042 Подготовить PR `[F216]` с русским описанием, lane, exact SHA,
  evidence, `Refs #6090`/closing keywords только по факту и checklist
  release/no-deploy boundary; получить explicit approval перед commit.

## Phase 8: Convergence

- [ ] T043 Подключить `scripts/dev-harness.py` к существующим Compose,
  backend/frontend и macOS build/install adapters, чтобы `build → promote →
  smoke` выполнял реальные Dev probes при сохранении metadata-only boundary
  (FR-011, FR-016; partial).
- [ ] T044 Добавить source SHA и manifest metadata в
  `apps/macos/Scripts/build-dev-app.sh` и сохранить atomic identity checks в
  `install-dev-app.sh` (FR-013–FR-015; missing).
- [ ] T045 Подключить `scripts/validate-pr-metadata.py` к pre-merge/fast
  preflight и проверить Feature ID/umbrella/task/SHA linkage на реальном PR
  body (FR-010; partial).
- [ ] T046 Расширить `infra/scripts/release-candidate.sh` attestation path:
  schema validation, one-authoritative-full guard и go/no-go update без
  перезаписи frozen candidate (FR-020–FR-023; partial).
- [ ] T047 Провести reviewer-owned checklists, повторный analyze/converge,
  quickstart и финальный fast CI; закрыть только подтверждённые task issues и
  подготовить PR после explicit approval (FR-034–FR-035; missing).

- [ ] T048 После получения approval на implementation commit выполнить live
  adapter sequence на чистом exact SHA: `build --live → promote --live →
  status → smoke --live`, сохранить metadata-only evidence и проверить
  rollback/остановку backend без изменения production boundary (FR-011,
  FR-016; convergence of T043).

## Phase 9: Convergence follow-up

- [ ] T049 Реализовать проверенный live rollback: восстановить предыдущий
  backend-процесс и Dev app до публикации active pointer, либо явно оформить
  отдельный fail-closed adapter с доказанным восстановлением (FR-017, SC-003;
  partial).
- [ ] T050 Добавить неизменяемую post-publication attestation, связывающую
  decision, exact SHA, CalVer tag и фактический GitHub Release URL после
  `gh release create`; decision не перезаписывать (FR-024, SC-005; missing).
- [ ] T051 Перевести producer artifact digests с identity-only записи на
  хэши фактически созданных release/Dev артефактов и сохранить отдельную
  проверку source-revision (FR-021, SC-005; partial).
- [ ] T052 После одобренного repair path Feature 221 повторить live Dev
  sequence и сохранить evidence миграционного head, promote, smoke и rollback;
  volume и production не изменять обходными командами (FR-013, SC-003;
  blocked-by-external-feature).
- [ ] T053 Опубликовать текущий generic harness из чистого exact commit как
  следующий immutable SemVer release, обновить consumer lock и migration notes,
  затем повторить clean sample/package/provenance checks (FR-030, SC-007;
  pending explicit approval).
- [ ] T054 [P] Разрешать актуальный Alembic migration head при
  `dev-harness build` в реальном GRAF checkout и добавить regression test, чтобы
  канонический `build → promote` не создавал манифест с `unknown`; fixture-режим
  сохраняет явный synthetic head (FR-013, SC-003; convergence follow-up).

## Dependencies and parallelism

- T001–T004 создают безопасную основу; T005–T010 зависят от T001.
- T011–T015 зависят от T009 и могут частично выполняться параллельно с
  T005–T010, если пути не пересекаются.
- T016–T023 — последовательный Dev manifest путь; T021–T022 независимы друг
  от друга, но T023 ждёт все операции.
- T024–T029 зависят от manifest schema и существующего CI; T026 и T029 могут
  быть параллельны после контрактов.
- T030–T035 требуют стабильных validators; T033/T034 имеют внешний GitHub
  side effect и выполняются только после review package contents.
- T036–T042 — финальные reviewer, analyze, issue-sync, validation, converge и
  отдельный legacy follow-up gates; implementation commit не делается до
  explicit approval.

## Definition of Done

- [ ] Все обязательные tasks и reviewer checklists закрыты evidence, а не
  предположением.
- [ ] `AGENTS.md` стабилен, active context per-worktree, mtime fallback
  отсутствует.
- [ ] Feature ID/umbrella/task/PR/SHA связаны и не конфликтуют.
- [ ] Changelog fragment вместо прямой правки root `CHANGELOG.md`.
- [ ] Dev status/smoke/rollback доказывают один manifest и один Dev app.
- [ ] Stale CI не считается evidence; Full CI не запускался до candidate freeze.
- [ ] Legacy Impact присутствует; `legacy_new=0`, `unowned_legacy=0`,
  `expired_exceptions=0`.
- [ ] Reusable harness опубликован отдельно только после clean sample validation
  и не содержит GRAF private/product data.
- [ ] Product release/deploy не заявлены и не выполнялись в этой фиче.
