# Независимая итоговая проверка US3: итоговый PASS после очистки

Дата:2026-10-23. Feature F263, T007/FR-011, #6907, PR #7737.
Ветка `codex/263-cleanup-validation`, исходный HEAD
`fc42afe2aa180309b7e175d6fe28022f11ccf7a6` и текущий незакоммиченный diff.
Lane: active Spec Kit slice, CI tooling/Docker/PostgreSQL.
Применён ранее прочитанный skill code-reviewer.

**PASS: обязательных замечаний к текущему узкому исправлению нет.**
Это независимое чтение кода и уже выполненных доказательств, не новый запуск
тестов и не hosted CI. После коммита нужен новый точный SHA/base набор checks.

## Исправление прежней оценки рецензента

В `review-us3-implementation-20261023.md:40–41` было утверждение, что ранняя
строка результата перед EXIT не является итоговым receipt. Этим утверждением
было ошибочно оправдано сообщение `postgres_test_result=pass` после которого
обязательная очистка могла завершиться отказом. Это **неполная проверка
рецензента**, а не исключение из FR-011. Код возврата процесса был правильным,
но отдельное сообщение PASS оставалось ложным. Настоящий отчёт исправляет эту
оценку; прежний PASS не покрывает ранний marker и не используется как основание
приёмки нового diff. Требование всё время оставалось прежним.

## Фактический diff и проверка ветвей

Runtime diff состоит из одной пустой `result_marker` до trap, одного условного
вывода в конце cleanup и трёх замен раннего printf на сохранение прежнего текста.

- `runner:16` задаёт пустую строку до установки EXIT/INT/TERM traps.
- `cleanup:24–44` сохраняет исходный статус, удаляет метаданные, исполняет
  прежнюю точную Docker cleanup команду и её failure semantics. Вывод результата
  возможен только после этих действий, при exit_status0 и непустой строке.
- Fast сохраняет полный буквальный marker только после обеих своих фаз;
  pure fast без контейнера проходит container_not_started до PASS.
- Focused сохраняет прежние partitioned/shard значения после всех выбранных
  фаз, как для обычного, так и partitioned/sharded запуска.
- Full сохраняет collection_digest только после strict/performance/parallel;
  последний printf -v успешно заканчивается0 и вызывает общий EXIT trap.
- Help/inventory-only/ошибки аргументов/пустота/setup failure не заполняют строку.
  Сигналы130/143 и исходная17 остаются ненулевыми; даже непустая строка при
  ненулевом окончательном статусе не выводилась бы. Новых функций/протоколов
  результата, повторных фаз, Docker удаления или зависимостей нет.
- Точные marker contents и единственная завершающая LF сохранены.
  printf -v совместим с Bash3.2. Docker selection, namespace, Postgres/RLS,
  migrations, worker/partition/strict и product paths не менялись.

Проверены вызывающие участки ci-local, ci-behavior-tests и оба release-full
компонента: они продолжают получать статус отдельного процесса, component
receipts/JUnit/coverage остаются самостоятельными доказательствами. Нового
зависимого парсера, требующего раннего вывода, не найдено. Существующие
literal/focused marker assertions сохранены.

## Проверенные исполняемые пробы

Contract diff расширяет существующий harness вместо нового runner. Подставная
uv команда направляет tests/unit в временную коллекцию; fixture допускает
отсутствие worker database для pure режима. Это необходимо только для покрытия
fast. Старые проверки с PostgreSQL prefix сохраняются, код fixtures продукта
не меняется.

Отрицательные cleanup случаи охватывают ordinary focused, partitioned,
sharded focused, full и fast с ресурсами: итог1, ни PASS, ни ложного removed,
единственная команда удаления собственного имени. Существующие17/130/143 и
startup cleanup ownership остаются. Успешные варианты проверяют ровно один
marker и порядок removed→PASS. Pure fast проверяет отсутствие Docker calls,
три исполненных case и container_not_started→PASS. Help/inventory-only и
ошибочные аргументы дополнительно запрещают тестовый PASS.

Прочитанные журналы основного исполнителя:

- RED `red.log`: **11 FAIL /3 PASS /86 deselected,67.08s**. Пять успешных фаз
  с failed cleanup обнаружили ложный marker, пять success вариантов обнаружили
  неверный порядок, pure fast — тот же порядок. Три прежних ненулевых/сигнальных
  пути уже не имели marker и прошли. Это доказанная чувствительность regression.
