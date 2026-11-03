---
description: "Dependency-ordered tasks for Feature 228 managed legacy retirement"
---

# Tasks: Управляемое поэтапное retirement legacy

> **Пересмотр объёма 26.10.2026:** действующий объём и индивидуальные решения
> заданы в [решении для ранней стадии](scope-decision-20261026.md).
> До его слияния это предложение. После слияния перечисленные там задачи
> отменены как NOT_PLANNED, сохраняют `[ ]` и не подлежат реализации по старому
> плану. Принятые защиты и предметные требования безопасности сохраняются.


**Input**: `spec.md`, `clarifications.md`, `plan.md`
**Risk lane**: Significant feature.
**Precondition for implementation**: reviewer-owned checklists are reviewed,
`speckit-analyze` has no unresolved Critical/High finding, and task-to-issues
has completed. None of these tasks authorizes runtime deletion or production
mutation.

## Phase 1: Reconcile and establish the planning baseline

- [X] T001 Record Feature 228 ownership, exact base SHA and planning-only scope in `specs/228-legacy-retirement-process/spec.md` and `.specify/feature.json`. (Issue #6239).
- [X] T002 [P] Compare `specs/220-legacy-retirement/` on `codex/220-legacy-retirement` with current `HEAD`; record adopted, superseded and unverified requirements in `specs/228-legacy-retirement-process/plan.md`. (Issue #6240).
- [X] T003 [P] Record the read-only comparison of `codex/206-legacy-cleanup`, `specs/206-mediascribe-polling-recovery/` and current processing compatibility in `specs/228-legacy-retirement-process/plan.md`. (Issue #6241).
- [X] T004 Create the canonical Feature 228 issue/task mapping through `.specify/extensions/github-issue-canon/` and `specs/228-legacy-retirement-process/tasks.md`. (Issue #6242).

## Phase 2: Foundational safety contracts

- [ ] T005 [P] Write failing metadata-only, contained-path and forbidden-field tests in `tests/governance/test_legacy_inventory.py`. (Issue #6243).
- [ ] T006 [P] Write failing registry/exception lifecycle tests in `tests/governance/test_legacy_registry.py`. (Issue #6244).
- [ ] T007 [P] Write failing scope-fence, protected-domain and rollback-requirement tests in `tests/governance/test_retirement_slice.py`. (Issue #6245).
- [ ] T008 Define the versioned registry and metadata-only inventory schemas in `governance/legacy/registry.schema.json` and `governance/legacy/registry.v1.yaml`. (Issue #6246).
- [X] T009 Extend `scripts/validate-legacy-impact.py` only where tests show it cannot enforce finite exception fields or exact classification. (Issue #6247).
- [ ] T010 Wire schema and changed-path validation fail-closed into `scripts/check-development-process.py` without broad file-system/user-data scanning. (Issue #6248).

## Phase 3: User Story 1 — Deterministic inventory (P1) 🎯 MVP

**Goal**: Produce a safe candidate registry before any removal decision.

**Independent test**: two runs on one SHA match exactly; source or registry
digest change reports stale; content-bearing field fixtures fail.

- [ ] T011 [P] [US1] Add deterministic ordering, exact-SHA and stale-evidence fixtures in `tests/governance/test_legacy_inventory.py`. (Issue #6249).
- [ ] T012 [US1] Implement a stdlib-only metadata discovery adapter with stable contour IDs in `scripts/legacy-inventory.py`. (Issue #6250).
- [ ] T013 [US1] Implement source digest, registry digest, sorted output and stale detection in `scripts/legacy-inventory.py`. (Issue #6251).
- [ ] T014 [US1] Seed only observed candidates as `candidate` or `blocked` with source evidence in `governance/legacy/registry.v1.yaml`; do not label them removable. (Issue #6252).
- [ ] T015 [US1] Add a metadata-only inventory runbook and candidate/approved distinction in `docs/agent-guidance/legacy-retirement.md`. (Issue #6253).

## Phase 4: User Story 2 — Prevent new unowned legacy (P1)

**Goal**: Make a compatibility exception finite, visible and task-backed.

**Independent test**: unowned legacy-sensitive changes and expired exceptions
fail; an explicit bounded exception passes without false positives on archival
evidence.

- [ ] T016 [P] [US2] Add synthetic alias, fallback, flag, dependency, fixture and documentation changed-path fixtures in `tests/governance/test_validator_safety.py`. (Issue #6254).
- [ ] T017 [US2] Implement `retain-with-exception` validation against the registry owner, expiry, trigger, validation and linked task/issue in `scripts/validate-legacy-registry.py`. (Issue #6255).
- [ ] T018 [US2] Add a narrow active-path taxonomy and documented archival/evidence exclusions to `scripts/legacy-inventory.py` and `docs/agent-guidance/legacy-retirement.md`. (Issue #6256).
- [X] T019 [US2] Update `.github/pull_request_template.md` and `docs/agent-guidance/development-process.md` with the bounded Legacy Impact declaration, extend `scripts/validate-pr-metadata.py` for complete exception fields, and add negative validator fixtures without adding active context to root `AGENTS.md`. (Issue #6257).

## Phase 5: User Story 3 — Prepare one safe retirement slice (P1)

**Goal**: Ensure future removal is small, reversible and independently reviewable.

**Independent test**: a synthetic slice fails without every applicable
protected-domain evidence item and passes only with a bounded scope fence.

- [ ] T020 [US3] Add migration and persistent-data contract fixtures to `tests/governance/test_retirement_slice.py`. (Issue #6258).
- [ ] T021 [US3] Add Temporal replay/history compatibility contract fixtures to `tests/governance/test_retirement_slice.py`. (Issue #6259).
- [ ] T022 [US3] Add macOS/Sparkle signing/appcast continuity contract fixtures to `tests/governance/test_retirement_slice.py`. (Issue #6260).
- [ ] T036 [US3] Add historical MediaScribe dual-track/drain cutoff, canonical-source, unavailable-outcome and bounded-cleanup negative fixtures to `tests/governance/test_retirement_slice.py`. (Issue #7741).
- [ ] T023 [US3] Implement protected-domain and rollback/abort validation in `scripts/validate-retirement-slice.py`. (Issue #6261).
- [ ] T024 [US3] Add a retirement slice template and per-domain rehearsal references in `docs/agent-guidance/legacy-retirement.md`. (Issue #6262).
- [ ] T025 [US3] Create task-backed child issues only for owner/reviewer-approved `remove` records using `.specify/extensions/github-issue-canon/`; leave candidate and blocked records open. (Issue #6263).

## Phase 6: User Story 4 — Keep agent context bounded (P2)

**Goal**: Give an agent enough local instruction for one contour without a
shared mutable root file.

**Independent test**: context validation rejects active feature/registry state
in root instructions and accepts active scoped links and Feature pointer.

- [ ] T026 [P] [US4] Add root-router stability and scoped-guidance regression cases in `tests/governance/test_agent_context.py`. (Issue #6264).
- [ ] T027 [US4] Extend `scripts/validate-agent-context.py` for legacy-slice pointer and root-context size/content rules. (Issue #6265).
- [ ] T028 [US4] Document the minimum agent read set and "do not load full registry" rule in `docs/agent-guidance/legacy-retirement.md` and `docs/agent-guidance/README.md`. (Issue #6266).
- [ ] T029 [US4] Extract generic registry/schema/context templates to the `graf-development-harness` source repository only after GRAF tests establish their portability. (Issue #6267).

## Phase 7: User Story 5 — Release-train traceability (P2)

**Goal**: Bind an included retirement slice to its released candidate without
re-running Full CI for each feature commit.

**Independent test**: a candidate manifest without exact merged SHA, fragment
digest, slice/contour link or authoritative Full receipt is rejected.

- [ ] T030 [P] [US5] Add retirement-slice candidate/receipt negative fixtures in `tests/governance/test_release_candidate.py`. (Issue #6268).
- [ ] T031 [US5] Extend `infra/scripts/release-candidate.sh` and its schema only as needed to record included contour/slice references and fragment digest. (Issue #6269).
- [ ] T032 [US5] Update `docs/agent-guidance/release-and-validation.md` with the release-train inclusion rule and one-Full-CI boundary. (Issue #6270).

## Phase 8: Analysis, evidence and handoff

- [X] T033 Run `$speckit-analyze`; resolve every Critical/High planning finding in `specs/228-legacy-retirement-process/`, then obtain an independent reviewer-agent check of both checklists with evidence and reread totals; the implementation agent must not change their checkmarks. (Issue #6271).
- [ ] T034 Run Feature 228 metadata-only quickstart scenarios, `python3 scripts/check-development-process.py --self-test` and focused governance tests; after validated commit/PR require GitHub `governance-fast`, `macos-pr`, `pr-metadata` on the exact SHA/checked base and PASS `scripts/validate-pr-checks.py`; attach evidence to the Feature 228 PR. Local wide fast remains diagnostic only. (Issue #6272).
- [ ] T035 Run `$speckit-converge`, confirm `legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0`, and record only the remaining blocked contours/limitations in `changes/unreleased/F228.yaml`. (Issue #6273).

## Dependencies and Parallel Opportunities

- T001–T004 establish provenance before implementation.
- T005–T010 are foundational and block all user stories except the independently scoped T009/T019 below.
- US1 (T011–T015) produces the candidate baseline before owner classification.
- US2 (T016–T019) and US3 fixtures (T020–T022, T036) use separate files after
  schemas. Within US3, T020, T021, T022 and T036 run sequentially because they
  all change `tests/governance/test_retirement_slice.py`; all four precede T023.
- T023–T025 depend on US1/US2 and reviewer-approved records.
- US4 (T026–T029) can proceed after T015; it must not edit root `AGENTS.md`.
- US5 (T030–T032) depends on the Feature 227 release-train contract when it is
  available; otherwise it records an explicit dependency, not a duplicate flow.
- T033–T035 are final gates. No task may delete legacy or execute production CD.

## Requirement-to-task Traceability

| Requirement | Primary tasks | Evidence of completion |
|---|---|---|
| FR-001–FR-004 / SC-001–SC-002 | T005, T008, T011–T015 | Deterministic metadata-only registry/inventory tests on one exact SHA. |
| FR-005–FR-007 / SC-003 | T006, T009–T010, T016–T019 | Negative and valid exception/changed-path fixtures. |
| FR-008–FR-009 / SC-004 | T007, T023–T025 | Retirement-slice scope, abort, rollback and issue-link validator. |
| FR-010 / SC-005 | T020, T023–T024 | Migration/data protected-domain fixture and rehearsal contract. |
| FR-011 / SC-005 | T021, T023–T024 | Temporal replay/history protected-domain fixture and contract. |
| FR-012 / SC-005 | T022, T023–T024 | macOS/Sparkle trust/rollback protected-domain fixture and contract. |
| FR-008–FR-009, FR-018 / protected MediaScribe boundary | T036, T023–T024 | Historical media cutoff, canonical-source, unavailable-outcome and bounded-cleanup negative fixtures; no runtime deletion. |
| FR-013 / SC-004 | T014, T018, T023–T025 | Candidate classification plus reviewed, bounded removal-slice criteria. |
| FR-014 / SC-006 | T026–T029 | Root-router/context validator and scoped guidance review. |
| FR-015–FR-016 / SC-007 | T019, T030–T032 | PR/fragment/release-candidate schema and receipt tests. |
| FR-017 / SC-008 | T033–T035 | Independent reviewer evidence and reread totals; implementation does not change reviewer checkmarks; metadata-only closeout. |
| FR-018 / SC-008 | T001, T033–T035 | Planning-only scope and no destructive/production operation in evidence. |

## Уточнение зависимостей и сверка трекера — 26.10.2026

Самостоятельный срез T009/#6247 и T019/#6257 проверяет только декларацию
существующих спецификаций/PR по FR-005/006. Реестр и discovery не являются
его потребителями или входом, поэтому этот срез допускается до T005–T010.
Для остальных историй исходные зависимости сохранены. T017/T018, изменённые
пути и полный SC-003 остаются открытыми. Исторические описания задач не
переписаны. Разрешение на коммит/PR/слияние уже дано пользователем.

T001–T004 индивидуально сверены с закрытиями #6239–#6242, фактически слитыми
PR #6313/#6790 и сохранёнными spec/plan: это только принятая подготовка.
Их [X] восстановлены после этой проверки; первоначальные описания сохранены.
Для существующей T036 после проверки всех открытых и закрытых issues F228
и отдельного поиска создан отсутствовавший владелец #7741. Каждая из 36
задач получила явную ссылку на своего владельца; дублей не создано. Остальные
незавершённые задачи остаются [ ].

Локальная проверка T009/T019 завершена: финальные профильные 262 PASS,
независимое ревью реализации PASS после исправления повторного раздела.
Доказательства: `validation-exceptions-20261026.md` и
`review-implementation-20261026.md`. Закрытие #6247/#6257 требует слияния
и итогового live closeout; вся F228 и T034/T035 остаются открытыми.

## Пересмотр объёма — ранняя стадия, 26.10.2026

Исходные 36 строк выше сохранены. После слияния решения 29 исходных задач
получают NOT_PLANNED по индивидуальной таблице `scope-decision-20261026.md`;
их `[ ]` не означает исполнительскую очередь и не заменяется на `[X]`.
Семь принятых задач сохраняют свои результаты и issues.

- [X] T037 Record the early-stage scope decision, preserve all original task rows, obtain independent review, reconcile the cancellation-only tracker procedure in `docs/agent-guidance/tracker-policy.md` and its pointer in `docs/agent-guidance/development-process.md`, validate the unchanged protections, and record evidence in `specs/228-legacy-retirement-process/scope-decision-20261026.md`. (Issue #6238).

T037 — действительная документальная работа текущего пересмотра, а не приёмка
исходной системы. Она имеет отдельные ревью и проверки PR. Родитель #6238
владеет только T037; исходный T000 заменяется этим ID с сохранением старого
названия и критериев в истории. Его окончательное закрытие NOT_PLANNED
означает отмену первоначального расширенного плана, даже когда T037 выполнена.
Не считать это завершением всех первоначальных требований родителя.

Локальная документальная T037 проверена: независимое ревью6/0, анализ
Critical0/High0, 262 профильные проверки PASS и проверки процесса/структуры PASS.
Результат зафиксирован в validation-scope-20261026.md; PR/merge и фактическая
отмена трекера остаются отдельными воротами.
