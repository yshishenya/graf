# Качество требований T077: запросы удаления

Независимый допуск D1–D6/O14 до кода. High-risk-product,01.11.2026.
Отметки принадлежат reviewer, не implement. Качество требований, не приёмка кода.

- [x] CHK001 Однозначно ли определены источник, root/nested sources, inventory/current_state, независимость от дня и count строк? [D1]
- [x] CHK002 Однозначно ли определены четыре state/default/текущие writers, одна unknown/NULL и sorted groups/сумма? [D2; research]
- [x] CHK003 Однозначно ли определены предел active_purge_complete, backup/local/external/post-egress и retained observability? [D3; ConstitutionIV/PRD25]
- [x] CHK004 Однозначно ли определены null details/deadline/jobs/возраста/дат, без ложной приёмки SLA? [D3]
- [x] CHK005 Однозначно ли определены partial всегда, root/nested приоритеты и пустота против ошибки? [D4]
- [x] CHK006 Однозначно ли определены раздельные count fair-use/request, прежние pending buckets/reactionnull? [D4]
- [x] CHK007 Однозначно ли определены только SQLstate/count, запрет private fields/writers/egress, прежние guard/RLS/RR/лимиты/cleanup? [D5]
- [x] CHK008 Однозначно ли определены настоящие NOTNULL/FORCERLS и отличие модели/миграции, SQLVALUES для NULL без ослабления схемы? [D2/D6; model/research]
- [x] CHK009 Однозначно ли определены RED/PG/CLI/unknown/privacy/снимки/restart/no-write/schema/роли и affectedregressions? [D6; quickstart]
- [x] CHK010 Однозначно ли определены порядок до кода, независимостьreviewer, T077/#4932[ ]/87полныхстрок/58gaps/O6/T070/сроки/O8история без новойissue/task? [D6]

Итог независимой проверки требований:10 отмечены/0 не отмечены; PASS D1–D6.
Основания по каждому пункту и контрольные суммы:
[отчёт](../review-deletion-inventory-requirements-20261101.md).
Это допуск к реализации. T077/#4932, полный O6, T070,58 прежних незакрытых
пунктов, исходные сроки и исторический пробел O8 остаются открытыми.
Проверки кода, PostgreSQL/CLI и точного PR SHA/base ещё обязательны.