- GREEN `green.log`: **100 PASS,240.19s**, два прежних предупреждения Starlette.
  Новый итог прочитан в самом завершённом журнале, не только в validation prose.

## Два настоящих PostgreSQL прогона

Независимо прочитаны сохранённая команда `run-pg-verification.py`, workers JSON,
все6 JSONL и два полных worker log. Без запуска кода проверки пересчитаны
call IDs/исходы/фазы/наборы и порядок terminal сообщений из фактических файлов.

| Workers | Наблюдаемое время | Call cases | Фазы | Итог |
|---:|---:|---:|---|---|
| 1 |64.014s|68|66 parallel +1 performance +1 strict|exit0; PASS после removed|
| 2 |51.210s|68|66 parallel +1 performance +1 strict|exit0; PASS после removed|

Все setup/call/teardown records имеют passed; каждый call ID встречается ровно
один раз в своём запуске. Оба набора равны. Пересчитанный digest:
`f3ddcacd0583efe9f98ae62c7e5d5b1e5c2df461e049afee03537f17bfc8b24d`.
SC017 case_id
`2bbbdfe79717edb0a38491019b0365280e44281fe34c4701bab91d29065fdd5b`
найден именно в performance JSONL обоих запусков, все3 lifecycle records passed.
В каждом worker log ровно один PASS, непосредственно после cleanup removed.

Дополнительно рецензент выполнил только read-only инвентаризацию
`docker ps --all --filter 'name=^/graf-postgres-test-' --format ...`:
успешный пустой вывод, соответствующих оставшихся контейнеров сейчас нет.
Контейнеры/тесты/приложение не запускались. Разница двух времён не является
медианой, p95 или доказательством ускорения; прогоны частично пересекались
с contract работой, как честно записано в validation.

## Все4 checklist перечитаны

| Checklist | Checked | Unchecked | Применение |
|---|---:|---:|---|
| runner.md |8|0|FR-011 правдивость после cleanup, сигналы/изоляция и независимая приёмка сохранены.|
| calendar-behavior.md |15|0|Исходная US4, обязательный performance threshold и PG/RLS не затронуты.|
| document-reading.md |12|0|Хеши и чтение применимых документов сохраняются, US1 не расширяется.|
| requirements.md |7|0|Границы F263 и неизвестного baseline US2 остаются прежними.|

Это перечитанное состояние качества требований, не новая приёмка unrelated
задач. Рецензент не менял отметки ни одного checklist. Requirements gate
`review-us3-pass-marker-20261023.md` остаётся8/0; новые требования не добавлялись.

## Контрольные суммы и ограничения

Четыре значения ready-for-review.json самостоятельно сверены с фактическими
runtime/contract/validation/changelog bytes: все совпали. Validation-us3
исправляет прежнюю оценку review и содержит текущие100-case и PG результаты.

Записан только настоящий отдельный отчёт. Runtime/spec/plan/tasks/checklist,
Git/GitHub/приложение/релизы/данные не менялись. Сеть, установка и тесты не
выполнялись. Прежнее чтение неизменного constitution/guidance использовано
в том же диалоге; актуальные изменённые файлы и зависимости перечитаны.

Source CI на fc42 остаётся доказательством прежнего source. После коммита
данного diff обязательны новые governance-fast/macos-pr/pr-metadata точного
SHA/base и общий validate-pr-checks.py, затем merge и штатный live closeout
#6907. До этого issue не закрывается. Общая F263, US2 и прочие незавершённые
критерии не приняты; Full, release и production не выполнялись.

## SHA-256 фактически проверенного снимка

