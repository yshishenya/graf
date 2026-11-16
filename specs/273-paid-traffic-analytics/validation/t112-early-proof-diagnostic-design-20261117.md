# T112 — проект минимальной диагностики раннего GET без proof

17.11.2026. Независимый проверяющий `/root/public_counter_readiness_review`. Существующая F273/T112/#7698, T113/#7804, полоса `high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`, HEAD `6ecc7335962b0c1728fdab911f6b76c3321b4e80` указан поручением; Git в этом проходе не вызывался. Область — чтение и только этот новый отчёт. Код/тесты/требования/план/tasks/checklist/прежние отчёты/Git/GitHub/службы не менялись, тесты и приложения не запускались, новые агенты не создавались.

## Решение и вопрос опыта

**DESIGN ONLY: рекомендован отдельный одинарный GET-пробник без global tracing; исполнения пока не назначено.** Нужно различить, на какой редкой функциональной границе исчезает результат: входная eligibility, вход/выход ограниченной inspection-транзакции, исключение/отмена/исчерпанный срок, пустой набор допустимых bindings либо отказ после уже сформированного результата при cleanup. Это не повтор V4, не продолжение его израсходованного допуска и не новый87.

Предлагаемый механизм — временные test-only обёртки редких функций с сохранением их исходного делегирования. Они позволяют увидеть исключения до существующих blanket catches без глобального перехвата каждого Python-вызова/строки. Конкретный код пробника и обёрток должен получить отдельное статическое ревью до любого HTTP/PG исполнения. Этот документ не является таким ревью ещё не существующей реализации.

## Что подтверждено завершённым V4-опытом

Полностью прочитаны `t112-causal-v4-native-validation-20261117.md` и metadata `/private/tmp/graf-t112-causal-v4-native-metadata-20261117.json`. Отчёт сообщает ровно **2FAIL/EXIT1** на исходной integration:1159: GET HTTP200 и0 proof вместо2. В обоих metadata-объектах есть только scenario AssertionError:1159 и снимок до finally; post_enter/M1/guard нет, entered=False, tracer_restored=True, переполнения96 нет. Значит normal POST2/fault POST1 не достигнуты. Допуск V4 использован однократно и повторно не применяется.

Числа7.239948s/3.791994s — время от старта всего case до snapshot, включая подготовку БД/прогрев/seed/auth/render. Это **не** измерение длительности `optional_result_view_proofs` и не доказательство исчерпания его work1.5s/hard2s. Отсутствующие target facts/deadlines в V4 — состояние COMMIT-сценария, а не доказательство отсутствия/истечения deadlines GET helper.

Raw log с SHA-256 `491c3a92b389ccba146e9a85552942807e22ea8fee753ad85eaf9a1c784e7ada` содержит синтетическую страницу/сессию. Он здесь не открывался, тело/сессия/proof не извлекались и не цитируются. Его hash и результат очистки берутся из прочитанного авторского отчёта; metadata файл самостоятельно сверён по hash. Исторические repeated unavailable, normal POST2 без завершённого ASGI-ответа и fault response_held timeout этим новым GET-отказом не объяснены.

## Исходная цепочка и места потери результата

Прочитаны оригинальные функции, не только поиск/заголовки:

1. `result_views.optional_result_view_proofs` создаёт actual work/cleanup deadlines, проверяет доступ owner/view/full и `_eligible`; ранний отказ возвращает `{}`. Затем запускает `issue_result_view_proofs` через `_run_result_view_operation`. Любое Exception, включая ошибку operation cleanup, превращается в `{}`. Поэтому только наружный результат не различает ранний return и проглоченное исключение.
2. `issue_result_view_proofs` передаёт вложенный inspect в `_inspect_result_view`. Inspect получает `load_fresh_result_view_bindings`, проверяет owner.checkpoint до/после signer и складывает непустые подписи. Выход `_inspect...` None или пустой dict превращается в `{}` оператором `or {}`.
3. `_inspect_result_view` имеет отдельный ранний None при неполном principal/session/workspace/sessionmaker/surface, проверяет deadlines, входит в `_account_transaction(require_period=True,inspection=True)`, вызывает inspect и проверяет admission после него. Exception возвращает None.
4. `_account_transaction` проверяет period context/точный inspection owner, текущие admission/session/account fences, затем yield context и повторную inspection-проверку. Рабочий `_result_period_context` остаётся `yield None`; в имеющемся `http_period` fixture только для синтетической проверки подставляется реальный ограниченный inspection owner. Это не включение рабочего T113.
5. `load_fresh_result_view_bindings` может нормально вернуть пустой dict при недопустимом fence/недоступном review/отсутствии owner/render mismatch. **Пустые bindings не означают отсутствие строк/контента в БД.** Положительное число bindings и нулевое число итоговых proofs при обычном завершении — другая ветвь; это ещё не доказательство конкретной причины отказа signer.
6. `_run_result_view_operation` может отклонить уже построенный dict из-за остаточного ownership/cleanup. Поэтому отдельное наблюдение этой редкой функции необходимо: успешный issue и пустой optional не означают пустую проекцию.

