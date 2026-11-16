# T112 — откат транзакции при закрытии Session

16.11.2026. Продолжение существующей `high-risk-product` F273/T112.
Основа: `41ff49078c30d02d8c6c626018ae1a3c0584e68f`.
Рабочий сбор выключен, настройки сервера и содержимое сайта не меняются.

## Причинный исходный результат

Независимый [preflight тестов](t112-close-preflight-20261116.md) принят до
добавления тестового кода:124/0 требований, P1=0/P2=0 в области тестов.
Прежний85 профиль не повторялся. Guard остался побайтно прежним:
SHA-256 `1cd220b5c9b6a5936c01668c9d3312bdf1e052609e3744bd7fd480e41b6b76ee`.

В существующий контрактный тест добавлены шесть случаев: три фазы с обычной
сетью и те же три при задержанном настоящем ответе PostgreSQL на ROLLBACK.
Фазы — Session синтетического handler без commit, исключение в штатной auth
Session после SQL и исключение в штатной renewal Session до commit.
Исключения — безопасный ProblemDetail503 и SQLAlchemyError соответственно;
в контрольном renewal сохраняется успешный ответ без незавершённого renewal.
Штатные AsyncSession, __aexit__, rollback и driver close не подменены.

Публичный callback rollback подтверждает точные Connection/DBAPI/driver,
тот же request owner и отдельную close task, отличающуюся от root/checkout
task. До rollback независимый прямой observer подтверждает реальную
транзакцию, синтетическую строку FOR UPDATE и locks целевого backend.
Только затем callback закрывает сетевой response gate.

Законченный исходный профиль: **3 контрольных PASS, 3 fault FAIL**,
1 прежний fixture warning;11.00s, runner14s/EXIT1,
`isolated_container_removed`. Во всех трёх fault HTTPX обнаруживает
незавершённый ASGI ответ после hard2s. Это новый причинный RED на неизменном
guard, а не повтор прежнего pre-ping.

Первая попытка дополнительно имела ошибку ожидания теста: контрольный handler
допускал последующий штатный renewal на том же slot/driver, поэтому общий
счётчик checkin был2 вместо1. Тест уточнён до первого возврата точного entry
после выбранной транзакции. Контроль стал PASS; три fault остались FAIL.
Ошибка теста не объявляется четвёртым дефектом продукта.

