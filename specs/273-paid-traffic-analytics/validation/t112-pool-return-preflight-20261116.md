# T112 — независимый проект проверки возврата в пул и замены поколения

16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Точная основа: `b573c49e050bff010f95ce91a1fed674103f99aa`;
принятый runtime/test checkpoint: `37274e642820ef87ba52a6dd6e8cd8ed185fe595`.
Полоса: существующая `high-risk-product`, F273/T112, **TEST DESIGN ONLY**.
Поручение: `/private/tmp/graf-t112-pool-return-review-request-20261116.txt`.

## Фактические находки и решение

**Проект: PASS для двух новых причинных случаев normal/fault ниже.**
**Приёмка ещё не проверенного пути: HOLD до baseline и независимого разбора.**
Новых runtime-дефектов по одному чтению исходников не установлено: P1=0.
P2=1 — пробел доказательства бюджета при замене старого поколения *до*
выдачи соединения запросу. Это находка о покрытии, не доказанный дефект продукта
и не заранее предписанное исправление. В уточнённом проекте остающихся
блокирующих недостатков проекта P1=0/P2=0. Тесты не запускались.

1. Обычный `AsyncConnection.close()` возвращает соединение в пул. После
   успешного commit нормальны живой native socket и backend `idle` без
   транзакции. Их сохранение нельзя объявлять утечкой. `Connection.closed`
   относится к отпущенному объекту Connection, а не к физическому сокету.
2. У реальных auth/renewal/account callers используются `AsyncSession`,
   commit и штатный выход. При незакрытой транзакции Connection.close делает
   rollback; принятое Session.close normal/fault уже проверяет этот сетевой
   rollback и передачу владения shielded child, включая Session root.
3. Возрастной `pool_recycle` в фабрике GRAF **не включён**: передаётся только
   `pool_pre_ping=True`, библиотечное значение recycle равно -1. Однако замена
   старого поколения остаётся достижима: реальный disconnect/pre-ping отказ
   инвалидирует поколение пула, а следующий checkout другого старого idle
   entry закрывает его и подключается заново. Нельзя исключать этот путь
   только из-за отсутствия настройки возраста.
4. Такая замена выполняется в `ConnectionPoolEntry.get_connection()` *до*
   создания checkout proxy: `entry.in_use=False`, нового request lease нет,
   Pool.checkout ещё не наступил. Это отличается от принятого pre-ping с
   созданным proxy, от холодной инициализации I1 и от C1 hard invalidate(None)
   с точным уже выданным lease. C1 не заменяет проверку этого пути.
5. После успешного commit адаптер asyncpg уже сбросил собственное состояние
   транзакции. Обычный default rollback-on-return в этой фазе не выполняет
   нового сетевого rollback. Fault на Pool.reset здесь не задерживает
   реальный native SQL. Искусственная native-транзакция, собственный reset
   SQL или изменение `pool_reset_on_return` создали бы другой сценарий.

Изменять runtime по этому отчёту нельзя. Сначала реализуется только уточнённый
тест/наблюдение в существующем contract-файле, затем снимается baseline.
Ни успех, ни RED заранее не предполагаются. Принятый профиль233 не повторять
на основании одного этого проекта.

## Восстановленные требования и область прежних ворот

Применён разрешённый владельцем порядок восстановления F273 в том же диалоге.
Происхождение собственного scoped чтения — прежние requirements/http/close/
init/driver-close preflight отчёты; текущее поручение и оригиналы сверены.
Полное новое чтение всей истории PRD/status здесь не заявляется. Карта
`/private/tmp/graf-t112-pool-return-reading-20261116.json` принадлежит основному
исполнителю и использована только как указатель; она не подменяет собственное
чтение. Её старое поле `guard_sha256=b22a…` не принято за текущий исходник:
актуальный guard отдельно проверен и имеет `eda3…` ниже.

Применимая карта исходных требований:

- `result-visibility.md` §§1–7, особенно §5: общий исходный HTTP-бюджет2s,
  lock≤250ms/statement≤500ms, прежние auth/CSRF/renewal, отсутствие пережившей
  бюджет DB-задачи и автоматического повтора неизвестного commit; §7 требует
  причинной проверки и независимого ревью.
