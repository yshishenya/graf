# Качество требований T077: наблюдения чеков

Независимый допуск Q1–Q6/O13 до нового кода. High-risk-product.
Отметки принадлежат reviewer; это не доказательство реализации/всегоO6.

## Полнота, ясность и измеримость

- [x] CHK001 Ясны ли существующий map source, nested receipts, composite root source, inventory/current_state и отсутствие новых сущностей? [Q1]
- [x] CHK002 Разделены ли invoice_count, missing map/JSON null, invalid root/map, empty object и count entries без ложного нуля? [Q2]
- [x] CHK003 Полны ли18совместных групп и одна unknown для NULL/nonstring/malformed entry, сортировка/сумма и отсутствие уникальности/сверки? [Q3]
- [x] CHK004 Ясны ли top-level payment projection против map, отсутствие shop proof/immutable проверки и фильтров по дню/status/environment? [Q1/Q3]
- [x] CHK005 Определены ли отсутствие pending_since/возраста, прежние null/partial, обоих уровней reason priority, пустота и schema failure? [Q4]

## Безопасность, зависимости и приёмка

- [x] CHK006 Определён ли защищённый CASE до json_each, SQL JSON без миграции/загрузки JSON в Python, сохранённые constraints/forced RLS? [Q2/Q5]
- [x] CHK007 Ясны ли разрешённые JSON поля и запрет key/ID/shop/времён/контактов/сумм/URL/egress/writers, прежние guard/RR/as_of/cleanup/лимиты? [Q5]
- [x] CHK008 Покрывает ли quickstart RED/реальный CLI/PG, все18сочетаний/malformed/приоритеты, два снимка/новый процесс/privacy/no-write/схему/роли и минимальный affected набор? [Q6]
- [x] CHK009 Согласованы ли spec/plan/tasks/research/model, сохраняющий путь16entries, receipt canceled/pending сроки и O6/financial/privacy границы? [Q1–Q6]
- [x] CHK010 Сохранены ли порядок до кода, независимый допуск/analyze, T077[ ]/#4932OPEN/87tasklines/58gaps/исторический O8, отсутствие новой задачи/issue/релиза? [Q6]

## Решение reviewer

PASS только по качеству требований O13/Q1–Q6: 10 отмечены / 0 открыты.
Независимый reviewer: /root/f140_notification_content_review, диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594; base a139c07581668adb269bb7960ad8b15c87668233.
Основания по каждому пункту, полные чтения текущих семи оригиналов и
проверенные сохраняющие пути — в
[отчёте](../review-receipt-inventory-requirements-20261101.md).
Это не приёмка реализации/доставки/финансов/всегоO6; T077[ ]/#4932OPEN,
58прежнихgaps и исторический пропуск O8 остаются. Основной исполнитель
отметки не ставит.
