# A5 resource optimization requirements review

Owner: independent reviewer. Implementation must not check items. Scope FR-034–037, SC-018, T053–T057.

- [x] CHK001 Are pure/DB boundaries and fail-closed missing resource outcomes complete?
- [x] CHK002 Are unchanged Full scope, union/disjointness and worker isolation explicit?
- [x] CHK003 Are fixture changes limited by reviewed callers and preservation of negative behavior?
- [x] CHK004 Are environment/report provenance and collection-not-PASS clear?
- [x] CHK005 Are executable verification and before/after measurement feasible with existing tools?

## Независимая проверка требований — 2026-09-13

Рецензент: `fixture_research`, отдельно от исполнителя A5. Проверены FR-034–037,
SC-018, A5 `plan.md`, T053–T057, текущие `conftest.py`, PostgreSQL runner,
`fixtures/cabinet.py`, оба выбранных семейства, `test_meeting_progress_ui.py`,
`tests/browser/playback-refresh.test.cjs`, hosted workflows и поведение
установленного pytest JUnit writer. Код и другие артефакты не менялись;
тесты, браузер, Docker и CI не запускались.

- **CHK002 PASS.** FR-034/035/037 и A5 plan требуют сохранения полного набора,
  union/disjointness и прежних worker databases. Full сохраняет отдельные
  ordinary/performance/strict фазы; ограничение четырёх процессов относится
  к новой DB-unit части. Существующие миграции и advisory lock не заменяются.
- **CHK003 PASS.** FR-036/T055 ограничивают первый объём artifact-egress и
  speaker-names. В прочитанном коде их операции используют ready; остальные
  состояния не являются основанием этих проверок. Общий пятисоставный helper
  сохраняет прежнее поведение, косвенные callers и отрицательные
  multi-state/foreign/list/count сценарии исключены из автоматической замены.

Открытые замечания:

1. **A5-R01 / HIGH / CHK001 — браузер теряется внутри определения pure.**
   A5 plan выбирает pure через `-m 'not postgres'`. Но
   `tests/unit/test_meeting_progress_ui.py::test_first_transcript_refresh_keeps_live_audio_and_comment_draft`
   не использует DB fixtures и пропускается при отсутствии `GRAF_NODE_MODULES`.
   `tests/browser/playback-refresh.test.cjs` требует пакет Playwright и
   запускает Chromium; WebKit выбирается только через `GRAF_BROWSER=webkit`.
   Установка Node из T056 не устраняет этот skip. Требуется определить явный
   browser resource и единственное обязательное место выполнения с пакетом и
   браузерным бинарником, результат при отсутствии ресурса и учёт этого case в
   union/disjointness. Это браузерный сценарий, а не проверка нативного GRAF.
   Новый отдельный GitHub job не обязателен: подготовленная стадия
   существующего job достаточна. Тихое исключение case или зачёт его skip как
   успешной pure-проверки противоречат FR-035.
2. **A5-R02 / MEDIUM / CHK004 — формат отчёта не выполняет заявленный договор.**
   FR-037 требует отдельные setup/call/teardown; plan предлагает уникальный
   JUnit каждой фазы и публикацию только метаданных. Стандартный pytest JUnit
   суммирует duration в одном testcase time и записывает `longrepr` в
   failure/error даже при `junit_logging=no`. Сырые ошибки могут содержать SQL
   и параметры, а отдельные времена этапов теряются. Уточнить минимальную
   безопасную проекцию (node ID, phase/when, outcome, duration, связь SHA/run)
   и способ её получения; не публиковать raw longrepr/параметры. Малый pytest
   hook или очищенная проекция стандартных отчётов достаточны, отдельная
   система наблюдения не нужна. Сохранить вывод collection-only как
   инвентаризацию, без PASS выполнения.
3. **A5-R03 / MEDIUM / CHK005 — нет текущего рецепта приёмки A5.**
   SC-018 и T057 требуют чистый запуск без Docker, проверку DB-boundary,
   real collection union/disjointness и сопоставимое измерение двух
   семейств, но в `quickstart.md` пока есть только A4/A3 и исторические
   команды. До реализации зафиксировать команды и ожидаемые исходы A5,
   включая неизвестный CLI argument/конфликт режимов без запуска Docker,
   pure/DB/browser состав и одинаковую Python/lock/worker среду до/после
   fixture change. Старое измерение Python 3.14 нельзя напрямую сравнивать с
   новым Python 3.13 и относить разницу к фикстуре.

Итог первого прохода: **2/5 PASS; CRITICAL 0, HIGH 1, MEDIUM 2**.
Открытые пункты требуют уточнения требований/приёмки, не разрешают ослабить
браузерный или PostgreSQL барьер. Реализация и результаты тестов этим review
не подтверждены.

## Повторная независимая проверка — 2026-09-13

