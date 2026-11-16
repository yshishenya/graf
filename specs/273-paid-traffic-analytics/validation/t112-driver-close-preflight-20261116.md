# T112 — независимый проект теста штатного закрытия native driver

16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Документальный checkpoint: `662d07367937903cf95d677ddeaac90c00148719`;
проверенный runtime/test код: `78cd1ea855b77726c75b5877cf8a094d226a8684`.
Полоса: существующая `high-risk-product`, F273/T112, **TEST DESIGN ONLY**.
Поручение: `/private/tmp/graf-t112-driver-close-review-request-20261116.txt`,
SHA-256 `78633848294a7d68535d8752425865d3c12e58e3d80af75d5d54a11eda563ed9`.

## Решение

**PASS минимального проекта двух новых причинных случаев с обязательными
уточнениями ниже; P1=0, P2=0 в этом уточнённом проектном объёме.** Допустимы
только тест в существующем `test_result_view_http_budget.py` и его локальное
расширение TCP relay необязательными `eof_gate`/`eof_seen`. Исправление runtime,
новые ownership hooks или работа с закрытым API библиотек не согласованы.
Сначала нужен законченный baseline; его PASS или RED не предрешён.

Принятый I1 не пересматривался. Принятые207 проверок не запускались повторно.
Успешный новый тест не будет приёмкой всех вариантов close, всего HTTP или F273.

## Восстановленные исходные ограничения

Применён разрешённый владельцем порядок чтения F273 и действующая инструкция
`document-reading.md`. Происхождение прежнего scoped чтения проверено по
собственным `t112-requirements-preflight`, `t112-http-preflight`,
`t112-close-preflight`, `t112-init-preflight` и принятому I1 отчёту в том же
диалоге. Новое полное чтение всего PRD/истории статуса здесь не заявляется.

Карта заново проверенных применимых оригиналов:

- `AGENTS.md`, guidance index, `document-reading.md`, `spec-kit-flow.md`,
  `product-gates.md`: границы независимого ревью, high-risk путь, запрет
  расширения разрешений и содержимого в evidence. Короткие guidance прочитаны
  полностью; полномочия проверяющего ограничены настоящим отчётом.
- Конституция: ограничения секретов и внешних границ §III, lifecycle §IV,
  Spec Kit §VI, Product/Platform Constraints, Development Workflow и Governance.
  Нет изменения принципов, нового хранилища или получателя.
- PRD: Backend Architecture §14, Meeting Detail §23, применимая граница данных
  §25 и Observability §31. Статус: текущая шапка и историческое различие
  публичной аналитики F093 и продуктовых вех; история не выдаётся за новую приёмку.
- `spec.md`: clarify T112, FR-021/025, SC-006; `plan.md`: измеряемые границы,
  продолжение T112/T113 и проект T112; `tasks.md`: T112/T113 и их уточнение.
- `contracts/result-visibility.md` §5: общий бюджет2s, lock≤250ms,
  statement≤500ms, отсутствие пережившей бюджет DB-задачи и автоматического
  повтора неизвестного commit; §7 и T112 quickstart: синтетический стенд,
  causal baseline и независимое ревью. `activation-milestones.md`:
  действующие основание/lifecycle/restore; новая проверка не снимает T113.
- `validation/t112-analyze-20261116.md`: прежняя проверка проекта сохраняется;
  результат теста, runtime/T0 и коммерческий результат из неё не выводятся.

Исходники guard, существующего relay/close contract и установленные
SQLAlchemy2.0.51/asyncpg0.31.0 прочитаны применительно к новой фазе. Путь
библиотеки проверен по исходникам, без запуска нового DB/network эксперимента.

## Почему invalidate(None) относится к проверяемой границе

Public `AsyncConnection.invalidate(exception=None)` передаёт операцию обычному
SQLAlchemy Connection через greenlet. В проверенной версии hard invalidate
публикует Pool.invalidate, затем Pool.close и вызывает штатное завершение
DBAPI connection. Для asyncpg адаптер в greenlet ожидает через shield
native `Connection.close(timeout=2)`; это реальное штатное закрытие драйвера.
Ни wrapper, ни native close/rollback/terminate тестом не заменяются.

Текущий guard специально обрабатывает Pool.invalidate с CancelledError;
обычная причина None эту ветвь не включает. Поэтому выбранный путь проверяет
отдельную оставшуюся границу внутри внешнего request budget. Это искусственный
синтетический вызов публичной операции в handler, а не утверждение, что будущий
ledger handler всегда явно вызывает invalidate. Он не доказывает обычный
`AsyncConnection.close()`, `Session.__aexit__`, recycle/reset, все library
ошибки или TLS shutdown. Не нужно менять продуктовый handler ради теста.

