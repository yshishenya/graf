# Scoped converge F140/T077 O12 — 01.11.2026

Результат: новый обзор F1–F6 сходится с требованиями; полный FR089/O6 остаётся
HIGH partial исходной T077/#4932. Новая задача не создаётся.
Prerequisites --json --require-tasks --include-tasks PASS; spec существует.
Before/after_converge hooks отсутствуют. tasks.md этим анализом не меняется.

| Требование | Фактическое покрытие |
| --- | --- |
| F1 | collect_billing_report подключает _fair_use_inventory; одна агрегация FairUseReviewRecord, inventory/current_state без report_date. |
| F2 | _closed закрывает пять state/NULL/unknown; SQL GROUP BY/ORDER BY, сумма строк. confirmed исключён из pending, не объявлен cleared. |
| F3 | CASE сначала NULL/isfinite, затем порядок/numeric epoch>86400. Внешний CASE даёт invalid→future→deadline→waiting; FILTER только notice/restricted/appealed. Четыре количества исчерпывают pending. |
| F4 | Всегда partial, deletion/reaction null. Unrecognized приоритетнее invalid; пустота нулевая, schema error не подменяется пустотой. Даты и возраст не выводятся, SLA/решение не выводятся из счётчика. |
| F5 | SELECT только state/две даты внутри выражений/count; прежние CLI/guard/READ ONLY RR/as_of/лимиты/cleanup. Модели/миграции/деньги/права/egress неизменны. |
| F6 | Независимые requirements10/0 и analyze до RED/кода. Реальные CLI/PG/constraints/FORCE RLS/приватность/снимки/новый процесс; независимые review и exact PR gates обязательны. |

7 решений плана подтверждены: существующий collector/одна агрегация;
без generic future-invalid возраста; защищённый CASE/numeric elapsed;
без новых сущностей/миграций/зависимостей; реальные constraints/forced RLS;
профильные unit/PG и отдельный synthetic VALUES без ослабления схемы;
сохранение исходной задачи и отдельной PR/выпускной границы.

7 принципов конституции сохранены: I/II capture/видимость/Stop не затронуты;
III секреты/egress/content не добавлены; IV удаление не меняется и не принимается;
V распространение macOS не затронуто; VI независимый процесс/проверки обязательны;
VII UI/сторонние материалы не меняются. Legacy Impact нового среза untouched.

Проверено6 требований/7 решений/7 принципов; новых missing/partial/
contradicts/unrequested и CRITICAL/HIGH/MEDIUM/LOW=0. Полный O6 — отдельная
существующая HIGH partial, не скрыт и не размножен в дублирующую задачу.
Все87 полных исходных task lines и T077[ ] сохранены; 58 старых gaps не приняты.
Исторический пропуск чтения до первоначального PR7884 кода остаётся, весь O8
не PASS. Независимая сверка этого converge записывается reviewer в отдельном
кодово́м отчёте. Проверки10 уникальных PASS (3unit/4новыхPG/3затронутыхпрежнихPG)
сохранены в fair-use-implementation-validation; повторы не суммируются.

Следующие ворота: независимый code review, три GitHub checks и common validator
точных source/base, защищённый merge, validator после merge и один статус4932.
Только Refs #4932; закрытие issue, Full/CD/выпуск/Dev не входят в этот срез.
