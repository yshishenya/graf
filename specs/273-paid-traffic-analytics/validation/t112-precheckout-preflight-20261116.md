# T112 — независимый preflight владения до checkout

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
HEAD: `7ece19e783ff844319f2ab88b8d3e796f318de5f`.
Полоса: продолжение существующей `high-risk-product` F273/T112.
Поручение: последний раздел `/private/tmp/graf-t112-http-review-request-20261116.txt`.
Меняется только настоящий новый отчёт. Код, требования, задачи, списки,
Git/GitHub и runtime не менялись; тесты проверяющий не запускал.

## Решение

**PASS минимального проекта только для automatic cancellation во время
pre-ping уже зарезервированного entry: P1=0, P2=0 при условиях ниже.**
Дополнительный hook до каждого pre-ping не обязателен: синхронный public
invalidate callback может дать точное phase-specific основание для этого
одного прекращения соединения. Один ContextVar либо один in_use такого
основания не дают. Это не предварительное владение любым entry для будущих
операций и не PASS physical connect/initialization, native ping/network stall,
полного HTTP/T112/T113, runtime или T0.

Качество прежних требований и основных списков сохраняется124/0.
Применимые original result-visibility/activation-milestones и предыдущий
http-preflight восстановлены собственным чтением в этом же reviewer-диалоге;
новый проект не меняет субъекта, auth/CSRF, данные, получателей, бюджет или
договор хранения. Новый код исправления ещё отсутствует. Guard сохранил
принятый SHA-256 `c28b32cbfb4cbb5f204d19b8380c3e1beee7ebeedb56a1e6a4fad0fffaeab512`;
изменённый контрактный тест другого агента сохранён.

## Фактический порядок public API

Прочитаны установленные SQLAlchemy2.0.51 исходники pool/base.py,
pool/events.py, engine/events.py и asyncpg dialect; прежнее чтение
SQLAlchemy termination/asyncpg0.31.0 остаётся применимым.

Для reused connection с pool_pre_ping=True:

1. Pool уже выделил entry и DBAPI connection; создаётся proxied connection,
   так что публичный `ConnectionPoolEntry.in_use` возвращает True.
2. Pre-ping выполняется до `PoolEvents.checkout`.
3. Если текущая операция прерывается CancelledError, cleanup SQLAlchemy
   вызывает hard `ConnectionPoolEntry.invalidate` на том же entry, затем
   checkin. Callback invalidate исполняется синхронно на пути этой операции.
4. Public `PoolEvents.invalidate(dbapi_connection, connection_record, exception)`
   вызывается до последнего штатного close. В callback ещё доступны точные
   public dbapi_connection/driver_connection и in_use. После callback штатный
   код продолжает invalidation и возвращение slot в pool.
5. Public checkin происходит до возвращения entry для нового заёмщика.

Именно совокупность причинного вызова cancellation callback и текущих
идентичностей позволяет остановить собственный driver до долгого adapter
close. Нельзя переносить вывод на произвольный вызов invalidate с вручную
переданным CancelledError или на сканирование чужих entries. Private имена
библиотеки использованы при чтении порядка; продуктовый код к ним не обращается.
Решение привязано к проверенной версии; обновление библиотеки требует
повторной причинной проверки этого порядка.

## Минимальный допустимый путь pre-ping

В существующем invalidate listener сохранить уже принятый путь точного
checkout lease. Для отсутствующего lease добавить только узкую ветвь
подтверждённого automatic pre-checkout cancellation:

- есть текущий уникальный owner **по identity**, принадлежащий именно
  ограниченному result-viewed запросу, и выполняющая callback asyncio task
  входит в этот owner context; сама task ещё существует;
- exception — фактический CancelledError прерванной текущей операции;
  callback исполняется в её отменяемой task, а не в постороннем observer,
  GC, таймере или задаче другого запроса. Проверка текущего cancellation
  состояния task, например `task.cancelling()>0`, допустима как дополнительное
  ограничение; неизвестный/неподтверждённый случай не открывает этот fallback;
- public entry.in_use=True, entry.dbapi_connection **is** callback argument,
  underlying driver из этого argument **is** entry.driver_connection;
  driver — поддерживаемый public asyncpg Connection;
- у entry нет действующего lease другого owner/DBAPI/driver поколения.
  Чужую или противоречивую существующую связь не стирать и не «усыновлять»
  по одному текущему ContextVar. Старый закрытый/переиспользованный entry
  не является текущим pre-ping ресурсом;
- все проверки и public driver.terminate() выполняются синхронно без await.
  Между сверкой поколения и terminate нет возможности вернуть connection
  и передать его другому request. Не вызывать private adapter/pool API,
  engine.dispose, новый connect или raw SQL login;
- после terminate штатные SQLAlchemy invalidation/checkin завершаются.
  При необходимости можно сохранить временный lease **этой** callback task
  в прежнем owner registry до checkin; это не отдельный hook, writer или
  фабрика. Cleanup снимает только совпадающее поколение;
- текущий ASGI owner всё равно дожидается окончания task и поздних shielded
  tasks, используя прежний единый deadline. Мгновенный terminate transport
  не объявляется доказанным rollback/прекращением server commit.

