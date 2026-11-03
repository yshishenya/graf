# Scoped converge F140/T077 O14 — 01.11.2026

Проверены D1–D6, семь решений plan (reuse/одна агрегация/закрытые группы/
раздельные сущности/мигрированная fixture/профиль/порядок) и семь принципов
конституции. Scope — только O14, не полный FR089/O6. Hooks converge отсутствуют.

| Требование | Реализация и проверка | Исход |
| --- | --- | --- |
| D1 | _deletion_inventory читает все видимые state/count без WHERE; root/nested sources; PG разные report_date/снимки/restart. | PASS |
| D2 | Четыре DELETION_STATES, _closed/CASE, sorted groups/count; PG восемь реальных состояний, NULL/unknown SQL VALUES отдельно, NOT NULL/defaultrequested/FORCE RLS сохранены. | PASS |
| D3 | Только count/groups, пять полей деталей/срока/jobs null; docstring/fragment ограничивают смысл active_purge_complete, retained observability сохранена. | PASS |
| D4 | Nested и root partial даже при пустоте; unknown любого источника выше invalid_schedule, затем новая неполнота деталей/реакции; отдельные count/reactionnull. PG schema failure отвергает весь CLI. | PASS |
| D5 | Один helper/одна SQL aggregation; прежние guard/RLS/RR/as_of/cleanup/лимиты, нет дат/private fields/writers/egress/миграций/прав/зависимостей. PG fingerprint/privacy/роль/READ ONLY до hook. | PASS |
| D6 | Независимые требования10/0 и analyze/issue sync до RED;15 уникальных финальных PASS (6new+9affected),0FAIL/ERROR/SKIP; code review и exact PR gates далее обязательны. | PASS локального порядка; внешние ворота далее |

Новых missing/partial/contradicts/unrequested findings в O14:0; новых
CRITICAL/HIGH/MEDIUM/LOW0. Tasks.md после проверки не меняется:87 исходных
полных строк прежние. Оставшийся HIGH partial полного FR089/O6 уже находится
в исходной T077: источники/storage/add-on/финансовая сверка, постоянные
attempts/errors/retries, регулярность/heartbeat, alerts/retry и сохраняемая
реакция с реальными owner/severity/evidence/сроками/разрешением. Дублирующую
задачу не добавлять. T077/#4932 и отдельная T070 остаются открытыми;58 старых
gaps/исходные сроки/исторический O8 пропуск не приняты.

Дальше независимая сверка кода и этого converge, затем обязательные exact
SHA/base governance-fast/macos-pr/pr-metadata и общий валидатор. Это не
полная приёмка F140, выпуск, финансовая или ручная приёмка.
