# T112 — независимая проверка реализации rollback при Session.close

16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Проверенный checkpoint: `afa72de5deb2f2d335df62b9b178092a441e201f`.
Основа diff: `41ff49078c30d02d8c6c626018ae1a3c0584e68f`.
Полоса: прежняя `high-risk-product`, F273/T112. Поручение получено и выполнено:
последние окончательные разделы `/private/tmp/graf-t112-http-review-request-20261116.txt`.

## Решение

**PASS текущего ограниченного этапа реализации: P1=0, P2=0.**
Это implementation review актуального кода и причинного evidence, не новое
предварительное согласование. Прочитаны весь изменённый guard/unit/contract
diff, текущие hooks и cancellation/cleanup путь, новые тесты, changelog
fragment, validation report и законченный окончательный120 журнал.
Контрольные суммы трёх исходных файлов и журнала совпали с поручением.

Принимаются точная передача исполняющей task через public события, строгая
очистка завершённой собственной request metadata и три native rollback
fault случая в штатном Session.__aexit__, с тремя контролями и прежними
регрессиями в новом профиле. Полные HTTP/T112/T113 и коммерческая цель
этим решением не принимаются; точные ограничения перечислены ниже.

## Соответствие проекту и исходным требованиям

Повторно прочитаны актуальные положения result-visibility §5 и
activation-milestones о2s, отсутствии фоновых сессий после бюджета и
неизвестном commit, scoped analyze и собственный ранее принятый preflight.
Собственное прежнее чтение остальных неизменных оригиналов использовано
по разрешённому порядку F273. Diff от основы не меняет requirements,
spec/plan/tasks/quickstart, contracts/checklists или analyze.

Основные checklist пересчитаны: requirements16/0, security27/0,
privacy-measurement52/0, infra29/0, всего124 checked/0 unchecked.
Их хеши совпали с предыдущим preflight. Это качество требований; проверяющий
не переотмечал их и не объявляет T112/T113 выполненными.
Старый scoped analyze относится к проекту; его исторический SHA договора
не выдаётся за новый exact-source анализ кода. Новое расширение проверяет
уже существующие бюджет и cleanup, не меняя источники/получателей/хранение.

## Реализация владения и передачи задачи

Root lease и connection lease теперь изменяемые списки со стабильной
identity. Точное connection_record сохраняется в поле4 connection lease;
поиск по pool либо сканирование чужих entries не выполняется.

Общий `_result_connection_lease` сначала возвращается при owner=None, до
asyncio.current_task. Поэтому глобальные Engine hooks не ломают обычную
синхронную Session без event loop; отдельный настоящий SQLite тест это
проверяет. Для собственного owner требуются task того же Context, открытый
неинвалидированный Connection и точные proxy/entry DBAPI/driver, in_use,
owner[entry] и entry.info lease identity. Closed/invalidated проверяются до
публичных свойств connection/info, которые способны вызвать reconnect.

Session.after_begin связывает только tracked root того же owner с этим
lease. Session.info и owner.transactions подтверждают одну identity root;
association содержит и root lease, и точный connection lease. Вложенный
SAVEPOINT не переписывает association. Checkout/checkin очищают её до reuse,
включая owner=None borrower. Новый root той же Session и reconnect с новым
driver получают новые связи, не прежнюю task.

Engine.before_cursor_execute/rollback/commit используют тот же exact helper.
Присутствующая association проверяется полностью до изменения обоих task
полей: неверный bound lease, foreign root и stale/missing root mapping
дают отказ без частичной передачи. Затем синхронно без await connection
lease[3] и root lease[2] становятся одной current task. Для raw Connection
без association обновляется только доказанный connection lease; чужой root
не присваивается. Стабильная identity сохраняет согласованность Session.info,
owner.transactions и association без копирования tuple и устаревших ссылок.

Новые hooks не выполняют SQL, не ждут, не закрывают соединения и не меняют
таймауты. Прежний точный invalidate callback остаётся единственным местом
public driver.terminate для этой отмены. Root ownership до checkout/pre-ping
сохранён. В cancellation набор попадает actual close task, а не оставшаяся
там прежняя parent task. После отмены выполняется прежний join всех owned
tasks, включая shielded cleanup; положительный путь продолжает отказывать
при оставшемся connection/root registry.

## Строгое завершение собственной metadata

`_forget_finished_result_transactions` вызывается после успешного join
только в exception/cancellation ветви. Если join прерван, до вызова helper
исполнение не доходит. Непустой connection registry либо другой Context
запрещают весь проход. Каждый root требует точных owner/key/lease identity,
done task и того же task Context. Проверяются public transaction.session,
Session.in_transaction=False и Session.info[key] is тот же lease.

Выбран строгий вариант: Session.info другого поколения оставляет **оба**
mapping без изменений. Ни чужая Session.info, ни заменённый root mapping
не очищаются. При подходящем завершённом собственном root удаляются лишь
два собственных metadata ключа, без await между сверкой и удалением.
Private transaction state не читается/не записывается, повторных close/
rollback/commit/dispose и SQL нет. Исключение повторно поднимается; helper
не превращает неизвестный исход БД в accepted или known rollback.

Это соответствует фактическому пределу SQLAlchemy2.0.51: CancelledError
внутри SessionTransaction.close может прервать исполнение до
after_transaction_end, хотя connection уже возвращён. Исправление удаляет
request ссылки после cleanup; оно не подменяет библиотечное состояние
транзакции и не является доказательством отсутствия commit.

## Новые тесты и причинные границы