Такой callback получает право на конкретную завершаемую связь в момент её
автоматической invalidation, а не право распоряжаться всем pool. При
невыполнении какого-либо условия нужно сохранить обычное SQLAlchemy
поведение и закрытый исход аналитики; общий cleanup PASS тогда не заявляется.

## Что нужно причинно доказать после реализации

1. Reused connection с production pool_pre_ping=True: auth и renewal входят
   в медленный ping до нового checkout event. При отмене сверяются все
   callback identities/in_use/current task; штатный bookkeeping завершается,
   response_complete установлен в пределах общего бюджета, нет хвостовых
   tasks/checkout. Положительный быстрый ping не вызывает terminate.
2. Independent observer настоящей изолированной PostgreSQL подтверждает
   отсутствие относящейся к случаю работы/транзакции/locks; следующий обычный
   запрос использует pool. Эти наблюдения дополняют, а не заменяют callback
   identity evidence.
3. Одновременно чужой запрос с иным Context продолжает работу. Отдельно
   reuse того же slot/driver и reconnect с новым driver: прежний owner не
   закрывает нового заёмщика. Передача произвольного чужого entry, in_use=False,
   чужого DBAPI/driver поколения, другого owner либо не-CancelledError не
   включает новый fallback.
4. Не ломаются принятые checked-out SQL cancellation/auth/CSRF/renewal,
   send deadline и остальные маршруты. При известном либо возможном commit
   нет слепого повтора; прежняя семантика unavailable сохраняется.
5. Случай native asyncpg ping либо контролируемого реального сетевого stall
   проверяется отдельно: в native adapter ping есть transaction start,
   fetchrow и finally rollback. Замена public dialect.do_ping запросом
   pg_sleep10 проверяет cancellation на том же pre-checkout этапе, но сама
   по себе не исполняет все эти native операции.

## Разделение нового RED и ошибки fixture

Прочитан завершённый `/private/tmp/graf-t112-preping-red-20261116.log`.
В auth case прерванный pre-checkout pg_sleep доходит до общего hard срока,
ASGI response_complete отсутствует, HTTPX получает assertion. Это реальный
новый RED закрытого ранее validation gap, а не опровержение scope прежнего67PASS.

Renewal case этого первого запуска имеет отдельную ошибку ожидания:
сохранено два предшествующих auth checkout, а тест ждал один. Это **не** второй
продуктовый RED. В текущем изменённом тесте ожидаемое число фиксируется snapshot
непосредственно перед renewal. Исправление fixture не считается исправлением
продукта; следующий законченный GREEN проверяется отдельно. Ни один профиль
проверяющий не запускал и terminal успех нового исправления не утверждает.

## Physical connect и initialization — отдельная граница

Pre-ping ветвь нельзя расширить снятием in_use check. При новом физическом
connect proxied lease ещё может не существовать, entry.in_use=False, а driver
до возврата DBAPI connect отсутствует. Предложенное cancellation inference
не доказывает владение на этих стадиях.

Public `DialectEvents.do_connect(dialect, conn_rec, cargs, cparams)` даёт
точный record до физического connect; public Pool.connect даёт точный новый
DBAPI после его создания. Для следующего отдельного проекта допустимо
рассмотреть request/task binding record на do_connect и дополнение точным
поколением DBAPI/driver в connect listener с проверенным порядком до dialect
init. Для init нужен именно доказанный insert-before-init порядок, включая
первое подключение engine. Один do_connect не даёт ещё отсутствующий driver,
один поздний Pool.connect не закрывает зависший physical connect. Изменение
параметров connect не должно переписывать credentials/роль/SSL/auth поток.
Новые factory, override connect с возвращаемым собственным соединением,
выключение pre-ping всем маршрутам или monkeypatch library internals этим
отчётом не разрешены и не требуются.

На эти стадии сейчас нет implementation/test evidence и их PASS не выдан.
Нужны отдельный минимальный public design и причинные real connect/init
cancellation тесты до расширения общей HTTP гарантии.

## Итоговая граница

Можно исправлять только выявленный automatic pre-ping cancellation путь с
точными public identities и обязательными отказами/конкурентными тестами.
T112/T113, physical connect/init/native network, slow-close и полный HTTP
остаются открытыми до своих доказательств. Рабочая готовность, запуск
аналитики, восстановление, T0, выпуск и трафик/продажи этим preflight
не подтверждаются. Предыдущие accepted отчёты не переписаны.

## Точные входы

| Вход | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-http-review-request-20261116.txt` | `37162e563fc237732a4162a86342c24bcbfc968bc55a12be0d907ec5612ea740` |
| `/private/tmp/graf-t112-preping-red-20261116.log` | `9ce7549ce09f5331f829480fe1c4c8f38827ed9f41e3032ec1c362119a3be440` |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `c28b32cbfb4cbb5f204d19b8380c3e1beee7ebeedb56a1e6a4fad0fffaeab512` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `b2ecec92cc14df62f750314bafc936c9f98671391e24374509fe12602489b977` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py` | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/pool/events.py` | `1666b612f525f177db9cf118b116266ab46dba66099a9153131c6f3b86e63a69` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/engine/events.py` | `d4c0098fe0f97711c18535d96276f163c015888b51b639be184c53ad737e9eb6` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py` | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |
