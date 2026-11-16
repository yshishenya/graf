# T112 — проект причинных проверок медленного rollback при закрытии

16.11.2026. Независимый проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Проверенная основа: `41ff49078c30d02d8c6c626018ae1a3c0584e68f`.
Полоса: прежняя `high-risk-product`, F273/T112. Область поручения — последний
абзац `/private/tmp/graf-t112-http-review-request-20261116.txt`.

## Решение

**PASS проекта только новых изолированных причинных тестов, при обязательных
условиях ниже. P1=0, P2=0 в этой ограниченной области.** Можно добавлять
тесты в существующий contract файл и тестовый TCP relay. Runtime исправление
и передача владения close-задаче ещё не согласованы и этим отчётом не приняты.
Сначала нужен законченный причинный результат на неизменном guard, затем
отдельный проект минимального public ownership hand-off и его ревью.

Это уточнение проверки уже существующего общего бюджета и cleanup, без новых
данных, auth потока, фабрик, получателей или требований к продукту. Успешный85
профиль не повторён. Полные HTTP/T112/T113, collection/T0, release и runtime
остаются закрытыми до своих доказательств.

## Применимые исходные требования

Заново прочитаны актуальный result-visibility, связанные разделы
activation-milestones, T112 матрица quickstart, scoped analyze и предыдущий
независимый t112-precheckout-review. Остальной ранее прочитанный корпус не
перечитывался по разрешённому порядку F273.

Result-visibility §5 требует общий срок2s, отсутствие фоновой сессии после
бюджета, прежние auth/CSRF отказы и отсутствие retry неизвестного commit.
Activation-milestones сохраняет владение ресурсами и блокировками до
разрешения commit/rollback и закрытия DB при неизвестном исходе. Предыдущий
implementation review прямо оставил slow rollback/close открытым и не
распространил task ownership события создания транзакции на произвольную
передачу Session между задачами.

Git diff от предыдущего проверенного `5ed913c6292c143f7d8799b6902c5406f39097f7`
до текущей основы не содержит изменений spec/plan/tasks/quickstart, обоих
контрактов, основных checklist или analyze. Существующий analyze остаётся
проверкой проекта FR-021/025, SC-006, T112/T113, а не выполненных тестов.
Его историческая таблица хешей не выдаётся за новый анализ текущего кода.
Сейчас не требуется расширение области analyze: проверяется прежний cleanup
контракт. Если исправление меняет требования/владение/архитектуру, новый
проект и соответствующая проверка нужны до runtime кода.

Основные списки заново пересчитаны без изменения отметок:
requirements16/0, security27/0, privacy-measurement52/0, infra29/0;
**всего124 checked/0 unchecked**. Это качество требований, не приёмка кода.

## Проверенный порядок библиотеки и гипотеза

В SQLAlchemy2.0.51 `AsyncSession.__aexit__` создаёт новую asyncio task для
`self.close()` и ожидает её через shield. Close выполняет sync_session.close
через greenlet. Закрытие активной SessionTransaction вызывает закрытие её
connection transaction; `ConnectionEvents.rollback` возникает до public
dialect.do_rollback, который вызывает настоящий asyncpg rollback.
Конец SessionTransaction публикуется после закрытия её connection ресурсов.

Таким образом, task создания root transaction/checkout может уже ожидать
shielded close child. Её отмена сама по себе не доказывает отмену действующей
close task. Новый тест должен причинно подтвердить либо опровергнуть этот
конкретный пробел; результат заранее не объявляется RED или PASS.

Public EngineEvents.rollback подходит для включения сетевого сбоя в тесте:
он синхронен и возникает в задаче, исполняющей rollback. Разрешается лишь
`gate.clear()` и запись ограниченной тестовой metadata. Сам callback не
должен ждать, отменять задачу, закрывать/invalidating соединение, менять
параметры драйвера или подменять rollback/close. Продуктовый код остаётся
побайтно неизменным до причинного RED и отдельного согласования исправления.

## Обязательное точное попадание в нужную фазу

1. Отдельный request engine с pool_pre_ping=True прогревается до включения
   сбоя; setup/seed/прогрев/положительный auth не попадают в fault. Listener
   ставится только на этот engine, с явным одноразовым phase marker.
2. Gate закрывается только для ожидаемого request owner по identity и
   конкретного заранее полученного connection/DBAPI/driver поколения.
   Public Connection.info и публичные connection/driver свойства допустимы
   для тестовой metadata; private pool/Session/adapter API не нужны.
