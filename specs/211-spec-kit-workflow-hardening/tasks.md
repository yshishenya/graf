# Tasks: Надёжный Spec Kit workflow

**Input**: Design documents from `specs/211-spec-kit-workflow-hardening/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `quickstart.md`, `contracts/governance-check.md`
**Risk / Validation Lane**: `significant-feature`, no deploy

## Phase 1: Setup And Source Alignment

**Purpose**: Начать с проверенных stable источников без изменения master или чужих worktrees.

- [X] T001 Fast-forward clean bootstrap source checkout to published `v0.8.0` in `/Users/yshishenya/Documents/speckit-bootstrap` and record exact source/executable hashes in `specs/211-spec-kit-workflow-hardening/research.md` per FR-011
- [X] T002 Run the non-frozen schema 2 → 3 migration in `/Users/yshishenya/.codex/worktrees/e029/crisp/.specify/speckit-bootstrap.lock.json` and review every generated `.agents/skills/` and `.specify/` change without deleting legacy user-level skills per FR-001, FR-002 and FR-003

---

## Phase 2: Foundational Integrity

**Purpose**: Доказать, что штатный bootstrap state целостен до project-specific изменений.

- [X] T003 Verify `speckit-bootstrap . --doctor --frozen`, project-local skill hashes and managed `.specify/.gitignore`; correct only generated state owned by bootstrap in `.agents/skills/` and `.specify/` per FR-003 and FR-004
- [X] T004 Verify direct agent-context plan refresh through the `specify` tool Python and document the supported invocation in `docs/agent-guidance/spec-kit-flow.md`; patch `/Users/yshishenya/Documents/speckit-bootstrap` only if its existing runtime fallback fails per FR-003

**Checkpoint**: Bootstrap integrity passes and no user-owned legacy state was removed.

---

## Phase 3: User Story 1 - Воспроизводимое обновление Spec Kit (Priority: P1) 🎯 MVP

**Goal**: Повторный refresh остаётся воспроизводимым и объяснимым.

**Independent Test**: Выполнить Scenario 1, Scenario 2 и Scenario 4 из `quickstart.md`; второй refresh не создаёт необъяснимый tracked drift.

- [X] T005 [US1] Re-run bootstrap dry-run/apply and record idempotence evidence plus exact lock/version state in `specs/211-spec-kit-workflow-hardening/quickstart.md` per FR-001 and FR-010

---

## Phase 4: User Story 2 - Полный GRAF SDD-цикл (Priority: P1)

**Goal**: Канонический guidance не пропускает обязательные стадии и не смешивает reviewer/implementation ownership.

**Independent Test**: Прочитать `AGENTS.md` и `docs/agent-guidance/spec-kit-flow.md` как новый участник; единственный полный GRAF path включает `converge`, а upstream six-step workflow имеет явную границу.

- [X] T006 [P] [US2] Update the canonical sequence, reviewer-owned checklist rules, convergence loop, upstream workflow boundary and supported agent-context hook path in `AGENTS.md` and `docs/agent-guidance/spec-kit-flow.md` per FR-005, FR-006, FR-007 and FR-008

---

## Phase 5: User Story 3 - Раннее обнаружение drift (Priority: P2)

**Goal**: Future bootstrap/upstream refresh ломается в focused validation, а не после начала feature work.

**Independent Test**: `python3 scripts/check_spec_kit_governance.py --self-test` доказывает положительный fixture и четыре отрицательных класса; обычный запуск проходит на repository state.

- [X] T007 [P] [US3] Implement the stdlib governance validator and its built-in positive/negative self-test in `scripts/check_spec_kit_governance.py` per FR-009 and `contracts/governance-check.md`
- [X] T008 [US3] Run the governance validator from the fast lane in `infra/scripts/ci-local.sh` without adding a dependency or network requirement per FR-009

---

## Phase 6: Polish And Closeout

**Purpose**: Зафиксировать user-visible operational change и пройти declared gates.

- [X] T009 Update `[Unreleased]` Russian tooling/operations notes in `CHANGELOG.md` and reconcile Feature 211 quickstart evidence in `specs/211-spec-kit-workflow-hardening/quickstart.md` per FR-012
- [X] T010 Run the governance self-test, repository guard, frozen doctor, Feature 211 quickstart and `infra/scripts/ci-local.sh --fast`; record exact results in `specs/211-spec-kit-workflow-hardening/quickstart.md` per SC-001, SC-002, SC-003, SC-004, SC-005 and SC-006
- [X] T011 Run Ponytail review and `$speckit-converge`; complete any appended tasks before declaring Feature 211 PR-ready per FR-008
- [X] T012 Publish bytecode-safe `github-issue-canon v0.3.2` and `speckit-bootstrap v0.8.1`, adopt their immutable refs in GRAF, then prove issue-canon command → frozen doctor without `__pycache__` per FR-013 and SC-007

## Dependencies And Execution Order

- T001 precedes T002 so migration uses the published source baseline.
- T002 precedes T003–T005 because lock/project-local skills do not exist before migration.
- T003 and T004 precede project-specific guidance and guard changes.
- T006 and T007 may proceed in parallel after T003–T004; T008 depends on T007.
- T009 follows behavior changes; T010 follows all implementation; T011 is the initial consistency gate; T012 is append-only convergence work discovered by the publication recheck.

## Implementation Strategy

1. Finish setup/integrity and stop if bootstrap doctor fails.
2. Deliver the reproducible migration as the MVP.
3. Add the smallest project-specific guidance and guard diff.
4. Validate focused paths, then run the fast PR lane once.