Порядок Pool.close — маркер **перед** обращением к драйверу, а не завершение
закрытия. В asyncpg protocol.close выставляет closing, отправляет Terminate
и ждёт разрыва сервером; transport.abort выполняется в finally. Публичный
`driver.is_closed()` уже может быть True при ещё незавершённом ожидании:
он не является самостоятельным доказательством освобождения сокета.

## Минимальный тестовый объём и точная стадия

Матрица: normal/fault × один handler phase, один существующий native alias.
Остальные auth/CSRF/alias матрицы этим минимальным проектом заново не требуются.
Seed, настоящие auth/tenant/CSRF и renewal используют direct engine. Только
синтетический `before_response` открывает отдельный request engine через relay.
У этого engine один slot и одно исходное соединение; до проверки target cleanup
нет нового checkout, прогрева второго stream или same-pool foreign connection.

Handler выполняет настоящий SELECT1/получение PID и явный успешный commit,
после чего вызывает `await connection.invalidate(exception=None)`.
До вызова и в наблюдающих public Pool.invalidate/close callbacks связать exact
request owner/current task, public entry, DBAPI wrapper, native driver и PID.
Зафиксировать cause=None, отсутствие активной native transaction и совпадение
lease; никаких изменений lease или callback exceptions. В close callback
одноразово закрыть только EOF gate для fault. Обычный data gate остаётся открыт
в обоих случаях; auth/connect/init/SELECT/commit не задерживаются.

**Обязательное уточнение о direct pool:** нельзя удержать foreign connection
в direct engine с прежним `_run` default pool_size=1 и одновременно ожидать
auth/observer через тот же pool. Нужна явно достаточная ёмкость тестового
direct engine (например,3 для foreign+observer+обычной работы) либо отдельный
независимый engine наблюдателя. Это настройка изолированного теста, не runtime.
Observer имеет собственный handle, пустой Context и ограниченное время; он
не блокируется target relay и не удлиняет двухсекундный бюджет продукта.

После close marker наблюдатель подтверждает upstream EOF и исчезновение target
backend/locks до отмены target request. Проверить порядок по событиям/времени,
а не случайный итог после cleanup: callback identity → native close/серверный
EOF → backend absent, при ещё не отменённом request. Нет необходимости
распознавать пакеты протокола: причина None, законченный commit, native public
путь и настоящий EOF однозначно отделяют фазу от SQL/rollback/init stalls.
Непопадание в эту стадию или занятый observer pool — ошибка доказательства
стенда, не продуктовый RED этой фазы.

## EOF gate и FIRST_COMPLETED

Существующий relay удерживает только непустые данные: EOF немедленно завершает
server→client pump. Минимальное расширение добавляет необязательные keyword
`eof_gate`/`eof_seen`; существующий yield из трёх значений и все callers остаются.
Только held server→client pump при `read()==b''` выставляет eof_seen и ждёт
eof_gate перед обычным выходом. Опции не влияют на обычный data gate и другие
тесты. Новый поток идентифицируется sole-stream условием выше; без него
глобальный EOF gate не даёт права объявить fault точно адресным.

`FIRST_COMPLETED` корректен: когда upstream EOF удержан, этот pump остаётся
pending; client→server pump также ждёт native клиента. Запись Terminate —
данные, сама по себе не EOF. Если клиент сам закрывает своё направление,
другой pump завершается, relay finally отменяет EOF waiter, закрывает оба
writer и дожидается обоих wait_closed. Такое освобождение до gate.set —
допустимый реальный cleanup, его нельзя блокировать ради заранее ожидаемого RED.

До измеряемой фазы подтвердить eof_seen на нужном stream и фактическое
удержание EOF; если FIRST_COMPLETED завершил relay ещё до этой стадии, тест
не доказал задержанное закрытие. Если native клиент освобождается сам и весь
путь завершается в срок, это возможный успешный baseline конкретного случая;
он не доказывает отмену уже зависшей close-задачи, если её не было.

В аварийном finally relay/test обязан открыть также eof_gate, завершить observer
и убрать стенд. Watchdog3s служит только выходу из RED; его срабатывание
фиксируется и никогда не считается выполнением2s. Проверки успешного cleanup
выполняются **до** gate.set, engine.dispose и fixture teardown. Уборка после
ошибки не может ретроспективно превратить незаконченный запрос в PASS.

## Что считается доказанным исходом