- `spec.md`: clarify16.11, FR-021/025, SC-006; `plan.md`: продолжение
  T112/T113 и весь проект T112; `tasks.md`: T112/T113 и уточнение16.11;
  `quickstart.md`: T112. Это продолжение той же задачи и тех же целей.
- `activation-milestones.md`: browser/manual ветвь не доказывает capture или
  нового внешнего клиента; ledger, lifecycle/restore и закрытое включение
  T113 остаются отдельными. Синтетический HTTP accepted не доказывает ledger.
- Конституция III/IV/VI, Product/Platform, Workflow/Governance; PRD14/23/25/31;
  текущая шапка/непринятые границы status; guidance index,
  `document-reading.md`, `spec-kit-flow.md`, `product-gates.md`: scoped
  независимое ревью, сохранность данных, синтетическое metadata-only evidence,
  неизменные внешние разрешения и отсутствие обхода выпуска.
- Прежний scoped `t112-analyze-20261116.md` применим к неизменённому проекту
  требований: CRITICAL/HIGH/MEDIUM=0. Это не повторный analyze всей F273 и не
  доказательство реализации нового случая.

Контроль четырёх неизменённых reviewer-owned списков: requirements16/0,
security27/0, privacy-measurement52/0, infra29/0; всего **124 checked / 0
unchecked**. Отметки не менялись. Сохраняется прежняя приёмка требований;
пересчёт/совпадение хешей не являются новой приёмкой runtime или всех T112/T113.

## Сопоставление вызывающего кода и библиотечных фаз

| Путь | Проверенный порядок | Что нужно добавить |
| --- | --- | --- |
| `db/session.py:create_engine` | `create_async_engine(..., pool_pre_ping=True)`, default rollback reset, age recycle disabled | Не вводить production-настройки ради опыта |
| `auth/dependencies.py:_principal_from_session_token`, `auth/session_renewal.py` | `async with sessionmaker()`, реальный SQL, commit, штатный выход | В новом normal наблюдать обычные reset/checkin после commit |
| `product_analytics/ingest.py:_account_transaction` | Ограниченный Session context, locks/read, свежая проверка, commit | Настоящий gate не открывать; прежняя T113 отдельно |
| `AsyncConnection.close`, `Connection.close` | Прямой await идёт через greenlet в текущей задаче; `__aexit__` создаёт shielded close child; active Connection TX сначала rollback | Нет отдельного raw caller в исследованном HTTP-коде; не размножать полную auth/renewal матрицу |
| Pool return/reset | Public reset до default reset; `transaction_was_reset=True` пропускает повторный rollback; после commit flag может быть False, но adapter rollback уже no-op | Проверить штатный return в normal; не придумывать reset-only сетевой fault |
| Generation recycle | Получить свободный entry → закрыть старый driver → подключить новый → создать proxy → pre-ping/checkout | Новые normal/fault, реальная auth-фаза, warm dialect |

Выполнен поиск явных `.invalidate`, `soft=True`, `detach`, `pool_recycle`,
`pool_reset_on_return`, `pool_reset` в `apps/server/src`. Найденные явные
invalidate относятся к billing reconciliation/CLI, не этому аналитическому
HTTP. Soft invalidation/detach/custom reset не найдены в проверенной области.
Возрастной recycle, overflow-discard, engine.dispose и GC не выдаются за
проверенные пути HTTP. Dispose выполняется после исходного запроса; новый
набор для этих библиотечных режимов без продуктового caller не нужен.

Проверены установленные SQLAlchemy2.0.51 / asyncpg0.31.0:
`ext/asyncio/engine.py:476,895`; `engine/base.py:1220–1270`;
`pool/base.py:708–747,820–865,880–909,970–1045,1265–1378,1403–1450`;
`connectors/asyncio.py:397–425`; `dialects/postgresql/asyncpg.py:870–930`.
Recycle вызывает close с terminate=True, который в greenlet может сначала
ожидать shielded native close(timeout=2). Public Pool.close — событие *до*
driver close, не доказательство завершения. Public driver.is_closed также не
заменяет завершение сокета. Реакцию на отмену доказывает опыт, не предположение.

## Минимальная причинная матрица

