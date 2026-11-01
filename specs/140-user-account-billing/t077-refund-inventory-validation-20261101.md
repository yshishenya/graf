# T077: проверка наблюдений возвратов — 01.11.2026

Полоса active Spec Kit slice/high-risk-product, owner repository-audit.
Только O11/R1–R6 внутри исходной T077/#4932; Legacy Impact untouched.
Все87исходных полных task lines сохранены, T077[ ], issue OPEN.

## Последовательность до кода

Семь текущих оригиналов полностью прочитаны собственными неусечёнными
выводами /root в том же диалоге, байты и происхождение проверены; прежние
16неизменных входов сверены с фактическими исходными выводами. Применимые
целые оригиналы/зависимости самостоятельно восстановлены, карта во внешних
материалах. Исторический пропуск до первоначального PR7884 кода сохранён;
весь O8 не PASS. Независимый [допуск требований](review-refund-inventory-requirements-20261101.md)
10/0, seven inputs совпали; [scoped analyze](analyze-refund-inventory-20261101.md)
6req/1task/100%/0новыхfindings. Canon ensure/validate243 PASS, единственная
существующая #4932 OPEN. Новые задачи/issues не создавались.

## Реализация и проверки

Одна _refund_inventory/SQL aggregation в существующем monitoring.py:
совместная succeeded/provider_observation и одна безопасная unrecognized,
count строк, без observed_at/age/day/env фильтра. database_inventory/current_state,
всегда partial, receipts/reconciliation_gaps=null. Модель/DDL/financial
writers/CLI/guard/RLS/снимок/cleanup/остальные семейства не менялись.
Существующий TABLES дополнен refund для forced RLS/fingerprint.

Owned apps/server/.venv, PYTHONPATH=src:. и подтверждённый __file__.
Штатная pytest fixture postgres_isolated_cluster_database_url создаёт свой
одноразовый migrated PostgreSQL и удаляет его через finally. Dev/рабочие
данные/внешние provider/почта не использованы.

| Выбор | Последний результат | Что доказывает |
| --- | --- | --- |
| unit -k refund_inventory | 3PASS/0FAIL/ERROR/SKIP | Пустота/причины/null, точная закрытая SQL-проекция без частных столбцов. |
| integration -k refund_inventory | 3новыхPASS | Несколько строк одного invoice, совместные пары, environments/NULL/future observed_at без фильтра/возраста, новый процесс/разные дни, RR старый/новый snapshot, no-write/privacy/ошибка схемы, реальная NOT NULL. |
| integration identity/SET ROLE/empty_then_populated | 3затронутых прежнихPASS | Реальный CLI/maintenance/RLS, отказ неверных login/SET ROLE/context, READONLYRR до hook, запрещённая mutation. |

Итого9уникальных последних PASS:6новых+3повтора, не складывать с прежними
наборами PR7884/7887/7890. PG36.07с,2прежнихwarning,0SAWarning.
После первого прогона уточнены только синтетические суммы нового pairs_time_privacy:
каждая частичная строка98765432, все6меньше invoice987654321. Изменённый
единственный случай повторён: final1 1PASS/0FAIL/ERROR/SKIP,6.97с.
Он заменяет прежний результат того же случая; итог остаётся9уникальных,
код продукта прежний, остальные8не повторялись.
Собственные одноразовые containers удалены fixture finally; чужой старый
контейнер от31.10сохранён. RED3ImportError/REDPG1sourceNone — история.
XML/log/hashes/11frozen inputs: внешний
f140-t077-refund-implementation-validation-20261101.json.
Ruff/process/governance/context/fragments/diff PASS.

## Scoped converge

R1–R6 проверены против текущего кода и сценариев:6требований,7решений
плана (existing collector/oneSQL/CASE/no time/private/schema/validation),
7конституционных принципов; новых missing/partial/contradicts/unrequested0.
Исходный O6/FR089 HIGH partial остаётся в существующей T077, новая задача
не дублируется. tasks.md не изменён converge. Hooks implement/converge
не исполняются: after_implement disabled, converge hooks отсутствуют.
Независимые [code review и отдельная scoped converge-сверка](review-refund-inventory-code-20261101.md)
APPROVE R1–R6/0новыхfindings:11/11frozen inputs и10XML/log hashes совпали;
reviewer самостоятельно пересчитал9уникальныхPASS. Фактический отчёт полностью
прочитан основным агентом, SHA256 a6c95017f267d1b4d1c3047dcd27834d605d530c830fe5c8ff7954489190e9ef.
Новые exact-SHA/base PR gates ещё обязательны.

## Открытый остаток

Чеки/финансовая сверка, остальные источники, постоянные counters попыток/
ошибок/повторов, регулярность/heartbeat, тревоги/retry и сохраняемая реакция
O6 с реальными owner/severity/evidence/сроком/разрешением открыты. Исходные
сроки и отдельная ручная/финансовая/приватностная/выпускная приёмки сохранены.
F272/F199 stop/runtime gates и отказ оплаченного срока F278FR041 не возвращены.
Только Refs #4932; эти9PASS не дают [X], closure, release или production PASS.
