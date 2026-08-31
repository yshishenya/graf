# Tasks: Восстановить воспроизводимое состояние локальной Dev-базы

**Source of truth**: this file. Tasks are dependency ordered; reviewer-owned
checklist checkbox state is not changed by the implementation agent.

## Phase 0 — Contracts and read-only probe

- [ ] T001 [P] [US1] Define metadata-only snapshot schema and redaction rules in `specs/221-dev-migration-repair/data-model.md`.
- [ ] T002 [P] [US1] Define repair decision contract and fail-closed boundaries in `specs/221-dev-migration-repair/contracts/repair-decision.md`.
- [ ] T003 [P] [US1] Define evidence contract and secret/path prohibitions in `specs/221-dev-migration-repair/contracts/evidence.md`.
- [ ] T004 [US1] Inventory current migration graph, Dev compose targets and expected head in `specs/221-dev-migration-repair/research.md`.
- [ ] T005 [US1] Add read-only probe adapter with explicit target and atomic metadata output at `scripts/dev-migration-repair.py`.
- [ ] T006 [US1] Add probe tests for unknown revision, multiple heads, production boundary and metadata-only output in `tests/governance/test_dev_migration_repair.py`.

## Phase 1 — Isolated backup and rehearsal

- [ ] T007 [US2] Add isolated backup/restore adapter using existing project backup tooling in `scripts/dev-migration-repair.py`.
- [ ] T008 [US2] Add digest and schema-fingerprint comparison without reading user rows in `scripts/dev-migration-repair.py`.
- [ ] T009 [US2] Add restore failure and mismatch tests in `tests/governance/test_dev_migration_repair.py`.
- [ ] T010 [US2] Document the rehearsal and abort paths in `specs/221-dev-migration-repair/quickstart.md`.
- [ ] T011 [US2] Record reviewer-owned infra checklist evidence in `specs/221-dev-migration-repair/checklists/requirements.md`.

## Phase 2 — Approved Dev repair

- [ ] T012 [US3] Implement decision validation requiring owner, approval, backup, rollback target and abort conditions in `scripts/dev-migration-repair.py`.
- [ ] T013 [US3] Implement idempotent forward upgrade against an explicit isolated/Dev target in `scripts/dev-migration-repair.py`.
- [ ] T014 [US3] Add current/head equality and two-run idempotency checks in `scripts/dev-migration-repair.py`.
- [ ] T015 [US3] Add restore-based rollback on failed upgrade or readiness in `scripts/dev-migration-repair.py`.
- [ ] T016 [US3] Add tests proving no stamp, manual pointer edit, volume deletion or production invocation in `tests/governance/test_dev_migration_repair.py`.
- [ ] T017 [US3] Add fault-injection tests for partial upgrade and failed restore in `tests/governance/test_dev_migration_repair.py`.

## Phase 3 — Unified Dev smoke and evidence

- [ ] T018 [US4] Integrate Feature 216 active-manifest and exact-SHA checks in `scripts/dev-migration-repair.py`.
- [ ] T019 [US4] Verify backend readiness and representative API before evidence publication in `scripts/dev-migration-repair.py`.
- [ ] T020 [US4] Add stale-SHA, non-loopback and wrong-bundle identity tests in `tests/governance/test_dev_migration_repair.py`.
- [ ] T021 [US4] Emit atomic metadata-only repair evidence and run the repository secret/path scanner in `scripts/dev-migration-repair.py`.
- [ ] T022 [US4] Add live Dev smoke rehearsal to `specs/221-dev-migration-repair/quickstart.md` without production endpoints.

## Phase 4 — Governance, issue and closeout

- [ ] T023 [P] [US1] Validate agent context and active feature pointer with `scripts/validate-agent-context.py`.
- [ ] T024 [P] [US2] Validate changelog fragment with `scripts/validate-changelog-fragments.py`.
- [ ] T025 [P] [US3] Validate Legacy Impact against Feature 216/220 policy with `scripts/validate-legacy-impact.py`.
- [ ] T026 [US4] Run focused migration-repair tests and record exact SHA/evidence path in issue #6146.
- [ ] T027 [US4] Run `infra/scripts/ci-local.sh --fast` once on the PR-ready SHA and attach result to the PR.
- [ ] T028 [US4] Run `$speckit-analyze` and resolve all CRITICAL/HIGH findings before implementation.
- [ ] T029 [US4] Run `$speckit-converge`, reconcile every completed task with issue #6146 and leave incomplete scope open.
- [ ] T030 [US4] Prepare a Russian PR with `Feature: 221`, task IDs, lane, evidence, exact SHA, Legacy Impact and `Refs #6146`; do not claim production readiness.