Два случая одной новой проверки, один существующий native HTTP alias,
реальные auth/tenant/renewal. Нет новой матрицы всех aliases/CSRF: она принята
отдельно. Normal заодно наблюдает штатный возврат после commit.

| Случай | Фаза и fault | Ответ и ресурсы |
| --- | --- | --- |
| R0 normal | Реальный auth checkout старого idle entry после настоящей pre-ping generation invalidation; EOF пропускается | Полный accepted<2s, committed renewal сохранён. Старое поколение закрыто, новое после commit вернулось idle без TX/locks. Живой pooled socket допустим |
| R1 fault | Та же фаза; удержан только EOF старого целевого stream после отправки native Terminate, data открыт | Полный unavailable<2s при доказанном удержании стадии до отмены. До открытия gate закончены own tasks/старое закрытие/checkin и очищен Session root. Если стадия реально завершилась раньше, исход не является доказанным R1 |

В R1 неизвестного аналитического commit нет: auth ещё не получил целевое
соединение и не начал SQL через него. Более ранние seed/primer commits известны
и не откатываются ответом unavailable. Новых application/SQL retries нет.
Нормальное библиотечное восстановление connection после pre-ping disconnect
используется только для подготовки поколения; это не повтор admission.

## Подготовка реального поколения без private API

Изолированные PostgreSQL/engine/данные; production не затрагивается.
Request engine: `pool_size=3`, `max_overflow=0`, `pool_pre_ping=True`, обычный
FIFO по умолчанию, без recycle/reset-настроек. Это ёмкость теста, не настройка
продукта. Direct seed/observer engine независим от relay и имеет достаточную
ёмкость; один observer handle заранее открыт и отпущен после проверок.

1. Прогреть три одновременно удерживаемых соединения F, P, T. Через public
   checkout/connect сохранить exact entry, DBAPI wrapper/native driver,
   `pg_backend_pid()` и точный relay stream каждого. Получить PID, закончить
   seed transaction явным commit. F остаётся удержанным чужим соединением.
2. Вернуть сначала P, потом T. Через public reset/checkin и независимый
   pg_stat_activity доказать, что T checked-in, idle/noTX/no locks,
   `entry.in_use=False`, у entry нет request/init/root keys. Dialect уже warm.
3. Независимым direct SQL один раз выполнить `pg_terminate_backend(:pid)`
   **только для выделенного синтетического P**, подтвердить его исчезновение.
   Если тестовая роль не может завершить собственный P, это ошибка подготовки,
   не PASS и не runtime RED. Не вызывать private Pool._invalidate и не менять
   часы/внутренние timestamps. Не использовать soft=True как замену caller.
4. Обычным checkout взять P: настоящий pre-ping обнаружит disconnect,
   опубликует invalidate старого P и подключит новое поколение. Public trace
   должен подтвердить эту причину. Новое P удержать до окончания опыта;
   подтвердить, что старый P stream со всеми pumps/wait_closed закончен.
   Тогда единственный свободный slot — старый T. F и новое P удерживаются;
   нормальное исходное `pool.checkedout()` равно2.
5. Запустить существующий полный ASGI POST через request sessionmaker.
   Public Pool.close для **exact старого T** должен возникнуть перед любым
   новым T checkout/connect. В callback зафиксировать current owner/task,
   `entry.in_use=False`, совпадение старых entry/wrapper/driver/PID,
   отсутствие нового connection/init lease и Connection/root association
   в entry.info. Auth Session root в owner.transactions уже может/должен
   существовать из autobegin; проверить его exact task и отсутствие ещё
   выданного Connection. Не путать этот root с уже привязанным DB lease.

Непопадание в эту стадию, иной свободный slot, старый живой P relay, не warm
dialect или недоказанная generation invalidation — ошибка причинности стенда,
не продуктовый результат R1. Нельзя менять private state, чтобы скрыть её.

## Адресный EOF gate и наблюдения

Достаточно узко расширить существующий test relay необязательным наблюдением
stream lifecycle: accepted stream ID, root/pumps/writers/wait_closed и EOF
markers. Pairing с T делается при последовательном прогреве: один новый
connect → один новый accepted stream → public checkout/SELECT PID. Никакой
разбор PostgreSQL-пакетов и native driver monkeypatch не нужны.

