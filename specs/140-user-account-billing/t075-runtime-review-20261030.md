# Независимое ревью реализации F140/T075 — 2026-10-30

## Итоговое решение

**PASS только для внутреннего операторского импорта B1–B3.**
R1–R3 исправлены и повторно проверены на замороженных файлах;
открытых замечаний в этой области не осталось. Финальная привязка файлов,
результатов и границ приведена ниже. Первоначальный REQUEST CHANGES и его
причины сохранены как история проверки.
Основа `eed85acee40613165d79c39313b454cb4421c9aa`, ветка
`codex/140-registry-implementation`, контракт `registry-operator-import.md` B1–B3.
Полоса: `Active Spec Kit slice`, высокий риск PostgreSQL/полномочий/финансовых данных.

## Замечания первого чтения

1. **R1 / P1 — стандартные строки итогов официального payments CSV отвергаются.**
   `billing/registry.py:149`: допустимые `EXTRA_FOOTERS` не включают официальные
   `Сумма принятых платежей за вычетом комиссии и НДС типа AC`,
   `Сумма комиссии без НДС за принятые платежи типа AC` и
   `Сумма НДС с комиссии за принятые платежи типа AC`.
   Официальная текущая страница
   https://yookassa.ru/docs/support/merchant/payments/reports/reports-new
   прочитана независимо. Эти строки присутствуют в обычном реестре платежей,
   но в новых синтетических fixtures отсутствовали. Каждый вариант на
   синтетическом минимальном отчёте фактически дал `invalid_footer`.
   Требуется принимать точные официальные строки, не выдавая проверку их
   комиссий/net/НДС за финансовую сверку.
2. **R2 / P2 — повреждённые пустые записи пропускаются.**
   `billing/registry.py:108`: `row and any(row)` удаляет и физические пустые
   строки, и CSV-записи `;;;;` / `;`. Эти записи обязаны пройти проверку ширины
   и непустых обязательных полей. Обе синтетические пробы фактически приняты
   с `row_count=1`, хотя содержали дополнительную повреждённую запись.
   Требуется пропускать только настоящие пустые разделительные строки.
3. **R3 / P2 — status может смешивать разные зафиксированные состояния.**
   `billing/registry_store.py:47–50`: три SELECT в обычном READ COMMITTED
   получают отдельные снимки. При commit импорта между запросами возможны
   старый `last_attempt`, новый `latest_accepted` и gaps другого поколения.
   Требуется один согласованный снимок или тот же scope lock; подтверждение
   — отдельная проверка с commit между чтениями.

Замечания переданы исполнителю и приняты к исправлению. В момент первого
чтения решение было REQUEST CHANGES; итог исправлений приведён ниже.

## Что прочитано

Полностью прочитаны текущие `registry.py`, `registry_store.py`,
`cli/billing_registry.py`, `db/models/billing_registry.py`, миграция 0107,
оба новых/переписанных файла unit/integration tests и изменения экспорта моделей
и фактического RLS inventory. Прочитаны действительные DB guard,
session/context restoration, применимые RLS helper и bootstrap grants.
Поиск callers не обнаружил рабочих потребителей удаляемого прежнего registry API;
новый внутренний CLI является единственным найденным входом импорта.

Видимые положительные границы: guard до CSV, повторная проверка перед каждым
защищённым store statement, scope lock до current/replay/replace, один transaction
для receipt/gaps, immutable receipt/history trigger, narrow maintenance RLS,
проверенный metadata-only вывод и отсутствие provider/invoice/entitlement mutations.
Эти наблюдения не являются финальной приёмкой работающего пути.

## Проверки reviewer-а и ограничения

Пять чистых проверок parser выполнены через `python3 -B` и `runpy` в памяти,
без записи файлов, DB, импорта приложения, запуска pytest или сборок.
Две malformed-empty пробы приняты; три official-footer пробы отвергнуты.
Это исходные отказы, а не положительное доказательство исправлений.
Официальный HTML прочитан без сохранения и без записи его реальных примеров
или идентификаторов в репозиторий.

Изменён только этот назначенный отчёт. Исходные 220 CHK не меняются;
предметный design gate 10/0 и глобальный итог 158/62 сохраняются.
T075/#4930 открыты. `files_complete` — только проверка файлов,
`financial_status=not_checked` обязателен. CSV/API/ledger, магазин, выпуск,
Windows/F200, F254, GRAF Dev и production этим проходом не принимаются.