3. До выхода из нужного блока настоящим SELECT pg_backend_pid фиксируется
   целевой PID; SELECT синтетического AuthSession FOR UPDATE действительно
   выполнен в той же ещё активной транзакции. Независимый прямой observer
   до начала rollback подтверждает её xact и подходящие locks. Одного факта
   вызова SQL или наличия PID недостаточно. FOR UPDATE здесь является
   временной блокировкой тестовой строки, а не read-only транзакцией БД.
4. В rollback callback фиксируются точная task, owner, connection identities,
   phase и число срабатываний. Для __aexit__ случая task должна быть иной,
   чем task начала транзакции/checkout, но иметь тот же owner. Это явное
   доказательство перехода исполнения в shielded close, без stack/name
   эвристик. Несовпадение фазы или отсутствие callback означает fixture
   failure, а не доказанный продуктовый RED.
5. Не заменять настоящие AsyncSession, __aexit__, rollback, driver close или
   dialect.do_rollback. Для auth/renewal допустима узкая тестовая инъекция
   обычного исключения после штатного SQL и до commit. Штатный auth/tenant/
   CSRF путь и фабрика сессий сохраняются.

## Минимальная матрица

| Фаза | Причина выхода | Что необходимо доказать |
| --- | --- | --- |
| Локальная Session синтетического handler | Нормальный выход без commit после настоящего SQL/lock | Именно штатный __aexit__/close child дошёл до rollback и ждёт native сетевой ответ |
| Штатная auth Session | Обычное обрабатываемое исключение после настоящего SQL до commit | Cleanup auth выполняется в собственной close task; auth не подменён и renewal не является причиной сбоя |
| Штатная renewal Session | Обычное исключение после настоящего SQL до commit | Fault относится к post-response renewal cleanup; ранний buffered ответ ещё не опубликован |

Для каждой фазы нужен контроль без закрытия gate: обычный безопасный ответ
и полный cleanup, подтверждающие корректность test fixture. Классы исключений
выбираются из существующих безопасно обрабатываемых ошибок. Их конкретные
ожидаемые ответы фиксируются в тесте заранее. Контроль сохраняет auth/CSRF
отказы; общий fault нельзя выдавать за разрешение переписать их в accepted.
При fault ожидается закрытое unavailable и завершение менее2s, а не вечное
ожидание либо неполный ASGI ответ. Новых ledger строк/provider calls нет.

## Наблюдения до снятия сбоя и до fixture teardown

- Общий срок измеряется от начала HTTP запроса до законченного ответа и
  возврата guard, включая dependency teardown и post-response renewal.
  Проверяется unavailable, одно завершение ответа, отсутствие успеха из
  прежнего буфера и отсутствие request-owner задач.
- До gate.set/engine.dispose/закрытия relay writers проверяются штатный
  checkin целевого slot и отсутствие собственного checkedout. Удерживаемое
  заранее чужое соединение того же pool учитывается отдельно: checkedout1
  может быть только этим известным соседом.
- Прямой независимый observer проверяет целевой PID в pg_stat_activity и
  pg_locks, отсутствие активной/idle-in-transaction работы и locks. При
  необходимости короткая ограниченная повторная выборка допускается внутри
  явно отдельного observer бюджета; состояние на момент возврата guard и
  позднее состояние не смешиваются. Новые ожидания observer не продлевают2s.
- Лишь после этих проверок можно открыть gate для проверки чужого соединения:
  прежний PID/SELECT1 сохраняются; после его закрытия checkedout0, следующий
  обычный checkout/SELECT1 успешен. Установка gate влияет на relay трафик
  обоих соединений, поэтому ожидание foreign SELECT при закрытом gate нельзя
  ошибочно признать повреждением foreign connection.
- Трёхсекундный watchdog и finally fixture нужны для выхода из RED и очистки
  стенда. Успех обязан завершиться до2s и раньше watchdog. Результаты после
  watchdog/fixture teardown не подтверждают очистку приложения. Продуктовый
  failure сохраняется даже при успешной последующей очистке стенда.

## Что этот fault не доказывает