В R1 **только** целевой T stream задерживает server→client `read()==b''`.
В public Pool.close(T) закрывается его одноразовый EOF gate. Все непустые
данные и другие streams пропускаются; auth setup, SELECT/commit, pre-ping
primer, F и новое P не задерживаются. Это позволит проверить F ещё до
снятия fault. Существующий общий data gate остаётся открыт.

Глобальный EOF gate без target identification допустим лишь при доказанном
единственном закрываемом stream; при трёх живых pooled streams предпочтительна
явная адресация T. Нельзя просто исключить весь relay_tasks набор из проверки
утечек и назвать целевое закрытие законченным.

Независимый observer в пустом Context, через заранее готовый direct handle,
после marker T.close подтверждает: T upstream EOF увиден и удержан; старый
T backend уже исчез/его locks отсутствуют, в этот момент task запроса ещё
не отменена. Это отделяет ожидание native close от SQL/rollback/connect/
инициализации. Public is_closed — только дополнительное наблюдение.
FIRST_COMPLETED relay сохраняется: если client→server реально завершается,
finally вправе закончить второй pump и закрыть оба writer до gate.set.
Это корректный cleanup, его нельзя блокировать для получения желаемого RED.

## Приёмка до снятия fault и teardown

Один абсолютный deadline: время начала полного POST+2s. Все проверки раннего
cleanup, в том числе observer, выполняются в остатке **этого** срока, без
нового самостоятельного двухсекундного ожидания после HTTP. Observer можно
подготовить/запустить заранее и синхронизировать событиями; его задачи
учитываются отдельно и тоже завершаются. Время fixture teardown не доказательство.

- Полный ASGI response завершён, не только headers/route return; в R0 сохранён
  настоящий committed renewal, в R1 закрытый ответ. Нет нового ledger/provider
  вызова; настоящий gate не включается. Неизвестные числа не подменяются нулём.
- Exact owner больше не владеет entry/transaction; owner.transactions пуст,
  Session root закончен и его ключ убран. Нет незавершённых задач с exact
  owner Context, в том числе shielded native close/Session.close children.
  Root-free/raw cleanup не выдаётся за проверку реального auth root.
- Пул до отпускания F/P имеет checkedout=2, точный T reservation возвращён.
  Одно pool.checkedout без task/lease/backend/socket доказательств недостаточно.
- **R0:** старый T backend/relay/writers завершены; новый T checked-in idle,
  xact_start=NULL, locks=0, driver жив. Public reset→checkin относится к exact
  новой generation; для commit-return ожидаются asyncio_safe=True,
  terminate_only=False, transaction_was_reset=False. Это не сетевой rollback;
  не требовать исчезновения нового idle backend/relay.
- **R1:** старый T backend отсутствует, locks=0; его relay root, оба pump и
  оба wait_closed закончены, writers закрыты до gate.set/dispose. Для
  отменённого checkout новое T поколение в этом запросе не требуется.
- F остаётся удержанным в **том же request pool**, имеет прежний exact PID,
  SELECT1 работает и завершается commit **при ещё закрытом T EOF gate**.
  Проверяется и сохранность удержанного primer P. Их нормальные живые sockets
  и relay tasks не относятся к own leaked work. Не использовать для этого
  лишь foreign connection другого direct engine.

После ранних доказательств открыть fault gate, выполнить новый checkout на
единственном доступном T slot, SELECT1 и commit/return. R0 вправе повторно
использовать новый живой PID; R1 должен дать работоспособное поколение, отличное
от уже закрытого старого T. Не требовать в R1 *ещё одной* замены, если новое
поколение уже было корректно создано до проверки. Затем отпустить F/P и
dispose. F был старым поколением во время pool invalidation: его PID обязан
сохраниться **пока он удержан**, но после его checkin следующий checkout
вправе штатно заменить поколение. Поздняя работоспособность не заменяет
раннюю проверку прекращения request work.

Watchdog3s разрешён только для выхода из RED и учитывается отдельным флагом;
он не может превратить результат после2s в PASS. В finally открыть все gates,
закончить observer/relay задачи, закрыть удержанные handles/dispose engine и
удалить изолированный стенд штатно. Ошибка утверждения до finally сохраняется.

