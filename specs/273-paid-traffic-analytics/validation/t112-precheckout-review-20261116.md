# T112 — независимая проверка отмены до checkout

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Проверенный HEAD: `5ed913c6292c143f7d8799b6902c5406f39097f7`.
Основа сравнения: `7ece19e783ff844319f2ab88b8d3e796f318de5f`.
Полоса: продолжение существующей `high-risk-product` F273/T112.
Область поручения: окончательный раздел локального файла
`/private/tmp/graf-t112-http-review-request-20261116.txt`.

## Решение

**PASS текущего ограниченного этапа реализации: P1=0, P2=0.**
Прочитаны весь актуальный diff трёх файлов, текущий guard, новые тесты,
предыдущий независимый preflight, отчёт реализации и законченный журнал85.
Порядок SessionEvents дополнительно проверен по установленному SQLAlchemy2.0.51.
Предварительное согласование не использовано вместо проверки реализации.

Это приёмка порядка отмены штатных auth/renewal задач до checkout, точной
invalidation на native pre-ping и одного конкретного startup cancellation
случая. Полные HTTP/T112/T113, initialization, slow rollback/close, все
commit/cleanup исходы и подключение ledger этим решением не принимаются.
Рабочий сбор, T0, готовность восстановления и продвижение не подтверждены.

## Корневая транзакция и владелец задачи

Public `SessionEvents.after_transaction_create` относится к логической
SessionTransaction; `transaction.parent is None` — документированный способ
выделить корень. В проверенной версии SQLAlchemy создание корня и событие
выполняются до `bind.connect()`, а значит до ожидания пула, физического
подключения и pre-ping. Текущая asyncio task в событии — задача, исполняющая
эту операцию, а не вывод из имени, стека или дерева AnyIO.

Registry сохраняет owner/transaction/task по identity. Он не присваивает
обычные owner=None сессии, вложенный SAVEPOINT или внутреннюю под-транзакцию.
`after_transaction_end` удаляет связь лишь при совпадении самого объекта
transaction. Конец вложенной транзакции не очищает корень; закрытие в другом
Context снимает исходный owner через сохранённую связь в session.info.
В установленном SQLAlchemy событие конца корня следует после закрытия его
connection/transaction ресурсов; связь остаётся видима во время cleanup.

Прочитаны штатные auth dependencies и session renewal: их локальная Session
создаётся, начинает SQL и используется последовательно в своей async task.
Поэтому событие даёт нужную задачу именно для проверенных путей. Гарантия не
расширяется на произвольную передачу уже начатой Session между задачами либо
на Session, начатую вне request owner: само событие создания не отслеживает
позднейшую передачу исполнения. Новый endpoint/service путь должен сохранять
проверенное владение либо отдельно доказать его до расширения приёмки.

В `_run_result_view_app` connection tasks и root transaction tasks имеют
приоритет отмены перед родительским ASGI. Это закрывает отсутствие checkout
lease во время pre-ping, не вводя отвергнутую эвристику AnyIO leaf. Затем
присоединяются все задачи точного request owner, включая поздние shielded
задачи SQLAlchemy. Нормальное завершение с оставшимся connection либо root
transaction registry не публикует успешный ответ. Новых фабрик, подклассов
Session в продукте или обхода auth/CSRF не появилось.

## Точность прекращения соединения

Invalidate callback требует owner, настоящий CancelledError, текущую task,
public entry.in_use и совпадение callback DBAPI/entry DBAPI/driver поколения.
Поддерживаемый driver проверяется через public asyncpg.Connection.
Существующий checkout lease дополнительно должен совпасть с owner registry;
чужая, устаревшая либо противоречивая связь не включает fallback.

Ветвь без lease ограничена текущей отменяемой task того же owner. Право на
конкретный driver следует также из синхронного automatic invalidate callback
того же reserved entry, его in_use и точных identities, согласно принятому
preflight; один ContextVar не используется как достаточное доказательство.
Между сверкой и public terminate нет await. Штатный invalidation/checkin
SQLAlchemy сохраняется. Runtime не обращается к private library API, не
вызывает engine.dispose и не отключает pre-ping для остальных запросов.

Unit случаи покрывают положительные checkout/precheckout и отказы для
owner=None, отсутствующей отмены, невыданного entry, другого DBAPI/driver,
чужого/устаревшего lease, другого lease driver и не-CancelledError.
Четыре lifecycle случая покрывают корень, вложенную транзакцию, foreign
owner=None и завершение в другом Context.

## Что доказывает новый сетевой профиль

