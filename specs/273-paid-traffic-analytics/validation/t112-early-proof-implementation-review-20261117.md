# T112 — независимое ревью реализации one-GET пробника

17.11.2026. Проверяющий `/root/public_counter_readiness_review`. F273/T112/#7698, T113/#7804, существующая полоса `high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`, exact HEAD по поручению `ef9f5047ac5ac6c3ba2381e05b985b5071f3875c`. Прочитано целиком `/private/tmp/graf-t112-early-proof-implementation-review-request-20261117.txt`. Только статическое чтение и этот новый отчёт; код, прежние отчёты, требования/план/tasks/checklist, Git/GitHub, службы и чужие изменения не менялись. Observer/selfcheck/приложение/тесты проверяющим не исполнялись; новых агентов не создавалось.

## Вердикт и граница допуска

**SCOPED IMPLEMENTATION PASS, P1=0/P2=0** для probe SHA-256 `e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8` и selfcheck `c73fa8b646f0d028e9f64d3b027018e4d8e0dee2203ac5c146b0211e4ddf8608`.

**Один GET/PostgreSQL диагностический опыт допустим по этому конкретному reviewer gate.** После проверки побайтового SHA разрешённой временной копии в `apps/server` — только `test_early_proof_single_get` через штатный focused runner с изолированной БД, прежними исходниками и сроками, затем очистка и снятие временной копии в finally. Нельзя загружать сохранённый файл непосредственно из validation: root source pins намеренно рассчитан на расположение временной копии в `apps/server`. При изменении hashes, механизма загрузки либо источников допуск автоматически не переносится.

Это новый ограниченный допуск, не возобновление использованного V4. POST/M1/native commit-тест/V4/87 не назначены и не запускаются автоматически ни при каком результате GET. PASS относится к наблюдателю и прозрачности его ограниченного механизма, не к успешности будущего GET/proof, причине старых отказов, рабочему T112/T113, выпуску, T0 или коммерческим критериям. В этом ревью GET/PG не выполнялся.

## Проверенные входы

| Материал | SHA-256 |
| --- | --- |
| `validation/t112-early-proof-probe-20261117.py` | `e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8` |
| `validation/t112-early-proof-selfcheck-20261117.py` | `c73fa8b646f0d028e9f64d3b027018e4d8e0dee2203ac5c146b0211e4ddf8608` |
| Собственный принятый проект `t112-early-proof-diagnostic-design-20261117.md` | `49fa99b03cd42e4b061605c3c2300a06712c3f03dcbb58693217241a367acbd6` |
| Авторский `t112-early-proof-draft-validation-20261117.md` | `68792d7b3afdef1539c6feada3288073c09b3d47f70e20435fd979ec064d732b` |
| `/private/tmp/graf-t112-early-proof-selfcheck-20261117.log` | `bbc7c7fe07cbe000442520991b5303685e0e6277d88258060a0d81bf5a206561` |
| `/private/tmp/graf-t112-early-proof-selfcheck-20261117.json` | `e6f6b486592b578bae4f4fc25a8371f7cc332d4c7de221fff08e747538964641` |

Probe/selfcheck/draft-report/log/receipt прочитаны целиком. Собственный проект и применимые оригиналы прочитаны в непосредственно предшествующем проходе того же диалога, содержание сверено. Повторно прочитаны реальные browser call site, optional helper и inspection boundary, а также настройка PYTHONPATH штатного runner. Все шесть PINS независимо вычислены по текущим файлам и совпали:

| Источник внутри apps/server | SHA-256 |
| --- | --- |
| `tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| `tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| `src/twobrain_rec_server/cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `src/twobrain_rec_server/cabinet/result_visibility.py` | `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04` |
| `src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |

Runner устанавливает рабочие `apps/server` и `apps/server/src` в начало PYTHONPATH до pytest. Именно этот путь входит в допуск: только проверка файлов на диске сама по себе не доказывала бы provenance imports при произвольном запуске через shared editable install.

## Прозрачность и соответствие проекту

Семь наблюдаемых стадий соответствуют принятому проекту. `install` захватывает оригиналы до monkeypatch; class-function wrappers сохраняют передачу self через `*args`; вызов всегда делегируется захваченному оригиналу один раз. Inactive ветвь не создаёт записи. Browser импортирует optional helper из result_views внутри обработчика, issue импортирует loader из result_visibility при вызове — выбранные точки разрешения имён действительно охватывают эту цепочку. Сам signer, owner/checkpoint/_refuse/DB/Pool/driver не подменяются.

Async boundary возвращает тот же объект, при Exception/CancelledError делает bare raise после записи только типа/модуля. Eligibility вызывает оригинал один раз; неизвестный тип результата даёт allowed=None/incomplete, не преобразуется в bool и не меняет возвращённое значение. Access/principal/session bool отражают имеющиеся аргументы; исходные проверки `_eligible`, admission, deadline validation и fences не вызываются второй раз.

Transaction wrapper использует исходный async with, yield того же context и один original enter/exit. Body exception записывается до исходного __aexit__, затем передаётся ему; подавление оригинальным manager сохраняется, а его изменившаяся cleanup-ошибка распространяется. Поля observation не дают wrapper собственного владения DB: нет commit/rollback/close, новых awaits кроме исходного context-протокола и делегирования. Test-only http_period остаётся прежним; настоящий runtime period не подменяется новой реализацией.

