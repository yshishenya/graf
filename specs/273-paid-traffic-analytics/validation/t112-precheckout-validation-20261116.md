# T112 — отмена до checkout: промежуточная реализация

16.11.2026, существующая полоса `high-risk-product`, основа
`7ece19e783ff844319f2ab88b8d3e796f318de5f`. Это продолжение внешней
HTTP-границы, не полный T112/T113. Рабочий сбор выключен.

## Текущее состояние

**Локальный профиль85 PASS; независимое implementation review этого
расширения ещё не получено.** Прежнее67PASS и его независимое ревью относятся
к прежней границе. Новый [preflight](t112-precheckout-preflight-20261116.md)
разрешил узкий public invalidate путь pre-ping при точных идентичностях;
он не заменяет ревью нынешних SessionEvents и всего текущего diff.
PR/обязательных GitHub checks/merge/выпуска этого расширения нет.

## Причина и минимальное изменение

Рабочий engine использует `pool_pre_ping=True`. Reused connection уже
зарезервирован, но `PoolEvents.checkout` ещё не вызван. Поэтому прежний
registry не знает владельца SQL и отменяет ASGI parent. В настоящем auth
pre-ping возникал незавершённый ответ, а после первого terminate-исправления
пул сохранял checkedout1: повторная отмена AnyIO parent прерывала штатное
SQLAlchemy invalidation/checkin, хотя driver уже был закрыт.

Текущий код использует существующую фабрику и публичные SQLAlchemy события:

- `Session.after_transaction_create` связывает только root transaction с
  текущим request owner и task. Autobegin происходит до получения соединения,
  поэтому действующий DB owner известен и при connect/pre-ping.
- `Session.after_transaction_end` снимает только совпавший root transaction;
  вложенный SAVEPOINT не снимает его, закрытие в другом Context также очищает
  исходную связь. Обычные сессии без owner не присваиваются запросу.
- Request-local `_ResultViewOwner` сохраняет прежний registry выданных
  соединений и короткий registry root transactions. На отмене известные DB
  tasks завершаются раньше родительской группы. На нормальном пути оставшиеся
  собственные connections/transactions не допускают успешного ответа.
- В синхронном invalidate callback сохраняется прежняя проверка checkout
  lease. До checkout требуются настоящий CancelledError, текущая отменяемая
  task того же owner, `entry.in_use`, точные entry/DBAPI/driver и отсутствие
  противоречивого lease. Только затем вызывается public asyncpg terminate,
  без await между сверкой и действием; штатный invalidation/checkin сохраняется.

Нет новых фабрик, auth/CSRF исключений, библиотек, engine.dispose в запросе,
private library APIs, SQL/application retry или изменения глобального pre-ping.
Эксперимент с выбором AnyIO leaf по дереву задач отвергнут: он угадывал DB
owner и ломал renewal. В текущем коде этого пути и импорта AnyIO нет.

## Причинные проверки

Первый RED с public `do_ping → pg_sleep(10)` воспроизвёл незавершённый auth
ответ. В том же запуске неверное ожидание числа предшествующих auth checkouts
в renewal было ошибкой fixture; вторым продуктовым RED оно не объявляется.

Затем построен временный локальный TCP relay к изолированной PostgreSQL,
который задерживает настоящие ответы сервера. Native asyncpg ping, его
transaction/rollback и close не подменяются. Вспомогательные relay tasks
имеют отдельный пустой Context и собственное завершение. Старые попытки,
прерванные при отладке завершения relay, не выдаются за законченный RED/GREEN.

Завершённый native RED после первого terminate-исправления:
auth вернул unavailable, но checkedout1; renewal прошёл. Callback подтвердил
CancelledError/owner/task cancellation/entry.in_use/DBAPI/driver match и
driver.is_closed=True. Это показывает отдельную необходимость законченного
bookkeeping; transport terminate сам по себе не означает освобождения пула.

