# T112 — проект причинного теста инициализации холодного engine

16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Checkpoint: `fb221efc9c0f54480cfc2b1cf50a2fd01fd1fdc4`;
код принятого close этапа: `afa72de5deb2f2d335df62b9b178092a441e201f`.
Полоса: прежняя `high-risk-product`, F273/T112. Поручение:
`/private/tmp/graf-t112-init-review-request-20261116.txt`.

## Решение

**PASS минимального проекта только четырёх причинных тестов initialization
с условиями ниже; P1=0, P2=0 в этой проектной области.** Разрешается тестовый
код в существующем contract файле и прозрачный локальный observation marker
public dialect.initialize. Runtime ownership hooks/исправление этим отчётом
не согласованы. Сначала нужен законченный baseline с точной фазой; его
RED либо PASS не предрешён. Принятый120 не повторяется.

Проект проверяет оставшуюся границу: физическое DBAPI подключение уже создано,
но dialect initialization ещё не закончена, checkout не состоялся. Прежний
startup тест задерживал handshake до DBAPI и этой стадии не доказывает.
Полные HTTP/T112/T113, raw driver.close/TLS, pool reset, прочие commit,
restore/runtime/T0 и продвижение остаются открытыми.

## Неизменные оригиналы и checklist

Использовано собственное полное чтение актуальных result-visibility,
activation-milestones, T112 quickstart/analyze и close-review в этом же
диалоге. Текущие хеши совпали с принятыми; diff от afa72de5d не содержит
изменений guard/contract теста, spec/plan/tasks/quickstart, обоих contracts,
основных checklist или analyze. Это разрешённое hash-scoped продолжение
F273, без нового чтения всего исторического корпуса.

Result-visibility §5 уже требует общий бюджет2s и отсутствие фоновой DB
сессии после него, сохранение auth/CSRF отказов и отсутствие retry по timeout.
Новый тест не меняет эти требования, субъект, хранение, получателей,
продуктовый SQL или фабрику. Scoped analyze остаётся проверкой проекта;
его исторические хеши не выдаются за новое execution evidence.

Основные reviewer-owned checklist пересчитаны без переотметок:
requirements16/0, security27/0, privacy-measurement52/0, infra29/0;
**всего124 checked/0 unchecked**. Это качество требований, не завершение
T112/T113 или приёмка нового initialization пути.

## Порядок событий проверенной версии

Прочитаны установленные SQLAlchemy2.0.51 engine/create.py, pool/base.py,
PoolEvents/event.listen документация, PostgreSQL default/base/asyncpg dialect
initialization и относящийся к кодекам asyncpg0.31.0 код.

1. Native creator возвращает новый DBAPI; entry.dbapi_connection уже присвоен.
   Затем исполняются Pool connect listeners, до checkout. Public
   ConnectionPoolEntry.dbapi_connection/driver_connection доступны.
2. `event.listen(request_engine.sync_engine, "connect", ..., insert=True)`
   добавляет тестовый callback в начало connect listener списка. В обычном
   свежем engine он возникает до штатного asyncpg on_connect и функции
   engine, вызывающей dialect.initialize. Не менять список handlers вручную.
3. Engine регистрирует native on_connect, затем свой once-unless-exception
   initialization callback именно на событии **connect**. Это не отдельный
   public PoolEvents.first_connect. В initialization callback после
   dialect.initialize есть штатный finally rollback; он также остаётся native.
4. Тестовый connect callback, добавленный обычным append после создания
   engine, при нормальном ходе исполняется после штатной initialization
   цепочки, включая её завершающий rollback. Checkout происходит ещё позже.

Public insert=True документирован, хотя обычно не рекомендуется без причины;
здесь он нужен для точного observation/fault до initialization в изолированном
тесте. На runtime разрешение этот вывод не распространяется.