Новые29 unit случаев:18 exact hand-off вариантов, один lifecycle
nested/new-root/reuse/reconnect, девять metadata исходов и один синхронный
owner=None случай. Негативные hand-off случаи не меняют ни connection task,
ни root task; closed/invalidated свойства дополнительно защищены assertion
против revalidation. Metadata случаи сохраняют pending task, held connection,
foreign owner/transaction/Context, active Session и чужую/заменённую связь.
Lifecycle тест использует настоящий SQLite Session/pool, не только fake dict.

Новые6 contract случаев используют настоящую PostgreSQL, production
pool_pre_ping, штатные auth/tenant/CSRF/renewal и AsyncSession.__aexit__.
Фазы — Session синтетического handler без commit, обычный auth ProblemDetail503
после SQL и обычный SQLAlchemyError в renewal до commit; каждая имеет контроль
и сетевой fault. Handler остаётся синтетическим и не пишет ledger.

Перед fault настоящий SELECT/FOR UPDATE и независимый direct observer
подтверждают целевой PID, idle-in-transaction и locks. В public rollback
callback сверяются Connection/DBAPI/driver/owner и отличие close task от
исходной task; **до gate.clear** обе runtime связи уже указывают на эту
actual task. Native asyncpg rollback/close не подменяются. TCP relay задерживает
только server→client ответы; его вспомогательные задачи имеют пустой Context.
Включая wait_closed, они явно учитываются тестовым tracked start.

Все три fault теперь дают законченный unavailable примерно за1.62–1.65s,
раньше2s и watchdog3s. До gate.set/fixture teardown проверяются целевой
checkin, checkedout1 только заранее удерживаемого чужого соединения,
Session.in_transaction=False, пустой own connection registry и отсутствие
tasks именно этого owner. Direct observer проверяет целевой backend/locks;
после этого отдельно проверяются пустой root registry и снятый Session.info
ключ. Только затем открывается gate, чужой connection сохраняет PID/SELECT1;
после его закрытия checkedout0, следующий обычный checkout/SELECT1 успешен.
Метаданные не используются вместо task/pool/Session/DB доказательств.

Response gate пропускает клиентский ROLLBACK: сервер мог уже выполнить
rollback, пока клиент ждёт ответ. Поэтому исчезновение locks само по себе
не доказательство завершённого client cleanup. Тест сочетает независимые
серверные и клиентские наблюдения и проверяет их до очистки стенда.
Watchdog/fixture finally не служат выполнением бюджета запроса.

## Завершённый профиль и точная привязка

Независимо прочитан окончательный журнал: **120 passed, 1 warning,
0 skips, 45.00s; runner48s; focused status=pass**,
`isolated_container_removed`, `result=pass mode=focused partitioned=false shard=none`.
Collection_count120/digest
`833f175054cfc4576cb2f86f58347d27056928b0e9e76158b47d72f0b0540c5c`.
Состав согласован с тестами:91 unit +21 contract +8 integration;
35 новых случаев и85 прежних регрессий. Warning — прежний повторный импорт
pytest fixture plugin. Terminal57752 EXIT0 указан основным агентом;
сам прочитанный законченный журнал независимо подтверждает pass и cleanup.

| Проверенный вход | SHA-256 |
| --- | --- |
| `api/product_analytics_guard.py` | `4a20f7efbda819e774410b3907ac14c659d3e82b50dcf6b730ca506fd89c4509` |
| `unit/test_result_view_http_guard.py` | `d75d5de9d3f9a3e6ea88bcb99762eba017df2655780e2b2d6f1c88ed9048080b` |
| `contract/test_result_view_http_budget.py` | `f66bc3f55495befd5395daaca62a4e53353dc5b9f2330f0e095e3f3dc4d847a4` |
| `/private/tmp/graf-t112-close-full-20261116.log` | `218d264e3075911c275abf634acea7f91d2d24e03f480e96d0000afb0805023a` |
| Предыдущий независимый close-preflight | `b69666a8b029a2d4dcdcb31f871cc7a99910e2a3fea8bcaf350a7593b2dc8071` |
| `contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |

Прочитанные ранее законченные baseline RED и промежуточный metadata RED
разделены: первый имел неполный HTTP ответ, второй уже проходил response/
checkin, но не metadata. Их последующие неисполненные assertions не
приписываются прежнему успеху. Ошибки fixture checkin2/1 и учёта relay
wait_closed не объявлены дефектами продукта и не включены в конечный GREEN.
Приёмка основана на актуальном120, не на названии промежуточного first-green
файла, старых85 или35. Проверяющий профиль не повторял.

## Оставшиеся границы и действие проверяющего

Это native rollback внутри Session.close/__aexit__ в рассмотренных штатных
локальных single-engine Session. Pool reset_on_return использует отдельное
событие и не принят; отдельные raw driver.close/TLS teardown, initialization,
прочие connect/commit исходы и полная HTTP-очистка ещё открыты.
Произвольная передача Session между owner, внешне привязанная Session или
конкурентная multi-bind работа не получают гарантии из этих тестов.
Commit hook обновляет metadata исполнителя, не доказывает DB исход и не
разрешает retry неопределённого commit.

Нужны настоящие endpoint/issuance/renewal/render и GET/HTMX proof, общий
ledger HTTP путь, browser/native проверки, готовность T113/restore и штатные
exact-SHA CI/merge/release gates. Публичные настройки, T0, рабочий сбор,
внешние Product Radar сообщения, визиты, регистрации, активации и продажи
не подтверждены. Changelog сохраняет эти ограничения; tasks не закрыты.
Наличие checkpoint/push не подменяет PR/CI/merge или рабочую приёмку.

Проверяющий добавил только настоящий новый отчёт. Прежние accepted отчёты,
код, требования, планы, задачи, checklist, Git/GitHub и runtime не изменялись.
Чужая работа сохранена; тесты/сборки/службы не запускались. Новых P1/P2,
требующих повторения успешного120, при этой проверке не найдено.
