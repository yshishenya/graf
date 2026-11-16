# T112 — повторное независимое ревью observer v2 и проект наблюдения двух новых отказов

17.11.2026. Проверяющий `/root/public_counter_readiness_review`. Существующая F273/T112/#7698 и T113/#7804, полоса `high-risk-product`; только независимое чтение и этот отчёт. Актуальный HEAD копии `/private/tmp/graf-f273-result-visibility-20261116` — `47944415aa979b468ca0d9ce7a4c32ef2adc075f`. Указанный в файле поручения `f8eabd30c5e11b9ccb28284c8559142d3a6f366d` — историческая основа попытки, не текущий HEAD. Код, тесты, требования, списки проверки, прежние отчёты, Git/GitHub и рабочие службы не менялись. Ничего не исполнялось из observer/selfcheck/application; тесты и службы не запускались, новые агенты не создавались.

## Решение

**V2 DIAGNOSTIC HOLD, P1=0/P2=1. P2-D01 устранён частично и остаётся OPEN**: семь заявленных случаев исправлены, но `response.json()` по-прежнему может выбросить `RecursionError` в `finally`. Минимальная следующая правка — добавить этот конкретный отказ разбора к уже обработанному `ValueError`, сохранив status=None и неизменный исходный response. Общий trace-подход не отвергнут; новая версия требует точного статического чтения до исполнения.

Проект ниже ограничивает следующее наблюдение normal POST2 и раннего fault POST1. Это **проект для реализации и последующего ревью**, не разрешение запустить новый87, не приёмка ещё не написанного наблюдателя и не основание исправлять runtime по предположению. Unknown repeated HOLD, полная приёмка T112/T113/T098, восстановление, T0 и коммерческие критерии остаются открытыми. P2-01 checkout/checkin остаётся CLOSED по отдельному прежнему отчёту.

## Точные прочитанные материалы

