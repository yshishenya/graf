# Scoped converge F140/T077 O13 — 01.11.2026

Область: Q1–Q6 сохраняемых наблюдений чеков. Новый срез сходится с требованиями;
полный FR089/O6 остаётся HIGH partial исходной T077/#4932 без новой задачи.
Prerequisites --json --require-tasks --include-tasks PASS; spec существует.
Before/after_converge hooks отсутствуют. tasks.md этим анализом не меняется.

| Требование | Фактическое покрытие |
| --- | --- |
| Q1 | _refund_inventory сохраняет refund count/groups и получает составной source; _receipt_inventory возвращает самостоятельный вложенный source, database_inventory/current_state без фильтров дня/status/shop/environment. |
| Q2 | Первая SQL считает все invoice и отдельно missing/invalid containers. root_object учитывает SQL NULL, json_typeof отличает JSON null/object/scalar/array. CASE даёт json_each только object map. Пустая map не missing; реальные NOT NULL не менялись. |
| Q3 | Вторая SQL раскрывает JSON entries; совместные type/value проверки трёх полей задают18сочетаний и одну unknown тройку. GROUP BY/ORDER BY и сумма counts; повторяющиеся JSON keys не объявлены уникальными чеками. UI projection не используется. |
| Q4 | Оба source partial. Возраст/эскалация/сверка null; nested unknown→invalid→missing→timing, root учитывает ещё unknown refund и завершает reconciliation_uninstrumented. Пустая БД нулевая; ошибка схемы даёт отказ всего CLI. |
| Q5 | Две invoice агрегации в прежнем collector, только закрытые поля/counts. JSON/key/IDs/времена/контакты/суммы/URL не выбираются в Python. Схема/права/RLS/CLI/guard/RR/as_of/лимиты/cleanup/финансовые writers не менялись. |
| Q6 | Независимые requirements10/0 и analyze предшествовали RED/коду. Реальные CLI/PG/FORCE RLS/NOT NULL/снимки/процесс/privacy/no-write/схема/роли подтверждены. Независимые code review и exact PR gates остаются отдельными обязательными воротами. |

Проверено6 требований,7 решений плана: существующий helper/collector;
две SQL без Python JSON; guarded JSON/types; закрытые совместные группы;
отдельные counts/null/partial; реальные constraints/CLI/снимки/приватность;
сохранение T077 и отдельной PR/выпускной границы.

Сохранены7 принципов: I/II capture/видимость/Stop не затронуты; III секреты/
egress/частные данные не добавлены; IV удаление не меняется и не принимается;
V macOS distribution не затронута; VI независимые процесс/проверки обязательны;
VII UI/сторонние материалы не меняются. Legacy Impact untouched.

Новых missing/partial/contradicts/unrequested и CRITICAL/HIGH/MEDIUM/LOW=0
в Q1–Q6. Полный O6 HIGH partial сохраняется в прежней T077, без дубликата.
Все87 полных task lines/T077[ ] и58 старых gaps прежние; исторический пропуск
чтения до первоначального PR7884 кода не исправлен, весь O8 не PASS.
16 уникальных окончательных PASS:8новых+8затронутых, без суммирования прежних
наборов. Независимая сверка converge — отдельная часть кодового отчёта reviewer.

Следующие ворота: независимый code review, три GitHub checks и общий validator
точных source/base, защищённый merge, validator после merge и один status4932.
Только Refs #4932; closure/Full/CD/выпуск/Dev не входят.
