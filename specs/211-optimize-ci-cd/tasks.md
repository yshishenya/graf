# Tasks: Быстрый и доказуемый CI/CD

**Input**: Design documents from `specs/211-optimize-ci-cd/`
**Tests**: Required by FR-011 and the user request to re-check all behavior before rollout.

**Current continuation**: A4, 2026-09-13, T048 onward. A3 / E01 T043–T047 shipped in v2026.09.13.1 (#6953; #6952 closed). A1/A2 merged via #6851; #6845/#6850 closed (verified live). T001–T042 and their historical authority/status notes below are preserved; the old full-inside-execute strategy is superseded by authoritative GitHub Full evidence reuse.

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

## Phase 12: US7 — Нужные проверки до PR (A3 / E01, P1)

Prerequisites: reviewed `checklists/behavior-selection.md`; analyze with no CRITICAL/HIGH findings; current GitHub task ownership. One owner of the runner: current implementation agent. Release decision remains with the product/release owner.

- [X] T043 [US7] Доказать сначала падающим тестом в `apps/server/tests/contract/test_ci_cd_contract.py`, что изменение общего JS обязано выбирать неизменённые проверки кабинета/настроек; использовать `run_stubbed_ci` (FR-025, SC-014). (Issue #6952)
- [X] T044 [US7] Добавить единый выбор групп и безопасный Git diff в `scripts/ci-behavior-tests.py` и `infra/scripts/ci-local.sh`: план без побочных действий, локальный focused, включение в fast без потери unit/changed/performance и без дубликатов (FR-025–030). (Issue #6952)
- [X] T045 [US7] Расширить существующие CI-контракты (`test_ci_cd_contract.py`, `test_local_postgres_test_runner.py`) и `tests/governance/test_governance_workflow.py`: реальные PR/MG/manual base, union, delete/rename/небезопасные пути, missing/empty/skipped proof, dirty/unknown, отсутствие побочных действий, остановка при ошибке и совместимость `check_active_docs` со всеми явными режимами (FR-026–030, SC-014). (Issue #6952)
- [X] T046 [US7] Выполнить выбранные существующие группы и отрицательный контроль JS в изолированной копии; записать число/время/ограничения в `specs/211-optimize-ci-cd/quickstart.md`, обновить `specs/6792-settings-product-experience/quickstart.md`, focused-инструкцию `docs/agent-guidance/release-and-validation.md` и `changes/unreleased/F211.yaml` (FR-027, FR-030, SC-014–015). (Issue #6952)
- [X] T047 Выполнить focused/static, review и converge A3; согласовать `specs/211-optimize-ci-cd/{spec,plan,tasks,quickstart}.md` с кодом. Записать отдельно местную готовность и ожидающие post-validation commit, PR/exact-SHA GitHub fast, merge/release/tracker closeout (FR-030, SC-014–015). (Issue #6952)

Dependencies: review → analyze → task sync → T043 FAIL → T044 → T045 → T046 → T047. No parallel code edits; no Full run merely to repeat baseline. The external E00–E12 master plan references these tasks but does not replace this file.

A3 local completion — 2026-09-12: T043–T047 реализованы и проверены; review PASS, converge без новых задач. Числа, команды и ограничения — в `quickstart.md`. Issue #6952 остаётся открытым: implementation commit требует согласования после проверки; PR, GitHub fast на точном SHA, merge и последующий релиз ещё не выполнены. Эти отметки не являются release/issue-closeout evidence.

A3 publication continuation — 2026-09-12: после локальной проверки пользователь разрешил коммит и доведение до готового PR. Предыдущая строка сохраняет состояние локального этапа; итоговые SHA, CI и PR-состояние записываются в опубликованном PR. Issue #6952 закрывается только после merge и предусмотренного подтверждения.

## Phase 13: A4 — ранние проверки и отсутствие повторов

Scope: E05.12/E05.16 and accurate CD diagnostics. Requirements FR-031–FR-033, SC-016–SC-017. High-risk requirements review, clean analyze and issue ownership precede code. Subsequent program stages receive their own append-only tasks after research; completion of T052 is not completion of the program.

- [X] T048 Добавить исполняемые регрессии порядка и остановки shell `release-full`, смешанного infra/changed и server-only diff, отсутствующего обязательного файла/отказа единственного CI contracts stage и правдивого dry-run в `apps/server/tests/contract/test_ci_cd_contract.py`. (Issue #6982)
- [X] T049 Перенести прежние lint/compile перед pytest в `.github/workflows/release-full.yml` и закрепить порядок в `scripts/validate-full-ci-workflow.py`; сохранить состав и authoritative evidence. (Issue #6982)
- [X] T050 Исключить повтор двух целых CI-контрактов в `infra/scripts/ci-local.sh` при смешанных изменениях; сохранить единственное обязательное исполнение и остальные файлы. (Issue #6982)
- [X] T051 Согласовать dry-run в `infra/scripts/cd-remote.sh`, действующие инструкции `docs/agent-guidance/release-and-validation.md`, исторические пометки F211 и фрагмент `changes/unreleased/F211.yaml`. (Issue #6982)
- [X] T052 Проверить оба CI-контракта, validator/self-test, Bash/Ruff/actionlint и governance; выполнить review/converge, записать результаты в `specs/211-optimize-ci-cd/quickstart.md` и подготовить PR с exact-SHA GitHub fast. (Issue #6982)


## Phase 14: A5 — серверные ресурсы и фикстуры

Prerequisites: independent resource-optimization checklist, clean analyze, task ownership. FR-034–037 / SC-018. Tests and runner remain one owner; no changes to product access/tenant context.

- [X] T053 Добавить реальные проверки раннего help/collection/неверных аргументов, fixture closure и union/disjointness в `apps/server/tests/contract/test_local_postgres_test_runner.py` и `tests/governance/test_test_resources.py`. (Issue #6983)
- [X] T054 Разделить чистые/DB unit через `apps/server/tests/conftest.py`, новый `apps/server/tests/fixtures/test_resources.py`, `apps/server/scripts/run_local_postgres_tests.sh`, убрать module skip в `apps/server/tests/unit/test_account_closure.py`; сохранить обязательный DB runner и ограничения workers. (Issue #6983)
- [X] T055 Сократить подготовку single-ready сценариев в `apps/server/tests/fixtures/cabinet.py`, `apps/server/tests/integration/test_artifact_egress_policy.py`, `apps/server/tests/integration/test_speaker_names.py`; измерить до/после и сохранить отрицательные сценарии. (Issue #6983)
- [X] T056 Закрепить Python/Node и frozen environment в `apps/server/.python-version`, `.github/workflows/governance-fast.yml`, `.github/workflows/release-full.yml`; обозначить browser-ресурс в трёх прежних skip и подготовить закреплённый `apps/server/tests/browser/package.json` / lock; сохранить безопасные phase JSONL и union/disjointness в `apps/server/scripts/run_local_postgres_tests.sh`. (Issue #6983)
- [X] T057 Проверить исполняемые регрессии, два DB-семейства, unit collection и Ruff/Bash/actionlint, обновить quickstart/research и `changes/unreleased/F211.yaml`; пройти review/converge. (Issue #6983)


## Phase 15: A6 — обязательные PR-проверки и устранение text-only повторов

FR-038–041 / SC-019. Independent checklist + analyze + task ownership before code. Foundation deployment precedes protection cutover; no gap in required checks.

- [X] T058 Добавить исполняемые scope/native-negative контракты в `tests/governance/test_pr_scope.py`, реализовать `scripts/ci-pr-scope.py` и `.github/workflows/macos-pr.yml` с точным SHA и безопасным итоговым check. (Issue #6986)
- [X] T059 Защитить `.github/workflows/pr-metadata.yml` и `scripts/validate-pr-metadata.py` trusted policy/double snapshot/isolated Python; расширить `tests/governance/test_pr_metadata_event.py`, сохранив прежний CLI. (Issue #6986)
- [X] T060 Проверить и опубликовать foundation PR с прежним combined gate; получить исходный SHA включения, проверить новые checks и добавить required `pr-metadata`/`macos-pr` без удаления `governance-fast`; сохранить read-back evidence. (Issue #6986)
- [ ] T061 После T060 исключить только text-only code reruns в `.github/workflows/governance-fast.yml`, согласовать `scripts/validate-governance-workflow.py` и `tests/governance/test_governance_workflow.py`; по уточнённому FR-040 доказать отсутствие отмены/повтора source code и разрешать новый stable required PASS только после проверки действительного source proof. Исправление live expected-check дефекта вынесено в T080–T081. (Issue #6986)
- [X] T062 Добавить единый `scripts/validate-pr-checks.py` для актуального полного набора, подключить `scripts/validate-issue-closeout.py` и `infra/scripts/release-candidate.sh` / train validation; сохранить исторический policy boundary и post-merge ancestry. (Issue #6986)
- [ ] T063 Проверить события/fork/identity/failure/consumer матрицу, пройти review/converge; согласовать `docs/agent-guidance/release-and-validation.md`, quickstart и фрагмент F211 с реально включённой политикой; опубликовать cutover PR и получить exact-SHA hosted evidence. (Issue #6986)


## Phase 16: Convergence — deterministic native boundary fixture

- [X] T067 [FR-038] Устранить зависимость `testShortRecordingBoundaryKeepsThirtySecondsFromTheFirstFrame` от произвольного 200 ms sleep в `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`: синтетический источник должен подтверждать обработку порции до подачи следующей, сохранив шесть граничных случаев, настоящий код записи и все frame/status/WAV assertions. Проверить отрицательный burst-control и focused Swift, затем hosted native. Не менять рабочий лимит памяти/таймер/правило 30 секунд. (Issue #6986)

## Phase 17: A7 — сокращение избыточных встреч в проверенных семействах

FR-042 / SC-020. Requirements checklist and current owner precede code; baseline may run read-only while review proceeds.

- [X] T064 Зафиксировать одинаковую исходную коллекцию/результаты 14 файлов из A7 allowlist и проверить шесть сохраняемых multi-state исключений в `specs/211-optimize-ci-cd/quickstart.md`. (Issue #6988)
- [X] T065 Применить `create_ready_meeting` к 113 рассмотренным функциям из `apps/server/tests/{integration,unit}`; минимально изменить общий `setup_comments`, сохранив реальные processing/foreign seed в двух исключениях; не менять assertions. (Issue #6988)
- [X] T066 Выполнить тот же набор после изменения, сравнить IDs/outcomes и время, проверить Ruff/diff/review/converge; обновить quickstart и `changes/unreleased/F211.yaml`. (Issue #6988)


## Phase 18: A8 — локальные образы, повтор выкатки и откат

FR-044–048 / SC-021; reviewer-owned image-reuse checklist and clean analyze before code. T067 is reserved for the native-fixture convergence in foundation.

- [X] T068 Переставить слои `infra/server/Dockerfile`, сохранив два targets, пакетные ресурсы и pinned dependencies/FFmpeg; доказать реальную сборку и reuse дорогих слоёв. (Issue #6989)
- [X] T069 Добавить минимальный `infra/scripts/release-images.py` с реальными previous IDs, двумя candidate builds, platform/source validation, сторонними refs, create-once attempts и Compose overrides; покрыть `tests/governance/test_release_images.py`. (Issue #6989)
- [X] T070 Подключить проверенные candidate/decision/evidence identity и images в `infra/scripts/cd-remote.sh`, `infra/scripts/cd-remote-runtime.sh`, `infra/scripts/run-production-smoke.sh`, `infra/scripts/verify-rec-migration.sh`, `infra/scripts/backup-rec-stack.sh`, `infra/scripts/rehearse-rec-restore.sh`; сохранить gates и правильные candidate/previous rollback ветки без пересборки/pull. (Issue #6989)
- [ ] T071 Проверить lifecycle/rollback/smoke отрицательные ветки и реальные образы; review/converge, quickstart, инструкции выкатки и `changes/unreleased/F211.yaml`, exact-SHA hosted проверки. (Issue #6989)

## Phase 19: Native-check convergence after A7

- [ ] T072 [FR-038] Устранить состязание двух DispatchQueue timers в `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`: поздний ответ подать только после полученного timeout, сохранить настоящий permission probe, проверку late/duplicate completion и следующего запроса. Проверить focused Swift и exact-SHA GitHub macos-pr; рабочий timeout/permissions не менять. (Issue #6986)

## Phase 20: A6 — постоянный required check с проверкой исходного результата

Уточнённые FR-040/SC-019; prerequisite: независимый requirements checklist PASS, analyze без CRITICAL/HIGH и подтверждённая связь с issue #6986. Владение — A6 в отдельной ветке PR #6990. T073–T079 заняты другими этапами и здесь не создаются. Тесты предшествуют реализации; source receipts не превращаются в text PASS.

- [X] T080 [FR-040] Сначала добавить исполняемые регрессии в `tests/governance/test_pr_checks.py`, `tests/governance/test_pr_scope.py`, `tests/governance/test_governance_workflow.py`: постоянные required names, отсутствие тяжёлых команд/new receipts на text-only, latest source attempt и failed/running/timeout/API failure, self-run/scope identity, два одновременно ожидающих текста, устаревший base/head, native required+skipped и отказ полного consumer при missing/running/failed/duplicate required gate. Проверить latest gate run/attempt включая text и финальную сверку source/gate attempts всех компонентов при same-SHA rerun и неизменном PR snapshot. Зафиксировать отрицательный результат до реализации. (Issue #6986)
- [ ] T081 [FR-040] После T080 реализовать проверку исходного компонента и актуального required check в `scripts/validate-pr-checks.py`, постоянные имена/guards/read-only permissions/изолированную concurrency в `.github/workflows/governance-fast.yml` и `.github/workflows/macos-pr.yml`, обновить `scripts/validate-governance-workflow.py`. Сохранить source receipts и historical/post-merge identity. Выполнить targeted executable suite/actionlint, review/converge; согласовать `docs/agent-guidance/release-and-validation.md`, `specs/211-optimize-ci-cd/quickstart.md` и `changes/unreleased/F211.yaml`. Основной агент выполняет commit/push и live body-edit acceptance на exact SHA: required contexts больше не expected, source tests не отменены/не повторены. (Issue #6986)

## A6 convergence correction after GitHub review

- [ ] T087 Исправить два review P1 в `scripts/ci-pr-scope.py`, `scripts/validate-pr-checks.py` и `.github/workflows/governance-fast.yml`: merged text использует проверенную историю/базу и сохраняет merge identity; артефакт различает run attempts с безопасным чтением старого имени. Проверить реальные Git истории и API/ZIP отрицательные регрессии в `tests/governance/test_pr_checks.py`, consumer suite, независимый review и live post-merge edit. (FR-040/SC-019) (Issue #6986)



## Phase 21: A9 / US9 — продолжение выпуска macOS

FR-049–054 / SC-022. Existing F211, high-risk lane. Requirements review → clean
analyze → issue ownership → implementation. One implementation owner; shared
state and wrapper files are sequential, no implementation delegation needed.

- [X] T073 [US9] Добавить сначала падающие исполняемые сценарии кэша/неизменяемого staging/upload/notary interruptions и ошибок записи в `tests/governance/test_release_artifacts.py`; использовать существующий shell signing test без production credentials. (FR-049–054, SC-022) (Issue #6992)
- [X] T074 [US9] Сохранить совместимый Swift scratch и общий lock в `apps/macos/Installer/Scripts/build-local-installer.sh`; добавить минимальные fingerprint/build receipt операции в `apps/macos/Installer/Scripts/release-artifacts.py`, сохранить архитектуры и упаковочные gates. (FR-049/054) (Issue #6992)
- [X] T075 [US9] Подключить content-bound same-version resume и complete output manifest к `apps/macos/Installer/Scripts/prepare-app-update.sh`; проверенный input/Sparkle cache, свежий Keychain и missing-only upload к `apps/macos/Installer/Scripts/sign-graf-app-update-local.sh` и существующему `test-release-signing-custody.sh`. (FR-050–052/054) (Issue #6992)
- [X] T076 [US9] Реализовать durable notary submit/info/wait/staple в `apps/macos/Installer/Scripts/release-artifacts.py`, сохранив исходные/final bytes, известные IDs, отказ при ambiguity и проверенное восстановление; синхронизировать `docs/agent-guidance/macos-notarization.md` и `apps/macos/Installer/README.md`. (FR-053/054) (Issue #6992)
- [ ] T077 [US9] Проверить focused Python/shell/native contracts и отрицательные сценарии, пройти независимый review/converge; записать результаты в `specs/211-optimize-ci-cd/quickstart.md`, фрагмент F211 и общий MD план, затем получить окончательные GitHub checks и один frozen-source Full. (SC-022) (Issue #6992)

Independent acceptance: same-command retry preserves verified bytes and known
Apple requests, while a changed input/trust/output or ambiguous submission fails
before publication. Real source-bound release validation follows implementation;
no stage marks public distribution complete from mocked command results.


## Phase 22: A10 — selected-server parallel execution

- [X] T078 Добавить исполняемые partition/selection/failure contracts в `apps/server/tests/contract/test_local_postgres_test_runner.py`, затем opt-in focused partition в `apps/server/scripts/run_local_postgres_tests.sh` и точный phase selector в `apps/server/tests/fixtures/test_resources.py`; только changed-server caller в `infra/scripts/ci-local.sh`. (FR-055) (Issue #6993)
- [X] T079 Доказать одинаковый состав и PASS реальным парным focused замером, записать экономию и review в `specs/211-optimize-ci-cd/quickstart.md`; hosted проверка на окончательном SHA отдельно. (SC-023) (Issue #6993)

## Phase 23: A11 — project template survives issue sync

- [X] T082 Исправить source extension `spec-kit-ext-github-issue-canon`: install-if-missing PR template, нейтральный общий template, отрицательный unittest и patch-release docs/version; пройти независимый review и source CI. (FR-056 / SC-024) (Issue #6986)
- [ ] T083 Штатно закрепить исправленную extension версию в GRAF и добавить исполняемый ensure regression в `tests/governance/test_validator_safety.py`; frozen doctor, повторный ensure, документация/общий MD и review/converge. Bootstrap executable уже корректен и не меняется. (FR-056 / SC-024) (Issue #6986)

## Phase 24: A12 — качество проверок и ранний Full

- [X] T084 Заменить word-search CSRF проверку в `apps/server/tests/contract/test_cabinet_static_assets_contract.py` исполняемым Node-сценарием; доказать FAIL на комментариях и PASS на handler, выполнить существующий `apps/server/tests/integration/test_cabinet_csrf.py`. Удалить только доказанные дубли из `apps/server/tests/unit/test_config_validation.py`, `apps/server/tests/integration/test_web_owner_session_context.py`, `apps/server/tests/contract/test_deployment_readiness_contract.py`; сохранить 1+1+3 соответствующих unit cases и независимые ожидания. (FR-057) (Issue #6994)
- [X] T085 Расширить контракт `apps/server/tests/contract/test_local_postgres_test_runner.py` для Full порядка/ранних отказов/cleanup; переставить strict/performance до parallel только в full ветке `apps/server/scripts/run_local_postgres_tests.sh`. Проверить ту же реальную strict/performance группу. (FR-058) (Issue #6994)
- [ ] T086 Выполнить независимый review/converge A12, сохранить число случаев, отрицательные результаты и локальные времена в `specs/211-optimize-ci-cd/quickstart.md`; согласовать инструкции, фрагмент F211 и общий MD. Окончательные hosted/Full результаты учитывать отдельно в T077. (SC-025) (Issue #6994)

- [X] T088 Устранить обязательный bootstrap-proof SKIP из-за глобальной media-role: изолированный одноразовый PostgreSQL fixture только для этого теста в `apps/server/tests/fixtures/postgres_test_database.py`, подключение в `apps/server/tests/integration/test_playback_normalization_postgres.py`, ограниченное ожидание и cleanup при ошибке, реальные миграции и все прежние assertions. Проверить последовательность media→bootstrap и исходную strict/performance коллекцию без skip; независимый review. (FR-057/SC-025) (Issue #6994)

## Phase 25: Convergence — mandatory synthetic media coverage

- [ ] T089 Сделать существующие 50 синтетических FFmpeg-проверок обязательными: заменить только media-tool skip в трёх `apps/server/tests/integration/test_playback_normalization_{media_matrix,workflow,test_rec_e2e}.py`, подготовить инструменты в существующих шагах `.github/workflows/{release-full,governance-fast}.yml`, сохранить private TestRec opt-in. Добавить исполняемые отрицательные проверки в `apps/server/tests/contract/test_playback_normalization_media_tools.py` и `tests/governance/test_governance_workflow.py`, проверить 50 PASS/0 SKIP, независимый review и metadata-only evidence в quickstart. (FR-057/SC-025, E02) (Issue #6994)
