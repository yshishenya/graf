# F227: индивидуальная сверка задач и issues — 27.10.2026

Полоса: `Docs-only / mechanical`, сверка существующей реализации и отметок.
Исходная проверенная версия: `48e5d90d197f450367770e5c093cd897eece31fd`.
Продуктовый код, правила CI, очередь GitHub и выпуск не меняются.

## Основание

Перечитаны исходные критерии всех 33 issues `feature:227`, их комментарии,
`spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, оба контракта и текущий код.
У 27 старых закрытых дочерних issues T001–T025/T027/T028 строки задач остались
пустыми. Закрытое состояние и общий прежний комментарий сами по себе не
доказывают выполнение. Отметки восстановлены только после сверки реализации.

Первоначальная реализация принята в PR [#6275](https://github.com/yshishenya/graf/pull/6275):
head `9f465ba05d890d010bf566bd022e2249cdb82c4f`, merge
`0f3becdc9970c0a86fc8aa273ef1bc26eca0b5a0` (01.09.2026).
Указанный в старых комментариях PR [#6790](https://github.com/yshishenya/graf/pull/6790)
— поздний принятый снимок: head `c061b21d8f4547b78ccdee9f09d5b392447a71d7`,
merge `0e7ebb7153bf6f1f00961f64f0f49d0ac4310f1f` (08.09.2026).
Эти ссылки описывают происхождение кода, а не новые проверки текущего SHA.

## Матрица исходных задач

`Подтверждено` означает существующую реализацию в проверенной версии и
соответствующие проверки ниже. Это не приёмка будущей native очереди и не выпуск.
`Остаток` сохраняет исходную строку `[ ]`; формулировки и номера не заменяются.

| Task | Issue | Решение | Проверенный источник / доказательство |
|---|---|---|---|
| T001 | #6208 | Подтверждено | Оба contracts, `infra/release/ci-receipt.schema.json`, `train.schema.json`; validators и event/train suites |
| T002 | #6209 | Подтверждено | Исходный fragment сохранён в `changes/releases/v2026.09.01.1/F227.yaml`; последующее усиление — `v2026.10.22.1/F227.yaml` |
| T003 | #6210 | Подтверждено | Четыре файла `tests/governance/fixtures/feature_227/`: PR, manual, merge_group, API; event/mapping tests |
| T004 | #6211 | Подтверждено | `scripts/ci-event-identity.py`: строгое разрешение событий, SHA/base, конфликтов и canonical keys; event suite |
| T005 | #6212 | Подтверждено | Схема receipt и `scripts/validate-ci-receipt.py`: обязательные поля, отрицательные terminal states, metadata-only; receipt adapter tests |
| T006 | #6213 | Подтверждено | Схема train и `scripts/validate-release-train.py`: actual/synthetic, неизменность, Full; train suite и self-test |
| T007 | #6214 | Подтверждено | `test_ci_event_identity.py`: PR/manual/group, malformed/conflicting input, receipt cancellation, synthetic source rejection |
| T008 | #6215 | Подтверждено | `governance-fast.yml`: события PR/merge_group/explicit dispatch, exact resolver; workflow suite |
| T009 | #6216 | Подтверждено | Exact checkout, SHA verification и event base в workflow; tests отклоняют незакреплённую/непроверенную базу |
| T010 | #6217 | Подтверждено | Workflow вызывает authoritative mapping, terminal receipt validators/upload; workflow/mapping suites. Реальный rehearsal принадлежит T029/T031 |
| T011 | #6218 | Подтверждено | Event-specific/malformed/failure/cancel cases в `test_governance_workflow.py` |
| T012 | #6219 | Подтверждено | Concurrency по PR/group/manual, `cancel-in-progress: true`; текстовые события вынесены из code concurrency; terminal failure/cancel tests |
| T013 | #6220 | Подтверждено | `ci-local.sh` сохраняет initial tree и сравнивает tracked/untracked после всех stages до success evidence; `test_ci_runs_final_cleanliness_before_success_evidence` |
| T014 | #6221 | Остаток | Producer содержит terminal `status`, но отдельные conclusion/cancellation_state/supersession_state пишет `emit-ci-receipt.py`, а не указанный в задаче `emit-ci-evidence.py`. Нужна явная сверка применимости исходного задания |
| T015 | #6222 | Остаток | Указанные guard/evidence suites проверяют stale SHA, но отдельный superseded сценарий в этих двух файлах не найден. Cancellation проверяется в event suite, актуальные latest-source отказы — в F211; это требует отдельной сверки применимости |
| T016 | #6223 | Остаток | Исходный и текущий `validate-pr-metadata.py` не требуют workflow URL/base/receipt в тексте PR. Новые F211 trusted proofs отдельно проверяют эти связи; буквальное исходное задание не выполнено |
| T017 | #6224 | Подтверждено | `release-candidate.sh`: train-freeze/train-validate, immutable create-once; train suite |
| T018 | #6225 | Подтверждено | train связан с freeze/validate/attest/decide и authoritative Full; положительные и отрицательные train/candidate tests |
| T019 | #6226 | Подтверждено | Candidate/train tests отделяют source от synthetic, проверяют current master/rollback и stale history |
| T020 | #6227 | Подтверждено | Изолированная Git-история с тремя PR, подставленными PR/Full proofs, пустыми serial queue collections; отрицательные ancestry/drift/duplicate cases |
| T021 | #6228 | Подтверждено | `harness/schemas`, `src/dev_harness/ci_contracts.py`, templates: portable resolver/receipt/stale checks; self-test/sample/package checks |
| T022 | #6229 | Подтверждено | Lock v0.1.13 → `6a8257186aee878087b68fd77716ddce595a012d`; live annotated tag peeled к тому же commit. Историческая Python 3.9/3.12 matrix — run 33497610330, не новый запуск |
| T023 | #6230 | Подтверждено | `development-process.md`, раздел CI and release rhythm: event/source, cancellation, clean worktree, train и one Full |
| T024 | #6231 | Подтверждено | `release-and-validation.md`: train-freeze/validate/attest/decide, frozen exact source и один authoritative Full |
| T025 | #6232 | Подтверждено | Русский PR template: Feature/task/issue, selected lane, source/checks, release/versioning/legacy gates |
| T026 | #6233 | Остаток | Анализ17.10 покрывает 18/18 требований; текущая сверка выявила T014/T015/T016 и не объявляет общий analyze/closeout законченным |
| T027 | #6234 | Подтверждено | Live все 33 issues: каждый T001–T025 имеет ровно одного владельца, canonical title и feature/priority/area/gate/type labels; T032/T033 совместно #7645 |
| T028 | #6235 | Остаток | Новые focused/workflow lint PASS; исходный полный local fast receipt не найден в текущих материалах. Старый общий комментарий не заменяет его; новый exact-SHA GitHub fast ещё предстоит |
| T029 | #6236 | Остаток | Настоящий GitHub PR + merge_group rehearsal/operator gate не подтверждён; fixtures его не заменяют |
| T030 | #6237 | Остаток | Выполнена индивидуальная документальная сверка, но общая convergence не заявлена: T014/T015/T016/T028/T029/T031 сохраняются |
| T031 | #6274 | Остаток | Current API resolver/tests существуют; полного реального native API rehearsal всё ещё нет |
| T032 | #7645 | Уже принят | Уточнение serial/native и pinned matrix; исходная отметка сохранена |
| T033 | #7645 | Уже принят | Общая raw Git ancestry base→actual source в freeze и всех consumers; новая train suite PASS; исходная отметка сохранена |

Итог: восстановлены 23 проверенные отметки (22 из T001–T025 и T027),
сохранены 2 прежние (T032/T033); 8 строк остаются открытыми.
Дополнительные задачи/дубли issues не создаются: у каждого остатка есть владелец.
Решение о неактуальности T014/T015/T016 этим документом не принимается. Нельзя
отмечать их выполненными или молча добавлять повторяющиеся механизмы проверки.

## Новая проверка текущего кода

На исходном чистом SHA выполнено 393 уникальных pytest проверки за 106.90 с:
PASS 393, FAIL 0, ERROR 0, SKIP 0. Выбраны целиком:

- `test_ci_event_identity.py`, `test_merge_group_mapping.py`;
- `test_ci_guard.py`, `test_ci_evidence_producer.py`;
- `test_governance_workflow.py`;
- `test_release_train.py`, `test_release_candidate.py`, `test_validator_safety.py`.

Дополнительно PASS:
`validate-governance-workflow.py --self-test`,
`validate-release-train.py --self-test`,
`verify-merge-group-mapping.py --self-test`;
переносимый `harness-check --self-test`, sample spec, package scan, version 0.1.13.
Новые зависимости не устанавливались. Проверки с подставленными GitHub/Full
ответами не выдаются за настоящие сетевые или release доказательства.

Контрольные суммы новых материалов вне git:

- focused.log: `c9554e1f13330425529f8d7caa515e26ebe25d951129762012a74c88d7455d3e`;
- focused.xml: `079c7d4e7453b6324e7ed37511b8d53246a552e900a87168c1590a2e72f45c83`;
- live labels snapshot: `ae380ed0002eb91bcef72b4b5c2692832dd19e0cbcd8de217927af6b4bdf3778`.

## Границы приёмки

Матрица устраняет ошибочные пустые отметки подтверждённой реализации. Она
не объявляет все старые закрытия корректными: T014/T015/T016/T028 требуют отдельной
сверки текущей приёмки и состояния внешнего трекера. Старые комментарии сохранены.
Перед новыми закрытиями нужны принятый PR, его обязательные проверки точного SHA
и live issue-closeout по действующим правилам. Никакая issue этим изменением
автоматически не закрывается. Umbrella #6207, T026/#6233, T029/#6236,
T030/#6237 и T031/#6274 остаются открытыми.

Не запускались и не менялись: Full CI, release/CD, branch protection,
native queue, приложение GRAF Dev, Docker-стенд, TCC и production.
