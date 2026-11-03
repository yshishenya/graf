# Повторное независимое ревью требований US3: PASS только после очистки

Дата: 2026-10-23. Feature F263, T007/FR-011, issue #6907, PR #7737.
Ветка `codex/263-cleanup-validation`, HEAD
`fc42afe2aa180309b7e175d6fe28022f11ccf7a6`.
Замечание PRRT_kwDOSpM8OM6vqUmD рассматривается по локальному источнику;
сеть для чтения самого GitHub thread рецензент не использовал.
Lane: active Spec Kit slice, CI tooling с изолированным Docker/PostgreSQL.

**Gate требований PASS: 8 checked / 0 unchecked. Пробелов требований,
требующих новой задачи/issue/фичи, не обнаружено.** FR-011 и CHK001/002
уже требуют отсутствия ложного PASS при отказе обязательной очистки.
Реализация этого повторного исправления пока не принята и в рамках review
не менялась. Нынешний код ещё печатает преждевременный marker.

## Причина и достаточность исходных требований

`spec.md:127` прямо требует: ошибки/пустота/cleanup не дают ложного PASS.
Session2026-10-23 дополнительно определяет весь запуск с учётом очистки,
изменение успешного итога на ошибку при отказе удаления и сохранение исходной
ошибки. `plan.md:139–153` назначает один существующий cleanup, точное владение
контейнером и сохранение ненулевого кода; расширять инфраструктуру не нужно.

В текущем runner `:428`, `:462–464` и `:490` печатают соответственно fast,
focused и full `postgres_test_result=pass` до EXIT trap. `cleanup:23–40`
затем может получить отказ docker rm и завершить процесс1. Exit code уже
правильный, но сообщение о результате противоречит FR-011. Это устранение
недоведённого существующего договора T007, а не новая пользовательская функция.

## Повторная проверка8 пунктов

| Пункт | Основание и итог |
|---|---|
| CHK001 | FR-011 и Session определяют успех всего процесса после очистки; ранний PASS запрещён тем же требованием. PASS. |
| CHK002 | Session/plan различают removed/failed, исходный exit code и130/143; исправление marker не должно менять эту семантику. PASS. |
| CHK003 | Plan ограничивает удаление только сгенерированным именем собственного контейнера; marker не требует новых Docker действий. PASS. |
| CHK004 | FR-008/009, SC-003 и прежние subprocess/phase контракты остаются действующими; перенос сообщения не меняет collection/partition/strict. PASS. |
| CHK005 | FR-011 сохраняет ошибки аргументов/пустоты/inventory; inventory_only и help с exit0 нельзя ошибочно превратить в тестовый PASS. PASS. |
| CHK006 | Plan/quickstart различают подставной Docker и настоящие PG/RLS прогоны workers1/2. Новые marker отрицательные/положительные contract пробы должны проверять реальный runner; они не доказывают реальную PostgreSQL очистку. PASS. |
| CHK007 | SC-002/003 и Session сохраняют неизвестный исходный baseline US2 и открытый общий остаток F263. PASS. |
| CHK008 | FR-015/016 и plan требуют независимое review/analyze/проверки/converge/точный PR CI; #6907 остаётся владельцем, production/release не меняются. PASS. |

Требования ясны для принятия узкого решения без новых вопросов владельцу.
Checklist перечитан после записи: **8 checked / 0 unchecked**.

## Callers и потребители результата

Проверен runner полностью в относящихся к setup/trap/mode/terminal sections,
все три места печати marker, inventory-only и help пути. Поиск литерала
`postgres_test_result` в исполняемых infra/scripts/.github/apps/server/tests/tests
показал runner и существующие contract assertions. Внешнего исполняемого
парсера этого marker в просмотренных tracked путях не найдено.

- `infra/scripts/ci-local.sh:178–194` вызывает runner отдельным Bash процессом;
  получает его exit status, stdout с marker не парсит.
- `.github/workflows/release-full.yml:310–338,464–483` вызывает partitioned
  focused serial и sharded parallel в subshell; формирует component result по
  коду возврата, проверяет coverage evidence отдельно. Изменение времени печати
  без изменения текста marker не требует новых workflow или receipts.
- `scripts/ci-behavior-tests.py:100–122` вызывает focused runner, проверяет
  returncode, затем реальный JUnit; marker не заменяет это доказательство.
- `test_local_postgres_test_runner.py:125` ожидает сохранения literal fast
  marker в source; `:259` запрещает PASS на ошибках, `:434` проверяет точный
  focused/partitioned/shard текст. Текущие cleanup-failure tests `:513–559`
  проверяют exit/removed, но ещё не запрещают ложный PASS — нужное расширение
  приёмки существующего контракта.
- `tests/governance/test_test_resources.py:94–106` проверяет returncode и
  штатный JSONL, не ранний PASS. Фикстуры PostgreSQL/playback содержат указание
  команды запуска как диагностику, не авторитетный парсер marker.

## Допустимый самый короткий вариант