| Материал | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-close-baseline-20261116.log` | `501a0923fbb93deb6dc67313fe9d3f6adf585ba63ba5350d8950da0c4fda6813` |
| Первая попытка `/private/tmp/graf-t112-close-red-20261116.log` | `77f36742a1381acf06f8b8a81957d1a4ed4c3553d137f428b7bbb94e29eff8d5` |

Collection6/digest
`2dc4a3dda455bfbe2e4726978d9e8a61f1911978d80c719fd04a21d25524f7c5`.

## Границы проверки

Задержка ответа не останавливает серверный ROLLBACK: PostgreSQL мог уже
освободить locks, пока client close ещё ждёт ответ. Поэтому одного observer
недостаточно; нужны task/pool/checkin до gate.set и очистки стенда.
Watchdog3s нужен лишь для выхода из RED, успех обязан закончиться раньше2s.

Это native rollback внутри Session.close, не отдельный тест медленного
raw driver.close/TLS teardown, всех initialization стадий или неизвестного
commit. Полные HTTP/T112/T113, настоящие endpoint/proof/render/ledger,
browser/native и restore остаются открытыми. Нет новых визитов, регистраций,
оплат, T0 или отправленных Product Radar сообщений.

## Минимальное исправление и окончательный локальный результат

Независимый preflight согласовал передачу владения до runtime правки,
а затем отдельно — удаление завершённой собственной metadata после отмены.
Текущий preflight SHA-256
`b69666a8b029a2d4dcdcb31f871cc7a99910e2a3fea8bcaf350a7593b2dc8071`.

Публичный Session.after_begin связывает точный корневой lease с точным
connection lease. Engine.before_cursor_execute/rollback/commit уточняют
исполняющую task только после проверки owner, entry, DBAPI/driver поколения
и root association. Lease сохраняют identity; меняется только task поле.
Root association содержит и connection lease, очищается до checkin/reuse.
Closed/invalidated соединение не читается через свойства, способные reconnect.
Обычные синхронные сессии без owner проходят без обращения к asyncio task.
Новых фабрик, SQL, зависимостей, таймаутов или private library API нет.

Первое исправление завершило ответ и checkin в пределах2s, но оставило root
metadata: отменённый SessionTransaction.close не дошёл до after_transaction_end.
Это отдельный законченный RED3/controls3,9.09s/runner13s/EXIT1; журнал
`/private/tmp/graf-t112-close-first-green-20261116.log`, SHA-256
`349a4660e2602de8448eab6f15297aaf8ee2eaaa44def2f02fbd93cd7118d149`.
Несмотря на имя файла, он не GREEN. Поздние observer/tasks проверки до него
не исполнились и не выдаются за прежний успех.

Теперь только в ветви прерванного запроса, после законченного join и при
пустом connection registry удаляется metadata завершённого точного root.
Проверяются task.done, контекст owner, exact registry/Session.info и публичное
Session.in_transaction=False. Чужая либо новая Session.info сохраняется;
выбран строгий отказ очистки обоих mappings при её несовпадении. Нет повторного
close/rollback/commit, изменения transaction state или подавления исходного
отказа. Обычный успешный путь продолжает отвергать оставшийся registry.

Окончательный профиль: **120 passed, 1 прежний fixture warning, 0 skips,
45.00s; runner48s/terminal57752 EXIT0; isolated_container_removed/result pass.**
Состав:91 unit +21 contract +8 integration. Collection_count120/digest
`833f175054cfc4576cb2f86f58347d27056928b0e9e76158b47d72f0b0540c5c`.
Новые35 случаев покрывают hand-off identities, nested/new-root/reuse/reconnect,
синхронную unowned Session, завершение metadata и шесть реальных сетевых фаз.
Все прежние85 регрессий прошли в этом изменённом общем профиле.

В каждом fault до gate.set/teardown проверены Session.in_transaction=False,
штатный checkin, отсутствие own checkout/tasks и независимые activity/locks;
затем отдельно — пустая root metadata. Чужой connection того же pool сохраняет
PID/SELECT1, после его закрытия checkedout0 и обычный новый SELECT1 успешен.
В rollback callback проверены обе runtime task связи, а не только обнаружение
новой close task тестовым listener.

Ещё один промежуточный отказ был в учёте стенда: relay создавал wait_closed
через gather без регистрации этих вспомогательных задач. Они имеют пустой
Context и не являются задачами продукта. Все relay wait_closed теперь создаются
тем же tracked start; точное отсутствие request-owner tasks проверяется
независимо. Ошибка не устранялась изменением бюджета или снятием требований
к очистке приложения. Новый focused35 прошёл, затем выполнен общий120.

| Окончательный вход | SHA-256 |
| --- | --- |
| `api/product_analytics_guard.py` | `4a20f7efbda819e774410b3907ac14c659d3e82b50dcf6b730ca506fd89c4509` |
| `unit/test_result_view_http_guard.py` | `d75d5de9d3f9a3e6ea88bcb99762eba017df2655780e2b2d6f1c88ed9048080b` |
| `contract/test_result_view_http_budget.py` | `f66bc3f55495befd5395daaca62a4e53353dc5b9f2330f0e095e3f3dc4d847a4` |
| `/private/tmp/graf-t112-close-full-20261116.log` | `218d264e3075911c275abf634acea7f91d2d24e03f480e96d0000afb0805023a` |
| Focused35 log | `4b5c0891e92ef1c7b886b26a5af853c1c2c3abfeefa8b4312c0f91e873b362e2` |

Ruff/diff-check/agent-context/changelog-fragments PASS. Требования и основные
checklists не менялись;124/0 — качество требований, не завершённая T112.
Независимое implementation review нового расширения ещё ожидается. Рабочий
сбор, PR/CI/merge/выпуск и весь объём раздела «Границы проверки» не приняты.