Relay задерживает server→client ответ, но пропускает клиентский ROLLBACK.
PostgreSQL мог уже выполнить rollback и освободить locks, пока close child
всё ещё ждёт ответ. Поэтому исчезновение locks отдельно не доказывает
завершение client cleanup. Предварительное подтверждение реальных locks и
последующие task/pool/checkin проверки обязательны вместе.

Такой сценарий проверяет native rollback как часть Session.close/__aexit__.
Он не является отдельным испытанием медленного raw driver.close/TLS teardown,
server-side rollback, который ещё не принят/выполнен, зависшего commit либо
всех initialization стадий. Эти границы сохраняются открытыми и не закрываются
общим названием «slow-close». Коммерческое измерение, T0 и рабочая готовность
не следуют из изолированного теста.

## Точные входы и действие проверяющего

| Вход относительно F273 | SHA-256 |
| --- | --- |
| contracts/result-visibility.md | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| contracts/activation-milestones.md | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| validation/t112-analyze-20261116.md | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| validation/t112-precheckout-review-20261116.md | `697d2cea105841f63eb6084cc4d43b5d892681aed6c9bd411a109b03281a14b2` |
| checklists/requirements.md | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| checklists/security.md | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| checklists/privacy-measurement.md | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| checklists/infra.md | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |

Прочитаны установленные SQLAlchemy ext/asyncio/session.py, engine/base.py и
engine/events.py, asyncpg dialect и connectors/asyncio.py в относящейся части.
Private исходники используются только для чтения порядка. Продуктовый runtime
к ним не обращается.

Проверяющий добавил только настоящий отчёт; код, requirements, планы, задачи,
checklist, Git/GitHub, runtime не изменял. Тесты/сборки/сетевые эксперименты
не выполнял. Отметки124/0 не переотмечались. Законченного нового RED/GREEN
на момент этого preflight нет; прежний85 результат не выдаётся за него.

## Дополнение: законченный baseline и проект передачи task ownership

Следующее поручение прочитано до runtime изменений. Независимо прочитаны весь
новый diff contract теста, законченный baseline журнал и фактический порядок
public Session.after_begin / Engine.before_cursor_execute / rollback / commit
в установленном SQLAlchemy2.0.51. Прежние разделы выше сохраняют историю
первого test-design preflight; состояние baseline теперь уточнено ниже.

**PASS минимального проекта передачи исполняющей task при условиях ниже;
P1=0, P2=0 в этой области проекта. Это ещё не implementation PASS.**
Допускается узкое изменение существующего guard с public событиями и
прежними registry. Новых фабрик, SQL, таймаутов, retry, AnyIO дерева или
изменений библиотек не требуется. Открытые границы прежней приёмки сохраняются.

### Подтверждённый RED

`/private/tmp/graf-t112-close-baseline-20261116.log` прочитан до конца:
3 passed controls / 3 failed network faults / 15 deselected / 1 прежний
fixture warning, pytest11.00s, runner14s, status=fail,
isolated_container_removed. Все три fault отказывают на HTTPX ASGI
`assert response_complete.is_set()`; продолжительность около2.09–2.10s.
Это реальный пробел законченного ответа к общему сроку, не отказ fixture.

В тесте перед выходом из Session настоящий SQL/FOR UPDATE и независимый
observer подтверждают целевой PID, idle-in-transaction и locks. Callback
точного Connection дополнительно проверяет DBAPI/driver/owner и отличие
исполняющей rollback task от исходной task. Guard остался побайтно прежним.
Три контроли прошли с ожидаемыми обычными ответами, включая auth503 и
сохранённый accepted при обрабатываемой ошибке renewal. Поэтому исходное
предположение о передаче выполнения в shielded close child подтверждено
причинно, без подмены rollback/close.

Ранняя попытка с неверным ожиданием checkin2 против1 не включается в этот
результат: после исправления одноразового фазового ожидания целевого entry
все три controls прошли, а три faults сохранились. Runtime исправление
не было причиной исправления fixture.

| Baseline вход | SHA-256 |
| --- | --- |
| Законченный baseline log | `501a0923fbb93deb6dc67313fe9d3f6adf585ba63ba5350d8950da0c4fda6813` |
| Неизменный guard | `1cd220b5c9b6a5936c01668c9d3312bdf1e052609e3744bd7fd480e41b6b76ee` |
| Contract тест с шестью случаями | `f64e6eef5e24154e84ec894bbd59f8901760f7ecdf2d0ee555ecae121c800e3c` |

### Допустимая связь root transaction с выданным соединением