Окончательный профиль: **85 passed, 1 прежний fixture warning, 0 skips,
38.63s; runner42s/terminal EXIT0; isolated_container_removed/result pass.**
Состав:62 unit,15 contract,8 прежних integration. Включены:

- настоящие auth и post-response renewal pre-ping при задержанном сетевом
  ответе; оба заканчиваются примерно за1.64s, до hard2s;
- точные public callback identities, закрытый driver и законченный checkin;
- независимые `pg_stat_activity`/`pg_locks` для целевого backend: нет активной
  или idle-in-transaction работы и locks после завершения;
- одновременно удерживаемое чужое соединение того же pool сохраняет backend
  PID и выполняет SELECT1; после закрытия соседа checkedout0, следующий
  обычный checkout/SELECT1 успешен;
- настоящее физическое подключение с задержанным ответом startup: нет
  выданного DBAPI, socket/relay tasks и checkout освобождены, новый connect
  успешен. Это один конкретный startup cancellation case, не все connect/init;
- root/nested/foreign Session и закрытие из другого Context;11 положительных
  и отрицательных callback identity случаев;
- прежние auth/CSRF/renewal, SQL cancel, pool wait, send deadline и три
  analytics ingress сохранены, рабочий сбор остаётся disabled.

Трёхсекундное освобождение искусственного сетевого сбоя — watchdog тестового
стенда. В успешных случаях guard заканчивается до2s, до этого watchdog;
он не становится новым бюджетом запроса. Принудительное закрытие только
собственных relay writers выполняется при завершении fixture после проверок
состояния приложения/пула, а не служит доказательством их очистки.

## Точные доказательства

| Вход | SHA-256 |
| --- | --- |
| `api/product_analytics_guard.py` | `1cd220b5c9b6a5936c01668c9d3312bdf1e052609e3744bd7fd480e41b6b76ee` |
| `unit/test_result_view_http_guard.py` | `4fef6152ed8adc776544098ed019321305c161583dab1b90f092fa2f3cb85461` |
| `contract/test_result_view_http_budget.py` | `a129566fcee229f572595986a9c820bb3c2c764de5bdaf7abdf90eda75a79670` |
| Final85 log | `9ae1a800b9d74bfa09b5ae9fdca486400cb9b2108f7b05312bdf6c9cec64d0cc` |
| Native checkedout1 RED log | `ae55a21bd5d2c1305edb905931dcc695f6c7b314456f6304c64095ca80fc9163` |
| Первый SQL-in-ping RED log | `9ce7549ce09f5331f829480fe1c4c8f38827ed9f41e3032ec1c362119a3be440` |
| Независимый preflight | `cdcefd11af4d204ac9a847ec2926169be0c179b6ee4ee5343293abf6510c44d2` |

Runner collection_count85, collection_digest
`b35ab182bd616795323fceeddaa727fc19c2e608732238c208fd36ae88af6623`.
Полные журналы сохранены локально отдельно от репозитория. Ruff/diff-check,
agent-context и changelog-fragments пройдены в изолированной копии.
19 ранее прочитанных требований/базовых входов побайтно совпали с preflight;
четыре checklist сохраняют124 checked/0 unchecked. Это качество требований.

## Открыто до полной приёмки

Нужны независимое implementation review нового расширения, отдельные
initialization/slow rollback/close и все исходы commit/cleanup с независимым
наблюдением. Сохраняются большой review preflight, реальные endpoints,
GET/HTMX выдача и обновление proof, общий ledger HTTP путь, browser/native
сквозные проверки и настоящая готовность T113/restore.

DB handler в этих HTTP тестах синтетический и не пишет ledger. Рабочие
настройки, контент/вёрстка, Postal, nginx/DNS/службы и backup не менялись.
Изолированные тесты не являются допустимыми внешними визитами, регистрациями
или оплатами; T0 не назначен, Product Radar не отправлен.
