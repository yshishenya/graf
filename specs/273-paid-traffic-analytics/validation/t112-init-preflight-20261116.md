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