| Файл | SHA-256 |
|---|---|
| `apps/server/scripts/run_local_postgres_tests.sh` | `b5858c56db899be16cdf842c42ecd87aa1984cac94f56015051eeb4e96240d07` |
| `apps/server/tests/contract/test_local_postgres_test_runner.py` | `494eb52775d37fe9a41a81bf0efe621af43794af5a1a4ab94e41c2bbe7b31bad` |
| `apps/server/tests/fixtures/test_resources.py` | `d8486960f20ba89f7c84f66025291c05fc69bf8113a1a02fdc71b69b302cf3f0` |
| `changes/unreleased/F263.yaml` | `9093044f6594fbad69c1fd0a9ca7cc06f6c873ee9077b9a27b334f0029bef597` |
| `specs/263-fast-feedback/validation-us3-20261023.md` | `18c6c3d244ae695552e4f5c08d2ac748a3ddcdcee95988944c5be33085090c47` |
| `specs/263-fast-feedback/spec.md` | `5e994d37e1c5425bda860e72cd3943fbac4ccec0270e2e1625a31b189b31bfd2` |
| `specs/263-fast-feedback/plan.md` | `d4285afe75002fb70c2f4c0aa6dd03610df77a1ec6dfdce5a9e4cbcd2bfaf522` |
| `specs/263-fast-feedback/tasks.md` | `d4fbd16d8406db73b14d845c86d0a79e793b6c05516694292623d6454d8dd375` |
| `specs/263-fast-feedback/quickstart.md` | `99d27b29e73fc4713d17b39a3ef14df56c5c2ac12d922a84a3088e4b29fc2d10` |
| `specs/263-fast-feedback/checklists/runner.md` | `85c25f39fd2ddf5aa7515bae471d29708f005b717d3fce659b38f431445376d0` |
| `specs/263-fast-feedback/checklists/calendar-behavior.md` | `90b8e2055bdc23c07de7857637817ab8f6c655d1f1281d1657b59149ffc8ecfc` |
| `specs/263-fast-feedback/checklists/document-reading.md` | `dc0e6711c3d60b21386359277cfad23ac70acfc4c33df71fb822e09d79c83c23` |
| `specs/263-fast-feedback/checklists/requirements.md` | `796bb2bf3cacb33f7e5ba7c83f89e64da087ffd7c10ec50eef57647856cab217` |
| `infra/scripts/ci-local.sh` | `8b62fe9739f7c7fdf0056dd8609e27ad8cbc5205d9d1456c7f0dcea15875af9a` |
| `scripts/ci-behavior-tests.py` | `b905e80f378e7b9556c27160a148eb35eb706e78dc300fda1935d59d53ca5392` |
| `.github/workflows/release-full.yml` | `22a9ba6d7c1e5db47359fcb2e3097b1078c7fb99d903d71205d0cc069a935987` |
| `.dev/us3-pass-marker/green.log` | `4bb25e57e0e211425cdf976644e5b672b6ca0621f95159f49f9560dc774d731d` |
| `.dev/us3-pass-marker/red.log` | `20aae5e3e567585e6e09460adf9fecffee7ef1a32b3c468b1d3f077ecf805050` |
| `.dev/us3-pass-marker/workers1.log` | `e4ac8268c38a24602939c0dd93fc183bd4c476000231f03ce08d1f7669d4b0a0` |
| `.dev/us3-pass-marker/workers2.log` | `7769f8112005acf95eaf082cd71d519f3b7f738dd75c7d6865df9ef7316e44b7` |
| `.dev/us3-pass-marker/workers1.json` | `e41e93262910b4de2394b00ee3728bf05da91224e6b8bf533ec6483c35b7edfa` |
| `.dev/us3-pass-marker/workers2.json` | `bfb345714c7584cbaac357aaacdeb4a5e339903ce542187ba13ba06f1e48a33f` |
| `.dev/us3-pass-marker/workers1/focused-parallel.jsonl` | `46f85bf4cb674a95c6c8134197f1418d6d68c1ecb735f9637b8a23538fc3e10b` |
| `.dev/us3-pass-marker/workers1/focused-performance.jsonl` | `ca3466c6bd52febf7b2ce28767697b9ecda2b2d3d1b40f688a69e7b9ff1283ae` |
| `.dev/us3-pass-marker/workers1/focused-strict.jsonl` | `1c341c91b8addbffbd275d52c71f2e475c780f28277ebb298d4520b1a1cc04d5` |
| `.dev/us3-pass-marker/workers2/focused-parallel.jsonl` | `0f5602c45ae6b10281abafb619a467a423b6231279dfc521db1f9b3abd29b099` |
| `.dev/us3-pass-marker/workers2/focused-performance.jsonl` | `fb42f20226ebb257c7af7d8167b07f80075a1c9e8c4909f152e49c5276e3e0dd` |
| `.dev/us3-pass-marker/workers2/focused-strict.jsonl` | `5207c60a311535fe11bfcd105778361f5b2fabf9efecc505223a92f4014a78d9` |
| `.dev/us3-pass-marker/ready-for-review.json` | `50630a844b150a9d4d26344b449148c00b4985700e32f8b011d58453aa19ac26` |