## Что этим проектом сознательно не закрывается

Новый raw `AsyncConnection.close` active-TX normal/fault без Session root не
требуется для принятия исследованных реальных HTTP callers: такого отдельного
caller здесь нет, native rollback path и shielded ownership handoff приняты
Session.close опытами, а no-root ветвь handoff проверена unit `raw`. Это не
объявляется отдельным native raw-close HTTP доказательством. При добавлении
такого caller нужен собственный узкий normal/fault context-exit опыт с
Engine.rollback, exact no-root lease и теми же ранними ресурсными условиями;
повторять все aliases/Session фазы не нужно.

Возрастная замена, нестандартный reset SQL, detach/overflow/GC/dispose внутри
запроса и иной dialect остаются вне доказанного объёма. Не меняются принятые
I1/C1/Session.close/pre-ping результаты. Новая работа не закрывает T112/T113,
настоящий ledger/browser/native/restore/runtime/T0, выпуск и трафик/продажи.
До реализации runtime при RED нужен отдельный причинный разбор и независимый
проект исправления; никаких новых cleanup hooks «на всякий случай».

## Точные суммы входов

| Вход | SHA-256 |
| --- | --- |
| Guard | `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14` |
| Unit guard | `7dbb443ab4f8ea2dc9211b98b742b5f7db778c4c6823f2285b52a3f3aa26aa57` |
| HTTP contract | `179ab88cf95fdd02f2a53be0cd22c9d0c474ac8b62376f8893db1219041e9932` |
| db/session.py | `a01c5ab2a45888fedc387dc6656defc92512707e3a485c1c5e2c8f83e616a529` |
| auth/dependencies.py | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| auth/session_renewal.py | `0fea864d2aeb6028666e9ba8befe5c351871f5fd095328d7bc8e3b36beb81fd1` |
| product_analytics/ingest.py | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |
| result-visibility.md | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| activation-milestones.md | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| spec.md | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| plan.md | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| tasks.md | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| quickstart.md | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| scoped analyze | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| Accepted C1 report | `fe303b41d68c2a65369d8f1635259b9d5d5e13df45d68d688a8cc1e34132acbf` |
| requirements checklist | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| security checklist | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| privacy-measurement checklist | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| infra checklist | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| Constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| Status | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| document-reading | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec-kit-flow | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |

Установленные library sources (корень `site-packages` существующей server venv):

| Путь | SHA-256 |
| --- | --- |
| sqlalchemy/ext/asyncio/engine.py | `d7db66ce683ee95c30982103c7c9f2c27ccff6a53ee630e31d334c3af4e22528` |
| sqlalchemy/engine/base.py | `53f38e544004d329ac38e243104bf4bbbaf7d0f0cecabd112b1923b78dde5614` |
| sqlalchemy/pool/base.py | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
| sqlalchemy/pool/impl.py | `ed1388cb028150edad2a85542d99808f819d1e7e8033bb19bf60e22ecbbb320a` |
| sqlalchemy/connectors/asyncio.py | `44d173217bfaf38174149b84d396bed502bf769a98ad41f022269408edf69f9b` |
| sqlalchemy/dialects/postgresql/asyncpg.py | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |
| asyncpg/connection.py | `e9abd5c153bc70cfadb61215f11140e90741c2fed5929e574b6548ef8092b48c` |
| asyncpg/protocol/protocol.pyx | `962e254213b73deba572f4b2ebf1a2e0f240529dc61c4f5efa7aa1eb1b50f905` |

Изменён только настоящий отчёт. Код, тесты, требования, список задач, checklist
отметки, Git/GitHub и рабочая среда не изменялись. Это проект эксперимента,
не отчёт об успешном эксперименте и не разрешение публиковать сообщения до
ранее согласованной приёмки измерения.

## Дополнение — независимая приёмка baseline, checkpoint c420927

