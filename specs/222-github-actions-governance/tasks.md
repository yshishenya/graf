# Tasks: Автоматические SHA-bound PR-проверки

## Phase 1: Setup

- [x] T001 [P] Создать контракт workflow и metadata-only artifact в `specs/222-github-actions-governance/contracts/workflow.md`.
- [x] T002 [P] Добавить reviewer-owned infrastructure checklist в `specs/222-github-actions-governance/checklists/infra.md`.

## Phase 2: Foundational

- [x] T003 Добавить validator invariants для `.github/workflows/governance-fast.yml` в `scripts/validate-governance-workflow.py`.
- [x] T004 [P] Добавить self/negative tests workflow validator в `tests/governance/test_governance_workflow.py`.

## Phase 3: User Story 1 — Fast-gate

**Independent test**: workflow contract и local fast lane принимают согласованный SHA и отклоняют mismatch.

- [x] T005 [US1] Создать `.github/workflows/governance-fast.yml` с pull_request/master, workflow_dispatch, exact-SHA checkout, bounded fast lane и безопасным artifact upload.
- [x] T006 [US1] Обновить `docs/agent-guidance/release-and-validation.md` и `docs/agent-guidance/development-process.md` canonical check name, rerun semantics и required-check boundary.

## Phase 4: User Story 2 — Cancellation

**Independent test**: две synthetic concurrency runs показывают отмену старого SHA и rejection stale evidence.

- [x] T007 [US2] Добавить в `tests/governance/test_governance_workflow.py` проверки `cancel-in-progress`, per-PR group и запрета production-команд.

## Phase 5: User Story 3 — Enablement

**Independent test**: GitHub API snapshot показывает включённый Actions и требуемый `governance-fast` check после реального PR run.

- [ ] T008 [US3] Подготовить metadata-only operator evidence и включить Actions/required status check на `master` только после reviewer approval и успешной проверки PR.

## Final Phase: Validation

- [x] T009 Запустить Feature 222 quickstart, `infra/scripts/ci-local.sh --fast`, `speckit-analyze` и `speckit-converge`; обновить PR evidence без Full CI и production actions.

## Dependencies

`T001,T002 → T003,T004 → T005,T006 → T007 → T008 → T009`.

## Implementation Strategy

Сначала контракт и негативные проверки, затем workflow и документация, затем
реальный GitHub PR proof. Включение branch protection — последняя ручная
операция и не выполняется до reviewer gate.
