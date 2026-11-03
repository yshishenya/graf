# T077: проверка сроков fair-use — 01.11.2026

Полоса active Spec Kit slice/high-risk-product, owner repository-audit.
Только O12/F1–F6 исходной T077/#4932; Legacy Impact untouched.
Все87 исходных полных task lines сохранены, T077[ ], issue OPEN.

## Последовательность до кода

Семь текущих оригиналов полностью прочитаны собственными неусечёнными
выводами /root в том же диалоге. Происхождение,23 текущих hashes и51 точный
диапазон исходных выводов проверены по фактическому журналу. После сжатия
применимые целые оригиналы и зависимости восстановлены до зависящей работы;
карта и подтверждения во внешних материалах. Исторический пропуск до
первоначального PR7884 кода сохранён; весь O8 не PASS.
Независимый [допуск требований](review-fair-use-inventory-requirements-20261101.md)
10/0; [scoped analyze](analyze-fair-use-inventory-20261101.md)
6req/1task/100%/0 новых findings. Canon ensure/validate243 PASS,
единственная существующая #4932 OPEN. Новые задачи/issues не создавались.

## Реализация и проверки

Один _fair_use_inventory/SQL aggregation в существующем monitoring.py:
пять состояний и одна unrecognized, count строк database_inventory/current_state
независимо от дня. Pending notice/restricted/appealed разделены на четыре
непересекающиеся группы invalid/not_started/deadline_reached/waiting.
Вложенный CASE проверяет NULL/isfinite до арифметики numeric epoch86400.
Будущее и нулевой срок допустимы; confirmed может сохранять ограничение.
Даты/возраст/частные поля не выводятся. Всегда partial, deletion/reaction=null;
достигнутый срок не доказывает глобальное нарушение SLA или закрытие incident.
Модель/миграции/финансовые writers/CLI/guard/READ ONLY RR/cleanup/права
и остальные семейства не менялись. Fragment сохраняет невыпущенные O10/O11.

Owned apps/server/.venv, PYTHONPATH=src:. и подтверждённый __file__.
Штатная postgres_isolated_cluster_database_url создаёт отдельную migrated
PostgreSQL и удаляет её через finally; рабочие данные/Dev не использованы.

| Выбор | Окончательный результат | Доказательство |
| --- | --- | --- |
| unit -k fair_use_inventory | 3PASS/0FAIL/ERROR/SKIP,0.03с | Пустота/группы/причины/null, одна SQL и разрешённые столбцы. |
| integration -k fair_use_inventory | 4 новых PASS | Реальные CLI/constraints/FORCE RLS, ±1мкс/равенства/zero/24ч/infinity/DST, malformed VALUES отдельно, privacy/no-write/схема, два снимка/новый процесс. |
| integration identity/SET ROLE/empty_then_populated | 3 затронутых прежних PASS | Maintenance/READ ONLY до hook, отказ подмены ролей/context/mutation, прежний JSON/no-write. |

Итого10 уникальных окончательных PASS:3unit+4новыхPG+3повтора;
0FAIL/ERROR/SKIP. Финальный PG7:35.05с,2прежнихwarning,0SAWarning.
Первоначальные RED3ImportError/REDPG1sourceNone сохранены.
Первый PG7 дал5FAIL/2PASS: fixture не давала SELECT workspaces для
существующего fair-use owner_scope RLS subquery. Исправлена только fixture:
узкий GRANT SELECT workspaces соответствует неизменному runtime bootstrap,
уже выдающему SELECT/DML на все таблицы. RLS/реальные constraints не ослаблены.
Недопустимые NULL/state/порядок/>24ч отдельно проверены synthetic SQL VALUES;
пример >24ч уточнён через DST fallback. FinalPG7 заменяет initialPG7,
повторы не суммируются; успешный unit3 повторно не запускался.
Собственные одноразовые containers удалены finally; чужие сохранены.
XML/log/nodeids/11 frozen inputs и история:
внешний f140-t077-fair-use-implementation-validation-20261101.json.
Ruff/process/governance/context/fragments/diff PASS.

## Независимое ревью и scoped converge

Фактический [кодовый отчёт и собственная сверка reviewer](review-fair-use-inventory-code-20261101.md)
полностью прочитаны основным исполнителем: APPROVE F1–F6,0 новых findings;
SHA256 8febf9f0f766cb39c23ea7d65287de5d85daa6d1fa3725fe5eab6d140fe7ef6a.
11 frozen inputs и5парXML/log независимо сверены; уникальный итог10 подтверждён.
[Scoped converge](converge-fair-use-inventory-20261101.md):6требований,
7решенийплана,7принципов,0новыхfindings. Полный O6 HIGH partial остаётся
в прежней T077 без новой задачи;58старыхgaps не приняты.
Следующие ворота — три GitHub checks/common validator точного source/base,
защищённый merge, validator после merge и один русский status #4932.

## Открытый остаток

Полный FR089/O6: остальные источники, постоянные показатели попыток/ошибок/
повторов, регулярность/heartbeat, тревоги/retry и сохраняемая реакция с
реальными owner/severity/evidence/сроком/разрешением остаются открытыми.
Исходные transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/
pending3дня, registry/F278FR041≤24ч и отдельные приёмки сохраняются.
F272/F199 stop/runtime gates и отказ оплаченного срока F278FR041 не возвращены.
Только Refs #4932;10PASS не дают [X], closure, финансовую/приватностную/
ручную/выпускную приёмку или production PASS. Full/CD/выпуск/Dev здесь нет.
