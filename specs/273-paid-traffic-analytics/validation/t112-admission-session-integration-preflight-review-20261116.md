# T112/T113 — независимый разбор подключения admission owner

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Заявленная основа `c78a3222c5f3f5a622f7d9c4eb56aea29967d77e`;
Git не опрашивался по границам задания. Содержимое проверено по SHA-256.
Полоса существующей F273/T112/T113: `high-risk-product`, проект до кода.

## Решение

**HOLD: P1=0, P2=2.** Направление с одной ограниченной RR Session,
двумя прежними решениями и закрытым настоящим периодом подходит. До кода
нужно зафиксировать два конкретных стыка: API исполнения exact INSERT и
пару абсолютных сроков. Ни новый продуктовый вопрос, ни расширение целей
сбора, ни новая задача для этого не нужны.

Разобран полностью текущий проект07f285be. Он уже выбирает `RETURNING id`
и общий последующий SELECT. Именно эта редакция принимается для оценки
размера возврата; первоначальная идея полного ORM RETURNING не используется
как основание настоящего решения. Чужой проект и исходники не менялись.

## P2-D1 — exact statement ещё не привязан к конкретному API исполнения

Проект §§5–6 требует разрешить ровно построенный примитивом statement,
но не выбирает, чем его исполнить. Для действующего read-only owner это
существенный разрыв: `_before_execute` требует `statement is _expected`.
Обычный `AsyncSession.execute` для ORM INSERT не сохраняет такую цепочку
идентичности. Установленный SQLAlchemy в `orm/session.py:2204–2229`
вызывает `orm_pre_session_exec` перед `do_orm_execute`; в
`orm/bulk_persistence.py:1233` возвращается аннотированная копия Insert.
При invoke_statement есть ещё один pre-session pass. Нельзя просто открыть
существующий `_permit(original)` вокруг db.execute и объявить exact путь
доказанным. Исправление через разрешение любого INSERT данного типа/таблицы,
отключение listeners или частные ORM annotations также не принимается.

Минимальный полный способ устранения, совместимый с выбранным scalar id:

1. Внутренняя точка `admit_account_milestone` получает конечный statement
   и передаёт его только замыканию текущего admission owner. Сам примитив
   по-прежнему один раз строит все values/ON CONFLICT/RETURNING id; нет копии
   SQL или чтения `Insert._values`. Default caller остаётся на db.execute.
2. Admission owner исполняет **этот же statement через свою закреплённую
   Connection.execute**, не через ORM Session.execute. Public AsyncConnection
   принадлежит той же Session/RR транзакции; его можно сохранить при start.
   Никакого engine.connect, новой транзакции или driver SQL. Scalar UUID
   не требует ORM materialization или ORM result-map.
3. Перед исполнением — phase/event/account/source check, свежий gate,
   checkpoint, лимит statement, резерв1row/32bytes. Затем `_permit(statement)`
   на точном объекте; before_execute подтверждает ту же Connection и объект,
   before_cursor — единственное учтённое фактическое исполнение. После
   execute/получения scalar — checkpoint и очистка разрешения finally.
4. Разрешение существует только внутри собственного вызова owner. Verifier
   получает db и не получает этот callback. Вся ошибка/отмена сохраняет
   failed до передачи вызывающему коду, включая перехваченную ошибку.
   Прямой db/connection INSERT вне точки, второй cursor, изменение RETURNING,
   лишнее/переставленное событие и повтор завершённой фазы отказывают.

Статическое основание маршрута: реализация public Connection.execute
в `_execute_clauseelement` отправляет исходный ClauseElement в before_execute
до компиляции; нет ORM
pre-session pass. BulkORMInsert без его ORM annotations компилируется как
raw; фиксированный `.returning(ProductActivationMilestone.id)` даёт scalar
UUID. Частные исходники здесь прочитаны только для объяснения поведения;
предлагаемый продуктовый код не обращается к частным свойствам SQLAlchemy.
Фактическая публичная Connection/ORM точка, row shape и число исполнений
должны получить причинную изолированную проверку после принятия проекта.

Это узкое дополнение проекта, а не новый универсальный DML framework.
До выбора такого либо равно доказанного конкретного маршрута D1 открыт.

## P2-D2 — у общего context manager не определены два разных срока