Asyncpg on_connect устанавливает стандартные pg_catalog json/jsonb codecs;
в проверенной версии их introspection использует builtin type map без
дополнительного query. Но при иных настройках/обновлении последовательность
может отличаться. Поэтому факт раннего connect не заменяет маркер входа в
dialect.initialize: fault, не дошедший до него, классифицируется как другая
стадия либо fixture failure, а не доказанный initialization RED.

## Допустимость прозрачного маркера

Обёртка public `request_engine.dialect.initialize` допустима только на
конкретном свежем тестовом engine. Она синхронно записывает entry marker,
вызывает сохранённый bound original ровно один раз с теми же аргументами,
возвращает его результат и пропускает исходное исключение без изменения.
Нет своего SQL, sleep, await, close/cancel, подавления ошибок или изменения
настроек. Это observation реального native пути, не его замена pg_sleep.

Разделить `entered`, `returned_normally` и `exited/finally`: finally выполняется
и при cancellation и не означает успешную initialization. Поздний connect
marker дополнительно подтверждает окончание всей штатной цепочки, поскольку
normal return initialize ещё не подтверждает её finally rollback.
Original сохраняется до замены; восстановление/fixture cleanup не оставляет
обёртку на глобальном классе или другом engine.

Более слабое угадывание по pg_stat_activity query text не требуется и не
равноценно: native initialization SQL может ждать ответ на BEGIN ещё до
посылки version query. Прозрачный marker плюс реальный backend/transaction
observer дают более точное доказательство фазы без вмешательства в работу.

## Четыре сценария и точная привязка сбоя

Матрица: auth/renewal × normal/fault. Seed и начальные данные создаются через
существующий direct engine. Request engine свежий, pool_pre_ping=True,
без warmup/предварительного соединения. Auth использует его сразу. В renewal
штатная авторизация проходит через direct engine; только изолированный
синтетический before_response callback меняет app.state.db_sessionmaker
на обычный maker холодного request engine. Product auth/tenant/CSRF и commit
не переписываются, новые factory/subclass не вводятся.

В раннем connect callback перед gate.clear необходимо подтвердить:

- конкретные DBAPI, public entry и public asyncpg driver соответствуют друг
  другу; native physical connect уже завершён, driver.get_server_pid() даёт
  целевой PID без SQL; driver ещё открыт;
- точный request owner/current task/context и существующий tracked root
  относятся к ожидаемой фазе; checkout ещё не было. Не переносить pre-ping
  ожидание entry.in_use=True на более раннюю стадию initialization;
- fault одноразово относится к первому target driver/generation этого engine.
  Callback не выполняет SQL, не закрывает, не отменяет ресурс и не создаёт
  runtime lease. Normal control оставляет gate открытым.

Marker initialize должен подтвердить этот же driver/entry и current owner,
без получения нового connection через свойства, способные reconnect.
В fault фиксируется initialize entered, а normal completion/late connect/
checkout до отмены не появляются. В normal должны пройти initialize normal
return, late connect и checkout в причинном порядке с тем же поколением.
Счётчики учитывают последующие обычные auth/renewal операции отдельно.

## Независимое наблюдение и приёмка baseline

Во время запроса отдельная tracked observer task с явным пустым Context
ждёт marker и через direct engine подтверждает существование целевого backend
и его initialization transaction/query состояние. Нужен допустимый
state/xact/query набор для этой стадии; не требовать исключительно version SQL,
если уже исполнился BEGIN. Наблюдение ограничено своим коротким бюджетом,
не ждёт target relay и не продлевает2s. Его handle обязательно завершить
и учесть отдельно от product tasks. Оно не устраняет fault и не очищает
целевой backend.

Fault должен закончиться полным unavailable<2s, раньше watchdog3s. До
gate.set/dispose/fixture teardown проверяются отсутствие tasks точного owner,
pool.checkedout0, driver.is_closed=True и отсутствие незавершённой собственной
Session/root metadata. Independent observer после ответа подтверждает,
что целевой backend **исчез**, нет его transaction/activity/locks. Idle backend
без locks не равен закрытому aborted новому driver и не даёт PASS.
Relay целевого соединения не должен иметь незавершённых socket/tasks;
ожидания peer EOF и auxiliary wait_closed учитываются явно. Пустота pool сама
по себе не доказывает отсутствие раннего driver вне checkout registry.

