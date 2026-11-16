# T112 — причинная проверка замены поколения до checkout

16.11.2026. Основа `3bb4f81cac072ead06f3498447d488d358a26d84`.
Существующая F273/T112, полоса high-risk-product. Runtime guard неизменён;
новый код только в существующем HTTP contract test и его relay. Рабочий сервер,
почта, настройки, контент и вёрстка не затрагивались.

## Допуск и исполненный опыт

Основной агент полностью прочитал независимый
[проект двух случаев](t112-pool-return-preflight-20261116.md) до тестового кода;
SHA-256 `8eaed6fc94364e5be9f1584a820ed7804600c16538a33c03342e3f98846c04f0`.
Reviewer подтвердил124/0 требований и применимость прежнего scoped analyze.
18 прежних входных хешей совпали, применимые целые оригинальные разделы
восстановлены в том же диалоге. Это не новый полный исторический reread.

Изолированный request pool3/pre_ping сохраняет FIFO/default reset/recycle.
Три одновременно выданных native соединения F/P/T прогреты настоящими SELECT1,
PID и commit. P/T возвращены в этом порядке; T подтверждён idle/noTX/no locks
и без request lease. Direct observer завершает только выделенный синтетический
P через pg_terminate_backend. Настоящий pre-ping даёт invalidate(P), новый P
удерживается вместе с F; прежний P relay закончен. Единственный свободный
старый slot — T.

Настоящий ASGI POST использует auth/tenant/CSRF/renewal и request sessionmaker.
Public Pool.close(T) подтверждает точные entry/DBAPI/native driver, in_use=False,
отсутствие Connection/init/root keys и новый auth Session root в owner.transactions
с exact task/Context, до нового T connect/checkout. Native close/terminate не
подменены, private timestamps/Pool.invalidate не используются.

Relay расширен необязательным stream lifecycle наблюдением, сохранив yield3 и
прежние callers. Каждый stream имеет собственный EOF gate/marker, root/pumps/
writers/wait_closed. Fault удерживает только EOF старого T; все данные, F и
новый P проходят. Независимый observer с пустым Context подтверждает upstream
EOF и исчезновение T backend/locks, пока request task ещё не отменена и новое
T поколение не создано. Watchdog3s служит только выходу из RED.

## Окончательный результат

**1 normal PASS / 1 fault FAIL / 27 deselected / 1 прежний fixture warning.**
Pytest5.96s, runner9s, terminal48609 EXIT1;
`postgres_test_cleanup=isolated_container_removed`.
Collection2/digest
`94da71d53e9473cfe32a83d93c8ffff40b2fb548d2f10789ddf616e602e7daf5`.

Normal: полный accepted около0.064s, committed renewal, ledger0. Старый T
socket/relay/root/pumps/wait_closed закончены до teardown. Новый T возвращён
idle/noTX/locks0 с живым driver; все три reset→checkin пар имеют
asyncio_safe=True/terminate_only=False/transaction_was_reset=False. Это
авторизация, проверка пространства и renewal, не три сетевых reset rollback.
Owner/Session root/задачи очищены. F и удержанный новый P в том же request pool
сохраняют exact PID/SELECT1 и commit в исходном2s; checkedout=2. После ранней
приёмки новый checkout/SELECT1/commit и нормальный return успешны.

Fault: нужная native graceful-close стадия доказана до отмены — exact reserved
T закрывается до checkout, upstream EOF удержан, backend/locks отсутствуют,
driver.is_closed=True, request/relay ещё pending. Около2.002s HTTPX ASGI
transport получает `response_complete` false (asgi.py:181). Watchdog не
сработал. Это новый причинный RED бюджета, не ошибка подключения/SQL/инициализации.
Поздние fault утверждения полного cleanup/освобождения root, сохранности F/P
при закрытом gate, ledger0 и reuse **не достигнуты**. Открытие gate в finally
и удаление контейнера не объявляются их PASS. Auth ещё не получил T; нового
аналитического commit нет, прежние seed/primer commits известны и не откатываются.

Первая попытка имела normal-ошибку тестового ожидания: посчитаны две return пары
вместо трёх. Исходный `_validate_tenant_scope` подтверждает третью Session.
Исправлено только точное ожидаемое число; повторены только эти два случая.
Первый журнал сохранён как история, итоговый baseline приведён выше.

| Вход | SHA-256 |
| --- | --- |
| Неизменный guard | `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14` |
| Итоговый contract test | `7b0c4bb447cc66aa828be731c1c61c64fde0e1b8fcecd9987d49f553a4139269` |
| `/private/tmp/graf-t112-pool-return-baseline-final-20261116.log` | `78a963b6003e48f426fd63bdbc593cde7bbb97cfaf2f31248c2400c15ddf907d` |
| Первая версия test | `e8807ecf83d9793c8caa66486ab2ab0ee645da3a24b5ed0f2c13819b5703d584` |
| `/private/tmp/graf-t112-pool-return-baseline-20261116.log` | `b3a98cc68c980ffc39ebfa65e2b4c3bb7e2306dd1d9d429b818e58a3e5844286` |

Перед стендом148223944KiB свободно, выше80ГБ; архивы и зависимости не копировались.
Ruff/diff check PASS. Оба runner закончили работу и удалили свои контейнеры.
Прежний233 не повторялся. Настоящий ledger handler по-прежнему не подключён.

## Следующая необходимая граница

Независимо проверить законченный baseline и новый тестовый diff; только после
этого отдельно принять минимальный проект runtime исправления. Этот документ
сам не является таким допуском. Приёмка замены до checkout, прочие close/TLS/
commit исходы, полные T112/T113/restore/runtime/T0, PR/CI/merge/выпуск,
рабочее измерение, трафик, регистрации и продажи остаются открытыми.