16.11.2026. Новое отдельное поручение:
`/private/tmp/graf-t112-pool-return-baseline-review-20261116.txt`, SHA-256
`e8b3f7ef1cb703cdc27013d544ac81fa856c911e6de6ad3e317df6eb324406f4`.
Проверена основа `c420927a7633596ca392799b61e46022ae7234d2` и фактический
test diff от `3bb4f81cac072ead06f3498447d488d358a26d84`. Guard неизменён.
До дополнения настоящий отчёт имел исходный SHA-256 `8eaed6fc94364e5be9f1584a820ed7804600c16538a33c03342e3f98846c04f0`.
Повторных тестов, сетевых опытов и изменений runtime не выполнялось.

**Причинный baseline: ACCEPTED RED. P1=1, P2=0 в проверенном объёме.**
P1-R1: полный HTTP-ответ не завершается за исходные2s при задержанном EOF
штатной замены старого поколения до checkout. Прежний P2-пробел доказательства
получил наблюдаемый отрицательный результат; это не два разных дефекта.
Исправление normal-ожидания с двух на три reset/checkin пары обосновано
реальным дополнительным Session в `_validate_tenant_scope` и не ослабляет
проверку fault. В принятом окончательном опыте отдельного дефекта теста P2
не найдено. Локальный READ/DIFF подтверждает соответствие принятому проекту.

Независимо проверены исходник нового теста/relay, окончательный журнал и
`t112-pool-return-validation-20261116.md`, SHA-256
`27105f1fff9780f8c1af87a0038a4f5ac3d6ec67a7476f765339dda449e5ad7d`.
Журнал `/private/tmp/graf-t112-pool-return-baseline-final-20261116.log`, SHA-256
`78a963b6003e48f426fd63bdbc593cde7bbb97cfaf2f31248c2400c15ddf907d`:
1PASS/1FAIL/27deselected/один прежний fixture warning; pytest5.96s,
runner9s, завершённый EXIT1, `isolated_container_removed`.
Collection2/digest `94da71d53e9473cfe32a83d93c8ffff40b2fb548d2f10789ddf616e602e7daf5`.

Почему RED принят как причинный:

- Физическое прекращение P через собственный синтетический PID, реальный
  pre-ping invalidate и новое P, законченный старый P relay, F/P удержаны,
  единственный свободный старый T. Нет подмены native методов, private pool
  state, timestamps или production-настроек.
- T.close callback проверяет exact entry/wrapper/native generation, текущие
  owner/task/Context, auth Session root и отсутствие entry lease/association,
  `in_use=False`, driver open/noTX. Fault адресует EOF только этого stream.
- Empty-Context observer действительно дошёл до наблюдения: upstream EOF,
  старый backend и locks отсутствуют, target task ещё не отменена,
  нового T поколения нет. Это подтверждается пройденными утверждениями перед
  `target["observed"]=True` и итоговой диагностикой `backend_gone_before_cancel=True`.
- Normal завершил ответ около0.064s и прошёл ранние owner/root/pool/socket,
  idle нового T, три reset/checkin, committed renewal, ledger0, сохранность
  F/P при исходном сроке и последующий checkout.
- Fault завершил вызов ASGI без полного ответа около2.002s;
  HTTPX `asgi.py:181` получил `response_complete=False`. Это не просто
  превышение2s из-за измерительного округления: полного ответа вообще нет.
  Watchdog3s не сработал. Журнал показывает отмену в настоящем
  `AsyncAdapt_terminate.terminate → shield(_terminate_graceful_close)`.

Из RED **не** выводится, какой exact child/lease оставался в момент2s:
отдельного снимка этих структур при падении нет. Утверждения fault о root,
F/P, pool return, ledger0 и следующем checkout не достигнуты. Открытие gates
и освобождение fixture не доказывают их раннюю приёмку. Нет нового
аналитического commit в этой фазе; повтор записи не нужен и не разрешается.

18 неизменённых входов требований повторно сверены с картой чтения:
расхождений нет. requirements16/0 + security27/0 + privacy52/0 + infra29/0
=124/0; отметки не менялись. Прежний scoped analyze остаётся применим к
неизменённым требованиям, но не объявляется приёмкой исправления.

## Отдельный runtime DESIGN — предупреждение ожидания выбранного idle close