Normal controls подтверждают accepted, штатный committed renewal и отсутствие
milestone ledger rows; init/completion/checkout markers действительно пройдены.
При fixture ошибки, отсутствующем physical connect либо initialization marker
нет права объявлять продуктовый RED нужной стадии.

Чужой backend удерживается отдельным direct engine: сохранить exact PID и
SELECT1. Это подтверждает отсутствие влияния на отдельное соединение, но не
объявляется same-pool cold-initialization изоляцией. Нельзя заранее держать
foreign connection того же холодного pool и одновременно называть engine
неинициализированным.

Только после evidence закрытия target можно открыть gate и выполнить новое
native request_engine.connect/SELECT1. Проверяются новое driver поколение/PID
и законченная initialization/reuse. Одноразовые callbacks/marker не должны
снова закрыть gate или спутать retry проверки с исходным target. Успех нового
соединения после снятия fault не означает, что исходное очистилось до этого.
Watchdog/finally нужны для завершения RED и стенда, не для выполнения runtime
бюджета или замены native cleanup.

## Точные входы и граница следующего шага

| Вход относительно F273 | SHA-256 |
| --- | --- |
| contracts/result-visibility.md | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| contracts/activation-milestones.md | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| validation/t112-analyze-20261116.md | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| validation/t112-close-review-20261116.md | `24e976546e6ee9bfac58d4814fe240208736e87c7085e4a4a779183e7e818e97` |
| checklists/requirements.md | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| checklists/security.md | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| checklists/privacy-measurement.md | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| checklists/infra.md | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |

После добавления тестов нужно прочитать законченный baseline, source hashes,
event/marker evidence и cleanup receipt. Только затем возможен отдельный
минимальный public runtime ownership проект и независимое ревью до кода.
Новые hook идеи этим test preflight не разрешены. Успешный baseline также
требует независимой проверки границ, не автоматической полной приёмки.

Проверяющий создал только настоящий отчёт. Код, требования, checklist, Git,
GitHub, runtime и прежние accepted отчёты не менялись; тесты/сборки/сетевые
эксперименты не выполнялись. Принятый120 не повторялся. Чужая работа сохранена.

## Дополнение: проект точного владения до окончания initialization

Поручение runtime-design прочитано до изменения runtime кода. Текущая основа
`d4dc1bfb963a18a9e22c8680ff720ee8a31443da`. Прочитаны полный новый contract
diff, законченный baseline и уточнённый public event/cancellation/cleanup
проект. Дополнительно проверен фактический constructor/get_connection/checkin
порядок SQLAlchemy2.0.51 и public asyncpg terminate/is_closed.

**PASS минимального проекта одного initialization marker и общего lease
registry с условиями ниже; P1=0, P2=0 в этой проектной области.** Допускается
реализация только предложенной точной ранней ветви. Это не implementation
PASS и не разрешение обходить отрицательные условия ради нового GREEN.
Отдельный owner.initializing dict не нужен: стадия и identity могут храниться
одним дополнительным entry.info ключом, указывающим на тот же lease5.

### Законченный причинный baseline

`/private/tmp/graf-t112-init-baseline-20261116.log` прочитан до конца:
**2 controls PASS / 2 faults FAIL / 21 deselected / 1 старый fixture warning**,
8.34s, runner12s, isolated_container_removed. Fault auth2.06s/renewal2.05s
отказывают на HTTPX response_complete. Дополнительная note в обоих случаях
подтверждает native DBAPI connect и вход в dialect.initialize; код test
до повторного raise также дожидается независимого observer настоящей
initialization transaction. Это доказанный RED нужной стадии, не handshake
до создания DBAPI и не искусственный pg_sleep вместо native initialize.

