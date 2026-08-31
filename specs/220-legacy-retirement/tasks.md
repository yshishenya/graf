---
description: "Dependency-ordered tasks for Feature 220 legacy inventory and retirement"
---

# Tasks: Безопасная инвентаризация и retirement legacy

**Input**: Design documents from `specs/220-legacy-retirement/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Risk lane**: significant-feature. Tests and metadata-only evidence are required before any retirement slice.

## Phase 1: Setup

- [ ] T001 Record Feature 220 preflight, exact SHA, branch and owner in `.specify/feature.json` and `specs/220-legacy-retirement/`
- [ ] T002 [P] Add the inventory JSON schema and forbidden-field rules in `specs/220-legacy-retirement/contracts/inventory.md`
- [ ] T003 [P] Add the retirement-slice acceptance template in `specs/220-legacy-retirement/contracts/retirement-slice.md`

## Phase 2: Foundational safety

- [ ] T004 [P] Add metadata-only redaction and source-containment fixtures in `tests/governance/test_legacy_inventory.py`
- [ ] T005 [P] Add deterministic exact-SHA snapshot fixtures in `tests/governance/test_legacy_inventory.py`
- [ ] T006 Implement the inventory snapshot schema and digest helper in `scripts/legacy-inventory.py`
- [ ] T007 Integrate the inventory command with the project process preflight in `scripts/check-development-process.py`

## Phase 3: User Story 1 — Legacy inventory (P1) 🎯 MVP

**Goal**: Produce a complete, deterministic, metadata-only inventory of all known legacy categories.

**Independent Test**: Run the inventory twice on one SHA and compare identical snapshot digests; verify no content-bearing fields are emitted.

- [ ] T008 [P] [US1] Add category discovery tests for aliases, fallbacks, flags, dependencies, fixtures, migrations, Temporal, update paths and documentation in `tests/governance/test_legacy_inventory.py`
- [ ] T009 [US1] Implement repository-relative contour discovery and stable `L###` identifiers in `scripts/legacy-inventory.py`
- [ ] T010 [US1] Implement sorted records, aggregate counts and `snapshot_digest` output in `scripts/legacy-inventory.py`
- [ ] T011 [US1] Add changed-SHA stale detection and incomplete-discovery failure states in `scripts/legacy-inventory.py`

**Checkpoint**: Inventory is repeatable, exact-SHA bound and safe to publish as metadata-only evidence.

## Phase 4: User Story 2 — Classification and exceptions (P1)

**Goal**: Require an explicit owner, risk and finite decision for every contour.

**Independent Test**: Synthetic `remove`, valid `retain-with-exception` and expired/incomplete exception fixtures exercise all validator branches.

- [ ] T012 [P] [US2] Add classification and exception regression fixtures in `tests/governance/test_legacy_impact.py`
- [ ] T013 [US2] Extend the Legacy Impact validator for contour IDs, owner, risk, future expiry, trigger, validation and retirement issue in `scripts/validate-legacy-impact.py`
- [ ] T014 [US2] Add a machine-readable owner/risk/classification register in `specs/220-legacy-retirement/inventory.yaml`
- [ ] T015 [US2] Add fail-closed checks for expired or missing exception fields to `scripts/check-development-process.py`

**Checkpoint**: Every retained contour is time-bounded and every removal decision is task-backed.

## Phase 5: User Story 3 — Independent retirement slices (P1)

**Goal**: Make each removal independently testable, reversible and releaseable.

**Independent Test**: Validate a synthetic slice with cutover, backup/restore or replay rehearsal, abort conditions and rollback target.

- [ ] T016 [P] [US3] Add a retirement-slice validator and negative fixtures in `scripts/validate-retirement-slice.py` and `tests/governance/test_retirement_slice.py`
- [ ] T017 [P] [US3] Document migration expand/contract, backup/restore and rollback requirements in `specs/220-legacy-retirement/contracts/migration-slice.md`
- [ ] T018 [P] [US3] Document Temporal replay/idempotency and history-retention requirements in `specs/220-legacy-retirement/contracts/temporal-slice.md`
- [ ] T019 [P] [US3] Document macOS Sparkle signing/trust continuity and rollback requirements in `specs/220-legacy-retirement/contracts/update-slice.md`
- [ ] T020 [US3] Generate task-backed child issues for approved contours using `specs/220-legacy-retirement/inventory.yaml` and the GitHub issue canon

**Checkpoint**: No runtime legacy removal can enter a release train without its own safety contract.

## Phase 6: User Story 4 — No new legacy (P1)

**Goal**: Block new aliases, fallbacks, flags, dependencies, fixtures and compatibility paths without a finite exception.

**Independent Test**: Changed-path fixtures with `untouched`, valid exception and missing declaration produce the expected pass/fail results.

- [ ] T021 [P] [US4] Add changed-path Legacy Impact mismatch fixtures in `tests/governance/test_validator_safety.py`
- [ ] T022 [US4] Connect changed-path scanning to `scripts/check-development-process.py` and fail closed on unowned legacy
- [ ] T023 [US4] Update `docs/agent-guidance/development-process.md` with the per-feature legacy checklist and ownership rules

**Checkpoint**: New legacy cannot pass the PR-ready governance lane.

## Phase 7: User Story 5 — Evidence and closeout (P2)

**Goal**: Make inventory and retirement decisions traceable in GitHub and release evidence.

**Independent Test**: Validate a closeout containing exact SHA, snapshot digest, commands, result, limitations and issue/PR links.

- [ ] T024 [P] [US5] Add metadata-only closeout schema and validator fixtures in `tests/governance/test_legacy_closeout.py`
- [ ] T025 [US5] Add Feature 220 inventory and closeout sections to `.github/pull_request_template.md`
- [ ] T026 [US5] Update `specs/220-legacy-retirement/quickstart.md` with runnable inventory, stale-SHA and safety scenarios
- [ ] T027 [US5] Run `pytest -q tests/governance` and `infra/scripts/ci-local.sh --fast` on the PR-ready exact SHA; attach evidence to PR #6142 or the Feature 220 PR

## Phase 8: Polish and convergence

- [ ] T028 [P] Add Russian inventory/retirement runbook links to `docs/agent-guidance/README.md`
- [ ] T029 Run `speckit-analyze`, resolve Critical/High findings and record the result in the Feature 220 PR
- [ ] T030 Run `speckit-converge`, append any newly discovered contour tasks and verify `legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0`

## Dependencies and execution order

- Setup T001–T003 precedes all work.
- Foundational T004–T007 blocks user stories.
- US1 (T008–T011) is the MVP and precedes classification.
- US2 (T012–T015) precedes child retirement issues.
- US3 (T016–T020) and US4 (T021–T023) can proceed in parallel after US2 foundations, provided they touch different files.
- US5 (T024–T027) depends on the inventory and governance validators.
- T028–T030 are final convergence gates; no production release is part of this feature.

## Parallel opportunities

- T002/T003, T004/T005 and T017/T018/T019 can run in parallel.
- T008 and T012 can be prepared in parallel once the foundational schema exists.
- T021 and T024 can be prepared in parallel because they use separate fixtures.

## Implementation strategy

1. Deliver the metadata-only inventory MVP (T001–T011).
2. Stop and review classifications before any runtime change.
3. Add exception/no-new-legacy gates (T012–T015, T021–T023).
4. Create independent retirement slices with domain-specific rollback (T016–T020).
5. Close out with exact-SHA evidence and convergence (T024–T030).