## Хеши первого чтения реализации

Контрольные суммы ниже обозначают просмотренную изменяемую версию; после
исправлений они должны быть заменены отдельной новой записью.

| Путь | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/registry.py` | `2c4e089b0602edd48de6756dcd85680a955f9ca72b9e2409ca22eae79dced640` |
| `apps/server/src/twobrain_rec_server/billing/registry_store.py` | `5551fcb7dc7ade2bfe6e17605bfb72d5b49d7ef6ec23ed06020c1bcca6b99245` |
| `apps/server/src/twobrain_rec_server/cli/billing_registry.py` | `3070681009a5ac31163765200ca1706436d028731bc67bff95b66ac58a5ad2ab` |
| `apps/server/src/twobrain_rec_server/db/models/billing_registry.py` | `54e198344440251a7639c238fbf99d4bc8f285019e9a64f6ae3bfc1e22a09471` |
| `apps/server/src/twobrain_rec_server/db/migrations/versions/0107_billing_registry.py` | `72660862e24e6d6174bcd078123c520f4dc334030eaa91218ac1118296a8e903` |
| `apps/server/tests/unit/test_billing_registry.py` | `f6452b3812d80bffaad8c4e0b952dd0154b8f23b383bb41981e2cf8696122fb8` |
| `apps/server/tests/integration/test_billing_registry.py` | `cc683c9860f18abff186b84cf7b6771b45b335e08a741096f9a0384af8fedf96` |

## Повторная проверка R1/R2 до замораживания

Исправленный parser прочитан; те же пять синтетических проб в памяти повторены.
`;;;;` даёт `invalid_identity`, `;` даёт `invalid_row_width`.
Каждая из трёх официальных net/commission/VAT-строк теперь принимается.
Проверены явные полные имена footer, ограниченный синтаксис и отказ при дубле;
нормализация внешних пробелов header выполняется до проверки уникальности.
Денежный итог по-прежнему сравнивает только gross/count, не комиссию/net/НДС.
R1/R2 устранены в просмотренных байтах; окончательная привязка к замороженным
файлам и общей проверке ещё ожидается.

R3 статически исправлен: status получает shared transaction advisory lock,
persist — exclusive peer того же canonical scope/hash/seed. Новый DB-сценарий
действительно ожидает непринятый advisory lock в `pg_locks` до продолжения
reader; это проверяет нужное пересечение, а не только незавершённость coroutine.
Фактический итог DB-сценария ещё не получен.

Статический AST-разбор полного графа миграций: единственная head
`0107_billing_registry`, отсутствующих родителей нет.


## Окончательная проверка замороженной реализации

Исполнитель явно подтвердил замораживание кода, миграции и тестов. После этого
полностью перечитаны parser, store, CLI, модель, миграция и оба файла тестов;
прочитаны точные изменения model exports, фактического RLS inventory,
quickstart, changelog и итоговый отчёт реализации. Контрольные суммы всех
11 файлов его таблицы совпали с текущими байтами.

- **R1 устранено.** Все три точных официальных имени footer принимаются
  с ограниченным синтаксисом. Дубликаты и неизвестные/повреждённые итоги
  отвергаются. Отдельный синтетический пример полной опубликованной структуры
  проверяет AC/PC и общий gross/count. Комиссии/net/НДС не выданы за сверку.
- **R2 устранено.** `rows if row` удаляет только настоящие пустые CSV-строки.
  Оба вида повреждённых delimiter-only records проходят валидацию данных и
  отвергаются. Есть четыре проверки непустого/пустого реестра × двух записей;
  первоначальные чистые пробы reviewer-а также повторно подтвердили отказ.
- **R3 устранено.** Общий shared scope lock status и exclusive lock persist
  имеют одинаковые scope/hash/seed и живут до конца транзакции. Прочитан
  отдельный сценарий PostgreSQL: reader останавливается после первого SELECT,
  writer действительно ожидает advisory lock в `pg_locks`, reader получает
  прежние attempt/accepted/gaps, затем writer успешно завершается. Итог этого
  сценария присутствует в окончательном JUnit без ошибки или пропуска.

Дополнительно проверены минимальные защиты ограниченного ввода: pinned CSV
field limit включён в config fingerprint, изменение глобального лимита даёт
фиксированный отказ; nonblocking open/fstat отвергает FIFO до чтения. Пределы
files/file/total/rows остаются явными. Новых зависимостей и служб нет.

Прочитаны настоящие DB-сценарии, а не только их названия: прямые запреты
SELECT/INSERT/UPDATE/DELETE обеих таблиц при широких grants; реальная роль,
SET ROLE, неверные operation/area и row_security; неизменяемая история,
owner/deadline, accepted closing receipt, actor/time; новый процесс/status,
replay/current replacement; конкуренция, rollback receipt/gaps; пустой
migration downgrade/upgrade и отказ downgrade при наличии истории.

## Проверенные окончательные доказательства

Непосредственно прочитаны итоговый журнал и JUnit по внешним путям:

- `/Users/yshishenya/Documents/Codex/2026-10-30/graf-repository-audit/f140-t075-b1-b3-final.xml`
  — SHA256 `b52deafc1e3cf2ca0cfc9df7eed5002366e759b1ac81b62b7c0a7bb127b7cc5c`.
- `/Users/yshishenya/Documents/Codex/2026-10-30/graf-repository-audit/f140-t075-b1-b3-final.log`
  — SHA256 `d35361fec044dbe79a1dee437a2c391297f5faabdbb8aac13062ad83b5fdfcf8`.

Оба hashes совпали с отчётом исполнителя. XML содержит ровно **59 testcase,
0 failure, 0 error, 0 skipped**; все девять integration-сценариев, включая
конкурентное status и downgrade/history refusal, реально присутствуют.
Журнал подтверждает `59 passed, 1 warning in 39.09s`. Предупреждение относится
к прежнему импорту pytest fixture; подмена пропущенным сценарием отсутствует.

Команда исполнителя из `apps/server`:

```sh
PYTHONPATH=src python -m pytest tests/unit/test_billing_registry.py \
  tests/integration/test_billing_registry.py \
  tests/unit/test_billing_reconciliation_activity.py -q
