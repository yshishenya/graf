# Проверка F263 / текущая часть US4

Это восстановленный документ2026-10-16. Оригинальные четыре node IDs US2
неизвестны; команды ниже не заменяют их и не закрывают T002/T005.

## Предпосылки

Python/uv/Node и уже подготовленное серверное окружение; Docker с существующим
postgres:17-alpine. Проверить свободное место; крупных сборок/копий не делать.
Сохранять только текстовые итоги, временный контейнер убирает штатный runner.

## Карта и обязательные отказы

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/server/src apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_ci_cd_contract.py
```

Проверить matching/API/model, calendar prefix, migration0021 и mapped tests;
union/covered без повторов; кабинет не выбирает календарь; unknown/shared/rename
и недоступная/неверная база не теряются; missing/empty/syntax/symlink отвергаются;
skip/deselect/ненулевой runner не дают PASS. Проверка runner-команды подтверждает
required performance, сброс фильтров и один JUnit. Stub сценарии — проверка
связывания команд, реальный продуктовый запуск ниже обязателен отдельно.

## Реальный календарь

```sh
GRAF_PERFORMANCE_GATE=required GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh --focused -q -o addopts= tests/contract/test_calendar_auto_context_contract.py tests/integration/test_calendar_auto_context_match.py
```

Оба файла PASS, включая serial_performance; нетskip, контейнер удалён. Затем
реальный `--focused` через карту для изменения matching.py должен выбрать и
выполнить те же файлы. В смешанном --fast целые mapped файлы исключаются из
changed-tests; calendar performance этап не повторяет исполненный полный файл.

## Регрессия и последующая приёмка

Runner contract, governance, shell syntax, Ruff, process/context/changelog/diff.
Converge перед commit. После commit/PR — три
required PR checks на точном SHA и checked base. Затем merge; release-full
понадобится только для будущего frozen release. Ни общий CI, ни вся F263,
ни installedGRAF не считаются принятыми по локальному результатуUS4.

## Самостоятельная US1 — повторное чтение

Исходные AGENTS/конституция/PRD/status/product-gates не меняются. До реализации
прочитать требования US1 в spec.md и plan.md, пройти независимый контрольный
список document-reading.md, analyze и сверку #6905. Проверка документации:

1. На текущих файлах записать SHA-256 и UTF-8 байты; первое чтение остаётся полным.
2. Известная область: прежние документы совпадают, полное чтение доступно в том
   же диалоге; сравнить байты повторного полного чтения и процедуры.
3. Пересечение: добавить и прочитать целиком инструкции второй области и
   зависимости; проверить, что прежняя область и общие ограничения сохранены.
4. Неизвестная область: все четыре базовых документа читаются полностью до
   изменений, сокращение повторного чтения не заявляется.
5. Изменение принципа: те же четыре документа полностью и отдельный путь
   изменения конституции; правила нельзя менять только через краткую процедуру.
6. Отказы: изменённый/неподтверждённый хеш, отсутствующий/нечитаемый файл, другой
   диалог/агент, одни заголовки/поиск, сжатый пересказ и неполный контекст.
   Каждый требует полного чтения или остановки до восстановления доступа.

Это документальная проверка объёма и сохранения обязанностей, не измерение
токенов, скорости модели или продуктовая приёмка. Итоги записать в validation.md;
T003 отмечать только после независимого review/converge. Новая часть требует
своих checks точного SHA/основы. Остальная F263 остаётся открытой.


## Самостоятельная US3 — T006/T007/T008, 23.10.2026

До реализации пройти reviewer-owned `checklists/runner.md`, анализ требований
и сверку существующей #6907. Первый отрицательный контроль должен подтвердить
ложный успех при отказе удаления временного контейнера. Режимы, сигналы и
неуспешные тесты проходят через один cleanup; product/deploy не запускаются.

Contract-профиль (реальные subprocess/xdist; Docker в contract заменён):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/server:apps/server/src apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_local_postgres_test_runner.py
```

Команду выполнять из корня репозитория с окружением текущей рабочей копии.
Отдельного contract-файла plugin нет; его поведение покрывается существующим
`test_local_postgres_test_runner.py` через настоящие subprocess-запуски.

Два независимых запуска одного набора, отдельно `GRAF_TEST_WORKERS=1` и `2`:

```sh
GRAF_TEST_WORKERS=1 GRAF_PERFORMANCE_GATE=required PYTEST_ADDOPTS='' \
  GRAF_TEST_REPORT_DIR=<новый-каталог-метаданных-первого-запуска> \
  bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned \
  -q -o addopts= \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_recording_origin_cancellation.py \
  tests/integration/test_rls_postgres_policies.py::test_runtime_roles_are_non_superuser_and_cannot_bypass_rls
```

Второй запуск использует workers=2 и другой новый каталог. На исходном коде
этот набор содержит 68 случаев: 66 parallel, 1 performance, 1 strict. Сверить
collection count/digest с call case IDs, непересекающиеся группы и одинаковую
выборку двух прогонов; setup/call/teardown не считать разными тестами.
Подтвердить настоящее выполнение миграций и RLS, отсутствие skips/failures,
обязательный SC017 и фактическое удаление собственных контейнеров. Записать
времена отдельно, не объявлять по двум запускам устойчивое ускорение.
Это приёмочный набор US3, а не подмена четырёх исходных node IDs US2.

После исправления: shell syntax, Ruff затронутого теста, процесс/governance/
changelog/diff, независимое code review и convergence; затем точные GitHub
checks/основа, обычный merge и live closeout. Выпуска и production нет.
