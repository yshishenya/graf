# F140/T075 — реализация внутреннего импорта B1–B3, 30.10.2026

## Область и результат

Полоса: `Active Spec Kit slice`, высокий риск PostgreSQL/полномочий/финансовых
данных. Основа: `eed85acee40613165d79c39313b454cb4421c9aa`.
Реализован внутренний CLI → проверка полномочий → CSV → атомарный результат
и история расхождений → отдельный status после перезапуска.
Новых зависимостей, службы, API или пользовательского интерфейса нет.

Это частичная реализация T075/#4930. `files_complete` означает только
полноту файлов. `financial_status=not_checked` сохраняется во всех ответах;
задача остаётся `[ ]`, issue — OPEN. Финансовая CSV/API/ledger сверка,
проверка магазина, внешние условия запуска и выпуск не приняты.

## Требования и проверки

| Требования | Реализация | Доказательства |
| --- | --- | --- |
| IMP001–002 / B1 | Один внутренний CLI, dry-run; фактические session/current identity, row_security, operation/area перед CSV и каждым обращением к store | CLI dry-run/execute; owner/app/worker, SET ROLE, off и неверные контексты отклонены до чтения файла |
| IMP003 / B1 | Две общие таблицы, ENABLE/FORCE RLS, точная maintenance policy; обе в фактическом inventory | Настоящие PostgreSQL подключения; прямые SELECT/INSERT/UPDATE/DELETE для обеих таблиц, включая широкие grants; pg_class flags |
| IMP004–006 / B2 | Один UTF-8 профиль, framing/shop/day, уникальные нормализованные заголовки, точная ширина, identity/RUB/time/count/gross/type, multipart/last/empty | Положительные и отрицательные unit tests, оба вида, 10 000 строк, отсутствие/дубли/смешанные части, повреждённые footer |
| IMP007 / B3 | Канонические versioned config/input hashes, реальные byte hashes, пределы файлов и CSV fields | Порядок/scope/BOM/CRLF, ограниченное чтение, FIFO без ожидания, отказ при смене csv.field_size_limit |
| IMP008 / B3 | Общий scope advisory lock, immutable receipts, replay, замена текущего digest | Новый процесс/status, исторический replay не становится текущим, две замены дают одного победителя; shared status lock проверен через pg_locks |
| IMP009 / B3 | Одна транзакция receipt/gaps; исходные owner/deadline, поколения и подтверждённое восстановление | Сбой trigger откатывает всё; owner/deadline и закрытая история неизменяемы; resolution actor/time/accepted receipt сохранены |
| IMP010 / B1–B3 | Только ограниченные метаданные; без CSV, сумм, provider IDs, исходных путей или workspace-подмены | CLI stdout и persisted metadata; поиск рабочих вызовов старых helpers; product/provider mutations отсутствуют |

## Исправленные отказы

Независимое ревью выявило R1–R3, они устранены до коммита:

- Официальные net/commission/VAT footer принимались неверно. Теперь разрешены
  точные официальные названия и ограниченный синтаксис; проверяются только
  gross/count, финансовый результат комиссии/НДС не заявляется.
- Строки `;` и `;;;;` исчезали при фильтрации пустых строк. Теперь пропускаются
  только действительно пустые CSV-строки; пустые записи проверяются как данные.
- Три чтения status могли смешивать поколения. Shared transaction advisory
  lock удерживает область до завершения чтений и блокирует новую замену.

Семь новых сценариев сначала дали `7 failed / 29 passed`; после исправлений
и расширения DB-проверок итоговая выборка ниже прошла полностью.
Официальное описание перечитано непосредственно:
https://yookassa.ru/docs/support/merchant/payments/reports/reports-new .
В опубликованном payments-примере 13 заголовков и 12 полей строки. В тесте
синтетической полной структуры восстановлено отсутствующее пустое поле;
неверная ширина реального входа по-прежнему отклоняется. В refunds-примере
пробелы вокруг заголовков нормализуются до проверки дублей. Неизвестные
форматы, включая отдельный b2b-профиль, не угадываются.

## Исполненная проверка

Из `apps/server`, существующее Python-окружение сервера, Python 3.13:

```sh
PYTHONPATH=src python -m pytest tests/unit/test_billing_registry.py \
  tests/integration/test_billing_registry.py \
  tests/unit/test_billing_reconciliation_activity.py -q
```

**59 passed, 0 failed, 0 skipped, 39.09 s.** Существующее предупреждение pytest
о повторном импорте модуля fixtures — одно; оно не является пропуском.
PostgreSQL 17: одноразовые изолированные кластеры с настоящими Alembic
миграциями и отдельными ролями. Новый CLI-процесс реально запускается.
Проверены downgrade/upgrade пустой схемы и отказ downgrade с сохранённой
историей. Очистка кластеров принадлежит fixture; исходные CSV синтетические.

