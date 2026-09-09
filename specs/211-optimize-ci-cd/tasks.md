# Tasks: Быстрый и доказуемый CI/CD

**Input**: Design documents from `specs/211-optimize-ci-cd/`
**Tests**: Required by FR-011 and the user request to re-check all behavior before rollout.

**Current continuation**: A1, 2026-09-09. T001–T032 and their old full-inside-execute strategy below are historical, not current acceptance or release permission. Current work is T033–T037; GitHub authoritative full reuse is unchanged.

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
- [X] T032 [US3] Reconcile generated registry metadata with the bootstrap lock, preserve the deployment-evidence scanner, handle a removed calendar performance proof, classify governance docs as partial, include untracked files in whitespace checks, parse every shell script independently, emit release readiness only after a passing full, run the focused contract/static checks and a real infrastructure-diff `infra/scripts/ci-local.sh --fast`, record duration/components, re-run analyze, then preserve the separate full-only release/deploy gate

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

## Phase 8: US5 — Достоверная и ранняя обратная связь (A1, P1)

**Prerequisites**: reviewed `checklists/ci-feedback.md` (8/8); current spec/plan/quickstart. Clean analyze and GitHub issue ownership must precede tests/code changes.
**Independent acceptance**: exact event-base behavior in disposable Git repositories, unchanged server static/test scope with early failure, consistent focused/GitHub-fast instructions. No actual Full CI or deployment.

- [X] T033 [US5] Добавить сначала падающие проверки event-base/default-base расхождения, недоступной базы, PR/MG/dispatch, ранних lint/compile и остановки до server tests в `apps/server/tests/contract/test_ci_cd_contract.py` и `tests/governance/test_governance_workflow.py`; использовать существующие identity tests и `run_stubbed_ci` (FR-015–FR-016, SC-010)
- [X] T034 [US5] Связать реальный diff с `identity.base_sha` через `GRAF_CI_BASE_REF`, блокировать недоступную event base до тестов и закрепить контракт в `.github/workflows/governance-fast.yml` и `scripts/validate-governance-workflow.py`; сохранить diagnostic dispatch, события, права, имена, concurrency и terminal evidence (FR-015, FR-018)
- [X] T035 [US5] Перенести прежние команды server lint/compile до выбранных серверных тестов fast/full в `infra/scripts/ci-local.sh` без изменения области, performance/RLS и терминальных результатов (FR-016)
- [X] T036 [US5] Согласовать локальные focused и обязательный GitHub fast в `docs/agent-guidance/spec-kit-flow.md`, `docs/agent-guidance/release-and-validation.md`, проверить `.github/pull_request_template.md`; зафиксировать изменения и ограничения в `changes/unreleased/F211.yaml` (FR-008, FR-010, FR-017–FR-018)

## Phase 9: Проверка A1

- [X] T037 Выполнить focused/static проверки из `specs/211-optimize-ci-cd/quickstart.md`, сверить spec/plan/tasks/code и сохранить результаты в этой quickstart; явно оставить GitHub PR/full/release gates и tracker closeout ожидающими, без нового SC-009 замера и без заявления об устранении edited-повторов (SC-010–SC-011, FR-011–FR-012, FR-018)

### A1 dependencies and incremental strategy

- Requirements review → tasks → clean analyze → issue sync → T033 → T034 → T035 → T036 → T037. Write only the next behavior's regression test, prove its failure, then the corresponding fix; do not run a full suite between these small loops.
- No new setup/scaffolding: existing runner, Git fixtures and validators suffice. No `[P]` tasks: one small slice, shared test file, sequential ownership.
- Possible independent execution after T033: documentation review for T036 alongside workflow work, but no extra implementation agent is needed or authorized.
- A1 is the independently deliverable minimum. A later code/metadata split needs its own reviewed tasks and confirmed required-check migration; no live settings change or skip shortcut here.
- Issue owner for T033–T037: [#6845](https://github.com/yshishenya/graf/issues/6845), open; canon.ensure and canon.validate passed on 2026-09-09. A checked local task does not imply merged/released acceptance or authorize issue closure.