| Материал | SHA-256 |
| --- | --- |
| Observer v1 `/private/tmp/graf-t112-repeat-trace-v1-20261116.py` | `9cb8aa72c07ded03f2b34206261d8dc5945d13264ac883faa293542b66a0dc76` |
| Observer v2 `/private/tmp/graf-t112-repeat-trace-v2-20261116.py` | `99881be3823365bac92d9fb059138eac5ba55e1ea4aa912d75114237e6799aa3` |
| Selfcheck `/private/tmp/graf-t112-trace-status-selfcheck-20261116.py` | `bcd458427981a0c07594c8207a9cd8a889c9baa3118a8bc45d1afee1935949b8` |
| Selfcheck log `/private/tmp/graf-t112-trace-status-selfcheck-20261116.log` | `33592c9c3d836cf68e1dbeaa13284bf911db8bba9c33baca118013ba1a609451` |
| Законченный профиль `/private/tmp/graf-t112-repeated-fault-trace-v1-20261116.log` | `c032537688103afe8a6bc460b4d0f2645d6165bfab3c4afd5aceb61d6d9bcb0a` |
| Собственный предыдущий `t112-repeat-trace-design-review-20261116.md` | `36b2ea20d2a15310e725413389cd2c9456fd803454f492c66fe896a9fbb6f7ef` |
| Авторский `t112-repeat-trace-attempt-20261116.md` | `a7a8a9c3e9b00942f3c396e94927acf2f0d68cf35dea8f302200fafdf9247b14` |
| Native integration `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Budget/relay `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| Guard `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |

V2 и selfcheck прочитаны целиком; собственный design-report и новый attempt-report также прочитаны целиком. В общем журнале прочитаны collection/result/cleanup, ранний normal marker и обе целевые цепочки отказа; весь журнал не выдаётся за построчно прочитанный. Для следующего проекта прочитаны `_guard_result_view`, `_result_view_unavailable`, `_run_result_view_operation`, native сценарий и настоящий relay `_postgres_response_gate`. Первоначальные чтения неизменных требований сохранены в том же диалоге; карта `/private/tmp/graf-t112-root-history-reading-20261116.json` проверена по содержимому, не использована вместо требований.

## P2-D01: что исправлено и что осталось

В v2:100–109 status сначала None; невалидный JSON с `ValueError` даёт decoded=None; массив/число не проходят dict; нестроковое и неизвестное строковое значение не проходят whitelist accepted/unavailable/renewed. Не выводятся body/proof/headers либо текст ошибки. Tracer и ContextVar восстановлены до разбора ответа. Wrapper по-прежнему делегирует original_post ровно один раз на вызов, не меняет методы owner/DB/Pool, выбранные code objects и сроки.

Статический пробел остаётся в v2:103–104: `except ValueError` **не ловит `RecursionError`** стандартного JSON-декодера при чрезмерной вложенности. Например, корректный JSON с достаточно глубоко вложенными массивами/объектами может исчерпать стандартную глубину рекурсии до проверки dict. Ограничение 4096 байт в guard этого само по себе не исключает: около тысячи вложенных пустых массивов занимает около двух тысяч байт. Сам guard уже различает этот класс разбора в product_analytics_guard.py:556. Здесь отказ находится в finally после return, поэтому снова заменит завершённый HTTP-ответ собственной ошибкой наблюдателя. Это статическая находка; отрицательный опыт в этом ревью не запускался.

Минимум: `except (ValueError, RecursionError)` при разборе JSON, затем прежние dict/string/whitelist проверки; ошибка оставляет status=None. Не нужен перехват BaseException, подавление исходного исключения original_post, увеличение recursion limit, подмена ответа, дополнительный POST или изменение runtime. Отдельный синтетический случай глубокой вложенности можно добавить к no-network selfcheck исполнителя; он должен проверять identity возвращённого response и восстановление tracer, не запускать HTTP/БД. Это не разрешение мне запускать такую проверку и не новый интеграционный профиль.

Существующий журнал selfcheck содержит только `observer_status_selfcheck=pass cases=7 network_calls=0`. Код действительно задаёт семь случаев, проверяет тот же объект ответа либо то же synthetic исключение, ровно два original вызова, status whitelist и восстановление tracer. Это достаточное свидетельство для этих семи случаев, а не полный перебор ошибок JSON или приложение/БД. ContextVar reset виден статически; selfcheck не проверяет его значение отдельным assert. Он также не упражняет реальные выбранные owner/guard frames и не доказывает причину старого отказа.

Ни исторический JSON unavailable, ни нынешний normal transport AssertionError этим остатком P2-D01 не объясняются. Если original_post выбрасывает исключение, response остаётся None и JSON не разбирается.

## Проверка завершённой попытки

Collection87/digest `6d62f13844d8b8bd0585c7b7032e595806dc81de0189e50d55d7a7a46a85b28d`; строки журнала3005–3007 подтверждают **22FAIL/65PASS/2warnings,258.22s**, runner288s и `isolated_container_removed`. EXIT1 записан автором; результат FAIL подтверждён журналом, нового опроса завершённого процесса не делалось. Старые87PASS не складываются с65 и не заменяют этот исход.

Normal: ранний marker журнала:138 фиксирует fault=False, elapsed1.161, offsets[0,1], same_pool_foreign/safe_reuse=True, watchdog=False. После этого отдельный POST2 достигается на integration:1262; traceback журнала:2455 и:2559–2563 заканчивается `httpx ASGITransport:181 assert response_complete.is_set()`. Это отсутствие **завершённого** ASGI-ответа; marker не доказывает отсутствие response.start или частичного body. Нет возвращённого HTTP response/status для этого вызова. Из одного AssertionError нельзя выбрать конкретную ветвь guard либо приписать сбой нагрузке.

Fault: первый POST и отдельный M1 observer останавливаются на ожидании `response_held` integration:1117, внутри timeout_at на:1115; исходный CancelledError превращён timeout manager в TimeoutError. До явного POST2 сценарий не дошёл. Observer сам имеет Context(), отдельный от HTTP task. Его ранний timeout — отдельный наблюдавшийся исход, не доказательство второй ошибки и не подтверждение нужного M1 снимка.

Число строк `t112_repeated_fault_trace` — **0**. Это согласуется с областью v1: normal исключён fixture, fault POST2 недостигнут. Следовательно JSON-finally v1 в нужном traced post не исполнялся; P2-D01 не является объяснением22FAIL. Авторский attempt-report корректно сохраняет эти границы, ошибку запуска до конкретного вердикта и отсутствие установленной причины. Значения load averages из его отдельного наблюдения не проверялись причинным опытом; доказанной причины нагрузки нет.

## Минимальный проект следующего наблюдения

### 1. Разделить HTTP и независимый M1 observer

Ограничить fixture точным native test, обеими его параметризациями и явными этапами. HTTP marker должен содержать только synthetic case normal/fault, ordinal POST1/POST2 и монотонное относительное время. **Да, normal POST2 нужно включить**: только fault=True,POST2 больше не покрывает наблюдавшийся новый отказ. Для normal достаточно подробного наблюдения POST2; для fault нужно видеть POST1 до ожидания M1 и его завершение/ошибку. Fault POST2, если он достигнут, получает собственную отдельную метку. Счётчик не даёт права добавить запрос или повторить текущий.

Передать HTTP marker дочерним задачам обычным ContextVar наследованием. **Не удалять `Context()`** независимого observer/relay ради диагностики: это изменило бы прежнюю изоляцию. Их метаданные связывать явно с принадлежащими данному сценарию target/stream ordinal в test-only fixture; значения owner/frame/task/stream в журнал не сохранять. В частности, расширение только ContextVar HTTP не позволит увидеть ожидание M1 или relay pumps, созданные с пустым Context.

### 2. До любого silent return сохранить branch/deadline/send metadata

В выбранных code objects guard/operation/unavailable сохранить прежние exception-type events и bounded запись входов. Для текущего исхода одного exception trace недостаточно. Нужны редкие наблюдения конкретных ветвей, привязанные к точному source hash; допустимы только ограниченные line events выбранных frames/строк или синхронные test-only наблюдения, без переписывания условий и без нового вызова функции. Не профилировать строки всей программы.

| Граница | Минимум метаданных и что различает |
| --- | --- |
| Guard после установки deadlines (:519–522) | time от начала POST, work_remaining/hard_remaining; исходные2s,work1.5s,cleanup0.5s |
| Вход/выход `_run_result_view_operation`, join до/после и exception cleanup (:488–509) | failed; числа leases/transactions/unbound_roots; число pending children, done/cancelling состояния собственных задач; что join начался и закончился либо прерван исключением. Не добавлять polling/all_tasks в горячие события; использовать уже вычисленные локальные pending/db_tasks или редкую конечную сводку |
| Guard перед выдачей буфера (:590–600) | buffer_count/response_bytes, число start, terminal_body_present, last_more_body, work_expired, response_started; только счётчики/логические признаки, без содержимого messages |
| Guard exception/выход (:601–604) | exception type/module, response_started, work_remaining/hard_remaining, выбран ли fallback или он пропущен после начала send |
| `_result_view_unavailable` (:458–470) | вход с hard_remaining; дошёл ли до immediate deadline return:459; send start/body attempted/completed; TimeoutError/OSError и ветвь return:470 |
| Guard receive disconnect (:537–538) | только факт disconnect и остатки сроков, чтобы отличить ранний обычный return |

Отсутствие завершённого body может возникнуть при истёкшем hard deadline до fallback, исключении fallback send либо начатом send с пропуском fallback. Это **список различаемых ветвей**, не вывод о причине текущего отказа. Guard `response_started=True` ставится **перед** `await send` на:599–600, поэтому этот флаг сам не доказывает успешную доставку start/body. Для этого нужен отдельный test-only внешний ASGI adapter вокруг существующего app в ASGITransport: один делегированный вызов app и тот же send/receive, синхронная запись attempted перед каждым исходным await send и completed после него. Записывать только тип ASGI-сообщения, status code, more_body и counters, без body/headers/URL. Любое исключение/отмена должны распространяться без подмены; app return и app raise различать. Adapter не делает дополнительного receive/send/await кроме делегирования существующих вызовов и не открывает новый timeout.

`sys.settrace` return event у coroutine может означать приостановку await. Не объявлять каждый такой event завершением cleanup/guard; использовать достигнутую точную ветвь после await либо конечный исход внешнего ASGI adapter. Это необходимо для причинной достоверности, а не расширения покрытия ради числа событий.

### 3. Для раннего fault POST1 — только имеющийся target/relay

В test-only `observe_committed_pair` сохранить метаданные входа: entered/response_held/response_gate, commit-relative time, два остатка `work_deadline-.1-now` и `.9` и фактически выбранный min deadline. При timeout — те же логические признаки, task done/cancelling, relay root/pumps done, client_eof/eof_seen/done и флаг watchdog. Снимать состояние до сценарной finally, открывающей gates и отменяющей задачи; снимок после finally не доказывает состояние в точке отказа.

В существующем test-only relay для целевого stream достаточно синхронных меток: upstream-read-completed, held-check, response_held-set, gate-wait-enter/leave, downstream-write/drain-completed, EOF/exception type. Нет чтения/декодирования PostgreSQL payload, новых чтений, sleeps, таймеров или вмешательства в gate. Target ordinal устанавливается из уже существующего сопоставления stream/driver; foreign generation должна оставаться отдельной. До сопоставления можно хранить только малые счётчики/последние времена собственных stream, чтобы не потерять ранний этап; не захватывать произвольные соединения.

Данные relay читаются в его изолированном Context через собственное состояние fixture; общий HTTP ContextVar не является условием записи relay. Raw chunk из upstream означает полученные байты, **не доказательство COMMIT acknowledgement**. Существующий независимый M1 snapshot двух строк, idle/xact_start=None/no-locks остаётся единственным прежним свидетельством этого этапа; нынешний ранний timeout его не заменяет. Наблюдение должно различить, был ли достигнут read, проверка gate, установка held или уже отмена, не назначая этим событиям заранее причину.

### 4. Границы реализации и допуска

Всё metadata-only, в памяти ограниченного fixture; сохранить лимит96 records с dropped и отдельные маленькие counters/terminal summary, чтобы переполнение не скрывало итог. Нельзя удерживать frames/tracebacks/exceptions/tasks/owners в выводимом буфере; нельзя печатать locals целиком. Только относительные времена, ordinals, bool, counts, source function/line и exception type/module. Не писать body/proof, SQL/parameters, headers, URL, credentials, account/meeting ID, приватный контент и текст исключений. Вывод после исходного завершения/исключения, с восстановлением tracer/ContextVar и невыбрасывающим ошибки разбором; ошибки ввода не превращать в accepted/unavailable.

Сохранить исходный class dispatch, DB/Pool/native методы, нагрузку/fixtures, locks/SQL caps, deadline/cancellation/cleanup, ожидаемые результаты и проверки F/B. Никаких дополнительных попыток, увеличения2s/work1.5s/cleanup0.5s, сокращения требований и runtime fix без причины. Добавленный trace/adapter имеет временные расходы; отрицательный исход под наблюдением не доказывает, что старый untraced отказ имел ту же причину.

Перед любой следующей попыткой нужны точный код минимального observer и его статическое ревью. Возможный последующий профиль — только точные две native параметризации, однократно, с прежними asserts/cleanup, если отдельно будет назначен после этого gate. Новый общий87 в этом решении **не назначен**. Если симптом не воспроизведён, dropped>0 или нужная ветвь не достигнута — причина остаётся неизвестной; цикл повторов ради PASS не допускается. Частичный диагностический результат не заменяет последующую исходную полную приёмку.

## Проверка требований и итоговые границы

Все18 `unchanged_inputs` карты сверены по SHA-256: **18SAME**, включая spec/plan/tasks/quickstart/research/data-model, два контракта, четыре checklist, requirements-review/analyze, constitution/PRD/status/product-gates. Повторно прочитаны все текущие124 вопроса четырёх checklist: requirements16/0, security27/0, privacy-measurement52/0, infra29/0, итого **124 checked/0 unchecked**, без изменений отметок. Это качество требований, не новая реализационная/выпускная приёмка.

Применимые границы восстановлены по оригиналам: document-reading, result-visibility §5–7, plan T112, quickstart T112 и текущие исходные guard/relay/ingest. Настоящий `_result_period_context` в ingest.py:181–188 по-прежнему `yield None`; это не утверждение об отключении всей публичной Метрики. Отдельное опубликованное состояние release/runtime/provider здесь не перепроверялось. Postal сохраняется как почта ГРАФ. Публикаций, production/CD/флагов/почты/провайдеров/внешних событий не менялось; трафик, продажи и готовность аналитики не подтверждены этим отчётом.

**Итог: V2 HOLD/P1=0/P2=1, P2-D01 OPEN только по оставшемуся RecursionError. Минимальный следующий проект описан без запуска; unknown repeated HOLD и остальные открытые критерии сохранены.**