Ruff по всему server src и двум изменённым тестам — PASS;
compileall по src и двум тестам — PASS; `git diff --check` — PASS;
`check_spec_kit_governance.py` и `check-development-process.py` — PASS.
GitHub-проверки точного коммита/основы ещё не выполнены на момент этого отчёта;
локальный результат не заменяет PR-проверки или выпуск.

## Предметный анализ и сходимость

Сопоставлены десять действующих IMP/B1–B3, план одного CLI/двух таблиц/одной
миграции и сохранение product gates. Независимый дизайн подтвердил 10/0 до
реализации; исходные 220 CHK и общая статистика 158/62 не переписаны.
Анализ ограниченного импорта после исправлений: не выявлено новых CRITICAL/HIGH
противоречий. Это не общий анализ всей F140 и не финансовая приёмка.

Сходимость B1–B3: нового обязательного объёма за пределами существующей T075
не выявлено. Остаток CSV ↔ authenticated provider GET/list ↔ ledger уже явно
принадлежит открытой T075, поэтому дубли задач и issues не создаются.
`tasks.md` оставлен побайтно неизменным. Новых checklist-отметок исполнитель
не ставит; итоговое независимое ревью кода ведётся отдельным reviewer.

Следующий этап T075: точный Moscow day по provider captured/created time,
все страницы API, GET/scope и обратное обнаружение пропусков, unknown/mismatch
owned gaps без изменения платежа или entitlement. Старые invoice.created_at
и refund.observed_at не заменяют дату операции провайдера.

## Совместимость и границы

Требуется миграция `0107_billing_registry`. История неизменяема;
downgrade при её наличии намеренно запрещён. Shop/environment берутся из
Settings, операторский label не даёт полномочий. По умолчанию записей нет;
`--execute` сохраняет валидный результат либо безопасную ошибку.
CSV не имеет проверяемой подписи; доверие к источнику остаётся у оператора.
GRAF Dev, Windows/F200, F254, production, реальные платежи и выпуск не менялись.
Legacy Impact: `remove` — удалены прежние невызванные pure-helper API
registry.py; production callers не обнаружены, оба старых тестовых файла
заменены проверками действующего внутреннего входа. Новых aliases/fallback нет.

## Контрольные суммы проверенных байтов

| Путь | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/registry.py` | `055491eb3107140b9951eec3c19d8a4a73a8cff821a3c824d9ff91dc521a7bd8` |
| `apps/server/src/twobrain_rec_server/billing/registry_store.py` | `f96c046cd61ef5a1d364cc45ec06945de355346454e4e2b8cdb74e3eaf773eed` |
| `apps/server/src/twobrain_rec_server/cli/billing_registry.py` | `3070681009a5ac31163765200ca1706436d028731bc67bff95b66ac58a5ad2ab` |
| `apps/server/src/twobrain_rec_server/db/models/billing_registry.py` | `54e198344440251a7639c238fbf99d4bc8f285019e9a64f6ae3bfc1e22a09471` |
| `apps/server/src/twobrain_rec_server/db/models/__init__.py` | `5545b3d8c6bc557583800de23dd14950ca9703f4e252487e4852c4e4159cdd7d` |
| `apps/server/src/twobrain_rec_server/db/migrations/versions/0107_billing_registry.py` | `df1dab897e2176eb13be5bce1486359fba24a98997de3fddf14fdcc9f93734d1` |
| `apps/server/src/twobrain_rec_server/db/rls_validation.py` | `5aa325a6b18af3a604025c5818863e504b63cc83eca0626fed78dccdd5e6a368` |
| `apps/server/tests/unit/test_billing_registry.py` | `52df97610f224e2bad411dbc1407db8febaca1875f62ab6a4a0a7fd5224657cc` |
| `apps/server/tests/integration/test_billing_registry.py` | `e80244f0f946392227b1c508ed2a900dd925fab2a26e3ef8529f721839981bef` |
| `specs/140-user-account-billing/contracts/registry-operator-import.md` | `297bfe6c3acb063d70a6ef634c287a901fc9c342549270eaeec2c15a35c5b0a5` |
| `specs/140-user-account-billing/tasks.md` | `2cdccb7df2c8d0686be3dc83a21c8d1ea3c93be4899f40563101fbfce6214599` |

Внешний JUnit и итоговый журнал содержат только результаты синтетической проверки:

- `f140-t075-b1-b3-final.xml` SHA256 `b52deafc1e3cf2ca0cfc9df7eed5002366e759b1ac81b62b7c0a7bb127b7cc5c`.
- `f140-t075-b1-b3-final.log` SHA256 `d35361fec044dbe79a1dee437a2c391297f5faabdbb8aac13062ad83b5fdfcf8`.