В §9 правильно запрещён новый2s, но заявлен прямой перенос HTTP work deadline
при переиспользовании нынешнего создания/срока/очистки. Текущий
`result_projection_session(..., deadline=...)` трактует этот параметр как
**конец cleanup** и вычитает0.5 для работы (`:227–241`). Middleware записывает
в request.state только **конец работы** (`product_analytics_guard.py:513–515`).
Прямо передать это значение в существующий параметр означает вычесть резерв
второй раз и оборвать cleanup на work deadline. Начать новый deadline в
периоде означает продлить запрос. Текущие вложенные timeout2/timeout1.5 в
ingest также нельзя оставить источниками новых самостоятельных сроков.

Минимальный полный способ: общий внутренний context принимает явно
`work_deadline` и `cleanup_deadline`, не вычисляет новые2s и не вычитает
резерв повторно. HTTP ingress передаёт одну созданную middleware пару;
при необходимости в request.state сохраняется и второй абсолютный срок.
Одиночный внутренний вызов создаёт пару **до входа в период**: end=start+2,
work=end-0.5. Пара идёт через admit_result_view → period/context → owner.
_account_transaction не перезапускает1.5s. Read-only public wrapper сохраняет
прежнюю семантику deadline=end и ровно один раз переводит её в эту пару.
Owner с самого начала до commit использует work, а rollback/close — исходный
end. После SQL и синхронных gate/catalog/JSON/digest проверяется тот же work.

Нужны явные interfaces/поток в проекте до реализации. Проверки после кода:
задержка до входа в период/checkout не даёт нового времени; ввод HTTP work
не сокращает его ещё на0.5; ошибки commit/close и отмена не переживают end.
Полный precheckout/HTTP cleanup runtime остаётся отдельным незавершённым
обязательством, а не переносом прежнего частного PASS.

## Принятые конкретные части проекта

- `RETURNING id`: известный UUID, не более одной строки; предварительный
  резерв1row/32bytes, включая конфликтный0, без refund. После этого общий
  SELECT account/event возвращает прежний ORM row через действующий numeric
  raw-byte/raw-shape preflight. Полный RETURNING JSON больше не требуется
  доказывать по одному ограничению размера. Default callers получают лишний
  SELECT при создании; это явный impact и нужны обе ветви регрессий.
- Схема и0106 подтверждают UUID PK, account+event uniqueness, unique event_id,
  объект safe_payload≤16KiB, source/state/reason ограничения,
  запрет изменения исходного решения и RLS. Один размер JSON сам по себе не
  доказывает depth32/nodes65536; новая схема scalar+preflight обходит этот
  пробел без ослабления бюджетов или нового ledger. Детерминированность
  event_id обеспечивается прочитанным примитивом, а не schema constraint.
- Общая admission Session остаётся свежей; read-only wrapper не получает
  право записи. require_period обязан проверить owner и `context.db is
  owner.db` до verifier. Только server-auth путь без периода сохраняет старую
  семантику. Произвольный result/value JSON остаётся trigger_unverified.
- Fixed advisory SH(273,3), оба SET и tenant controls учтены; namespace не
  приходит от verifier. Порядок filesystem SH → DB advisory SH → identity/
  session/membership/device → Meeting/source/result сохраняется. Настоящий
  source периода остаётся yield None, без started_at из текущего времени.
- Commit резервирует отдельную единицу в прежнем128 до единственной попытки;
  все SET/numeric/original/INSERT cursor исполнения также учитываются.
  Нужна конечная последовательность owner: reads → event1 completed →
  event2 completed → commit attempted → terminal, без сброса failed.
  Оба completed означают завершение штатного primitive, включая duplicate
  SELECT; они не требуют двух новых строк. Только owner разрешает короткую
  commit-операцию после свежего gate и пустых new/dirty/deleted. Verifier
  commit/rollback/flush/Connection.commit не могут завершить и возобновить
  снимок. Unknown commit даёт False, без retry и без нового показания успеха.
- RR40001 — отказ без немедленного retry. Следующая настоящая видимость на
  новом снимке разрешает старые authoritative keys, сохраняет прежние payload
  и может добавить только недостающую веху. Ошибка второй записи не даёт
  новой частичной пары. Существующие строки при rollback не переписываются.

## Обязательное доказательство после принятия проекта