```

Reviewer сам не запускал pytest, DB, приложение, сборку или миграции.
Лично выполнены описанные выше чистые parser-пробы в памяти и read-only
сверки source/artifact hashes, XML, истории checklist/tasks и графа миграций.
Ruff/compileall/governance/development-process PASS прочитаны в отчёте
исполнителя; отдельными самостоятельными запусками reviewer их не объявляет.
`git diff --check` reviewer выполнил отдельно, результат PASS.

## Предметный gate и сохранённый остаток

Повторный пересчёт design IMP001–IMP010: **10 отмечены / 0 открыты**.
Все восемь общих checklist перечитаны при сверке; исходные 220 CHK-строк
буквально совпали с `847ccc82e7b2180a8c38f8769bc67ff39a342c8b`:

| Checklist | Отмечены | Открыты |
| --- | ---: | ---: |
| launch-readiness | 32 | 8 |
| operations | 10 | 8 |
| payments | 14 | 6 |
| post-plan-readiness | 24 | 16 |
| product-market-2026 | 35 | 5 |
| requirements | 16 | 9 |
| security | 11 | 6 |
| ux | 16 | 4 |
| **Всего** | **158** | **62** |

Новых отметок reviewer не ставил. `tasks.md` побайтно совпадает с HEAD;
T075 не завершена. Общего PASS для F140, внешних условий запуска, магазина,
финансовой CSV ↔ authenticated provider API ↔ ledger сверки и #4930 нет.
`files_complete=true` всегда сопровождается `financial_status=not_checked`.
Сохраняются границы предыдущего чтения: это узкая проверка B1–B3, без новой
полной приёмки продуктовой основы или общего состояния продукта.
GitHub-проверки будущего точного коммита/основы и разрешённый путь принятия
проверяет владелец реализации; локальные тесты их не заменяют.

## Контрольные суммы окончательно просмотренных файлов

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
| `specs/140-user-account-billing/quickstart.md` | `d8eb2107be04b8bb1bf847b0687e52468eb79e9a916ebdf9f329035403741606` |
| `changes/unreleased/F140.yaml` | `fb670a0206e04e5026a998ac96e9c1d2e2a868fefc3beb3f075061b1f6a36a46` |
| `specs/140-user-account-billing/t075-import-implementation-20261030.md` | `d48a1d593e7365b9fa4d81157c682845ccaf28090685f47d06167b3dd5addf41` |
| `specs/140-user-account-billing/t075-import-design-review-20261030.md` | `a93089f54f488a70421e7b66276d7140ff9dab4f94013d1e497977beaaa61d4a` |