## Объём следующего пробника

Один отдельный временный диагностический case, **один GET**, затем обычная очистка. Он воспроизводит раннюю предпосылку исходного native setup: тот же isolated_admission/http_period, изолированная PostgreSQL, request engine pool2/pre-ping, тот же реальный `_postgres_response_gate`, два последовательных warm connects, их возврат, тот же `_real_app(request_engine)` и native auth helper. Данные/порядок/auth/seed остаются исходными. Fault-переключатель начинает действовать позднее при COMMIT, поэтому для GET-предпосылки нет необходимости дублировать обе параметризации.

Не вызывать исходный полный native test с искусственным skip/перехватом assertion или остановкой после успешного GET: это подменило бы его смысл и могло бы случайно продолжить POST. Новый prefix-only case заранее заканчивается после GET и своей очистки; он не объявляется приёмкой native commit-теста. Не создавать POST/M1/watchdog, не ставить response gates для fault, не повторять GET и не увеличивать work/hard/lock/statement caps. Настоящий relay остаётся без V4 line tracing; его протокол/потоки и пустой Context() не меняются.

Из HTTP response разрешено прочитать только status code. **Не читать `page.text`, response body, headers, proof-атрибуты и не вызывать `_proofs`.** Число результата получать из `len(dict)` внутри функциональных границ; ни ключи, ни строки-подписи не читать. Это намеренно не проверяет HTML-вставку. Если серверные границы дают2, а прежний HTML давал0, следующий вопрос будет уже о render/wiring и потребует отдельного проекта, а не разбора страницы в этом опыте.

## Точный механизм редких наблюдений

Никаких sys.settrace/sys.setprofile/sys.monitoring, локальных line hooks, перехвата driver/SQLAlchemy/Pool, `_refuse`, checkpoint, SQL events или task-factory. Вместо этого захватить оригинальные функции до monkeypatch, поставить прозрачные temporary wrappers только для указанного case и включать metadata-маркер ContextVar на время одного GET. Они делегируют исходной функции ровно один раз, с теми же аргументами, возвращают тот же объект и повторно выбрасывают то же исключение/отмену; inactive вызовы сразу делегируются без наблюдений.

| Граница | Минимальные события и допустимые значения |
| --- | --- |
| `result_views.optional_result_view_proofs` | enter/leave/raise, относительная длительность; четыре access bool (present/owner/view/full) без ID/модели; форма результата и только len(dict). Actual deadlines здесь ещё не заданы — не придумывать их по времени wrapper |
| `result_views._eligible` | один исходный вызов: bool либо exception type/module. Не повторять проверку в wrapper и не читать request headers/host/user-agent |
| `ProductAnalyticsIngestService.issue_result_view_proofs` | enter/leave/raise, actual work_deadline/cleanup_deadline из переданных аргументов как остатки времени, dict count; не копировать principal/meeting/review/selection/secret |
| `ProductAnalyticsIngestService._inspect_result_view` | enter/leave/raise; чистые precondition bool из аргументов (principal/session present, membership match, session workspace match, sessionmaker present, allowed surface), None против dict count и actual остатки сроков. Не вызывать `_check_admission`/validate повторно |
| `ProductAnalyticsIngestService._account_transaction` | прозрачный asynccontextmanager: enter_begin, yielded, body_exception, exit_begin/finished/exception. Yield ровно исходный context; только is_none и точный inspection-owner bool плюс actual остатки сроков. Не заменять `_result_period_context`/source/owner |
| `result_visibility.load_fresh_result_view_bindings` | await исходного helper ровно один раз; enter/leave count(dict)/raise с type/module, остатки actual срока из текущего marker. Не читать binding values, keys, db/SQL/проекцию |
| `result_views._run_result_view_operation` | один делегированный вызов исходного operation, enter/leave/raise и dict count. Это видит отказ cleanup до blanket catch optional; callback/порядок задач/source и owner не переписывать |