Обычный полный60мин/600+600 fixture должен проходить не отдельно reader,
а всю auth/tenant/source/projection/оба INSERT/SELECT/commit цепочку в прежних
128/2s/row/byte/JSON пределах, с точным равенством результата. При отказе
не уменьшать fixture и не повышать caps. Нужны causal проверки чужого context
до verifier, direct DML/flush/commit/rawConnection, extra execution/shape,
стадий/порядка событий, полного расхода UUID и последующего SELECT, bounds
cap/cap+1, свежего gate между записями/перед commit, исходной ошибки после
numeric и отмены в SQL/commit/close. Проверки состояния вне sanitizing owner.

Writer/phantom races должны использовать реальные продуктовые fences,
а не только самосогласованный тестовый lock. Проверять RR conflict,
unknown commit и следующее отдельное наблюдение, pool/listener reuse,
отсутствие живых задач/Session и сохранение default primitive callers.
Настоящий закрытый период обязан по-прежнему не вызывать verifier и не писать.
Это проект испытаний, новых PASS или запусков он не содержит.

## Требования, чтение и пределы решения

18 входов независимо сверены с картой предыдущего полного чтения того же
исполнителя/диалога: SAME. Analyze0252da92 не менялся. Reviewer-owned
checklists прочитаны для подсчёта: requirements16/0,security27/0,
privacy-measurement52/0,infra29/0 — **124 checked/0 unchecked**. Не менялись.

Применимые оригиналы восстановлены целыми разделами: result-visibility
весь1–7, activation-milestones весь контракт, spec Session16.11 иFR021–025,
plan continuation27.10 иT112, tasksT112/T113 с продолжением, quickstartT112,
researchT112, data-model account decision/proof, analyze полностью.
README/document-reading прочитаны полностью; product-gates целиком;
constitution I–IV/VI–VII/platform/workflow/governance, PRD14/23/25/31,
current-status current header/NotAccepted восстановлены в оригиналах.
V не затрагивается: приложения/подпись/публикация отсутствуют. Прежние
неизменные исторические части не перечитывались вместо применимых оригиналов.

Полностью прочитаны новый проект и ingest; относящийся целый primitive
admit_account_milestone, actual19-column model/constraints/0106 migration;
Session source95108da9 уже прочитан полностью в собственном R4, нынешний
hash SAME. Дополнительно прочитаны точные SQLAlchemy ORM/Core пути и
events builder, а не исполнялись introspection/SQL/компиляционные пробы.

Runtime verifier T113, readiness/receipts/backup/restore/filesystem guards,
полный HTTP/issuance/renewal/cleanup, maximum envelope, рабочие T0/измерение,
трафик/продажи и выпуск остаются открытыми. Их отсутствие не включено в число
двух замечаний к этому изолированному проекту и не маскируется фикстурой.

Создан только этот собственный новый отчёт. Code/spec/plan/tasks/checklists,
чужой проект и старые HOLD, Git/GitHub, runtime/данные/службы не менялись.
Тесты/сборки/пробы, новые агенты и межчатовые сообщения не запускались.
Отдельных вопросов владельцу не требуется; D1/D2 — инженерные уточнения.

## Точные SHA-256

| Артефакт | SHA-256 |
| --- | --- |
| Новый integration design | `07f285be119006510607d4e68930c068a1cc5c46540256f6ea016d0c29cf9bba` |
| ingest.py | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |
| milestones.py | `f6fa054826632f5f6f40c16fd8449f05ea82c35f64750f3e5fea26480ee31f02` |
| Model product_analytics.py | `fbf089996f1a6c611c5549524d52832608e78e8eae9a77cf70ed2c49972e897d` |
| Migration0106 | `7e464638f72e3fb240e2af048bcdb25022cb9101df3405aaa14068e7b1386898` |
| Session owner | `95108da96f1df0c479ad402cc80a563382049f395d276c5976499a8a67874dc8` |
| HTTP guard | `0ee850ee5310ff1c83d3c6e32d209ce8cee97951393863e937ac33f8e51421bc` |
| events.py | `fda49dcb207933ca3b9a28c1ca784cdccd9de26fade4943dfd6ede4c628888ab` |
| SQLAlchemy orm/bulk_persistence.py | `629245228121de3b28ad7d7c1f064fd9ac1628c8ea0c506d6aeac3da74449c8a` |
| SQLAlchemy orm/session.py | `b75a4e427f453c2eaf19f04d87f66c2da644698a14f3b11880f56a73e2a0760d` |
