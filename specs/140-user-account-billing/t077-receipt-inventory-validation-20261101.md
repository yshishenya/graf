# T077: проверка наблюдений чеков — 01.11.2026

Полоса active Spec Kit slice/high-risk-product, owner repository-audit.
Только O13/Q1–Q6 исходной T077/#4932; Legacy Impact untouched.
Все87 исходных полных task lines сохранены, T077[ ], issue OPEN.

## До кода

Собственное полное чтение семи текущих изменённых оригиналов и происхождение
неизменных документов подтверждены фактическими51диапазонами/45callIDs того
же диалога /root. После сжатия применимые целые original sections/dependencies
восстановлены до зависящей работы; карта/текущие hashes во внешних материалах.
Исторический пропуск до первоначального PR7884 кода сохранён; весь O8 не PASS.
[Независимые требования](review-receipt-inventory-requirements-20261101.md)
10/0, [scoped analyze](analyze-receipt-inventory-20261101.md)
6req/1task/100%/0 новых findings. Canon ensure/validate243 PASS,
единственная существующая #4932 OPEN. Новых задач/issues не создавалось.

## Реализация и проверки

Один _receipt_inventory в существующем monitoring.py: две SQL-агрегации
BillingInvoice.plan_snapshot.receipt_observations. Контейнеры invoice/missing/
invalid отдельно от числа JSON entries; CASE защищает json_each от scalar/
array/null.18 совместных parent_kind/status/source групп и одна unknown,
без загрузки частных JSON/key/IDs/времён в Python. Составной root source,
прежние refund count/groups; оба source partial, timing/reconciliation null.
Схема/права/RLS/финансовые writers/CLI/guard/RR/as_of/cleanup/лимиты прежние.
Fragment сохраняет невыпущенные O10/O11/O12 и добавляет O13.

Owned apps/server/.venv и PYTHONPATH=src:.; __file__ подтверждён.
Штатная fixture создаёт отдельную migrated PostgreSQL17 с FORCE RLS и удаляет
только свой cluster через finally с проверкой результата. Рабочие данные/Dev
не использовались; старые чужие containers сохранены.

| Выбор | Окончательный результат | Содержание |
| --- | --- | --- |
| unit -k 'receipt_inventory or refund_inventory' | 7PASS/0FAIL/ERROR/SKIP,0.11с | 4новых:counts/priority/закрытая SQL/приватность;3затронутых:root refund с вложенным источником. |
| integration -k receipt_inventory | 4новыхPASS | Пустота/NOT NULL/схема;18пар/malformed root/map/entry/missing/JSON null/{}/privacy/no-write/разные дни; SQL NULL и duplicate keys отдельно; два снимка/новый процесс. |
| integration refund_inventory/identity/SET ROLE | 5затронутыхPASS | 3прежнихrefundсценария и2проверки maintenance/READ ONLY до hook/ролей/context/mutation. |

Итого16 уникальных окончательных PASS:8новых+8затронутых;0FAIL/ERROR/SKIP.
PG9:47.66с,2прежнихwarning,0SAWarning. RED4ImportError отсутствующего helper
и REDPG1 старого root source сохранены отдельно. После final Ruff только
переставил два локальных import-блока тестов; collector/test logic прежние,
успешное без новой причины не повторялось. XML/log/nodeids/11frozen inputs:
внешний f140-t077-receipt-implementation-validation-20261101.json.
Ruff/process/governance/context/fragments/diff PASS из правильного repo root;
предварительная ошибочная cwd попытка не считается доказательством.

## Независимая проверка и остаток

[Независимый code review](review-receipt-inventory-code-20261101.md) APPROVE
Q1–Q6/0новыхfindings;11frozen inputs/8XML-log hashes независимо сверены.
Фактические210строк отчёта полностью прочитаны основным исполнителем;
SHA25637f50fc6195dca581ce767743797a0ded73bad06c5a72c44e5cca58a805d48bb.
[Scoped converge](converge-receipt-inventory-20261101.md):6requirements/
7plan decisions/7principles/0новыхfindings и отдельная независимая сверка PASS.
Далее три GitHub checks/common validator точных source/base, protected merge
и validator после merge; один русский status #4932 с прочтением обратно.

Полный FR089/O6/T077 остаётся открытым: остальные источники, постоянные
attempts/errors/retries, регулярность/heartbeat, тревоги/retry и сохраняемая
реакция с реальными owner/severity/evidence/сроком/разрешением.58старыхgaps
не приняты. Transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/
pending3дня, registry/F278FR041≤24ч сохраняются независимо от подключения.
Ни счётчик, ни JSON не принимают реальные чеки/финансы/приватность/ручные
ворота или выпуск. F272/F199 stop/runtime gates и отказ оплаченного срока
F278FR041 не возвращены. Только Refs #4932; Full/CD/выпуск/Dev здесь нет.