Normal: полный accepted<2s, штатный сохранённый auth renewal, нулевой milestone
ledger; native invalidate и освобождение точного поколения действительно
пройдены. Fault: полный закрытый unavailable в оставшемся общем бюджете,
либо accepted только если реальный close уже полностью завершился до допуска.
Сам по себе текст ответа без доказанного окончания ресурсов недостаточен.

До снятия fault и в пределах исходного абсолютного2s необходимо подтвердить:

- Полный ASGI ответ, завершённый handler/close child и все задачи exact owner;
  оба реестра owner пусты, собственного transaction/root следа нет. Снимок
  задач не подменяется одним `driver.is_closed()` или pool.checkedout().
- Target backend исчез, его locks отсутствуют. Состояние idle без transaction
  недостаточно: здесь ожидается именно закрытие соединения.
- Sole target relay root, оба pump и wait_closed закончены; оба writer закрыты
  и их публичные wait_closed завершились. Существующий tracked tasks набор
  включает root и auxiliary wait_closed: требуется его пустота, а не просто
  исключение всех relay tasks из глобальной проверки утечек. Допустимы узкие
  тестовые маркеры завершения; доступ к private driver transport не требуется.
- Request pool.checkedout=0; нет новых request/DB/socket задач. Если нужно
  дождаться очередного оборота event loop, использовать остаток того же2s,
  а не новый независимый срок. Observer handle закрыт отдельно и учтён.

Direct foreign backend сохраняет exact PID и SELECT1. Это доказательство
изоляции отдельного соединения, **не same-pool foreign coverage**. После
принятия cleanup открыть gate, выполнить новый native checkout/SELECT1 и
проверить другое driver поколение/PID; одноразовый fault не должен сработать
повторно. Этот поздний успех не заменяет доказательство раннего cleanup.

Commit SELECT1 до fault известен и синтетический; ledger не подключается.
Unavailable не означает rollback уже прошедшего commit. Нет retry и нового
подключения в исходном запросе ради успешного результата.

## Точные входы, контроль списков и границы

| Вход | SHA-256 |
| --- | --- |
| Guard | `b22a95714a2e6d94ec1645bad0475e1b99b518386caa7ebab785fb0d42dd0088` |
| Contract test | `45f937184fd0f3569ee385659fc3529d5af1a3acb8d8a5b12fd72fce7dfad2ac` |
| result-visibility | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| activation-milestones | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| scoped analyze | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| Constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| Current status | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| document-reading | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |

Diff кода/requirements/contracts/checklists/analyze между code checkpoint и
текущим HEAD пуст. Основные списки пересчитаны по неизменным хешам без
переотметок: requirements16/0, security27/0, privacy-measurement52/0,
infra29/0; всего124 отмечено/0 не отмечено. Это качество требований, не тестовый
результат и не закрытие T112.

Отдельно остаются TLS, обычный raw close, pool reset/recycle, прочие фазы и
commit исходы, полные HTTP/issuance/ledger/browser/native T112/T113,
restore/runtime/T0, PR/CI/merge/release, рабочее измерение, трафик и продажи.
После нового baseline нужен разбор точной фазы/исходников/cleanup receipts.
Любое runtime исправление требует отдельного проекта и независимого ревью
до кода; его необходимость и форма здесь не предполагаются.

Проверяющий создал только настоящий отчёт. Исходники, тесты, требования,
checklist markers, Git/GitHub и рабочая среда не менялись. Тесты, сборки,
старый207 профиль и сетевые эксперименты не запускались; чужая работа сохранена.

## Дополнение — независимое ревью законченного baseline

Поручение: `/private/tmp/graf-t112-driver-close-baseline-review-20261116.txt`.
Основа по-прежнему `e9eb5076197bbac912aa0f5b9118ded0f35f6edd`; рабочий diff
меняет только contract test. Runtime guard побайтово прежний. Прочитаны весь
новый diff, relay/handler/observer и законченный итоговый журнал, включая
traceback и квитанцию удаления контейнера. Новый исполнительский отчёт
`t112-driver-close-validation-20261116.md` также сверён с этими входами.

**Causal baseline принят как RED нужной фазы: P1=0, P2=1 (C1) в runtime.
Блокирующих P1/P2 дефектов самого узкого теста не найдено.** Это не PASS
реализации и не подтверждение поздних fault cleanup проверок.

### C1 — native graceful close съедает весь срок ответа

