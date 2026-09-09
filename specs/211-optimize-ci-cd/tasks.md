# Tasks: Быстрый и доказуемый CI/CD

**Input**: Design documents from `specs/211-optimize-ci-cd/`
**Tests**: Required by FR-011 and the user request to re-check all behavior before rollout.

**Current continuation**: A2, 2026-09-09, T038–T042. A1 T033–T037 is locally complete in draft PR #6846, not merged. T001–T032 and their old full-inside-execute strategy below are historical, not current acceptance or release permission. GitHub authoritative checks and full reuse are unchanged.

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

- [X] T033 [US5] Добавить сначала падающие проверки event-base/default-base расхождения, недоступной базы, PR/MG/dispatch, ранних lint/compile и остановки до server tests в `apps/server/tests/contract/test_ci_cd_contract.py` и `tests/governance/test_governance_workflow.py`; использовать существующие identity tests и `run_stubbed_ci` (FR-015–FR-016, SC-010) (Issue #6845)
- [X] T034 [US5] Связать реальный diff с `identity.base_sha` через `GRAF_CI_BASE_REF`, блокировать недоступную event base до тестов и закрепить контракт в `.github/workflows/governance-fast.yml` и `scripts/validate-governance-workflow.py`; сохранить diagnostic dispatch, события, права, имена, concurrency и terminal evidence (FR-015, FR-018) (Issue #6845)
- [X] T035 [US5] Перенести прежние команды server lint/compile до выбранных серверных тестов fast/full в `infra/scripts/ci-local.sh` без изменения области, performance/RLS и терминальных результатов (FR-016) (Issue #6845)
- [X] T036 [US5] Согласовать локальные focused и обязательный GitHub fast в `docs/agent-guidance/spec-kit-flow.md`, `docs/agent-guidance/release-and-validation.md`, проверить `.github/pull_request_template.md`; зафиксировать изменения и ограничения в `changes/unreleased/F211.yaml` (FR-008, FR-010, FR-017–FR-018) (Issue #6845)

## Phase 9: Проверка A1

- [X] T037 Выполнить focused/static проверки из `specs/211-optimize-ci-cd/quickstart.md`, сверить spec/plan/tasks/code и сохранить результаты в этой quickstart; явно оставить GitHub PR/full/release gates и tracker closeout ожидающими, без нового SC-009 замера и без заявления об устранении edited-повторов (SC-010–SC-011, FR-011–FR-012, FR-018) (Issue #6845)

### A1 dependencies and incremental strategy

- Requirements review → tasks → clean analyze → issue sync → T033 → T034 → T035 → T036 → T037. Write only the next behavior's regression test, prove its failure, then the corresponding fix; do not run a full suite between these small loops.
- No new setup/scaffolding: existing runner, Git fixtures and validators suffice. No `[P]` tasks: one small slice, shared test file, sequential ownership.
- Possible independent execution after T033: documentation review for T036 alongside workflow work, but no extra implementation agent is needed or authorized.
- A1 is the independently deliverable minimum. A later code/metadata split needs its own reviewed tasks and confirmed required-check migration; no live settings change or skip shortcut here.
- Issue owner for T033–T037: [#6845](https://github.com/yshishenya/graf/issues/6845), open; canon.ensure and canon.validate passed on 2026-09-09. A checked local task does not imply merged/released acceptance or authorize issue closure.

## Phase 10: US6 — Отдельная проверка описания PR (A2, P1)

**Prerequisites**: independent `checklists/pr-metadata.md` PASS 10/10; current A2 spec/plan/contracts; clean analyze and issue ownership before tests/code.
**Independent acceptance**: executable CLI and workflow-shell checks with disposable Git repositories and synthetic API responses. Existing body-file CLI and mandatory workflow remain compatible. No real product tests or Full CI.

- [X] T038 [US6] Добавить первый падающий сценарий event/current PR и совместимость старого CLI в `tests/governance/test_pr_metadata_event.py`; затем добавлять по одному следующему поведению перед соответствующей реализацией: устаревший текст, идентичность/типы, scoped/multiple features, удаления/переименования и ошибочная история (FR-020–FR-022, SC-012) (Issue #6850)
- [X] T039 [US6] Добавить парные `--event` / `--current-pr` в `scripts/validate-pr-metadata.py`, проверить текущий открытый PR и checkout, получить точные NUL-separated пути `--no-renames` и переиспользовать `validate()` без изменения правил старого CLI; ошибки закрывают проверку без возврата к event body (FR-020–FR-022) (Issue #6850)
- [X] T040 [US6] После падающей проверки реального shell добавить `.github/workflows/pr-metadata.yml`: PR-only события, current API snapshot, read-only права, закреплённый checkout, отдельная concurrency и timeout 5 минут; проверить API failure, fork payload и shell injection в `tests/governance/test_pr_metadata_event.py`, не менять `governance-fast.yml` (FR-019, FR-022–FR-024, SC-012–SC-013) (Issue #6850)
- [X] T041 [US6] Описать дополнительную, ещё необязательную проверку и границу будущего переключения в `docs/agent-guidance/release-and-validation.md`, дополнить существующий `changes/unreleased/F211.yaml` и ссылки на issue в `specs/211-optimize-ci-cd/tasks.md` (FR-023–FR-024) (Issue #6850)

## Phase 11: Проверка A2

- [X] T042 Выполнить целевые тесты, статические проверки, review и converge по `specs/211-optimize-ci-cd/quickstart.md`; записать результаты и ограничения в quickstart и issue. Отдельно доказать совместимость прежнего CLI и неизменность обязательного workflow; не объявлять локальные проверки live acceptance, устранением повторов или разрешением на commit/merge/Full CI/release (SC-012–SC-013, FR-024) (Issue #6850)

### A2 dependencies and acceptance mapping

- Requirements PASS → tasks → clean analyze → issue sync → T038/T039 in small test–implementation loops → T040 → T041 → T042. No `[P]`: shared files and one implementation owner; no new setup, dependencies or generic receipt/cache machinery.
- US6 scenarios 1/7: T040; 2/3/4/5: T038–T039; 6: T040; 8: T041–T042. FR-019: T040; FR-020/021: T038–T039; FR-022: T038–T040; FR-023: T040–T041; FR-024: T040–T042. SC-012/013: T042 with executable evidence from T038–T040.
- Local implementation was the initial A2 delivery boundary. After validation the user approved publication and GitHub checks; required-check activation, merge-group support, freshness/retarget race acceptance, edited-code rerun removal, tracker closure and release remain separate, unapproved steps.
- Issue owner for T038–T042: [#6850](https://github.com/yshishenya/graf/issues/6850), open. Canon hooks passed on 2026-09-09 after correcting the auto-created branch-reservation issue #6848 (missing T000 context and mismatched area). That reservation is not Feature 211 task ownership. Local checked tasks never imply merged/live acceptance or issue closure.
