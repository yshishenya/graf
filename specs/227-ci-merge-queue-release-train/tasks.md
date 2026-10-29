# Tasks: CI merge queue и provenance release train

## Phase 1: Setup

Текущий объём и отмена дополнительной автоматизации определены в
spec §«Завершающий объём — 28.10.2026». Исторические разделы ниже сохраняют
состояние своих дат; это не действующее требование внедрить очередь.

- [X] T001 [P] Зафиксировать CI receipt и release-train schemas per `specs/227-ci-merge-queue-release-train/contracts/ci-receipt.v1.md` и `contracts/release-train.v1.md`.
- [X] T002 [P] Добавить metadata-only changelog fragment в `changes/unreleased/F227.yaml`.
- [X] T003 [P] Добавить synthetic PR/manual/merge_group fixtures в `tests/governance/fixtures/feature_227/`.

## Phase 2: Foundational contracts

- [X] T004 Добавить event identity resolver с fail-closed validation для PR, manual и merge_group в `scripts/ci-event-identity.py`.
- [X] T005 [P] Добавить JSON schemas и validator для CI receipt в `infra/release/ci-receipt.schema.json` и `scripts/validate-ci-receipt.py`.
- [X] T006 [P] Добавить JSON schema и metadata-only validator для release train в `infra/release/train.schema.json` и `scripts/validate-release-train.py`.
- [X] T007 Добавить contract tests для SHA/base/event/conclusion invariants в `tests/governance/test_ci_event_identity.py`.

## Phase 3: User Story 1 — Exact event validation

**Independent test**: synthetic event fixtures produce a receipt whose target
SHA equals the checked-out SHA; missing/unknown identity fails closed.

- [X] T008 [US1] Обновить `.github/workflows/governance-fast.yml` для `pull_request`, `merge_group` и explicit `workflow_dispatch` target resolution.
- [X] T009 [US1] Добавить exact checkout и base/SHA verification в `.github/workflows/governance-fast.yml`.
- [X] T010 [US1] Добавить merge-group PR mapping и metadata-only receipt upload в `.github/workflows/governance-fast.yml`.
- [X] T011 [US1] Покрыть event-specific workflow contract и malformed payloads в `tests/governance/test_governance_workflow.py`.

## Phase 4: User Story 2 — Stale and superseded protection

**Independent test**: injected SHA drift, cancellation and final tree changes
produce terminal non-success receipts rejected by validators.

- [X] T012 [US2] Ввести canonical concurrency key и cancellation contract в `.github/workflows/governance-fast.yml`.
- [X] T013 [US2] Добавить final tracked/untracked cleanliness gate после всех stages в `infra/scripts/ci-local.sh`.
- [X] T014 [US2] Расширить CI evidence producer полями cancellation/supersession/conclusion в `scripts/emit-ci-evidence.py`.
- [X] T015 [US2] Добавить stale/superseded negative tests в `tests/governance/test_ci_guard.py` и `tests/governance/test_ci_evidence_producer.py`.
- [ ] T016 [US2] Обновить PR metadata validator и template полями workflow URL, target/base SHA и receipt в `scripts/validate-pr-metadata.py` и `.github/pull_request_template.md`.

## Phase 5: User Story 3 — Release train provenance

**Independent test**: a synthetic train with three PRs accepts one matching
authoritative Full CI receipt and rejects stale, duplicate or synthetic-only
release evidence.

- [X] T017 [US3] Добавить train manifest freeze/validate operations в `infra/scripts/release-candidate.sh`.
- [X] T018 [US3] Связать train manifest с candidate `freeze`, `validate` и `decide` в `infra/scripts/release-candidate.sh`.
- [X] T019 [US3] Проверить post-merge `master` SHA отдельно от synthetic merge SHA и rollback target в `tests/governance/test_release_candidate.py`.
- [X] T020 [US3] Добавить release-train rehearsal fixtures и negative tests в `tests/governance/test_release_train.py`.

## Phase 6: Portable harness and documentation

- [X] T021 [P] Вынести generic receipt schema, resolver contract и stale validator в `harness/schemas/`, `harness/src/` и `harness/templates/`.
- [X] T022 [P] Обновить `harness/harness.lock.json` только после immutable merged harness tag.
- [X] T023 Обновить `docs/agent-guidance/development-process.md` правилами merge queue, stale evidence и release train.
- [X] T024 Обновить `docs/agent-guidance/release-and-validation.md` train freeze и one-Full-CI workflow.
- [X] T025 Обновить `.github/pull_request_template.md` русскими release/provenance gates и ссылками на issue/task.

## Phase 7: Validation and operator gate

- [X] T026 Запустить `$speckit-analyze`, устранить critical/high findings и сохранить coverage report.
- [X] T027 Запустить `$speckit-taskstoissues`, проверить отсутствие дубликатов и canonical labels для T001–T025.
- [X] T028 Запустить focused governance tests, workflow lint и `infra/scripts/ci-local.sh --fast` на exact SHA.
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
  `abe63e09627cb5273f0621685e56a7101c713a6a`; receipt
  `.dev/ci-evidence/ci-fast-abe63e09627c-53014.json` имеет `status=passed`.
  Remote Actions rehearsal и
  operator-owned enforcement после merge остаются открытыми.