TCP relay задерживает только настоящие PostgreSQL server→client ответы.
Native dialect.do_ping, asyncpg ping, rollback и close не подменяются.
Request engine прогрет настоящим SELECT; есть отдельный чужой connection
того же pool. В auth gate закрыт до запроса, в renewal — перед ответом,
когда начинается штатное post-response обновление сессии. Счётчик checkout
и metadata invalidate подтверждают отмену до checkout: lease отсутствует,
entry занят, DBAPI/driver совпадают, task cancelling=1, driver уже закрыт.

Оба native pre-ping случая завершаются unavailable менее чем за2s, около1.64s.
Независимый прямой observer engine проверяет целевой backend в
pg_stat_activity и pg_locks: нет активной/idle-in-transaction работы и locks.
Оставшийся checkedout1 относится к заранее удерживаемому соседу; после его
закрытия checkedout0. Его прежний PID и SELECT1 сохраняются, следующий
обычный checkout также работает. Новых request-owner tasks после ответа нет.

Startup case создаёт новый физический connect через закрытый gate: до
первого public connect event запрос отменяется, пул возвращается к checkedout0,
relay/socket tasks завершаются до fixture teardown, последующее подключение
успешно. Это доказательство конкретного раннего сетевого stall до выдачи
DBAPI. Оно не доказывает все DNS/TLS/auth/connect этапы или зависание dialect
initialization после появления driver.

Watchdog освобождения gate назначен на3s; успешные ответы уже закончены до2s.
Принудительное закрытие writers при завершении fixture идёт после проверок
очистки приложения и не подменяет их. Relay задачи имеют отдельный Context,
поэтому они не присваиваются request owner и не маскируют его cleanup.
Одновременно gate удерживает ранний native ping обмен; отдельные зависания
в последующих rollback/close фазах этим сценарием не локализованы и остаются
открытыми.

## Квитанция проверки и точные входы

Полный журнал прочитан, его SHA-256 и SHA-256 трёх исходных файлов совпали с
заявленными. В журнале: **85 passed, 1 warning, 0 skips, 38.63s**;
runner duration42s, `postgres_test_phase=focused status=pass`,
`postgres_test_cleanup=isolated_container_removed`,
`postgres_test_result=pass mode=focused partitioned=false shard=none`.
Collection_count85; collection_digest
`b35ab182bd616795323fceeddaa727fc19c2e608732238c208fd36ae88af6623`.
Warning относится к повторному импорту pytest fixture plugin, не к отказу
продукта. Terminal EXIT0 указан в поручении основного агента; независимо
прочитанный завершённый журнал подтверждает pass и cleanup.

| Вход | SHA-256 |
| --- | --- |
| `api/product_analytics_guard.py` | `1cd220b5c9b6a5936c01668c9d3312bdf1e052609e3744bd7fd480e41b6b76ee` |
| `unit/test_result_view_http_guard.py` | `4fef6152ed8adc776544098ed019321305c161583dab1b90f092fa2f3cb85461` |
| `contract/test_result_view_http_budget.py` | `a129566fcee229f572595986a9c820bb3c2c764de5bdaf7abdf90eda75a79670` |
| `/private/tmp/graf-t112-precheckout-full-green-20261116.log` | `9ae1a800b9d74bfa09b5ae9fdca486400cb9b2108f7b05312bdf6c9cec64d0cc` |
| Installed SQLAlchemy `orm/session.py` | `b75a4e427f453c2eaf19f04d87f66c2da644698a14f3b11880f56a73e2a0760d` |
| Installed SQLAlchemy `orm/events.py` | `8386df91c26c4459e3cb37d61f143ce21d8608d3c72912f95f439e40137a1d24` |

Это новый завершённый профиль85, не прежние67 или промежуточные13.
Ошибки fixture, прерванные при отладке relay запуски и старый SQL-in-ping
профиль не включены в его результат. Проверяющий тесты повторно не запускал.

## Сохранённые ограничения и изменения проверяющего

Синтетический HTTP handler не пишет ledger и не доказывает просмотр
реального результата. Ещё нужны настоящие endpoint/issuance/renewal/render,
GET/HTMX proof, browser/native сценарии и единый ledger HTTP путь; отдельные
init/slow rollback/close и commit cleanup исходы требуют собственных
причинных доказательств. Успешный транспортный cleanup не утверждает rollback
неизвестного commit; retry продуктовым исправлением не добавлен.

Прежние требования и основные checklist остаются124 checked/0 unchecked
по ранее принятой проверке качества требований. Они не переотмечались и
не заменяют проверку реализации. T112/T113 и задачи не закрыты. PR/CI/merge,
выпуск, runtime/T0 и трафик не приняты этим локальным отчётом.

Проверяющий добавил только настоящий отчёт. Код, требования, планы, задачи,
checklist, Git/GitHub, рабочие службы и настройки не менялись; чужая работа
сохранена. Успешный85 профиль не повторялся, новых тестов/сборок не запускалось.