**DESIGN PASS с обязательными ограничениями ниже; P1=0/P2=0 проекта.**
Это разрешённый узкий проект для дальнейшей реализации/проверки, не готовый
код и не доказанный GREEN. Устранённым P1-R1 станет только после проверки
точной новой версии. Новых продуктовых требований/настроек для описанного
предупреждения ожидания не нужно: SQLAlchemy уже решил закрыть физическое
соединение, а незавершённая транзакция и чужое владение исключаются.

Минимальная точка — отдельный короткий public `Pool.close` callback в
существующем guard. До вызова библиотечного native graceful close он вправе
вызвать публичный `asyncpg.Connection.terminate()` **только** для указанного
самим Pool.close, уже предназначенного к закрытию, idle поколения при всех
следующих доказанных условиях одновременно:

1. Есть exact current request owner; current task существует, имеет тот же
   owner в своём Context и ещё не отменяется. Owner не содержит connection
   leases и не находится в failed-состоянии. Это предупреждение ожидания,
   не новый обработчик поздней отмены.
2. Exact callback entry имеет `in_use=False`; его текущий dbapi_connection
   тождественен аргументу callback; текущий driver_connection тождественен
   `dbapi_connection.driver_connection`, имеет проверенный тип AsyncpgConnection.
   Нельзя получать соединение заново, делать checkout или читать private pool
   queue/generation timestamps. Любое расхождение identity означает no-op.
3. В entry.info отсутствуют все прежние connection/init/root guard keys;
   entry не фигурирует ни в одном lease текущего owner. `owner` пустота также
   исключает другое инициализируемое/выданное соединение этого же запроса.
4. У owner ровно один действующий Session root: exact прежний список
   `[owner, transaction, current_task]`, тождественен записи transactions;
   transaction.parent=None, transaction.session находится в этой транзакции,
   public session.get_transaction() возвращает её, transaction.is_active=True,
   session.info хранит exact root. Нет Session root handoff к другой задаче,
   чужой/законченной/вложенной/множественной транзакции.
5. Только после identity/root проверок публичные driver.is_closed() и
   driver.is_in_transaction() подтверждают ещё открытый native driver без TX.
   Already-closing/closed и active TX не обрабатываются этим проектом.

**О резервировании и границе полномочий.** `!in_use` не доказывает владение
запроса резервом и само по себе никогда не разрешает terminate. Public
Pool.close не сообщает reason/recycle и не предоставляет отдельный признак
«этот entry уже вынут из очереди именно этим Session». В baseline резерв T
доказан полной последовательностью стенда. В runtime нельзя выдумывать такой
признак или создавать request lease задним числом.

В проекте разрешение на прекращение exact idle generation даёт **сам
синхронный public Pool.close: пул уже выбрал это конкретное соединение для
физического закрытия до driver-вызова**. Current owner/root доказывают
ограниченный контекст ожидания; identity + отсутствие любого lease/init/root
на entry + noTX исключают вмешательство в работающий ресурс. Это не
утверждение, что старая connection принадлежала данному account/request.
Callback корректно именовать bounded idle pool close, а не proof of checkout
reservation. Он не должен перечислять/закрывать остальные entries в пуле.

Public событие не различает recycle и иные уже выбранные пулом idle closes.
Если иной close намеренно выполняется в таком же ограниченном контексте при
тех же строгих условиях, действие по смыслу такое же: сокет уже выбран для
закрытия, незавершённой транзакции и чужого lease нет. Это явная граница
проекта, а не скрытое предположение о reserve bit. **Вариант, требующий
исключительно recycle-specific reservation ownership, на одном public
Pool.close — HOLD:** публичного доказательства причины нет; нельзя заменять
его чтением `entry._ConnectionRecord__pool` или других private полей.

После terminate библиотечный путь продолжается штатно: Pool.close callback
возвращает управление, SQLAlchemy сам выполняет dialect close/terminate,
обнуляет старый dbapi, подключает новое поколение и проводит checkout/
checkin. Прямых изменений entry/dbapi/owner/root registry нет; новый task,
таймер, retry, callback admission или production-флаг не добавляются.
Callback не бросает собственных исключений и не меняет owner.failed при
отклонении чужого случая; ошибки библиотек остаются в существующем guard.