Пробник явно выполняет два warm connects/SELECT pid/commit/close, прежние real_app/relay/native auth и ровно один client.get. Это prefix-only case, не урезанный исполняемый original native test. После GET нет _proofs/page.text/body/headers/proof parsing, POST, M1/watchdog/fault. ACTIVE устанавливается только на время GET и сбрасывается в finally; внутренние задачи наследуют тот же Observation, не переписывая task factory/Context(). Оба engine и собственный relay очищаются штатными finally/context manager. Нет global tracing/profiling/monitoring и чтения SQL payload.

Actual work/hard значения берутся из kwargs issue/inspection/account, сравниваются с loop.time и не меняются; до их получения стоят None. Summary содержит только фиксированные stage/event labels, bool, counts, времена, форму результата и type/module исключений. Dict shape использует только isinstance/len; proof/binding keys/values не читаются. Ни аргументы/контекст/response/owner/исключения/tracebacks, ни их repr/str не попадают в records или summary. Временные ссылки внутри делегируемого вызова нужны для сохранения исходного объекта и не становятся диагностическими данными.

Cap32 ограничивает records, dropped/incomplete отражают переполнение; summary имеет максимум семь стадий и обновляется независимо от cap, сохраняя первый exception type/module. Поэтому последний этап не вытесняется полным буфером. Вывод расположен после _run и очистки; ordinary stdout предпосылки не доказываются этим ревью, но код не добавляет печать или сетевой/файловый I/O в активный GET.

## Доказательства selfcheck и пределы проверки

Журнал и совпадающий receipt сообщают **15 synthetic PASS/EXIT0, network_calls=0/database_calls=0**. Скрипт AST извлекает только Observation/shape/error_type/boundary/eligibility/transaction и не импортирует приложение/fixture. Три результата None/empty/nonempty проверяют identity и отсутствие keys/values access; два случая ошибки/отмены — тот же original exception; два eligibility bool — один original вызов. Шесть manager-сценариев проверяют normal/entry/body/cancel/suppress/cleanup, один enter/exit, identity context/ошибок, передачу body error оригинальному __aexit__. Ещё два случая проверяют privacy/cap/terminal после переполнения и inactive delegation/ContextVar reset.

Это поддерживает статический вывод о прозрачности обёрток, но не является исполнением реальных optional/inspection/operation функций, установкой monkeypatch в pytest, проверкой sourcepins при копировании или реальным GET/PG. Особые ветви формирования access/principal facts не исполняются этими синтетическими случаями; их текущие kwargs сверены статически с оригинальными caller/signatures. Проверяющий не запускал selfcheck; факт прошлого исполнения поддержан прочитанным raw log/receipt, его не следует выдавать за новый запуск.

## Как принять результат единственного GET

Сам diagnostic test не утверждает HTTP200, число proofs или полноту цепочки. **Pytest PASS здесь означает, что пробник завершился, а не что выдача proof исправна.** Оценивать отдельно http_status/http_elapsed, summary каждого достигнутого stage, actual остатки сроков, None/empty/nonempty и первую ошибку. Если stage не достигнут, отсутствие строки не равно положительному/нулевому факту; incomplete сейчас отмечает переполнение/неожиданную форму, но само по себе false не доказывает, что вызваны все семь стадий.

При раннем access/eligible отказе — входная ветвь. При None inspection без account — проверять preconditions. Ошибка account-enter/body/exit/operation до наружного None/{} локализует существующий catch, но generic ProjectionBudgetExceeded не доказывает time-limit. Loader count0 — пустые допустимые/render-matching bindings, не пустая БД. Issue count>0 с последующим operation raise — отказ после построения результата. Optional count2 и GET200 подтверждают только серверную предпосылку этого опыта, не HTML-вставку и не причину прежних0proofs.

Остановиться после одного GET/cleanup независимо от результата. Если есть собственная ошибка наблюдателя, отсутствующая стадия при необъяснимом пути, dropped/incomplete либо симптомы не воспроизвелись — причина остаётся неизвестной. Даже без global tracing обёртки имеют расходы; успешный новый prefix-case не доказывает причинность старого tracing. Не повторять до PASS, не менять сроки/caps/locks/F/B, не включать runtime и не переходить автоматически к POST/V4/87. Сохранить raw log/точные hashes/результат очистки; полное тело развёрнутого failure не включать в Git.

## Требования и неизменные границы

Свежая сверка карты `/private/tmp/graf-t112-root-history-reading-20261116.json`: **18SAME**. Собственные чтения применимых оригиналов по document-reading восстановлены в предшествующем design-проходе: constitution/workflow, PRD14/23/25/31, product-gates, result-visibility, plan/spec/tasks/quickstart T112 и исходные зависимости. Они не заменялись пересказом исполнителя. Актуальный пересчёт checklist: requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124 checked/0 unchecked**; вопросы ранее прочитаны собственноручно в том же диалоге, hashes неизменны. Маркеры не менялись; качество требований не равно реализации/выпуску.

Текущий оригинал `_result_period_context` перечитан: настоящий `yield None` сохраняется. Postal остаётся почтой ГРАФ. Unknown repeated HOLD, T112/T113/T098/restore/readiness/T0 и коммерческие критерии открыты. Состояние всей публичной Метрики/release/runtime/provider и внешний трафик здесь не проверялись. Этот отчёт не создаёт публикаций/CD/событий/продаж.

**Итог: exact implementation PASS/P1=0/P2=0; допустим один самостоятельный one-GET/PG диагностический опыт с последующей очисткой. В этом ревью ничего не исполнялось.**