Public Session.after_begin получает конкретные SessionTransaction и
Connection после получения соединения и создания его DB transaction, до
дальнейшего пользовательского SQL. Только transaction.parent=None, тот же
текущий owner и точная ранее tracked root связь Session.info/owner.transactions
могут установить association в Connection.info. Одного текущего ContextVar
недостаточно. Существующая противоречивая association не переписывается.
Nested SAVEPOINT/internal transaction не заменяет корневую association.

Connection.info — публичный словарь, который живёт вместе с DBAPI connection
и переживает возврат в pool. Поэтому association обязана быть привязана к
текущему connection lease/DBAPI/driver поколению; одного owner+transaction
в долговечном словаре недостаточно. Checkin и следующий checkout удаляют
прежнюю association до reuse, в том числе при owner=None. Снятие старой
SessionTransaction не должно стирать association нового поколения/транзакции.
Новый borrower никогда не получает task ownership старого request.

### Передача actual task перед работой соединения

Public before_cursor_execute, rollback и commit выполняются синхронно в
task, которая начинает конкретную SQL/transaction операцию. Rollback event
на рассмотренном __aexit__ пути возникает именно в shielded close child.
Поэтому эти callbacks могут передать исполняющую task без угадывания её
по stack/name/дереву AnyIO. Они не должны ждать, выполнять SQL, менять его
или самостоятельно завершать ресурс.

Перед любым изменением нужно проверить всё основание:

- есть current task и точный owner; current task context содержит этот owner;
- Connection не closed и не invalidated **до** чтения connection/info/proxy:
  public Connection.connection умеет revalidate/reconnect, поэтому чтение
  не должно случайно создавать новый ресурс в callback;
- proxy DBAPI/driver точно совпадают с текущим lease; найденный entry относится
  к собственному owner registry, а entry.info и owner[entry] содержат один и
  тот же lease по identity; entry занят и его текущее поколение совпадает;
- если присутствует root association, её owner/transaction/lease поколение
  и current owner.transactions подтверждены точно. Чужая, устаревшая либо
  противоречивая association запрещает **всю** передачу, а не только обновление
  root registry. Нельзя обновить connection task и оставить в root registry
  прежнюю parent task: при отмене обе снова попадут в набор cancellation;
- только после полной сверки синхронно, без await заменяются оба connection
  lease указателя и актуальная root task связь вместе с её association.
  Если association использует identity актуального root tuple, её tuple
  обновляется одновременно с owner.transactions, чтобы следующий callback
  не встретил искусственно устаревшую связь.

Для собственного Core Connection без root association допустимо обновление
только connection task при всех connection identity проверках; это не право
присваивать чужую или недоказанную Session. Отсутствие association не должно
толковаться как разрешение обойти найденную противоречивую root связь.
Пре-checkout/root registry по-прежнему сохраняет исходную task до after_begin;
новые Engine hooks не подменяют прежнее pre-ping доказательство.

Session.info может сохранить первоначальную root lease: при снятии важны
сохранённые owner и **та же transaction identity**, а не устаревшее поле task.
after_transaction_end удаляет текущую запись owner.transactions по точному
transaction, включая уже обновлённую task. Событие идёт после close ресурсов.
Nested end не снимает root; завершение в другом Context сохраняет cleanup.
Новая root transaction той же Session не наследует старую task association.

### Проверки после минимальной реализации

Нужны отрицательные unit случаи ownerNone/другая current task owner,
closed/invalidated Connection без попытки revalidate, другой DBAPI/driver,
in_use=False, чужой/устаревший entry lease, несовпадение owner registry,
foreign/stale/missing root registry и противоречивая association. При отказе
ни один registry не изменяется частично. Положительный hand-off меняет
connection и root task на одну actual task; прежняя parent task исчезает из
обоих актуальных cancellation источников. Повторный callback остаётся
согласованным. Nested begin/end, checkin/reuse, owner=None borrower, reconnect
с новым driver и новый root той же Session не наследуют старую association.

В причинной шестёрке до закрытия gate полезно явно проверить, что runtime
callback уже передал оба registry текущей rollback task, а не лишь тестовый
callback обнаружил её. Нужны завершённый unavailable<2s, штатный checkin,
отсутствие owner tasks и собственных leases, независимый observer, тот же
соседний PID/SELECT1 и следующий обычный checkout. Затем запускается общий
затронутый профиль с точными новыми source hashes/collection/cleanup receipt;
старый85 не повторяется без этого изменения и не выдаётся за новый GREEN.

