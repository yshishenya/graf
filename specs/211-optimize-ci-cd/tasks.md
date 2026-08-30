# Tasks: Быстрый и доказуемый CI/CD

**Input**: Design documents from `specs/211-optimize-ci-cd/`
**Tests**: Required by FR-011 and the user request to re-check all behavior before rollout.

## Phase 1: Baseline and contract

- [X] T001 Record the approved scope, trust boundary and immutable-image exclusion in `specs/211-optimize-ci-cd/spec.md`, `plan.md`, `research.md` and `contracts/ci-cd-cli.md`
- [X] T002 Inventory ambiguous active CI commands and current deploy/full behavior in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T003 Capture the pre-change full-lane timing baseline in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T004 Add failing CLI, deploy-order and documentation contract cases in `apps/server/tests/contract/test_ci_cd_contract.py`
- [X] T005 Remove the local receipt helper and false-attestation path from `infra/scripts/ci-receipt.py`, `infra/scripts/ci-local.sh` and `infra/scripts/cd-remote.sh`
- [X] T006 Preserve configurable performance-gate semantics in `apps/server/scripts/run_local_postgres_tests.sh`

## Phase 2: User Story 1 — Быстрый feedback loop

- [X] T007 [US1] Require explicit `--fast` or `--full` in `infra/scripts/ci-local.sh`
- [X] T008 [US1] Classify reviewed server, macOS and documentation paths conservatively in `infra/scripts/ci-local.sh`
- [X] T009 [US1] Execute the union of known component stages without duplicates in `infra/scripts/ci-local.sh`
- [X] T010 [US1] Cover missing mode, component union and fail-closed escalation in `apps/server/tests/contract/test_ci_cd_contract.py`

## Phase 3: User Story 2 — Один authoritative full на exact SHA

- [X] T011 [US2] Keep full as the complete canonical repository gate in `infra/scripts/ci-local.sh`
- [X] T012 [US2] Run full after initial sync, re-check unchanged worktree/HEAD/remote SHA, then start remote actions in `infra/scripts/cd-remote.sh`
- [X] T013 [US2] Preserve incident-only `--skip-local-ci` and every remote production gate in `infra/scripts/cd-remote.sh`
- [X] T014 [US2] Cover dry-run declaration and clean → sync → full → remote ordering in `apps/server/tests/contract/test_ci_cd_contract.py`

## Phase 4: User Story 3 — Понятная диагностика

- [X] T015 [US3] Emit stable lane, component, reason, stage and total-duration output in `infra/scripts/ci-local.sh`
- [X] T016 [US3] Keep performance setup/database/functional failures hard and isolate only the load-sensitive p95 threshold in the server runner and marked test
- [X] T017 [US3] Require the performance threshold for related calendar paths, controlled runs and synchronized-master full in `infra/scripts/ci-local.sh`
- [X] T018 [US3] Cover timing, failure trap and performance-gate forwarding in `apps/server/tests/contract/test_ci_cd_contract.py`

## Phase 5: User Story 4 — Документация совпадает с кодом

- [X] T019 [P] [US4] Update risk lanes, one-full deploy workflow, batching and performance boundary in `docs/agent-guidance/release-and-validation.md`
- [X] T020 [P] [US4] Update operator examples in `infra/scripts/README.md` and verify `AGENTS.md` remains aligned
- [X] T021 [P] [US4] Update validation fields in `.github/pull_request_template.md`
- [X] T022 [US4] Enforce active-document consistency in `apps/server/tests/contract/test_ci_cd_contract.py`
- [X] T023 [US4] Record the operational change in `docs/current-product-status.md` and `CHANGELOG.md`

## Phase 6: Validation and rollout

- [X] T024 Run shell/Python static checks and focused contracts from `specs/211-optimize-ci-cd/quickstart.md`
- [X] T025 Prove component-only fast p50 against the recorded baseline
- [X] T026 Run and record a complete repository full baseline during implementation
- [X] T027 Reconcile the CD dry-run and active docs against executable output
- [X] T028 Perform final spec/plan/tasks/code/docs/contract analysis and preserve remote production gates

## Phase 7: Production feedback — fast без скрытого full

- [X] T029 [US1] Add failing fast-invariant scenarios for high-risk server, changed contract/integration tests, infrastructure, unknown and unavailable diffs in `apps/server/tests/contract/test_ci_cd_contract.py`
- [X] T030 [US1] Keep every explicit fast invocation bounded, run changed server test files and infrastructure safety checks, and emit coverage/next-gate truth in `infra/scripts/ci-local.sh`
- [X] T031 [P] [US4] Reconcile the no-escalation contract in `docs/agent-guidance/release-and-validation.md`, `infra/scripts/README.md`, `docs/current-product-status.md` and `CHANGELOG.md`
- [X] T032 [US3] Reconcile generated registry metadata with the bootstrap lock, run the focused contract/static checks and a real infrastructure-diff `infra/scripts/ci-local.sh --fast`, record duration/components, re-run analyze, then preserve the separate full-only release/deploy gate

## Dependencies and strategy

- T001–T006 establish the contract before behavior changes.
- US1 precedes US2; US3 and US4 reconcile the final operator surface.
- T029 must fail before T030; T031 is parallel to implementation after the
  clarified contract; T032 closes the follow-up only after code and docs agree.
- Focused checks and fast feedback precede the frozen release candidate.
- The normal release path does not run preflight full: after review and merge,
  `cd-remote.sh --execute` owns the one authoritative full on synchronized
  `master` before remote production actions.
- Immutable image build/push remains a separate architecture slice.