Проверенный asyncpg public `terminate()` не ждёт pending data. Затем native
close видит закрытое соединение и не начинает protocol-close ожидание.
Это **предупреждение** задержки до начала graceful close, а не доказательство
отмены уже зависшего graceful-close child. Последний вариант отдельной
работой здесь не принимается. Нет утверждения rollback неизвестного commit.

Существующие C1 None, CancelledError/pre-ping, I1 initialization cleanup,
Session root handoff и DB-first cancellation менять не требуется. Новый
callback обязан исключить их entry/lease/initialization состояния условиями
выше. Нельзя расширять прежнюю ветвь invalidate снятием проверки in_use и
объявлять этим доказанным владение старым резервом.

## Доказательства после будущей реализации

Сначала узкие unit-проверки самого решения (не подмена native API в DB опыте):
один точный допустимый случай; no-owner/wrong-Context/cancelling; непустой
owner/failed; in-use; другой wrapper/driver/тип; каждый connection/init/root
key; отсутствующий/чужой/множественный/stale/ended/nested root, другая task
или Session.info; active TX/already closed. Во всех отказах native terminate
не вызывается, bookkeeping/чужие объекты не меняются. Проверки driver не
читаются до подтверждения identity. Успех действует только на exact driver.

Сохранить baseline test/log/SHA неизменяемыми историческими доказательствами.
GREEN normal/fault использует тот же реальный pre-ping/поколения/синтетические
F/P/T и адресный EOF, но обязан явно проверять **предупреждение ожидания**:

- EOF gate T можно заранее закрыть после окончания primer, до POST: T idle и
  единственный target, непустые данные/F/P не задерживаются. Так fault готов
  ещё до production callback и не зависит от порядка позднего observer.
- В следующем наблюдающем public Pool.close callback можно проверить уже
  закрытый exact native driver до перехода SQLAlchemy к driver close;
  не сохранять baseline-утверждение «после hook driver обязан быть open».
  Не менять native методы/driver и не принуждать callback order скрытой
  подменой. Если выбранный реальный порядок listener иной, доказательство
  порядка нужно получить публичными маркерами и отразить явно.
- Early empty-Context observer больше не обязан видеть старую task pending
  до отмены или ровно4 поколения: предотвращённое ожидание позволяет сразу
  создать новое T. Он подтверждает исчезновение старого backend/locks и
  целевого relay/writers; отдельный trace доказывает close-before-checkout
  старого entry и последующие новый connect/checkout/commit/return.
- При успешном предупреждении нормален полный **accepted в обеих ветвях**,
  с настоящим auth/tenant/renewal. Unavailable нельзя требовать только ради
  прежнего RED ожидания. Accepted в стенде не доказывает рабочий ledger.
- В исходном2s до открытия EOF gate/dispose повторно доказать весь прежний
  набор: response complete, own tasks/owner/root чисты, checkedout=2, старые
  T backend/locks/relay/pumps/wait_closed завершены, новый T idle/noTX/no locks,
  три reset/checkin пары, F и новое P exact PID/SELECT1/commit, renewal и ledger0.
  Затем следующий checkout/reuse, штатная очистка. Живой новый pooled socket
  не утечка; F может сменить поколение после возвращения в пул.

Если backend не получил Terminate при немедленном abort, EOF может прийти
от закрытия клиентского направления: это допустимый настоящий cleanup и
должен завершить relay через FIRST_COMPLETED. Нельзя искусственно удерживать
этот pump, чтобы сохранить прежнюю pending-стадию. Раннее исчезновение
backend/socket доказывается наблюдением, не одним driver.is_closed.

Только после новых focused GREEN и независимого implementation review
обоснован общий затронутый regression-профиль (включая принятые C1/I1/rollback/
pre-ping/DB-first): runtime действительно изменён, поэтому это уже новое
основание для проверки, в отличие от повторения старого233 без изменений.
Реализация, converge, exact-SHA CI, T112/T113, restore/runtime/T0, выпуск,
приёмка измерения и трафик/продажи данным дополнением не закрываются.

Точные проверенные исходники дополнения: guard `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14`,
contract `7b0c4bb447cc66aa828be731c1c61c64fde0e1b8fcecd9987d49f553a4139269`.
Library hashes/версии и требования в исходной таблице остались прежними.
Изменён только настоящий отчёт; baseline не повторялся.