Engine rollback/commit события не покрывают pool reset_on_return: для него
у SQLAlchemy отдельный public PoolEvents.reset. Этот проект не принимает
все reset/raw-close/init стадии, произвольный session handoff между owner,
внешне привязанную Session/multi-bind конкурентную работу или неизвестный
commit. Новая commit task metadata не доказывает rollback либо отсутствие
commit и не разрешает retry.

Для текущих штатных локальных Session и single-engine путей проект минимален:
использует уже проверенные identity registry и уточняет исполнителя там,
где public callback даёт конкретное соединение. После кода всё равно нужны
новый законченный GREEN и независимое implementation review; scoped
preflight не закрывает T112/T113, release, runtime/T0 или полный HTTP.

Проверяющий только дополнил этот отчёт. Новые тесты и их исходные файлы
прочитаны, сохранены без изменений; тесты не запускались. Checklists124/0,
requirements и analyze не переотмечены и не изменены.

## Дополнение: остаточная request metadata после отменённого close

Последнее поручение прочитано до следующего runtime изменения. Прочитаны
актуальные hand-off hooks, cancellation/join ветвь guard, соответствующие
assertions contract теста и законченный новый шестислучайный журнал.
Проверка этого дополнения ограничена проектом удаления request metadata;
это не полное implementation review уже добавленных hand-off hooks.

**PASS узкого проекта завершения собственной metadata после отмены при
условиях ниже; P1=0, P2=0 в этой проектной области.** Удаление разрешено
только после успешного join и подтверждённо пустого connection registry,
по точным identity lease. Оставшийся metadata mapping не является основанием
вызывать библиотечный close/rollback/commit повторно.

### Что теперь доказано и что пока не доказано

Прочитан `/private/tmp/graf-t112-close-first-green-20261116.log`:
3 controls PASS / 3 faults FAIL / 15 deselected / 1 fixture warning,
9.09s, runner13s, isolated_container_removed. Название файла не означает
полный GREEN. Во всех faults уже пройдены assertions законченного
unavailable<2s, checkedout1 известного foreign connection и одного штатного
целевого checkin. Отказ возникает на пустоте owner.transactions, когда
connection registry уже пуст. Длительности fault около1.59–1.60s.

Поздние проверки отсутствия tasks, Session.in_transaction и post-response
PG observer ещё не подтверждены этим журналом: исполнение до них не дошло.
Нельзя объявлять их PASS из одного checkin. Проверка до rollback по-прежнему
подтверждает настоящие transaction/locks; состояние после отмены проверяется
отдельно новым завершённым профилем.

В SQLAlchemy2.0.51 SessionTransaction.close сначала меняет текущую
Session transaction ссылку, затем закрывает connection transaction.
CancelledError внутри этого close может выйти до dispatch.after_transaction_end,
который не находится в finally. Поэтому отсутствие события конца не
противоречит уже закончившейся close task и checkin: callback удаления
request metadata мог просто не исполниться. Читать этот private порядок
для объяснения допустимо; менять его либо вызывать private API не нужно.

| Новый вход | SHA-256 |
| --- | --- |
| Законченный шестислучайный журнал | `349a4660e2602de8448eab6f15297aaf8ee2eaaa44def2f02fbd93cd7118d149` |
| Guard, прочитанный для этого preflight | `ac1e2c49a07f27a56231826bb6c9694d03c62e628dd4db9128466c656042bdb7` |
| Актуальный unit файл | `69ae2c5165e168d0efe4f046096df86e51c26a87fce5c9f7682b586aeac9e98b` |
| Актуальный contract файл | `354571520ac7a6c40944dabb29e06577858da90963cdf376540bcd881d5729ef` |

Таблица фиксирует прочитанные текущие исходники; это ещё не exact-source
квитанция общего нового успешного профиля. Такой профиль не запускался.

### Стабильные identity leases и bounded entry

Уточнения предыдущего проекта — изменяемые list leases со стабильной identity
и exact connection_record в пятом поле connection lease — допустимы как
минимальная внутренняя форма прежнего registry. Они не создают новый общий
реестр и устраняют необходимость сканировать pool. Root Session.info,
owner.transactions и connection association могут ссылаться на один lease;
после всех проверок меняется только task поле. Условия all-or-nothing,
generation checks и очистки association до reuse сохраняются.
Это согласование формы данных, не приёмка всей текущей реализации.

