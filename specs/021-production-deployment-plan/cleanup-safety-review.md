# Независимая проверка требований bounded smoke cleanup

Дата: 2026-10-02. Reviewer: отдельный агент header_review. Область: новое расширение FR-023–027 / T067–070 в существующей F021; исторический ingest-only rollout не переоценивается.

## Вердикт

PASS для качества требований перед реализацией. Все 10 пунктов cleanup-safety подтверждены ссылками на specification, plan, data-model, smoke-evidence contract и quickstart. Это не PASS реализации, стенда, CI, cleanup или production readiness. Реализация T067–070 пока не подтверждена этим review; production CD не разрешен.

## Проверенные границы

- Повторяется вся транзакция только при SQLSTATE 40P01 до commit, всего до трех попыток; задержки 100 и 300 ms выполняются после полного rollback и закрытия неудачной попытки.
- Сохраняются точный synthetic run и существующие identity, tenant/RLS, prefix и SQL deletion filters; широкая очистка и остановка обработчиков исключены.
- Счетчики каждой неудачной попытки отбрасываются; storage и проверка остатков идут после commit. Ошибки после commit не запускают повторное удаление.
- Non-40P01, exhausted и postcommit ошибки сохраняют неуспешный required gate. CLI/output shape, backup, residue, readiness и rollback gates не ослабляются.
- Требуется настоящий конкурентный PostgreSQL цикл DELETE workflow ↔ INSERT result, доказанное падение старого helper и успешный повтор нового; соседние обычные данные проверяются на неизменность. Только одноразовая изолированная БД, без production fixtures и содержимого реальных встреч.
- Нужны independent implementation review и обязательные exact-SHA PR checks. Frontend, F283, schema, grants и текущая production выкладка не меняются этим пакетом.

## Повторное чтение checklist и счетчики

| Checklist | Отмечено | Не отмечено | Область доказательства |
| --- | ---: | ---: | --- |
| cleanup-safety.md | 10 | 0 | Новые требования FR-023–027, независимо проверены сейчас |
| requirements.md | 16 | 0 | Существующие исторические отметки, прочитаны без изменения |
| security.md | 26 | 0 | Существующие исторические отметки, прочитаны без изменения |
| infra.md | 25 | 0 | Существующие исторические отметки, прочитаны без изменения |
| Итого | 77 | 0 | Исторические отметки не являются новой аттестацией production |

Неподтвержденных пунктов нового requirements-quality checklist нет. Блокеров качества требований не выявлено. До выпуска сохраняются независимые блокеры реализации/CI и отдельного согласованного release gate; данный документ их не снимает.

Изменены только cleanup-safety checklist и этот review report. Код, specification, plan, tasks, остальные checklist, GitHub и production не изменялись reviewer.

## Независимый review реализации и тестов

2026-10-02: просмотрены diff helper и новый test_smoke_cleanup_deadlock.py. Блокирующих high/medium дефектов реализации не обнаружено. Публичная signature и CLI сохранены; существующие SQL filters, deletion order, tenant contexts и storage prefix не менялись.

Private retry signal появляется только для DBAPIError с orig.sqlstate=40P01, пока database_committed=false. Handler находится снаружи engine.begin(), поэтому aborted transaction закрывается до сигнала; finally dispose заканчивается до backoff. Каждая попытка заново создает engine, counters и те же deterministic identifiers. Только private signal перехватывается наружным ограниченным циклом; другие ошибки и исчерпание остаются failure. Флаг commit переключается до storage/residue, поэтому postcommit ошибка не повторяет удаление.

Прочитаны локальные журналы RED и GREEN: прежний helper действительно получил PostgreSQL DeadlockDetectedError (1 failed); исправленный набор содержит 23 passed. Не запускались новые DB/production проверки reviewer. Новый конкурентный тест моделирует FK lock cycle на упрощенной isolated schema; это не доказательство точного полного lock graph production. Он координирует реальный заблокированный INSERT через pg_blocking_pids, фиксирует две cleanup попытки, один storage вызов, корректные counters и неизменность соседних строк. Отдельные тесты покрывают exhausted/non40P01 и postcommit40P01 без повторного удаления. Существующие cleanup/RLS тесты входят в сообщенный GREEN набор.

Неблокирующее усиление: storage callback в конкурентном тесте считает вызовы, но не выполняет независимый SELECT для доказательства видимости committed удаления в момент самого вызова. Последовательность после commit подтверждена кодом; такой SELECT сделает регрессионную проверку этой границы сильнее. При postcommit failure helper сохраняет failure через exception и не возвращает успешные counters; структурированного отчета committed counts для аварии этот неизмененный CLI не предоставляет. Не заявлять, что такой отчет уже доказан.

Exact-SHA required CI, независимые release blockers и последующее разрешение CD остаются вне данного code review. Отметки requirements-quality checklist сохранены; дополнительных implementation attestations в checklist не добавлено.