- Ранее выполненный диагностический `infra/scripts/ci-local.sh --full` на
  branch-point SHA `add984368a45d60cab39bd88b0560591ed72aa94` прошёл:
  3788 тестов, 1 skipped, server lint и все финальные gates — PASS. Он был
  запущен без frozen candidate и потому не является release evidence
  (`candidate_id` и `authoritative_full=true` отсутствуют); для выпуска нужен
  новый clean candidate и один authoritative Full CI на его SHA.
- Live Dev build/signing на exact SHA проходит. Promote/smoke остаются
  заблокированы до отдельной настройки полноценного worker/Temporal runtime:
  текущий `start-local.sh` запускает server-rendered backend с
  `processing_enabled=false`, а существующая локальная БД содержит revision,
  которого нет в текущей ветке. Production app и production data не трогались.

## Phase 9: Уточнение применимости и защита базы (2026-10-17)

Исходные T001–T031 сохранены без фиктивного завершения. Текущий срез не закрывает
настоящие GitHub merge-group gates T029/T031 и всю F227.

- [X] T032 Уточнить serial/native границы F227 и pinned harness matrix, провести независимое ревью checklist и повторный анализ spec/plan/tasks без unresolved critical/high; Refs #6233. (Issue #7645)
- [X] T033 [US3] Требовать base → actual source в `infra/scripts/release-candidate.sh`; в `tests/governance/test_release_train.py` доказать serial freeze с тремя PR без queue receipts и отказ несвязанной базы до создания train/identity, сохранить changelog fragment и итоговую проверку. (Issue #7645)

Зависимости: T032 → T033. Для T033 до реализации нужен собственный issue;
исторические закрытые issues не переоткрываются без проверки исходной приёмки.

Собственник текущих T032–T033: [#7645](https://github.com/yshishenya/graf/issues/7645).
Дедупликация: проверены все32 исходных issues feature:227; совпадений T032/T033 нет.

## Сверка реализации и трекера — 27.10.2026

Индивидуальные основания для 23 восстановленных отметок сохранены в
[reconciliation-20261027.md](reconciliation-20261027.md). Исходные описания,
ID и порядок задач сохранены; closed issue не использована как единственное
основание. Новые focused проверки текущего кода: 393/393 PASS.

T014/T015/T016 остаются `[ ]`: отдельные terminal поля и доверенная проверка PR
теперь находятся в других частях общей системы; буквальные исходные задания
не доказаны и повторяющаяся автоматика не добавляется. T028 сохраняется до
проверки полного exact-SHA fast evidence. T026/T030 и настоящие native
T029/T031 не объявлены завершёнными. Umbrella #6207 остаётся открытой.


## Отдельная приёмка T026 — 27.10.2026

- T026 (Issue #6233; umbrella #6207)

Итоговый анализ в существующем `analysis-provenance-20261017.md`:
CRITICAL 0 / HIGH 0, покрытие 18/18; независимое итоговое ревью APPROVE.
Отмечена только T026: итог 26 выполненных / 7 открытых задач.
T014/T015/T016/T028/T029/T030/T031 сохраняют исходные критерии и открытые отметки.
Историческая матрица выше сохранена; новых задач и дублей issues нет.
#6233 закрывается после принятия документального PR и live-проверки.

## Возвращённая T014 / #6221 — 28.10.2026

Исходная строка T014, её описание и владелец #6221 сохранены. Задача вновь
открыта после исполнения настоящего terminal step: готовый локальный PASS
перекрывает известные failure/cancelled. Проверка общего consumer отдельно
отвергает фактический неуспех GitHub; обход merge/release не установлен.

Текущие пути исходной T014: `.github/workflows/governance-fast.yml` выбирает
evidence; `scripts/emit-ci-receipt.py` уже производит conclusion/cancellation/
supersession, дублирование в `emit-ci-evidence.py` не требуется. До кода:
независимое ревью обоих checklists и анализ. Затем исполняемая регрессия
`tests/governance/test_governance_workflow.py`, минимальное исправление общего
terminal step, профильные проверки и итоговое ревью по plan/quickstart.
Отметка T014 допустима после локальной проверки, закрытие #6221 — только после
обязательных проверок PR SHA/base, слияния и индивидуального live-closeout.
Другие шесть открытых задач и umbrella #6207 этим срезом не закрываются.

## Локальный результат T014 — 28.10.2026

- T014 (Issue #6221)

Исходное описание сохранено. Поля состояния уже формирует общий
`scripts/emit-ci-receipt.py`; исправлены только приоритет известного неуспеха
и его причина в существующем terminal step. Исполняемая матрица: исходные
36 FAIL / 20 PASS, после исправления профиль 367 PASS / 0 SKIP / 0 FAIL.
Подробности, контрольные суммы и узкая сверка сходимости —
[validation-terminal-20261028.md](validation-terminal-20261028.md).
Отмечена локальная реализация T014; issue остаётся открытой до независимого
итогового ревью, нового PR, трёх проверок точного SHA/base, слияния и live-closeout.
Итог: 27 выполненных / 6 открытых задач; вся F227 не завершена.

## Завершающая сверка — 28.10.2026

Исходные 33 строки, описания и владельцы сохранены. На момент подготовки этой
таблицы новые отметки не ставились; последующий локальный результат T015 ниже.

| Задача | Владелец | Решение и оставшееся условие |
|---|---|---|
| T015 | #6222 | COMPLETED только после прямой регрессии общего consumer, ревью, PR checks/merge и live-closeout. Исторический CLOSED сам по себе недостаточен. |
| T016 | #6223 | NOT_PLANNED: лишняя ручная копия URL/base/receipt; сохраняются нынешние машинные проверки. Исходная `[ ]`; исторический reason исправить после принятия решения. Вернуться при доказанной потребности нового потребителя. |
| T028 | #6235 | COMPLETED по focused/lint и тому же fast на GitHub runner exact SHA/base; местный повтор не заявлять. Нужны PR checks/merge и live-closeout. |
| T029 | #6236 | NOT_PLANNED для оставшегося native этапа в personal repo. PR путь сохраняется; вернуться при доступности очереди и конкретной потребности по spec. |
| T030 | #6237 | Обязательная полная сверка и converge принятого объёма; пока `[ ]`. |
| T031 | #6274 | NOT_PLANNED для native authoritative mapping приёмки; существующие fail-closed guards сохраняются. Условия возвращения те же, что T029. |

T016/T029/T031 остаются `[ ]` и после принятой отмены. Все COMPLETED дети
проверяются индивидуально; общая #6207 — последней NOT_PLANNED смешанного
исходного плана, без ложного завершения native очереди. Новых дублей задач нет.

## Канонические ссылки существующих владельцев

Это связи уже существующих задач, а не новые executable tasks. Исходные строки,
описания и отменённые отметки выше не изменяются. У каждой задачи один владелец;
T032/T033 совместно принадлежат существующей #7645.

- T001 (Issue #6208)
- T002 (Issue #6209)
- T003 (Issue #6210)
- T004 (Issue #6211)
- T005 (Issue #6212)
- T006 (Issue #6213)
- T007 (Issue #6214)
- T008 (Issue #6215)
- T009 (Issue #6216)
- T010 (Issue #6217)
- T011 (Issue #6218)
- T012 (Issue #6219)
- T013 (Issue #6220)
- T014 (Issue #6221)
- T015 (Issue #6222)
- T016 (Issue #6223)
- T017 (Issue #6224)
- T018 (Issue #6225)
- T019 (Issue #6226)
- T020 (Issue #6227)
- T021 (Issue #6228)
- T022 (Issue #6229)
- T023 (Issue #6230)
- T024 (Issue #6231)
- T025 (Issue #6232)
- T026 (Issue #6233)
- T027 (Issue #6234)
- T028 (Issue #6235)
- T029 (Issue #6236)
- T030 (Issue #6237)
- T031 (Issue #6274)
- T032 (Issue #7645)
- T033 (Issue #7645)

## Локальный результат T015 — 28.10.2026

Реализовано соответствие существующим producer/consumer путям из spec. Исходные
guard/evidence проверки сохранены; недостающие два случая добавлены в общий
`test_pr_checks.py`. Успешный baseline и schema-valid stale/superseded receipt
при неизменных успешных run/job завершаются точным отказом consumer. Новый
производственный механизм не нужен; код producer/consumer и workflow не менялись.

Профиль quickstart: 603 уникальных PASS / 0 FAIL / 0 SKIP. Оба новых случая
повторно прошли после уточнения cleanliness superseded к существующему producer.
Отмечена только локальная реализация T015; T028/T030 остаются `[ ]` до своих
доказательств. T016/T029/T031 сохраняют `[ ]` как отменяемый объём. Итог:
28 отмеченных / 5 неотмеченных исходных задач. Полный closeout ещё не выполнен.
Подробности и пределы — новый раздел reconciliation-20261027.md от28.10.


## Приёмка снимка исторических задач — 29.10.2026

T019/#6226: единственный найденный пробел устранён одной assert
`rollback_target` в существующем test_release_train.py. Исходная формулировка
и владелец сохранены; точечный тест 1 PASS. Проверки source/base/synthetic
уже существовали. Производственный код и механизм отката не меняются.

T028/#6235 отмечена после принятого #7806: настоящий governance-fast 40647941764
на source bc6643504265e6a03cb573fc8156ffac6112457e и
base 668dd771341a92e0bbc3286585b25e99c2eacf86, общий consumer PASS до/после merge.
Применимость GitHub runner вместо повтора на Mac принята в spec. Собственная
приёмка 23 исторических детей и T028 через новый PR/live-closeout ещё впереди.

T030/#6237 остаётся `[ ]`; отменённые T016/T029/T031 также `[ ]`. Итог:
29 отмеченных / 4 неотмеченных исходных задачи, все 33 описания и владельцы
сохранены. Подробная поимённая матрица — reconciliation-20261027.md.
