# Независимое ревью реализации F263 / T009, 2026-10-16

**Результат: PASS. Нерешённых замечаний к просмотренной реализации не найдено.**
Это независимое ревью текущей локальной части US4/#6908. Оно не подтверждает
слияние, выпуск, закрытие issue или завершение US1–US3 и всей F263.

Рецензент `/root/review_f263` прочитал фактический diff относительно
`aaa5e7a2b01205d4ab962c7fb126ef7e99dadf7d` и текущие файлы целиком в применимых
областях. Рабочая копия:
`/Users/yshishenya/.codex/worktrees/fast-feedback-audit/crisp`.
Рецензент изменяет только этот отчёт; код, задачи, checklist и GitHub не меняет.

## Проверенная версия

SHA256 исходных файлов до и после независимых проверок совпали:

```text
94c8a5bc06029ed41d66f4201bca1e18725a0183c1c7a75ec90efe8cae6182ab  scripts/ci-behavior-tests.py
8b62fe9739f7c7fdf0056dd8609e27ad8cbc5205d9d1456c7f0dcea15875af9a  infra/scripts/ci-local.sh
93656ec3d3fb8a1f2c28b578517dbd28ae8d594407552cdb9636a421fbefb14a  apps/server/tests/contract/test_ci_cd_contract.py
```

## Соответствие утверждённым требованиям

| Область | Проверенный результат |
|---|---|
| CHK001–002: границы | Diff ограничен выбором и исполнением тестов. Продуктовые функции, fixtures, старые измерения, чтение документов и разбиение runner не менялись. Восстановление источников и незавершённость старых историй отражены в spec/tasks. |
| CHK003: источники | Новая группа содержит ровно два существующих contract/integration-файла. Prefix calendar, API calendar.py, модель calendar.py, миграция0021 и сами цели выбирают обе проверки. Семь параметров теста карты соответствуют утверждённой области. |
| CHK004: union/covered | Общий set выбранных файлов сохраняет отсутствие дублей; covered вычисляется после проверки пригодности всех целей. Смешанный fast исключает полные behavior-файлы из changed-tests, settings unit остаётся за unit-этапом. Контракты проверяют пять файлов, непересечение и точное объединение. |
| CHK005: обязательная скорость без повтора | При наличии полного calendar integration в behavior_targets fast отмечает performance покрытым. Behavior выполняется раньше; ненулевой результат возвращается до остальных тестов. Executor принудительно задаёт GRAF_PERFORMANCE_GATE=required, поэтому даже входной report не ослабляет порог. Отдельный performance-этап не повторяет файл; существующий тест p95≤50ms сохранён и присутствует в обоих реальных журналах. |
| CHK006: cabinet-only | Условие shared теперь ограничено двумя группами cabinet-shell/settings. PostgreSQL runner выбирается только при наличии календарной цели в исполняемом наборе; иначе остаются прежний Python pytest, проверка Node для ASSETS и прежнее окружение без БД/Docker. Независимый вызов реального select_tests это подтвердил. |
| CHK007: непригодный файл | Для всех новых целей применяется общий is_file/resolve/AST/test-name контроль до execute, включая covered. Новые случаи missing/empty/syntax/symlink требуют ненулевого результата и отказа до server_venv_missing. |
| CHK008: ошибка исполнения | Общий check_execution сохраняет отказ на skipped и отсутствие выбранного модуля в JUnit. Runner failure17 возвращается наружу; pytest failure1 и skip/deselect2 проверены направленными контрактами. PYTEST_ADDOPTS очищается, addopts переопределён пустым. Один JUnit передаётся существующему runner. |
| CHK009: неизвестные пути и diff | Изменённые пути сохраняются целиком; coverage остаётся partial. Git diff, обработка ошибок/базы и обоих концов rename не менялись. Новый реальный rename-тест сохраняет удалённый matching.py и неизвестное назначение; прежние контракты bad base/collection error продолжают проходить. |
| CHK010: PostgreSQL | Используется существующий run_local_postgres_tests.sh --focused без --partitioned. Он сохраняет изолированные временные БД, реальные миграции/RLS через штатные fixtures, снятие унаследованных DB/xdist параметров и cleanup. Новый отдельный runner или зависимость не созданы. |
| CHK011: действительное исполнение | Stub tests явно ограничены связыванием команд. Отдельные настоящие журналы содержат46PASS напрямую и46PASS через карту, одинаковый collection digest и cleanup обоих контейнеров. Через карту дополнительно пройден check_execution после runner. |
| CHK012–013: процесс и приёмка | Требования качества ранее независимо приняты15/15. В этой проверке нет commit/PR/merge/release и закрытий issues. Общие критерии T001–T008/T010–T011 не принимаются по T009. Exact-SHA GitHub checks и штатный closeout остаются обязательными после разрешённого коммита. |
| CHK014: данные и Dev | Diff не меняет Dev, production, данные встреч или секреты. Артефакты исполнения — временный JUnit и технические журналы. Незакоммиченная ссылка apps/server/.venv использует уже подготовленное окружение зависимостей; её нельзя включать в commit. |
| CHK015: остальные gates | Изменение ci-local добавляет только учёт уже исполненного полного integration-файла. Unit/component/static/governance/full/release этапы не удалены. Изменённые прежние assertions отражают перенос календарного файла в единственный behavior-этап и сохраняют fail-fast/единственное исполнение. |

