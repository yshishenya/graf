# Независимое ревью требований F263 / US4, 2026-10-16

Результат: **PASS — 15 подтверждено, 0 не подтверждено**. Это проверка полноты,
ясности и согласованности требований до реализации T009/#6908. Реализация,
локальные проверки, принятие PR и закрытие issue этим результатом не подтверждаются.
US1–US3 и вся F263 остаются незавершёнными.

Рецензент: отдельный агент `/root/review_f263`. Основа
`aaa5e7a2b01205d4ab962c7fb126ef7e99dadf7d`, ветка `263-fast-feedback`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/fast-feedback-audit/crisp`.
Рецензент меняет только этот отчёт и `checklists/calendar-behavior.md`.

## Прочитанные источники

- Текущие spec, plan, tasks, research, quickstart, data-model и оба checklist F263.
- `AGENTS.md`, `.specify/memory/constitution.md`, индекс guidance,
  `spec-kit-flow.md`, `tracker-policy.md`, `github-issue-canon.md` и применимые
  разделы `release-and-validation.md` о целевых проверках, PR и доказательствах.
- Исходные сохранённые bodies #6901/#6908 из `/tmp/f263-live-inventory.json`.
- `scripts/ci-behavior-tests.py`, выбор и этапы `infra/scripts/ci-local.sh`,
  режимы, очистка и исполнение `apps/server/scripts/run_local_postgres_tests.sh`.
- Существующие `test_ci_cd_contract.py`, contract/integration календаря,
  включая обязательный тест `test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95`.
- Текущая `.specify/feature.json` и вывод `check-prerequisites.sh --json --paths-only`
  подтверждают именно `specs/263-fast-feedback/`.

## Проверка каждого пункта

| Пункт | Статус | Доказательство требований |
|---|---|---|
| CHK001 | PASS | Spec §«Происхождение и границы восстановления» и Research §«Резерв и утраченные материалы» прямо называют текст восстановленным из issues и запрещают придумывать исходные четыре node IDs/результаты. |
| CHK002 | PASS | Spec §Clarifications, Plan §Summary/Dependencies и Tasks отделяют независимую US4/T009 от открытых US1–US3 и T010/T011 всей фичи. |
| CHK003 | PASS | После замечания рецензента Plan §«Точное соответствие источников» содержит calendar prefix, matching.py, точные пути API/model/migration0021 и обе существующие цели. Сверено с файлами репозитория; сокращения больше не являются единственным определением карты. |
| CHK004 | PASS | Spec US4 scenarios1–2, Plan Phase1.2/4 и data-model задают объединение без повторов, непересечение tests/covered_tests, владение целыми файлами behavior-этапом и исключение их из changed-tests. Unit/component остаются. |
| CHK005 | PASS | Spec Independent Test/SC004 и Plan Phase1.3/4 требуют required performance и подавление отдельного повторного performance-этапа только при исполнении целого integration-файла. Существующий тест сохраняет порог p95≤50ms на100измерениях; режим report способен дать xfail, поэтому план явно требует required. |
| CHK006 | PASS | Spec US4 scenario5 и Plan Phase1.1/3/5 требуют прежний путь Python/Node для cabinet-only, исключают распространение cabinet shared на новую группу и отражают PostgreSQL/Docker только для календарной выборки. |
| CHK007 | PASS | Spec US4 scenario3, Plan Validation и Quickstart называют missing/empty/syntax/symlink с отказом до исполнения. Существующая проверка is_file/resolve/AST является исходным механизмом, который план предписывает сохранить для каждой новой цели. |
| CHK008 | PASS | Spec US4 scenario3, data-model и Quickstart требуют отказа на skip/deselect выбранного файла, ненулевом результате runner и отсутствии JUnit-доказательства. Plan сохраняет check_execution и сбрасывает PYTEST_ADDOPTS/addopts. |
| CHK009 | PASS | Spec FR014/scenario4, Plan Phase1.5/точное соответствие/Validation и Quickstart охватывают unknown/shared, оба конца rename, удаление источника, rename обязательной цели и недоступную/неверную базу. Карта явно partial; ошибки diff не дают полного покрытия. |
| CHK010 | PASS | Plan Storage/Dependencies/Phase1.3 предписывает существующий focused runner без partitioned, реальные миграции/RLS, один последовательный pytest и один JUnit, без новых зависимостей. Read-only сверка runner подтверждает уникальную временную БД, очистку унаследованных DB-настроек и trap cleanup контейнера; фактический запуск ещё требуется. |
| CHK011 | PASS | Quickstart прямо отделяет проверки связывания команд со stub от двух обязательных реальных шагов: оба календарных файла через штатный runner и затем focused через карту для matching.py. Контрактные проверки команды не принимаются за реальный PostgreSQL. |
| CHK012 | PASS | Spec FR015, Plan Dependencies, Tasks T009 и Quickstart сохраняют review→analyze→issue sync до кода; red→green, converge, отдельное разрешение commit, три проверки на точном PR SHA и checked base, отдельные merge/release. Этот отчёт не подменяет следующие этапы. |
| CHK013 | PASS | Tasks сохраняет T001–T011 и связи #6904–#6909 открытыми; #6901/T000 явно требует согласования до закрытия. Spec SC002/003 и Research не принимают похожие F21127/131-case результаты вместо исходных четырёх тестов, трёх повторов и workers1/2. |
| CHK014 | PASS | Plan Constraints не разрешает менять общий Dev; Spec ограничивает продукт/production и выпуск. Data-model запрещает секреты и данные встреч; Quickstart сохраняет текстовые итоги и убирает временный контейнер. Для этой части нужны только технические сведения о тестах. |
| CHK015 | PASS | Plan Constitution Check до/после проектирования, Spec FR014/Assumptions и Plan Phase1.4 сохраняют product, unit/changed/component/static и release gates. Нет нового сервиса, новых принципов или исключения для F259. Заявленный путь соответствует significant-feature/active slice с полным процессом. |

## Замечание и его исправление до PASS

Изначально Plan Phase1 использовал только сокращения «каталог/API/модель/миграция0021».
Рецензент сообщил автору пробел CHK003. Автор добавил точные source paths, обе
цели, поведение удаления/rename источника и требование обновить карту при rename
обязательного теста. Рецензент перечитал фактический изменённый plan и проверил
существование названных файлов. Других блокирующих пробелов требований US4 не найдено.

## Версии просмотренных материалов

SHA256 перед отметкой checklist:

```text
1ecbf3907771e9c2e3ea633199133a13a2004e94a68d544590dd0a8c007ef19d  spec.md
56e000d76a0f7f494d65150f79cc41a2e31a00338c8a26d31297451a4ee7fbba  plan.md
673beec191304e6578bacdf355926bab91df8a0d5fe88e30565c834f730852e1  tasks.md
6c4f795403a4f7fae16fd4d9604efd5b1fd2c9e1e37db331b2c30b3de79b3003  research.md
4e3d4b5ffe80d24171bd98a21cd26c4e12c067e7060a78a8ab51fd4c31f66d40  quickstart.md
3510bbc96d4ffe336a713588b10dbbd5fa207f862af43782b0fbb0fcbcd2e580  data-model.md
```

Следующие обязательные этапы: штатное оформление задач, analyze без нерешённых
CRITICAL/HIGH, сверка существующего #6908 без дубля, затем реализация и реальные
проверки из quickstart. Перед приёмкой кода отдельно проверить, что подавление
performance-этапа связано с обязательным успешным исполнением полного integration,
а cabinet-only не требует PostgreSQL/Docker. Не закрывать #6908 до содержательной
приёмки и обязательного exact-SHA PR gate; не закрывать #6901 по одной US4.