Одна пустая строковая переменная результата, созданная до trap; каждая из
трёх существующих успешных ветвей после всех своих фаз только сохраняет в неё
свой прежний полный marker (с mode/partitioned/shard/digest). Никакого вывода
PASS в этот момент. В конце единственного cleanup, после удаления метаданных
и обработки Docker, печатать сохранённую строку только если окончательный
exit_status==0 и строка непустая. Затем существующий exit с тем же статусом.
Допустим `printf -v` для форматированных focused/full строк: он есть в Bash
Mac3.2, отдельная функция/формат/зависимость не нужны.

Так ранний help/argument/setup/inventory_only exit не получает marker: ни одна
успешная тестовая ветвь не сохранила строку. Настоящий успешный pure запуск без
контейнера сохраняет marker и получает его после container_not_started; это
не повод требовать Docker для чистых unit. Сигнал/ошибка с уже установленной
строкой также не печатает PASS, поскольку итоговый статус ненулевой. Можно
эквивалентно хранить один success флаг и печатать существующие строки в cleanup,
но не нужно вводить новый result protocol, общий dispatcher, wrapper runner,
state machine, повторную очистку или повторный запуск фаз.

Сохранить точный текст и единственность mode-specific marker, привычные
cleanup diagnostic строки, прежние коды ошибок и130/143, все параметры режима
и исходную выборку. Очистка должна предшествовать единственному PASS в stdout.

## Минимальная приёмка исправления

Исполнять настоящий runner через существующий subprocess harness. Для fast,
focused, partitioned/sharded focused и full подтвердить: при успешных фазах,
но failed cleanup нет PASS и returncode1; при успешном cleanup ровно один
прежний marker после cleanup. У fast охватить чистый путь без контейнера и
путь с ресурсами. Для исходных ошибок17/сигналов130/143 сохранить итоговый код,
не выдавать PASS. Inventory_only/help/ошибки аргументов/пустой inventory/setup
failure не получают тестовый marker, хотя некоторые из этих путей завершаются0.

RED должен показать именно ложный PASS старого runner при failed cleanup;
затем GREEN для нового кода и весь профиль существующего contract. Прежние
реальные PG/RLS доказательства сохраняются как доказательства той версии,
а актуальность повторения прогонов/точного CI оценивается исполнителем по
изменению и исходным plan/quickstart; старый SHA не выдаётся за новый.
Независимое code review, converge, новый exact-SHA/base required CI и общий
валидатор обязательны до merge/closeout #6907. Ни этот gate требований, ни
локальный contract не доказывают hosted success, выпуск или production.

## Ограничения рецензента

Записаны только runner checklist и настоящий отдельный отчёт. Код/spec/plan/
tasks, Git/GitHub и приложение не менялись; тесты/сеть/установки не выполнялись.
Использованы ранее полностью прочитанные неизменные AGENTS/constitution и
процессное guidance с повторной сверкой хешей и относящихся sections; индекс
guidance перечитан. Исторические unrelated части F263 не перечитывались целиком.
Чужие изменения сохранены.

## Контрольные суммы снимка требований и потребителей

| Файл | SHA-256 |
|---|---|
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/tracker-policy.md` | `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/263-fast-feedback/spec.md` | `5e994d37e1c5425bda860e72cd3943fbac4ccec0270e2e1625a31b189b31bfd2` |
| `specs/263-fast-feedback/plan.md` | `d4285afe75002fb70c2f4c0aa6dd03610df77a1ec6dfdce5a9e4cbcd2bfaf522` |
| `specs/263-fast-feedback/tasks.md` | `d4fbd16d8406db73b14d845c86d0a79e793b6c05516694292623d6454d8dd375` |
| `specs/263-fast-feedback/quickstart.md` | `99d27b29e73fc4713d17b39a3ef14df56c5c2ac12d922a84a3088e4b29fc2d10` |
| `specs/263-fast-feedback/checklists/runner.md` | `85c25f39fd2ddf5aa7515bae471d29708f005b717d3fce659b38f431445376d0` |
| `apps/server/scripts/run_local_postgres_tests.sh` | `34d8751a54a24ca3a961430d248cdddb6a24c7c91e28f05e3bdb0519b1d6e3e7` |
| `apps/server/tests/contract/test_local_postgres_test_runner.py` | `1fe6fcd238f0b6468ba9023b90f5be6e312acfc303b25b57c28f050c14f22be5` |
| `infra/scripts/ci-local.sh` | `8b62fe9739f7c7fdf0056dd8609e27ad8cbc5205d9d1456c7f0dcea15875af9a` |
| `scripts/ci-behavior-tests.py` | `b905e80f378e7b9556c27160a148eb35eb706e78dc300fda1935d59d53ca5392` |
| `.github/workflows/release-full.yml` | `22a9ba6d7c1e5db47359fcb2e3097b1078c7fb99d903d71205d0cc069a935987` |
| `tests/governance/test_test_resources.py` | `4bb87604d242db2e200a43056ca4fc98540dbfad15ae9cf4e1e23068dfb03c60` |