Поздние fault driver/backend/pool/tasks cleanup assertions этим baseline
ещё не выполнены; они не принимаются на основании успешных controls.
Новый код не добавлен, guard остался прежним. Сам120 не повторялся.

| Прочитанный baseline вход | SHA-256 |
| --- | --- |
| Initialization baseline log | `c5466a4e03a0be5deae7420cc325bebb197686558827dd356fa915f380c4b60b` |
| Неизменный guard | `4a20f7efbda819e774410b3907ac14c659d3e82b50dcf6b730ca506fd89c4509` |
| Contract тест с четырьмя случаями | `35250db3f0995ff13abad7f15912bb3a8318acbd898f575c92dd13f15861f0e0` |

Collection4/digest
`cc2462890c57737cbaadb1d2c95f0dbded4aef46344a6a4a787cc478d6d74359`.
Git diff требований/checklist/analyze от принятого test preflight пуст;
прежние124/0 остаются качеством требований, без переотметок.

### Почему public connect marker даёт отдельное точное основание

Pool.connect callback получает конкретные DBAPI и entry непосредственно
после native создания driver. В этой стадии ещё нет checkout proxy,
entry.in_use=False. Предлагаемый ранний listener может сохранить task/owner,
DBAPI/driver и сам entry в прежнем lease5, одновременно опубликовав один и
тот же lease в owner[entry], обычном owner-key и новом initialization-key.
Это явное владение ресурсом на конкретном public событии, не предположение
по ContextVar либо по одному in_use=False.

Один существующий handler с default connection_proxy=None допустим для
connect/checkout: публичный checkout передаёт proxy, connect — только два
аргумента. Регистрация connect с insert=True обязана происходить до native
on_connect/initialize на рассмотренном engine. Положительный тест должен
показать, что marker уже существует до transparent initialize wrapper.
Не менять private event списки или once flags.

На ранней регистрации нужны корректные current task/context того же owner,
exact entry.dbapi/driver/wrapper driver, поддерживаемый AsyncpgConnection
и отсутствие противоречивых прежних собственных ключей/generation.
Owner=None возвращается без asyncio task обращения и без присвоения
соединения. Нельзя перезаписать чужой/stale marker или root association,
чтобы создать искусственно согласованный lease. Неизвестный случай оставляет
измерение закрытым; продуктовый поток не получает нового обхода auth.

### Переход initialization → checkout/checkin

На обычном checkout снимается только exact current initialization lease
после сверки marker/normal-key/owner registry/entry/DBAPI/driver поколения.
После его точного снятия может создаваться обычный checkout lease по прежним
правилам. В этот момент in_use уже True; отрицание in_use относится к раннему
termination, не к успешному переходу checkout.

Отдельно важен порядок проверок: наличие contradictory initialization key
проверяется **до** прежних безусловных pop/overwrite generic checkout/checkin
кода. Нельзя стереть marker, обновить обычный owner-key новым borrower и
лишь потом пытаться проверить прежнюю identity. При несовпадении ни marker,
ни прежний mapping не «усыновляются». Checkin удаляет только доказанную
соответствующую initialization metadata, если она ещё присутствует.
Обычный путь без initialization marker сохраняет прежнее поведение.

Повторное физическое подключение/новый driver того же entry не наследует
ранний lease прежнего поколения. При невозможности доказать переход нужно
сохранить закрытый исход, а не ослаблять matching. Гарантия этого проекта
пока относится к новому cold initialization, не всем reconnect/custom
on_connect случаям; они не получают автоматический PASS из общего listener.

### Прекращение только отменяемого раннего driver

В exception/cancellation ветви сохраняется DB-tasks-first порядок. После
синхронного cancel точных db_tasks, но до join, новый helper может прекратить
только early lease, для которого одновременно подтверждены:

