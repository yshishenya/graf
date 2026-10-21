# Tasks: F290 Эксплуатационные хвосты

**Lane**: high-risk-product. Base c6c5441c930b8c1ecffed6de9b80773aa0e757e5.
Источник всех работ — #6501; #7646 — резерв/umbrella F290.
Implementation ready не означает hosted/production/closeout PASS.

## Phase 1 — Обязательные ворота

- [X] T001 Завершить design, независимое requirements review в `specs/290-post-release-hardening/checklists/infra.md`, analyze и issue sync для #6501/#7646 до кода; FR001/009/010. (Issue #6501)

## Phase 2 — US1: Поддерживаемый CI (P1)

Независимая приёмка: три exact-SHA checks, реальный native build, прежние receipts.

- [X] T002 [US1] Добавить в `tests/governance/test_governance_workflow.py` исполнимые regression checks native selector и точных Actions contracts; подтвердить исходный отказ; FR002–004. (Issue #6501)
- [X] T003 [US1] Обновить шесть `.github/workflows/{governance-fast,macos-pr,pr-metadata,release-full,macos-diagnostic,backup-restore-rehearsal}.yml`, `scripts/validate-governance-workflow.py`, `scripts/validate-full-ci-workflow.py`, `tests/governance/test_pr_metadata_event.py`, `apps/server/tests/contract/test_ci_cd_contract.py` по research: Node24 commit pins, Swift6.0.3 с SDK guard, новый key/restore-prefix, ZIP/name, прежние gates; FR002–004/011. (Issue #6501)
- [X] T004 [US1] Выполнить `specs/290-post-release-hardening/quickstart.md`, независимое ревью, записать `validation.md` и `changes/unreleased/F290.yaml`; использовать действующее общее разрешение на проверенный commit/PR; FR009/010. (Issue #6501)
- [X] T005 [US1] Подтвердить три реальных exact-SHA PR checks через `scripts/validate-pr-checks.py`, включая Apple Swift build/XCTest/ContractValidation; записать receipts/ограничение macos14 в `specs/290-post-release-hardening/validation.md`; SC001. До runner retirement выполнить отдельный уточнённый план миграции image, если работа переходит его срок. (Issue #6501)

## Phase 3 — US2: Сохранённое изменение backup (P1)

Независимая приёмка: учёт100% stash, решение по каждой части, рабочие копии сохранены.
Эта фаза не блокирует первый CI-срез, но блокирует закрытие всей #6501.

- [ ] T006 [US2] Провести закрытую read-only инвентаризацию base/index/untracked stash, отдельно сверить пять файлов чужого владельца; в `specs/290-post-release-hardening/stash-disposition.md` сохранить только безопасные identity/coverage/решения, без diff и secret paths; FR005/009. (Issue #6501)
- [ ] T007 [US2] На основании T006 уточнить design/owned paths и независимое review в `specs/290-post-release-hardening/plan.md`; решение каждой части — transfer/retain/обоснованный отказ; не создавать параллельную ротацию и не выдумывать срок хранения; FR005/006. (Issue #6501)
- [ ] T008 [US2] После T007 перенести только нужные части в `infra/scripts/backup-rec-stack.sh` и адресные `apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py` либо доказать принятую замену/отказ; выполнить failure/concurrency/protected-copy/restore матрицу из quickstart, использовать действующее общее разрешение на проверенный commit; любое удаление сохранённой работы согласовать отдельно; FR006, SC002. (Issue #6501)

## Phase 4 — US3: Post-deploy результаты (P2)

Независимая приёмка: четыре отдельных воспроизводимых результата на разрешённой синтетике.

- [ ] T009 [US3] Написать и независимо проверить четыре процедуры с владельцем/source/time/prerequisites/rollback/cleanup в `specs/290-post-release-hardening/post-deploy-procedures.md`; учесть inventory writes и cleanup_result mapping, без нового retry/backfill API; FR007/008/011. (Issue #6501)
- [ ] T010 [US3] По T009 уточнить design/owned paths и проверить изолированно существующие retry/restart/backfill/Range/deletion сценарии штатным PostgreSQL runner; изменения `infra/scripts/cd-remote-runtime.sh` допустимы только после design/review и своих regression; записать в `specs/290-post-release-hardening/validation.md`; FR007/008. (Issue #6501)
- [ ] T011 [US3] После T010 и отдельного согласия на конкретные production действия выполнить четыре процедуры/обоснованный отдельный цикл, безопасные результаты и owner остатка в `specs/290-post-release-hardening/validation.md`; незавершённое не превращать в pass; SC003. (Issue #6501)

## Phase 5 — Convergence и закрытие

- [ ] T012 Сверить `specs/290-post-release-hardening/tasks.md` с реализацией через converge; на каждом новом PR свои checks, merge после обязательных проверок, для нового frozen release свой Full и dry-run/approved deploy; FR010. (Issue #6501)
- [ ] T013 После всех результатов и T012 выполнить live `scripts/validate-issue-closeout.py` для #6501 и затем umbrella #7646, добавить русские closure comments и проверить actual state; записать `specs/290-post-release-hardening/validation.md`; SC004. (Issue #7646)

## Dependencies / execution strategy

T001 → T002 → T003 → T004 → T005. US2/US3 независимы от CI реализации,
но требуют своих данных/design/review и полномочий. T006→T007→T008;
T009→T010→T011; все→T012→T013. Параллельных кодовых задач нет.
MVP данного среза: T001–T004; T005 только после разрешённого commit/PR.
T001–T004 локально подтверждены. T005/T014/T015 приняты в PR#7679 после настоящих проверок GitHub; T006–T013 остаются открыты до своей приёмки.


## Остаток настоящей native-проверки — 19.10.2026

- [X] T014 [US1] Исправить обнаруженную Apple Swift6.0.3 ошибку чтения argv из async main в `apps/macos/Shared/Tools/MeetingMuteTruthRuntimeProof/main.swift` через существующий Foundation ProcessInfo; сохранить все параметры/синтетические проверки, выполнить независимое review и настоящий native CI нового SHA. FR004; T014 → T005. (Issue #6501)


## Phase 6: Convergence — ошибки method reference в Apple Swift6.0.3

- [X] T015 [US1] Заменить две передачи MainActor-методов в Optional.map на явные синхронные замыкания в `apps/macos/RecApp/App/TwoBrainRecApp.swift`; сохранить проверки свежести решения, recovery text, fallback и actor/compiler/SDK gates; выполнить независимые review, scoped lifecycle/capture tests и настоящий Apple Swift6.0.3 build/XCTest/ContractValidation. FR004/SC001 (partial, HIGH); T015 → T005. (Issue #6501)


## Принятие CI-среза — 21.10.2026

T005/T014/T015 подтверждены PR#7679: source
d10b97b9bba73cdf0c8e8eb295b2eab0963cade4, checked base
845e6dcff7eb7f8e0e2b884902080ecb96582a3a, merge
a42b78e1878cc4830681e290aed8408cae10c556. Общий validate-pr-checks.py
завершился exit0; настоящие AppleSwift6.0.3 build,1234XCTest(2SKIP/0FAIL)
и ContractValidation успешны. Ссылки/пределы — в validation.md.
T006–T013 и #6501/#7646 остаются открытыми; принят только US1 CI-срез.
