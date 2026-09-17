# A4 delivery optimization requirements review

Created: 2026-09-13. Owner: independent requirements reviewer. Implementation reads this gate and must not mark items complete. Scope: FR-031–FR-033, SC-016–SC-017, T048–T052.

- [x] CHK001 Are the exact current scope and boundaries with remaining program work unambiguous?
- [x] CHK002 Are unchanged full-test scope, command ordering and static-failure consequences specified?
- [x] CHK003 Is deduplication restricted to complete proof within one invocation, with a sole mandatory owner and preserved other tests?
- [x] CHK004 Are server-only and mixed infra changes, missing/failed proof and absence of old-result reuse covered?
- [x] CHK005 Do CD diagnostic requirements preserve candidate validation, incident boundaries and every production gate?
- [x] CHK006 Are success criteria executable and free of unmeasured speed claims?
- [x] CHK007 Are tasks, source paths and validation commands traceable without new runtime dependencies?
- [x] CHK008 Are current user authority, publication stages and historical statements clearly separated?

## Независимая проверка требований — 2026-09-13

Рецензент: `fixture_research`, отдельно от исполнителя A4. Проверены актуальные
`spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, конституция 7.0.0 и существующие
места исполнения в `release-full.yml`, `ci-local.sh`, `cd-remote.sh`,
`test_ci_cd_contract.py`, `test_ci_guard.py`. Это проверка качества требований:
тесты, Docker, CI и production не запускались; выполнение T048–T052 не отмечено.

Подтверждения принятых пунктов:

- CHK001/CHK008: уточнения A4 в `spec.md` и Phase 13 в `tasks.md` явно ограничивают
  первый объём E05.12/E05.16 и диагностикой CD. Завершение T052 не означает
  завершения всей программы; история A1–A3 отделена от текущего поручения и
  следующих состояний PR/релиза.
- CHK002: FR-031 и SC-016 сохраняют полный состав, требуют прежние lint/compile
  один раз до любого server pytest и запрещают PASS после статического отказа.
  A4 `plan.md`, пункт 1, уточняет и governance pytest, и начало PostgreSQL,
  сохранение остальных команд и терминального результата.
- CHK003: уточнение A4 о пределах одного запуска и FR-032 требуют полного
  покрытия того же файла; A4 `plan.md`, пункт 2, назначает существующий этап
  `CI contracts` единственным исполнителем обоих файлов при infra diff и
  сохраняет остальные выбранные тесты. Кэш старых SHA/base/attempt не вводится.
- CHK005: FR-033, действующие FR-005–FR-008 и A4 `plan.md`, пункт 3, сохраняют
  валидацию candidate/evidence, отдельный incident bypass и production gates.
  Требуется исправление текста dry-run, без изменения договора execute.
- CHK006: SC-016/SC-017 проверяются исполняемыми shell-сценариями и счётчиками
  вызовов; A4 `plan.md`, пункт 5, прямо исключает заявление об ускорении
  33-минутной успешной PostgreSQL-фазы без измерения.

Замечания первого прохода (CRITICAL 0, HIGH 0, MEDIUM 2; закрытие записано ниже):

1. **A4-R01 / CHK004 — дополнить отрицательную матрицу.** FR-032 описывает
   server-only diff, а уточнения A4 требуют остановки после отказа единственного
   исполнения. Однако SC-017/T048 явно называют лишь смешанный diff и успешное
   выполнение. Добавить текущие критерии/задачу проверки отдельного server-only
   diff, отсутствующего обязательного файла и отказа единственного этапа
   `CI contracts`: результат неуспешен, зависимые действия не начинаются,
   второе исполнение не используется как повторная попытка. Существующий
   `run_stubbed_ci` может подтвердить порядок/отказ; потерю файла проверять
   исполняемым сценарием. Новый общий механизм доказательств не требуется.
2. **A4-R02 / CHK007 — завершить текущую инструкцию проверки.** T052 называет
   Ruff и governance, но секция A4 в `quickstart.md` содержит только два
   CI-контракта, validator/self-test, Bash и actionlint. Добавить точные текущие
   команды Ruff и governance, включая
   `tests/governance/test_ci_guard.py::test_cd_exposes_reuse_contract_for_authoritative_full_evidence`,
   а также команды требуемых Spec Kit/process checks. Историческая команда A3
   не должна быть единственной ссылкой на приёмку SC-017. Новые зависимости
   для этого не нужны.

Итог первого прохода: 6/8 пунктов подтверждены; CHK004 и CHK007 оставались
открытыми до проверки уточнений.

### Повторная проверка — 2026-09-13

- **A4-R01 закрыто / CHK004 PASS.** Обновлённые SC-017 и T048 явно включают
  отдельный server-only diff, отсутствие обязательного файла и отказ
  единственного infra-stage. Сохраняющееся уточнение A4 требует остановки
  зависимых действий после отказа и запрещает зачёт результатов других
  SHA/base/attempt. Матрица теперь покрывает обнаруженный пробел.
- **A4-R02 закрыто / CHK007 PASS.** Текущая секция A4 `quickstart.md` теперь
  содержит команды Ruff, полного `tests/governance/test_ci_guard.py` (включая
  названный reuse-контракт) и `scripts/check_spec_kit_governance.py`. Они
  дополняют два CI-контракта, validator/self-test, Bash и actionlint; пути
  существуют, новые зависимости не добавляются. Вызовы `doctor` и
  development-process из ранее записанного окружения можно уточнить при
  фиксации фактической среды T052; это не меняет проверенный договор A4.

Итог независимой проверки требований: **PASS, 8/8; CRITICAL 0, HIGH 0,
MEDIUM 0**. Статус относится только к требованиям FR-031–FR-033,
SC-016–SC-017 и плану T048–T052. Реализация, результаты проверок, analyze,
issue sync, PR и release acceptance подтверждаются своими последующими
записями; этим review они не объявлены выполненными.