Normal прошёл; fault около2.004s закончил выполнение приложения без полного
ASGI ответа, после чего HTTPX упал на `assert response_complete.is_set()`
в `asgi.py:181`. Это не недостижение подготовительной стадии: public
invalidate(None)/close callbacks проверяют exact owner/task/entry/lease/
DBAPI/driver и одно целевое соединение; настоящий SELECT1/PID/commit уже
завершён. Отдельный observer с пустым Context подтверждает upstream EOF,
исчезновение target backend и locks до отмены request task. В fault EOF gate
закрыт, data gate открыт, `is_closed=True`, invalidate ещё не вернулся и
request/relay ещё pending. Watchdog не сработал.

Сбой находится после штатной серверной обработки завершения соединения,
в ожидании клиентского graceful close. Прочитанный library traceback ведёт
через настоящий `AsyncAdapt_terminate.terminate` и shield native close.
Закрытый флаг не доказывает release сокета; этот baseline причинно показывает
именно различие. Исчезновение backend до отмены исключает объяснение
незаконченным SQL/rollback/init. Действующий guard отменяет DB owner, затем
присоединяет наследующие owner задачи; незаконченный shielded close не даёт
достаточного резерва для конечного unavailable. После общего дедлайна
`_result_view_unavailable` уже не отправляет ответ. Это нарушает §5 договора.

### Достоверность и пределы теста

Optional EOF параметры сохраняют прежний yield3 и callers. FIRST_COMPLETED
не маскирует fault: в fault наблюдение действительно достигло удержанного EOF
до отмены. Direct pool3 решает занятость foreign/observer/auth. Наблюдение
Pool.close стало одноразовым, поэтому повторный dispose вне owner не
подменяет итоговую ошибку; первоначальный журнал с такой ошибкой — история,
не окончательный baseline.

Normal прошёл все последующие условия: полный accepted0.103s, законченные
relay/wait_closed и owner/pool/tasks до teardown, renewal сохранён, ledger0,
foreign PID/SELECT1 сохранены, новый native driver/PID работает. В fault
падение происходит раньше последующих условий. Его законченные task/socket/
owner/pool cleanup, foreign readback и новый checkout **ещё не доказаны**;
удаление контейнера и последующая fixture уборка ими не являются.

Итоговый профиль: **1 passed,1 failed,25 deselected,1 старый fixture warning**,
pytest5.49s, runner9s, `postgres_test_phase=focused status=fail`,
`postgres_test_cleanup=isolated_container_removed`.
Collection2/digest:
`ccce981630874985a7e397fed77ddbffe162deaf84148862d8be5cf2021ba2d6`.

| Проверенный baseline вход | SHA-256 |
| --- | --- |
| Guard, без изменения | `b22a95714a2e6d94ec1645bad0475e1b99b518386caa7ebab785fb0d42dd0088` |
| Новый contract test | `084e0c3a561c982be062eab334de17985e8388737163f50198dc5b51b09c0e16` |
| Итоговый baseline log | `c42b671864664f8bdce3b0f79ead32d39ff1819d0960bfd92992d324e956962d` |

Новый запуск не выполнялся: фактический diff и законченный журнал достаточны
для этой находки; прежний207 не повторялся.

## Отдельное решение — минимальный public runtime проект после C1

**PASS только следующего узкого проекта упреждающего завершения при hard
invalidate(None), с обязательными проверками ниже; P1=0,P2=0 в проекте.
Реализация, GREEN и весь raw close этим ещё не приняты.**

Минимальный публичный путь не требует искать скрытую close task и менять
порядок общей отмены. Существующий public Pool.invalidate callback вызывается
до Pool.close и до native graceful close. Для обычной hard invalidation с
причиной None точного собственного native соединения **без активной
транзакции** допустимо один раз вызвать публичный `driver.terminate()` уже
в этом callback. Hard invalidation всё равно окончательно выбрасывает это
соединение; операция не возвращает его для дальнейшего использования.

Это осознанное немедленное закрытие только такого выбрасываемого соединения,
а не попытка повторно terminate уже closing driver. В проверенном asyncpg
terminate до начала close вызывает abort открытого протокола. Последующий
штатный SQLAlchemy graceful close видит уже закрытый driver и заканчивается.
Пул и Connection продолжают собственные штатные bookkeeping/checkin действия;
их поля, счётчики и состояние не переписываются агентским кодом. Новых SQL,
retry, timers, конфигурационных параметров, factory или сервиса нет.

### Обязательные отрицательные условия новой ветви

Сохранить прежнюю CancelledError ветвь и её pre-ping/DB-first порядок отдельно,
без расширения её fallback на причину None. Для **новой** ветви нужны все
условия одновременно:

1. Текущий Context содержит точный ограниченный owner; current task существует
   и её Context принадлежит этому owner.