Это семь редких границ цепочки одного GET, не обёртки каждого binding/SQL/checkpoint. Signer не подменяется и proofs не декодируются. Новых сетевых/DB/readiness вызовов нет. В `browser.py` helper импортируется внутри обработчика из result_views, а issue импортирует binding loader внутри своего вызова из result_visibility; перед реализацией сохранить именно эти точки разрешения имён, не создавать дублирующие wrappers и не патчить несколько aliases вслепую. Service-method wrappers должны сохранять исходную привязку self и никогда не вызывать текущий monkeypatched атрибут вместо захваченного оригинала.

Asynccontextmanager wrapper требует особой аккуратности: один оригинальный `__aenter__`, один yield того же context и исходный `__aexit__` с тем же exception/traceback. Ошибка body фиксируется **до** того, как исходный context может преобразовать её при cleanup; окончательная ошибка exit фиксируется отдельно. Уважать исходное подавление/преобразование ошибок context manager; не вводить собственное подавление, broad fallback или лишний close/rollback. В records сохранять только type/module, не объект/args/traceback. Это диагностическая оболочка, не новое владение DB.

Actual сроки брать только из параметров issue/inspection/account и сравнивать с тем же `asyncio.get_running_loop().time()`. До их получения значение unknown, не ноль. Сохранять elapsed этапов и остатки work/hard на enter/leave/exception; не вычислять новый независимый deadline и не продлевать старый. Для callback с отсутствующими полями оставлять unknown, не бросать ошибку наблюдателя. HTTP GET elapsed и elapsed optional — отдельные величины.

## Хранение метаданных и проверка перед исполнением

Фиксированный небольшой буфер, например32 редких enter/leave/error записей, плюс **отдельная ограниченная terminal summary по семи стадиям**, не вытесняемая cap. На стадию хранить count, entered/finished, первую ошибку type/module, первые/последние времена, форму результата/число элементов и актуальные остатки сроков; только примитивы. Сохранять dropped и флаг incomplete. Не удерживать frame/traceback/exception/task/context/review/owner/response/proofs/bindings в журнале либо его долговечных полях; временные ссылки функции допускаются только для исходного вызова и возврата.

Нельзя repr/str всех аргументов/locals/результатов/исключений, HTTP body/headers/URL, SQL text/parameters, binding keys/values, proof/секрет/ID/текст встречи. Даже синтетический полный failure HTML не включать в итоговые Git-материалы. Выводить только summary после завершения GET и очистки; stdout failure не должен менять сохранённый результат запроса. Если наблюдатель обнаружил собственную ошибку, зафиксировать испорченный опыт и остановиться, не превращать ошибку в штатный отказ приложения.

До какого-либо HTTP/PG нужны точная реализация, hashes целевых файлов/пробника, отдельное статическое ревью и небольшие no-network проверки прозрачности wrappers: same response/result/context, один original вызов, исходные args/self, normal/exception/cancellation identity, одно enter/exit и body/cleanup ошибки, None/empty/nonempty counts без чтения values, ContextVar reset, cap и terminal summary при переполнении. Эти проверки не заменяют реальные функции и не дают право автоматически повторять V4/87. Реализацию и её приёмку этот проект заранее не объявляет PASS.

## Как интерпретировать и когда остановиться