Проверены текущие FR-034–037/SC-018 (`spec.md:254–262`), A5 plan
(`plan.md:201–209`), T053–T057 (`tasks.md:143–151`) и новый рецепт
(`quickstart.md:274–290`). Lane: проверка требований существующего high-risk
Spec Kit slice; единственная правка — этот checklist. Исходный HEAD:
`9cf6e1bd74e4b02d6fa46ca82f44868d0efef3e9`, документы имеют незакоммиченные
изменения. Тесты, Docker, сеть, коммиты и действия с issues не выполнялись.

- **A5-R01 CLOSED / CHK001 PASS.** FR-035 и plan §1 явно исключают browser
  из pure и включают в обязательную resource-часть через взаимодополняющие
  выражения маркеров. Все три прежних skip охвачены; закреплённые
  Playwright/Chromium готовятся в обоих hosted jobs, отсутствие среды —
  ошибка. T056 и quickstart содержат подготовку браузера. Требования
  сохранения состава, worker isolation и отрицательных сценариев по-прежнему
  согласованы: **CHK002/CHK003 PASS сохранены**.
- **A5-R02 PARTIAL / MEDIUM / CHK004 остаётся открытым.** FR-037 и plan §4
  закрывают проблему JUnit: разрешённая проекция JSONL, отдельные when/duration,
  единственная запись контроллером, запрет longrepr/output/SQL. Plan §2
  сохраняет collection-only как инвентаризацию. Осталась ранее запрошенная
  связь отчёта с SHA/run: «отдельный файл для запуска/фазы» не определяет,
  как установить SHA исходников, run ID/attempt и фазу у опубликованного
  файла. Достаточно явно связать имя/каталог артефакта или безопасный manifest
  с существующим Full evidence; добавлять эти поля в каждую строку не нужно.
- **A5-R03 PARTIAL / MEDIUM / CHK005 остаётся открытым.** Новый quickstart
  задаёт одинаковые Python 3.13.3, lock, extras, worker/PostgreSQL и команду
  двух семейств; сравнение с Python 3.14 больше не предлагается. Есть команды
  collection, pure, browser preparation, fast и целевых контрактов. Однако
  ранее запрошенные неизвестный CLI argument и конфликт режимов не заданы
  конкретными сценариями: в рецепте нет вызовов help/invalid/conflict, а
  T053 не выделяет конфликт режимов. Добавить в рецепт или явную матрицу
  T053 случаи `--help`, неизвестный аргумент (например
  `--focused --a5-invalid-option`) и `--fast --full`, ожидаемые exit outcomes
  и проверку нуля вызовов Docker через перехват вызова команды. Ссылка на
  общий запуск contract-файлов без этих сценариев не закрывает этот остаток.

Итог повторной проверки: **3/5 PASS; CRITICAL 0, HIGH 0, MEDIUM 2**.
Gate требований A5 пока **не пройден**: остатки R02/R03 выше требуют
документального уточнения. Числа baseline прочитаны как запись автора;
реализация и результаты выполнения этой проверкой не подтверждены.

## Финальная независимая перепроверка R02/R03 — 2026-09-13

Область: только два оставшихся MEDIUM замечания по окончательным абзацам A5
в `spec.md:258–262`, `plan.md:205–211` и `quickstart.md:276–292`.
Lane: документальная проверка требований существующего Spec Kit slice;
единственная правка — этот reviewer-owned checklist. История предыдущих
проверок и результаты CHK001–CHK003 сохранены без повторной оценки.

- **A5-R02 CLOSED / CHK004 PASS.** FR-037 прямо связывает точный requested
  SHA, run_id, run_attempt и фазу с опубликованным отчётом. Финальный абзац
  plan и quickstart задают одно имя артефакта
  `graf-test-timings-<requested_sha>-<run_id>-<run_attempt>` и уникальные
  `<phase>.jsonl`, связанные с существующим authoritative Full evidence.
  Это закрывает остаток о происхождении отчёта; безопасная проекция,
  отдельные setup/call/teardown и запрет публикации payload сохранены.
  Collection остаётся инвентаризацией, отчёты не дают самостоятельный PASS.
- **A5-R03 CLOSED / CHK005 PASS.** Финальный абзац quickstart явно задаёт
  матрицу T053: `--help` → 0; `--focused --a5-invalid-option` → ненулевой
  код ошибки аргумента; `--fast --full` → ненулевой код конфликта режимов;
  `--focused --collect-only -q tests/unit` → 0. Для каждого случая требуется
  пустой журнал вызовов Docker через временную PATH-заглушку. Тем самым
  закрыт остаток о конкретных сценариях и доказательстве нуля вызовов;
  ранее принятые одинаковая среда и команда измерений до/после сохранены.

Итог по checklist с учётом сохранённых результатов: **5/5 PASS;
CRITICAL 0, HIGH 0, MEDIUM 0**. Gate требований A5 **пройден**.
Код, тесты, Docker и сеть не использовались; другие файлы не изменялись,
агенты не привлекались. Реализация, числа baseline и результаты выполнения
этой документальной перепроверкой не подтверждены.