- owner[entry] is lease; lease[0] is owner; lease[4] is entry; обычный owner-key
  и initialization-key entry.info оба is lease;
- entry.in_use=False, entry.dbapi_connection is lease[1],
  entry.driver_connection is lease[2], wrapper.driver_connection is lease[2],
  driver имеет поддерживаемый public native AsyncpgConnection тип;
- lease task — именно одна из только что отменённых db_tasks, её task context
  содержит этот owner и task.cancelling()>0. Owner Context текущего запроса
  также совпадает. Не включать произвольную already-done, чужую или обычную
  error task в список «отменённых» лишь ради этой ветви;
- проверка и public driver.terminate выполняются синхронно без await между
  поколением и действием. Никакого dispose/close/rollback/commit/retry.

Это ограниченное расширение explicit lease cancellation. Прежняя invalidate
ветвь обслуживает checked-out/pre-ping и не расширяется снятием in_use check.
Нет early terminate для ordinary checkedout, noinit/foreign/stale marker,
недоказанного поколения или noncancelled task. terminate не отменяет join и
не подменяет native constructor bookkeeping; закрытый transport не объявляется
known rollback/commit.

### После join: только собственная metadata закрытого раннего driver

В constructor-failure пути entry может не вернуться из Pool._do_get:
обычный checkin callback тогда вообще не возникает. Поэтому один checkin
listener не является полным механизмом удаления именно этой metadata.
После успешно законченного join допустим синхронный ограниченный проход
только собственного registry по still-exact initialization lease.

Нужны тот же owner/context и lease identity во всех mappings/entry/DBAPI/driver,
entry.in_use=False, done owner task и public driver.is_closed=True.
Только тогда удалить свои initialization-key, normal-key и owner[entry].
При любом mismatch сохранить все связи; не удалять всю entry.info, чужой root
association или текущий lease нового поколения. Если штатный checkin уже
снял связь, helper ничего повторно не делает. Если библиотека изменила
поколение и точное доказательство исчезло, нельзя объявлять cleanup PASS.

Это удаление metadata proven closed precheckout driver, а не изменение
pool counters, entry state или SessionTransaction. После него существующий
root metadata helper по-прежнему требует пустого owner connection registry.
Нормальный путь сохраняет отказ при оставшихся registry, исходная ошибка
не превращается в accepted. Если join не завершён, cleanup не вызывается из
безусловного finally. Новых фоновых задач или SQL в helpers нет.

### Проверки до implementation приёмки

Unit negatives должны отдельно покрыть ownerNone, noinit, staleinit,
foreign marker/normal-key/registry, другой entry, DBAPI/wrapper/driver,
in_use=True, другую task/Context, отсутствие cancelling и task вне только
что отменённого набора. При отказе нет terminate и нет частичного metadata
удаления. Normal early→checkout/checkin и ownerNone синхронный путь сохраняют
ожидаемое поведение; old marker не переносится новому driver/borrower.
Cleanup negatives — pending task, открытый driver, in_use, другое поколение,
foreign Context/ключи и уже сменившийся registry. Положительный cleanup
удаляет только exact closed done early lease и идемпотентен.

Затем нужны native4: marker уже действует до initialize, controls сохраняют
normal initialization/checkout/committed renewal, faults дают полный
unavailable<2s, driver closure/backend disappearance/tasks/pool/root/relay
до gate.set и teardown. После этого — полный затронутый профиль с новыми
hashes/collection/cleanup и независимое implementation review. Новый успешный
профиль нельзя подменять прежними120 или одним focused4.

Проект не покрывает custom initialization с произвольной передачей task,
все reconnect/DNS/TLS/rawclose/poolreset/commit, полный HTTP/issuance/ledger,
T112/T113/restore, runtime/T0 или коммерческий результат. Проверяющий только
дополнил настоящий отчёт; код, требования, markers, Git/GitHub/runtime не
менялись, тесты не запускались. Чужая работа сохранена.