| Наблюдение | Допустимый вывод |
| --- | --- |
| Access bool false либо original `_eligible` вернул false, issue не входил | Ранний входной отказ, а не доказательство таймаута или пустой БД |
| `_inspect` вернул None, account не входил, precondition false | Ранний inspection prerequisite; неизвестные bool не достраиваются |
| Exception появился в load/body/account-enter/exit/operation, затем наружный None/{} | Отказ в указанной границе проглочен существующим catch; первая ошибка и последующий cleanup фиксируются раздельно |
| Actual work/hard уже истёк в данной точке; TimeoutError/отмена видны на границе | Известен срок и место наблюдения. Generic ProjectionBudgetExceeded не равен доказанному time-limit: он используется также для иных budget/refusal; позднее время не доказывает первопричину |
| Loader вернул count0, account и операция завершились без исключения | Пустой набор **допустимых/render-matching bindings**, а не отсутствие данных/контента в БД |
| Loader count>0, inspection/issue нормально вернули count0 | Путь дошёл до bindings, но не выдал proof; причина signer/ограничений ещё не установлена, это не early eligibility |
| Issue вернул count>0, operation выбросил ошибку, optional вернул{} | Отказ после построения результата, включая cleanup; пустая проекция не доказана |
| Optional вернул count2 и GET200 | Ранняя серверная предпосылка в этом опыте проходит без V4 global tracing. HTML-присутствие proof, старый симптом, POST/M1 и полная приёмка не подтверждены |
| Стадия не вызвана при необъяснимой ветви, unexpected type, собственная ошибка observer, dropped/incomplete | Причина неизвестна; не чинить runtime по догадке и не повторять до PASS |

Остановиться после одного GET и очистки независимо от результата. Нельзя автоматически запускать native POST-сценарий при count2 либо назначать V4/87. Один новый отказ — одно наблюдение для решения следующего узкого шага. Успех без tracing сам по себе не доказывает, что global tracing было причиной: изменились диагностические условия, время и, при отдельном prefix-case, подготовка/состав fixture. Причинный A/B потребовал бы отдельного заранее принятого дизайна с контролем этих различий; сейчас он не назначен.

## Гипотеза о стоимости V4 и пределы фактов

V4 устанавливает global sys.settrace до выполнения native scenario, значит ещё на warm connects/seed/auth/GET. Его callback читает frame.f_locals до фильтра code/marker, а native scenario/relay получают line events. Малое число records не означает малое число callback-вызовов. Metadata relay содержит сотни событий ещё до target/M1, поэтому возможность влияния наблюдателя технически правдоподобна.

Но нет измерения optional elapsed/deadline в завершённом V4 опыте, нет сопоставленного A/B и нет установленного исходного исключения. Поэтому **стоимость tracing — гипотеза**, а не объяснение0 proofs. Предложение убрать global tracing уменьшает вмешательство следующего наблюдения; оно не исправляет предполагаемый runtime defect и не доказывает прежнюю причину.

## Сверенные источники и восстановление требований

| Материал | SHA-256 |
| --- | --- |
| Отчёт законченного native опыта | `fff16801481d324f1d5feeb2e9f74eb8cfca5e26689ea7e8c1be30c8ce01ee1b` |
| Native metadata JSON | `52096a596702fe6846aa08d6360c516f00154d2d9ecf64287bd573630a7d7d33` |
| `cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `cabinet/result_visibility.py` | `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04` |
| `cabinet/result_projection_session.py` | `b9a25a268349afa95caf6f5384e1953bdfee44a1197453a9c526b5839439229e` |
| `api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| Native integration | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Budget/relay | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |

По document-reading восстановлено собственное чтение в этом же диалоге: сам guidance перечитан целиком; применимые оригиналы constitution II/IV/VI и Development Workflow, PRD14/23/25/31, product-gates Diagnostics/Server boundaries, result-visibility §5, plan/spec/tasks/quickstart T112, исходные четыре функции и result-session/fresh-bindings, текущая status-шапка. Предыдущее собственное полное чтение неизменных требований и contracts сохраняется; длинный status/история не выдаются за новое полное чтение. Неизменность сверена по всем18 unchanged_inputs прежней карты: **18SAME**, включая research/model/analyze и четыре списка. Карта не заменяет оригиналы и не подтверждает реализацию.

Актуальный пересчёт reviewer-owned checklist: requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124 checked/0 unchecked**. Все текущие вопросы прочитаны в собственном предшествующем V4 review; hashes неизменны, отметки не менялись. Значение totals — качество требований, не живое измерение или приёмка нового опыта.

Настоящий period остаётся `yield None`; Postal остаётся почтой ГРАФ. T098/T113/T0/restore/readiness, unknown repeated HOLD и полная T112 остаются открытыми. Состояние всей публичной Метрики и текущий release/runtime/provider не перепроверялись. Трафик/продажи, новые публикации/CD/внешние события этим проектом не созданы и не подтверждены. Старые закрытые P2-D01/P2-01/P2-V4-01 сохраняются как отдельные ограниченные решения; прошедший V4-допуск использован, новый опыт требует конкретного нового ревью.
