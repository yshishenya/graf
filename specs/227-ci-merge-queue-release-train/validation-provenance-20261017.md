# F227: итоговая проверка T032–T033

Дата: 2026-10-17 Europe/Istanbul. Ветка: `codex/227-ci-merge-queue-release-train`.
Исходный SHA: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Lane: Active Spec Kit slice, инфраструктура/происхождение выпуска. Issue: #7645.
Изменения не закоммичены, не приняты в master и не выпущены.

## Причина и исправление

Обычный serial release operator уже создаёт настоящий synthetic commit;
новый режим/nullable SHA не нужны. До изменения функция принимала base,
если он предок synthetic ИЛИ source. Изолированный Git fixture подтвердил,
что base из посторонней истории ошибочно проходит по synthetic.

Общая проверка теперь требует base → actual source. Существование всех трёх
Git commit objects и distinct source/synthetic сохранены. CLI, schema,
проверки current source, чистоты, PR и Full CI не изменены. Все callers изучены:
train-freeze вызывает общую функцию; scripts/release.sh создаёт правильный
commit-tree. В F259 proof-binding пересечения кода нет.

## Выполненные проверки

- До кода новая regression: **1 FAILED / 0.94s**, ровно на ошибочном принятии
  несвязанной базы (`assert rejected.returncode != 0`, фактически 0).
- После исправления та же regression: **1 PASS / 0.91s**.
- Адресный итоговый набор: **121 PASS / 70.39s**, без skipped:
  `test_release_train.py`, `test_release_candidate.py`,
  `test_merge_group_mapping.py`, `test_ci_event_identity.py`,
  `test_governance_workflow.py`, `test_ci_evidence_producer.py`, `test_ci_guard.py`.
- Сама regression последовательно доказывает serial freeze/validate с тремя PR
  и пустыми queue arrays; отказ unrelated base и отсутствующего synthetic.
  При отказах нет manifest и sidecar identity.
- `validate-agent-context.py`, `check-development-process.py`,
  `check_spec_kit_governance.py` — PASS. Первоначально штатное разрешение путей
  создало неполный ignored pointer; до implementation заполнены branch/SHA,
  lane/owner/owned_paths, обе проверки контекста повторно PASS.
- `validate-release-train.py --self-test`,
  `validate-governance-workflow.py --self-test` — PASS.
- `bash -n` для release-candidate.sh и release.sh; `git diff --check` — PASS.
- Issue canon ensure — PASS без изменений tracked governance; validate —
  PASS (300 открытых Spec Kit issues). Для T032–T033 после проверки всех32
  исходных F227 issues создан один owner #7645; дубликатов нет.
- Независимое предреализационное ревью: CRITICAL0/HIGH0, requirements16/0,
  infra13/0. Ревью кода: findings0, собственные **9/9 PASS**, shell/self-test PASS.
  Отчёт: [review-provenance-20261017.md](review-provenance-20261017.md).
- Анализ: покрытие **18/18** FR+SC; CRITICAL0/HIGH0; MEDIUM1 — историческая
  reconciliation старых задач, которая остаётся в T030/#6237.

PR checks/Full CI в fixture подставлены. Эти результаты не являются настоящими
GitHub merge-group/PR/release доказательствами. Существующие 72 и отдельный новый
регрессионный проход входят в121; их нельзя складывать как различные проверки.

## Convergence текущего среза

T032–T033 локально выполнены, новых незавершённых работ в их области не найдено.
Весь исходный объём T001–T031 сохранён. Native T029/T031, полная reconciliation
T030/#6237, точный PR SHA/три GitHub checks, merge и вся F227 остаются открытыми.
Чеклист PASS означает качество требований, не завершение native инфраструктуры.

Дальнейшие gates: отдельное разрешение на commit и draft PR, затем exact-SHA
GitHub проверки. Merge, выпуск и развёртывание требуют отдельного разрешения.
Этот срез не менял GitHub protection/queue, приложение и production runtime.
Свободное место перед проверкой:91GiB; сборки/архивы не создавались.

## Контрольные суммы реализации

- `infra/scripts/release-candidate.sh`: `dcfa09b9e643cbf64481926ffa8586b61e130ec9844893bd6121feeee625beeb`
- `tests/governance/test_release_train.py`: `186669f39ecc5e824e788250a2d49e7aa4b8e29468ea0079f801deb47a7cf84d`


## Текущая сверка 19.10.2026 перед коммитом

Исторические результаты выше сохранены отдельно. Новое независимое ревью
[review-current-20261019.md](review-current-20261019.md) подтверждает APPROVE,
замечаний P0/P1/P2 нет. Оба списка требований перечитаны: requirements16/0
и infra13/0, всего29 подтверждённых пунктов /0 открытых.

Заново исполнены те же семь профильных файлов: **121 различный случай PASS,
0 FAIL/ERROR/SKIP за79.65с**. Девять release_train, включая новую regression,
входят в121; исторические результаты к ним не прибавляются. XML и журнал
самостоятельно разобраны reviewer. Код скрипта и тестов сохранил два хеша,
указанных выше. Новое ревью относится к этому снимку, а не к будущим изменениям.

Повторно PASS: validate-release-train --self-test,
validate-governance-workflow --self-test, bash syntax обоих release скриптов,
check-development-process и git diff --check. Тесты создают только отдельные
искусственные репозитории; настоящие PR proofs/Full CI не подменяются.
Приложение, Docker, рабочий сервер и GitHub protection не менялись.

Ожидание отдельного разрешения в историческом разделе устарело: пользователь
дал общее разрешение на проверенные коммиты, PR и защищённые слияния. План
обновлён только в этой формулировке после текущего ревью. Оба checklist
изменял только reviewer. Итоговый состав и хеши закреплены внешней квитанцией.

T032–T033 выполнены локально. Исходные T001–T031, историческая сверка
T030/#6237, настоящие native gates T029/T031 и вся F227 остаются открытыми.
#7645 остаётся открытой до принятия изменения, текущих трёх проверок точного
SHA/base, подробного комментария и live-валидатора. Во время согласованного
выпуска F280 слияние удерживается. Новый выпуск и развёртывание не выполняются.

## Устранение замечаний потребителей — 21.10.2026

Предварительный независимый план: review-plan-20261021.md, PASS29/0,
блокирующих замечаний0. Владелец T033/#7645; исходные T001–T031 не меняются.

Новая параметризация существующего настоящего Git-сценария воспроизвела
оба исходных обхода: legacy-unrelated — четыре потребителя вернули0;
replace-graft — четыре потребителя и train-freeze вернули0, хотя raw
история отвергала ancestry. RED:2failed/1passed. Согласованные sidecar
identity, candidate и подставленный Full были корректны, поэтому отказ
по другому условию не маскировал проблему.

Исправление состоит из общего вызова require_git_commit_relationship
после schema validation и --no-replace-objects у двух команд Git этой
функции. Форматы, source/synthetic distinct, PR/Full/cleanliness и
immutable evidence остаются прежними. Файл train suite:11PASS; связанный набор пяти файлов:103PASS,74.95с.
После отказа manifests/identity/candidate/evidence побайтово сохранены;
новых записей candidate/go/attestation/decision нет. Существующий decide
может создать пустой стабильный lock перед чтением train; этот файл
исключён из сравнения документов, защита его inode не менялась.

Исходные и итоговые журналы:
внешний набор доказательств 2026-10-21/f227-pr-closeout.
Локальная проверка не заменяет обязательные новые GitHub SHA/base checks;
настоящий Full, выпуск, production и native queue не запускались.