2. Public entry.in_use=True; callback DBAPI, entry.dbapi_connection,
   entry.driver_connection и wrapper.driver_connection совпадают по identity;
   driver — поддерживаемый native AsyncpgConnection.
3. Есть уже принятый обычный lease5: owner[entry] и normal-key указывают на тот
   же объект, lease owner/DBAPI/driver/entry точны, lease task — текущая task
   с тем же Context. Отсутствие lease **не** даёт права взять ресурс.
4. Нет initialization marker и противоречивой/root association этого entry;
   native driver открыт и `is_in_transaction()` ложно. Это не разрешение
   прервать чужую транзакцию или выводить known commit из одного закрытого
   флага. Уже начатый graceful close этим путём не принимается.

При owner=None, другом owner/task, неизвестном/противоречивом поколении,
другой причине, driver type, active transaction, закрытом driver или
неполной metadata — никаких действий с driver/foreign lease. Не добавлять
callback exception или retry. Противоречие текущего owner не должно
впоследствии становиться accepted лишь из пустоты реестров; сохраняется
принятая fail-closed семантика `owner.failed`, без присвоения чужого ресурса.

Одного расширения `exception is None or isinstance(CancelledError)` вокруг
прежнего менее строгого ownership predicate недостаточно: новой ветви нужны
перечисленные task/lease/generation/transaction условия.

### Почему не достаточно других коротких правок

- Поздний `driver.terminate()` после is_closed=True не гарантирует abort:
  public terminate проверяет is_closed, а native protocol уже closing.
  Доступ к `_protocol`/transport и мутация закрытых состояний не допускаются.
- Простое увеличение бюджета/возврат unavailable без join нарушает принятый
  срок либо оставляет работу и сокет. Оно не исправляет C1.
- Отмена всех owner children одновременно с DB owner может повторно прервать
  SQLAlchemy bookkeeping через родительские task groups. Общая двухфазная
  отмена потомков была бы более широким проектом с отдельным доказательством
  порядка и точного владения. В этом минимальном срезе она не нужна и данным
  решением не разрешается; прежний DB-first путь остаётся неизменным.

### Изменение доказательства после упреждающего закрытия

Этот проект намеренно предотвращает прежнее зависшее graceful ожидание,
поэтому нельзя требовать, чтобы после исправления снова существовала pending
native close task. Нельзя также просто удалить проверку фазы/сокета ради GREEN.
Сохранить точный исходный RED и его test SHA выше. Новый тест должен различать
два **наблюдаемых** пути, без флага доверия или подмены native методов:

- Исходный путь: driver открыт перед invalidate и при входе close, upstream
  EOF удержан, backend исчез, native ожидание ещё pending. На исходном guard
  это по-прежнему обязано приводить к C1.
- Исправленный путь: driver был открыт и без транзакции перед invalidate;
  public cause=None и exact ownership подтверждены; уже при Pool.close он
  закрыт вследствие новой ветви. Поздний ожидатель EOF не нужен для окончания
  native driver, но реальное освобождение доказывается завершением relay root,
  обоих pump и wait_closed, исчезновением backend/locks, пустыми owner/pool/tasks
  до gate.set/teardown в том же2s. Событие server EOF может не успеть публиковаться
  до client EOF/FIRST_COMPLETED; это не заменяет обязательные socket/task proof.

Проверка `is_closed()` должна предшествовать `is_in_transaction()` с коротким
замыканием. После публичного terminate asyncpg уже освободил protocol, поэтому
повторный `is_in_transaction()` на таком driver в runtime или тестовом close
callback недопустим; отсутствие транзакции фиксируется до завершения.

Нужны normal/fault, renewal/ledger0, foreign PID/SELECT1 и новый checkout/
generation. Нужны focused unit отрицательные случаи каждого нового identity,
task, причинаNone/другая/CancelledError, active transaction, owner=None,
initialization/root association и уже closing driver: никаких чужих terminate,
мутации metadata или возврата failure в accepted. Причинные тесты положительного
пути проверяют весь ответ и ресурсы, а не только вызов terminate в fake.
После кода — законченный профиль затронутого поведения и независимое review;
старый207 не является доказательством изменённого guard.

Требования/spec/plan/tasks/contracts/checklists/analyze не менялись. Четыре
списка повторно пересчитаны по принятым хешам:16/0+27/0+52/0+29/0=124/0;
это по-прежнему качество требований. Полные T112/T113, TLS/обычный close/
reset и остальные исходы, рабочее измерение/T0/restore, выпуск и трафик/
продажи остаются открыты. Проверяющий только дополнил этот отчёт и сохранил
параллельные изменения основного агента.
