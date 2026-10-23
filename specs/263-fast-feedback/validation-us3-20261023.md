# F263 / US3: текущая приёмка T006–T008

Дата: 2026-10-23. Issue #6907. Lane: active Spec Kit slice, CI tooling;
изолированные PostgreSQL/Docker, без продукта, выпуска и production.
Основа: `9324cd60e749c0e7bf4919a35d5f350dddca2b66`.

## Исходный отказ и исправление

Существующие 85 runner contract и два первоначальных настоящих PG-запуска
были успешны. Новый отрицательный контроль выявил дефект: ошибка `docker rm`
подавлялась, итог был exit0 и печаталось ложное `isolated_container_removed`.

Закреплены 7 направленных случаев в существующем contract-файле:
обычный focused, partitioned и full после успеха, исходный exit17,
настоящие сигналы INT/TERM родительскому Bash, отказ очистки при startup.
На прежнем runner все 7 ожидаемо FAIL; после исправления весь файл:
**92 PASS, 0 fail/skip**, 199.25 s. Предупреждения: 2 существующих сообщения
о повторной загрузке plugin и устаревшем httpx/TestClient; отказов нет.

В общем cleanup проверен исход удаления. Только успех печатает removed,
ошибка печатает remove_failed и превращает успешный код в 1. Исходные
17/130/143 сохраняются. При ошибке удаления во время startup запуск
останавливается и сохраняет владение точным контейнером для общего cleanup.
Префиксного удаления, обходов Docker, новых зависимостей и менеджеров нет.

## Настоящие PostgreSQL / миграции / RLS

Оба запуска исполнены после изменения runner командами quickstart §US3.
`GRAF_PERFORMANCE_GATE=required`, `PYTEST_ADDOPTS=''`, новый каталог каждого
прогона. Изоляция, миграции, настоящие RLS роли и worker-БД сохранены.

| Запуск | Workers | Время всего | Parallel | Performance | Strict | Итог |
|---|---:|---:|---:|---:|---:|---|
| 1 | 1 | 65.691 s | 66 | 1 | 1 | 68 call PASS, exit0 |
| 2 | 2 | 52.922 s | 66 | 1 | 1 | 68 call PASS, exit0 |

В каждом JSONL наборе 68 уникальных call IDs, группы не пересекаются,
setup/call/teardown все passed; наборы двух запусков совпадают.
Исходный collection count68, digest обоих:
`2efaa9c35e4470308cb944631052b9cea512e8eb38d7ae1b01c851a25a1e1034`.
SC017 выполнен, нет xfail/skips. После завершения Docker не содержит
контейнеров `graf-postgres-test` этих запусков. Два наблюдения не являются
медианой/p95 и не доказывают устойчивое ускорение.

Дополнительно: четыре настоящих запуска с workers0/9/-1/x отвергнуты exit2
до Docker; отдельный subprocess с requested8 подтвердил cap4 и ровно пять
синтетических cases. Docker подменён только в contract/cap проверках.

## Состав исходников и сохранённые доказательства

| Файл | SHA-256 |
|---|---|
| `apps/server/scripts/run_local_postgres_tests.sh` | `34d8751a54a24ca3a961430d248cdddb6a24c7c91e28f05e3bdb0519b1d6e3e7` |
| `apps/server/tests/contract/test_local_postgres_test_runner.py` | `1fe6fcd238f0b6468ba9023b90f5be6e312acfc303b25b57c28f050c14f22be5` |
| `apps/server/tests/fixtures/test_resources.py` (не изменён) | `d8486960f20ba89f7c84f66025291c05fc69bf8113a1a02fdc71b69b302cf3f0` |

Локальный реестр аудита `issues-334-audit` содержит:
`f263-cleanup-red-20261023.log`, `f263-runner-green-20261023.log`,
`f263-us3-green-workers{1,2}-20261023.log/.json` и их JSONL,
`f263-us3-green-evidence-20261023.json` с командами/окружением/хешами,
`f263-worker-invalid-20261023.log`, `f263-worker-cap-20261023.log`,
`f263-process-20261023.log`. Доказательства содержат только синтетические
случаи и технические метаданные; реальные встречи и секреты не использованы.

Shell syntax, Ruff затронутого теста, diff, process, context, governance,
changelog PASS. Требования приняты независимым reviewer: runner8/0,
calendar15/0, reading12/0, built-in7/0. Analyze CRITICAL0/HIGH0,
canon ensure/validate PASS, live #6907 владеет T006/T007/T008 без дублей.

## Convergence и границы

FR-007–011/SC-003: настоящая исходная subprocess-выборка, disjoint union,
strict precedence, ограниченные workers, ошибки/empty/изменение inventory,
честная очистка и реальные PG/RLS/two-runs проверены существующим механизмом.
FR-015/016: текущие требования/review/analyze/sync и журналы сохранены,
фрагмент F263 описывает только фактическое исправление. В текущей US3 нет
обязательного локального пробела или новой дублирующей задачи.

US2 и неизвестные четыре исходных node IDs/тройные замеры не приняты.
T001/T002/T004/T005/T010/T011 и общая #6901 сохраняют исходные критерии.
Установленный GRAF, Full release, выпуск и production не выполнялись.
До закрытия #6907 обязательны независимое ревью кода, commit/PR, три успешных
GitHub checks точного SHA/основы, общий валидатор, merge и live closeout.
