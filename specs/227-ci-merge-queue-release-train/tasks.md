# Tasks: CI merge queue и provenance release train

## Phase 1: Setup

- [ ] T001 [P] Зафиксировать CI receipt и release-train schemas per `specs/227-ci-merge-queue-release-train/contracts/ci-receipt.v1.md` и `contracts/release-train.v1.md`.
- [ ] T002 [P] Добавить metadata-only changelog fragment в `changes/unreleased/F227.yaml`.
- [ ] T003 [P] Добавить synthetic PR/manual/merge_group fixtures в `tests/governance/fixtures/feature_227/`.

## Phase 2: Foundational contracts

- [ ] T004 Добавить event identity resolver с fail-closed validation для PR, manual и merge_group в `scripts/ci-event-identity.py`.
- [ ] T005 [P] Добавить JSON schemas и validator для CI receipt в `infra/release/ci-receipt.schema.json` и `scripts/validate-ci-receipt.py`.
- [ ] T006 [P] Добавить JSON schema и metadata-only validator для release train в `infra/release/train.schema.json` и `scripts/validate-release-train.py`.
- [ ] T007 Добавить contract tests для SHA/base/event/conclusion invariants в `tests/governance/test_ci_event_identity.py`.

## Phase 3: User Story 1 — Exact event validation

**Independent test**: synthetic event fixtures produce a receipt whose target
SHA equals the checked-out SHA; missing/unknown identity fails closed.

- [ ] T008 [US1] Обновить `.github/workflows/governance-fast.yml` для `pull_request`, `merge_group` и explicit `workflow_dispatch` target resolution.
- [ ] T009 [US1] Добавить exact checkout и base/SHA verification в `.github/workflows/governance-fast.yml`.
- [ ] T010 [US1] Добавить merge-group PR mapping и metadata-only receipt upload в `.github/workflows/governance-fast.yml`.
- [ ] T011 [US1] Покрыть event-specific workflow contract и malformed payloads в `tests/governance/test_governance_workflow.py`.

## Phase 4: User Story 2 — Stale and superseded protection

**Independent test**: injected SHA drift, cancellation and final tree changes
produce terminal non-success receipts rejected by validators.

- [ ] T012 [US2] Ввести canonical concurrency key и cancellation contract в `.github/workflows/governance-fast.yml`.
- [ ] T013 [US2] Добавить final tracked/untracked cleanliness gate после всех stages в `infra/scripts/ci-local.sh`.
- [ ] T014 [US2] Расширить CI evidence producer полями cancellation/supersession/conclusion в `scripts/emit-ci-evidence.py`.
- [ ] T015 [US2] Добавить stale/superseded negative tests в `tests/governance/test_ci_guard.py` и `tests/governance/test_ci_evidence_producer.py`.
- [ ] T016 [US2] Обновить PR metadata validator и template полями workflow URL, target/base SHA и receipt в `scripts/validate-pr-metadata.py` и `.github/pull_request_template.md`.

## Phase 5: User Story 3 — Release train provenance

**Independent test**: a synthetic train with three PRs accepts one matching
authoritative Full CI receipt and rejects stale, duplicate or synthetic-only
release evidence.

- [ ] T017 [US3] Добавить train manifest freeze/validate operations в `infra/scripts/release-candidate.sh`.
- [ ] T018 [US3] Связать train manifest с candidate `freeze`, `validate` и `decide` в `infra/scripts/release-candidate.sh`.
- [ ] T019 [US3] Проверить post-merge `master` SHA отдельно от synthetic merge SHA и rollback target в `tests/governance/test_release_candidate.py`.
- [ ] T020 [US3] Добавить release-train rehearsal fixtures и negative tests в `tests/governance/test_release_train.py`.

## Phase 6: Portable harness and documentation

- [ ] T021 [P] Вынести generic receipt schema, resolver contract и stale validator в `harness/schemas/`, `harness/src/` и `harness/templates/`.
- [ ] T022 [P] Обновить `harness/harness.lock.json` только после immutable merged harness tag.
- [ ] T023 Обновить `docs/agent-guidance/development-process.md` правилами merge queue, stale evidence и release train.
- [ ] T024 Обновить `docs/agent-guidance/release-and-validation.md` train freeze и one-Full-CI workflow.
- [ ] T025 Обновить `.github/pull_request_template.md` русскими release/provenance gates и ссылками на issue/task.

## Phase 7: Validation and operator gate

- [ ] T026 Запустить `$speckit-analyze`, устранить critical/high findings и сохранить coverage report.
- [ ] T027 Запустить `$speckit-taskstoissues`, проверить отсутствие дубликатов и canonical labels для T001–T025.
- [ ] T028 Запустить focused governance tests, workflow lint и `infra/scripts/ci-local.sh --fast` на exact SHA.
- [ ] T029 Провести GitHub Actions PR и `merge_group` rehearsal; enforcement остаётся operator-owned до merge в `master`.
- [ ] T030 Провести `$speckit-converge` и обновить tasks только append-only remaining work.

## Dependencies

```text
T001,T002,T003 → T004,T005,T006,T007 → T008,T009,T010,T011
T008,T009 → T012,T013,T014,T015,T016
T004,T005,T006 → T017,T018,T019,T020
T005,T006 → T021,T022
T017,T018,T020 → T023,T024,T025 → T026,T027,T028,T029,T030
```

## Parallel execution

- T001–T003 can run in parallel.
- T005–T006 and T021 may run in parallel after T004 contract review.
- T008–T011 are one workflow ownership slice; T012–T016 are one stale-gate slice.
- T017–T020 are one release-candidate ownership slice.
- Documentation T023–T025 can run in parallel after contract names stabilize.

## Implementation strategy

1. MVP: exact event identity, merge_group checkout and receipt validation.
2. Safety: unified cancellation and final cleanliness.
3. Release: train provenance and one authoritative Full CI.
4. Portable extraction and docs.
5. Operator review, GitHub rehearsal and convergence.

## Legacy Impact

`untouched`: no product fallback, alias, compatibility dependency or legacy
runtime path is added. Legacy retirement remains Feature 220 and later slices.

## Phase 8: Convergence

- [ ] T031 [US1] Доказать authoritative GitHub API mapping для каждого PR в `merge_group` и добавить fail-closed rehearsal/evidence per FR-003 (partial; Refs #6274)

### Convergence evidence (2026-09-01)

- Локальная проверка `scripts/verify-merge-group-mapping.py --self-test` и
  `tests/governance/test_merge_group_mapping.py` проходят (10 тестов).
- Повторный локальный governance/fast lane проходит на exact SHA
  `072120c062216f90388a8941a1b8fa18dfd599b0`; receipt
  `.dev/ci-evidence/ci-fast-072120c06221-34518.json` имеет `status=passed`.
  Remote Actions rehearsal и
  operator-owned enforcement после merge остаются открытыми.
- Ранее выполненный диагностический `infra/scripts/ci-local.sh --full` на
  branch-point SHA `add984368a45d60cab39bd88b0560591ed72aa94` прошёл:
  3788 тестов, 1 skipped, server lint и все финальные gates — PASS. Он был
  запущен без frozen candidate и потому не является release evidence
  (`candidate_id` и `authoritative_full=true` отсутствуют); для выпуска нужен
  новый clean candidate и один authoritative Full CI на его SHA.