## Прочитанные журналы автора

Каталог: `/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/checks/`.

- `f263-map-red.log`:7FAIL до изменения реализации; в каждом случае выбранный
  набор пуст вместо двух обязательных файлов.
- `f263-ci-contract.log`:120PASS, один PytestAssertRewriteWarning.
- `f263-ci-contract-added.log`:4PASS,120deselected; завершают расширенный набор124.
- `f263-calendar-real-direct.log`:46PASS за25.89s, collection_count46,
  режим focused/partitioned=false, cleanup=isolated_container_removed.
- `f263-calendar-real-map.log`:46PASS за27.67s; JSON выбора содержит оба файла,
  required proof выполнен, итог ci_focused_result=pass, контейнер удалён.
- Оба реальных запуска имеют collection digest
  `fbaca184e29077996ddbb4e3d854a020f5769cf128ff1d82bd9ba02046f9de4d`.

При итоговом перечитывании `f263-runner-contract.log` завершился:
**85PASS за102.82s**, один прежний PytestAssertRewriteWarning. Промежуточные
точки в дописывавшемся журнале ранее не принимались за успешный итог.

## Независимые проверки рецензента

Рецензент выполнил:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/server/src apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_ci_cd_contract.py -k 'calendar or shared_cabinet or local_plan_and_fast or focused_requires_executed_proof or git_collection_failure'
```

Результат: **35PASS,89deselected за15.01s**, один прежний
PytestAssertRewriteWarning. Выбор включает календарные/mixed/covered/rename,
ошибочные цели, stub executor, сохранение cabinet, прежний JUnit fail-closed
и ошибки получения Git diff.

Дополнительно:

- pytest collect-only:124tests collected;
- независимый вызов реального select_tests: cabinet-only не выбирает календарь
  и сообщает прежнее окружение без БД/Docker, matching.py выбирает обе цели;
- `bash -n infra/scripts/ci-local.sh`:PASS;
- `git diff --check`:PASS;
- повторная SHA256-проверка всех трёх просмотренных файлов: совпадение.

## Остаток до принятия

Нерешённых замечаний к коду: **0**. До итоговой локальной приёмки завершить
остальные объявленные проверки/converge. Далее нужны отдельное разрешение на
commit и PR, обязательные проверки на точном SHA/base и содержательная сверка
issue. Общая F263 остаётся открытой по остальным историям.