### Предусловия удаления собственной metadata

1. Только путь прерванного/ошибочного запроса после существующего `await join()`.
   Если join отменён, не окончен или оставил owner children, helper не должен
   исполняться из безусловного finally. Сохраняется исходный exception и
   закрытый результат; cleanup metadata не публикует success.
2. Owner connection registry пуст до начала удаления и остаётся пуст во время
   синхронного прохода без await. Иначе не удаляется никакая root metadata:
   её наличие ещё может быть нужным для активного ресурса и отмены.
3. Для каждой записи независимо проверяются lease[0] is owner,
   lease[1] is transaction, owner.transactions.get(transaction) is lease и
   публичное task.done(). Live task, неправильный owner/key/lease либо
   другое поколение mapping не очищается. Task должна быть ранее проверенным
   исполнителем этого request lease; произвольная done task не разрешает
   присваивать чужую транзакцию.
4. Доступ к Session выполняется через публичное именованное поле
   `SessionTransaction.session`. В установленной версии это типизированный
   Session атрибут объекта, выдаваемого public SessionEvents; чтение не
   выполняет SQL и не меняет состояние. Для этой узкой операции допустимо
   только прочитать его и собственный ключ Session.info, без обращения к
   `_transaction`, `_state`, `_connections` или их записи. Зависимость от
   версии сохраняет обязательную повторную проверку при обновлении SQLAlchemy.
5. Session.info ключ удаляется только если **его значение is тот же lease**.
   Если ключ отсутствует либо уже содержит другое поколение, его не трогать.
   Собственный старый owner.transactions mapping допустимо удалить отдельно
   по совпадению identity и done task: это удаляет старую request ссылку,
   не новое состояние Session. Новую Session.info связь/её owner registry
   при этом не изменять. Это различие явно отражается в отрицательных тестах.
6. Само удаление синхронно и ограничено оставшимися root leases данного owner.
   Нельзя очищать весь Session.info, чужие registry, pool или искать другие
   Session. Нельзя подавлять исходную ошибку ради PASS. Никаких новых задач,
   SQL, сетевого observer, close/rollback/commit/retry/dispose в helper нет.

Такое действие завершает срок жизни собственных ссылок запроса. Оно не
объявляет transaction.is_active=False, не переводит SessionTransaction в
закрытое состояние и не доказывает commit/rollback серверной БД. Свойства
Session/transaction продолжают отражать библиотечное состояние как есть.
Обычный успешный путь всё ещё использует after_transaction_end; остающийся
registry там по-прежнему вызывает закрытый отказ, а не принудительную чистку
перед accepted.

### Проверки после этого изменения

Unit проверки должны охватывать завершённый собственный lease, live task,
непустой connection registry, другой owner/transaction, заменённый mapping,
отсутствующий Session.info, Session.info нового поколения и повторный вызов.
При новом поколении чужая Session.info связь сохраняется, удаляется только
точный старый собственный mapping; при заменённом owner.transactions mapping
не удаляется ни он, ни принадлежащая ему metadata. Тесты проверяют отсутствие
изменений библиотечного transaction state и отсутствие вызова DB операций.

В контрактной шестёрке сохраняются реальные Session и transaction объекты.
После ответа и **до** gate.set/fixture teardown сначала проверяются
Session.in_transaction=False, законченный целевой checkin, отсутствие своих
checkout/tasks и независимые pg_stat_activity/pg_locks. Затем оценивается
metadata cleanup как отдельная квитанция. Речь о порядке проверки evidence
в тесте, а не о добавлении observer или await внутрь runtime helper.
Если реальные ресурсы или Session всё ещё активны, пустой registry не даёт
PASS и не заменяет исправление настоящего cleanup.

Нужен законченный новый шестислучайный GREEN и общий затронутый профиль с
source hashes, collection и isolated cleanup; затем независимое implementation
review. Текущие3 fault остаются RED. Никаких выводов об общем HTTP/T112/T113,
pool reset/raw close/init, неизвестном commit, runtime/T0 или выпуске нет.

Проверяющий дополнил только этот отчёт, текущий код/тесты других агентов
сохранены. Новых тестов/сборок/сервисных действий не выполнялось. Checklist
и требования не менялись и не переотмечались.
