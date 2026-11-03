# Scoped analyze F140/T077 O13 — 01.11.2026

Полоса: active Spec Kit slice/high-risk-product. Только Q1–Q6 наблюдений
чеков в исходной T077/#4932. Это анализ требований до кода, не приёмка O6.
Prerequisites `--json --require-tasks --include-tasks` PASS; spec существует.
`--require-spec` локальным скриптом не поддерживается и не использован.
Before/after_analyze hooks отключены; внешних изменений анализ не делал.

| Требование | Покрывающая задача | Согласованные документы/проверки |
| --- | --- | --- |
| Q1 | T077 | spec O13/plan: составной root source, самостоятельный nested receipts, inventory/current_state, count возвратов отдельно. |
| Q2 | T077 | contract/model/research/quickstart2: invoice/missing/invalid/empty map; CASE до json_each, сохранённый NOT NULL. |
| Q3 | T077 | contract/quickstart2–3:18 совместных групп и одна unknown, сортировка/сумма, map entries без обещания уникальности или UI fallback. |
| Q4 | T077 | spec/quickstart1,3: оба partial, null возраста/эскалации/сверки, reason priorities, пустота/безопасный отказ, исходные сроки. |
| Q5 | T077 | plan/quickstart4: две SQL-агрегации, закрытые поля/counts, прежний guard/RR/as_of/лимиты/cleanup; без writers/egress/схемы/прав. |
| Q6 | T077 | tasks/quickstart5: независимый допуск до кода, RED, настоящий PG/CLI/FORCE RLS/снимки/процесс/privacy/no-write, review/converge/exact PR gates. |

Метрики:6 требований,1 существующая задача,100% покрытия; новых
CRITICAL/HIGH/MEDIUM/LOW, неоднозначностей и дублирования0; несвязанных задач0
в объявленной области. Конституционные I–VII сохранены: capture/видимость,
секреты/приватность/egress, удаление, macOS distribution и UI не меняются;
независимые требования/проверки обязательны. Legacy Impact untouched.

Полный FR089/O6 остаётся HIGH partial в той же T077: другие источники,
постоянные метрики/heartbeat/тревоги/retry/сохраняемая реакция ещё открыты.
58 старых checklist gaps не приняты; исторический пропуск чтения до
первоначального PR7884 кода не исправлен, весь O8 не PASS. Все87 исходных
полных task lines/T077[ ] сохранены; новая task/issue не создаётся.

Issue sync после анализа: обязательные canon ensure/validate выполнены;
243 Spec Kit issues проверены. Точный поиск канонического T077 владельца
нашёл одну #4932 OPEN, исходный body перечитан. Это переиспользование
существующей задачи, без нового комментария/закрытия/дубликата.

Следующий шаг: независимый PASS checklist receipt-inventory; затем RED и
минимальная реализация Q1–Q6. До reviewer-owned допуска код не меняется.
