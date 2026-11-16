# T112 — исходная проверка штатного завершения соединения

16.11.2026. Существующий F273/T112, полоса `high-risk-product`.
Документальная основа `e9eb5076197bbac912aa0f5b9118ded0f35f6edd`;
runtime guard остаётся побайтово прежним. Рабочий сбор выключен.
Контент и вёрстка сайта не меняются.

## Допуск и область

Независимый [проект двух проверок](t112-driver-close-preflight-20261116.md)
полностью прочитан до тестового кода; SHA-256
`a94840a222362b123096234fd72369461698d0b13ab10e3e505017b0421567cd`.
Перед baseline существующий reviewer заново подтвердил checklist124/0 и
применимость scoped analyze. Это допуск теста, не исправления runtime.
18 ранее прочитанных входных хешей совпали; применимые оригинальные разделы
восстановлены в том же диалоге по разрешённому владельцем порядку F273.
Нового полного чтения всей исторической документации этим не заявляется.

Обычная сеть и задержанное завершение одного native handler используют
настоящий `AsyncConnection.invalidate(exception=None)` после SELECT1/PID и
завершённого синтетического commit. Auth/tenant/CSRF/renewal остаются настоящими
и используют direct engine. Его pool_size=3 обеспечивает место для отдельного
foreign connection, observer и обычной авторизации. Request engine имеет
один slot и до fault ровно один поток через существующий TCP relay.

В relay добавлены только необязательные `eof_gate`/`eof_seen`; прежние три
возвращаемых значения и callers сохранены. Server→client EOF удерживается
отдельно от данных; обычный data gate открыт. Public invalidate/close callbacks
наблюдают cause=None, exact owner/task/entry/lease/DBAPI/driver/PID и отсутствие
транзакции. Native close/rollback/terminate и библиотечные состояния не заменены.

Наблюдатель с пустым Context через direct engine подтверждает upstream EOF,
исчезновение target backend и locks до отмены request task. В fault он также
видит is_closed=True при ещё незавершённых request/relay и закрытом EOF gate.
Этот флаг не объявляется доказательством освобождения сокета.

## Законченный исходный результат

**1 normal PASS / 1 delayed-EOF FAIL / 25 deselected / 1 прежний fixture warning.**
Pytest5.49s, runner9s, terminal59345 EXIT1,
`postgres_test_cleanup=isolated_container_removed`.
Collection_count2/digest
`ccce981630874985a7e397fed77ddbffe162deaf84148862d8be5cf2021ba2d6`.

Normal завершил полный accepted примерно за0.103s. Пройдены native invalidate,
законченный relay/wait_closed, пустые owner/transaction/pool/task следы до
teardown, committed renewal, нулевой ledger, сохранённый foreign PID/SELECT1
и новый checkout с другим native driver/PID.

Delayed EOF дошёл до той же настоящей native фазы: commit завершён,
backend/locks отсутствуют до cancellation, upstream EOF удержан, closed flag
уже True, watchdog ещё не сработал. Около2.004s HTTPX ASGI transport получил
отсутствие полного ответа (`response_complete` false, asgi.py:181).
Это конечный отказ бюджета; после ошибки fixture снимает задержку только для
уборки. Watchdog3s не используется как продуктовый срок.

Поздние fault-проверки законченного socket/close/relay/owner cleanup и нового
checkout не достигнуты и не объявляются PASS из успешного удаления стенда.
Синтетический commit до задержки не объявляется rollback; retry отсутствует.
Native graceful-close shield и его дальнейшая отмена требуют отдельного
разбора исходников и независимого проекта до изменения guard.

Первая попытка также дала normal PASS, но повторный close callback при
fixture dispose с owner=None замаскировал исходный отказ ASGI. Наблюдение
исправлено до однократного callback для target поколения; повторный запуск
двух случаев обоснован этой тестовой правкой. Первый журнал сохранён отдельно
и не подменяет окончательный baseline.

| Вход | SHA-256 |
| --- | --- |
| Неизменный `api/product_analytics_guard.py` | `b22a95714a2e6d94ec1645bad0475e1b99b518386caa7ebab785fb0d42dd0088` |
| Новый `contract/test_result_view_http_budget.py` | `084e0c3a561c982be062eab334de17985e8388737163f50198dc5b51b09c0e16` |
| Итоговый `/private/tmp/graf-t112-driver-close-baseline-final-20261116.log` | `c42b671864664f8bdce3b0f79ead32d39ff1819d0960bfd92992d324e956962d` |
| Первая попытка `/private/tmp/graf-t112-driver-close-baseline-20261116.log` | `b311f29d49ee485a47ec66789e0ac728234461876075454076f79917d626716c` |

Ruff и git diff --check прошли. Перед стендом свободно150049840KiB, выше80ГБ;
архивы и зависимости не копировались. Runner удалил свой временный контейнер.
Прежний207 без изменения guard не повторялся.

## Непринятые границы

Это исходный причинный тест, а не исправление или успешная приёмка бюджета.
Независимое ревью baseline и отдельный проект runtime исправления ещё нужны.
Обычный close/TLS/pool reset, same-pool foreign isolation, прочие connect/
commit исходы, полный защищённый HTTP/issuance/ledger/browser/native T112/T113,
restore/runtime/T0, PR/CI/merge/выпуск и коммерческий результат остаются открытыми.

## Исправление C1 после независимого проектного допуска

Независимый reviewer принял исходный результат как causal RED C1/P2 и отдельно
согласовал минимальный public runtime проект. Основной агент полностью прочитал
всё новое дополнение перед guard правкой; текущий SHA-256 отчёта
`eece78510fec7918b0a89faa44e6cb89f9857d9a6489f134ffb010a0f070dd77`.

В существующем Pool.invalidate callback появилась отдельная ветвь только для
причины None. Она требует принятого обычного lease5, точных owner/task/Context/
entry/DBAPI/native driver/generation, checked-out entry и отсутствия initialization/
root association. Противоречие отмечает failure только текущего owner, не меняя
чужие ссылки. Открытый native driver без транзакции завершается публичным
terminate **до** native graceful close. is_closed проверяется раньше
is_in_transaction. SQLAlchemy сам заканчивает bookkeeping/checkin. Прежняя
CancelledError ветвь, её pre-ping fallback и DB-first порядок сохранены.
Нет private API/transport, новых параметров/таймеров, retry или отмены всех задач.

24 новые unit-проверки сначала дали **21 FAIL /3 PASS /174 deselected**,0.73s:
на прежнем guard не выполнялись новый own abort, обнаружение противоречий и
проверки состояния driver. После правки: **24 PASS /174 deselected**,0.04s.
Проверяются foreign/absent/stale lease, owner/task/Context/entry/wrapper/driver,
initialization/root, причины, активная транзакция и уже закрытый protocol.
Чужие maps/driver не изменяются, failure сохраняется у текущего owner.

Native test теперь честно различает исходный graceful путь и новый упреждающий
abort по публичному состоянию при Pool.close. До invalidate driver открыт,
его SELECT1/commit завершены; при Pool.close исправленный driver уже закрыт.
Fault EOF gate ставится до invalidate, данные/SQL/commit не задерживаются.
Client EOF может завершить оба pump раньше публикации upstream EOF; observer
принимает это только при полностью законченном relay, затем подтверждает
исчезновение backend/locks. Он не проверяет освобождённый protocol повторным
is_in_transaction и не заменяет cleanup одним closed flag.

Новый focused native профиль: **2 PASS /25 deselected /1 прежний warning**,
3.63s/runner7s/terminal40658 EXIT0, isolated_container_removed/result pass.
Обычный/fault ответ около0.094/0.077s, путь preemptive_abort; upstream_eof=False
в обоих случаях из-за штатного завершения по client EOF. До gate.set/teardown
в исходном2s закончены owner/handler/close/relay/pumps/wait_closed, пусты оба
реестра и pool, target backend/locks отсутствуют. Renewal сохранён, ledger0,
foreign PID/SELECT1 неизменны, новый native checkout использует другое поколение/PID.

Окончательный профиль изменённого поведения: **233 PASS /0 skips /1 прежний
fixture warning**,198 unit+27 contract+8 integration,48.58s/runner53s,
terminal61198 EXIT0. Подтверждены isolated_container_removed и
postgres_test_result=pass. Collection233/digest
`db682996e8827c65a688b462dbaa8363644b755aa79686844ad018c08edf1ffb`.
Он включает прежние проверки авторизации/CSRF/renewal, small pool, sleeping SQL,
pre-ping, startup, native Session.close rollback, initialization и I1.
Прежний207 отдельно не повторялся и не используется вместо нового профиля.

| Исправленный вход | SHA-256 |
| --- | --- |
| Guard | `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14` |
| Unit | `7dbb443ab4f8ea2dc9211b98b742b5f7db778c4c6823f2285b52a3f3aa26aa57` |
| Contract | `179ab88cf95fdd02f2a53be0cd22c9d0c474ac8b62376f8893db1219041e9932` |
| Unit RED log | `7e477559e3c2c92d302194644c40998d171956968ab2d21dd852fd6941b1254d` |
| Unit GREEN log | `52cd1dd8e3c2cdb2c56880659e78b099c8a733b55a652ac70df9de06e8e49db7` |
| Focused native log | `7d3fab8629e90f337fb66845c00e085e2f0d90a847ccfb1ae0aaa3953d720200` |
| `/private/tmp/graf-t112-driver-close-full-20261116.log` | `dd7bd28a0a08e13d5dc2c10636ddc962135599e57026b2651170151110a25e80` |

Это локальный GREEN исправленного узкого пути; независимая проверка реализации
ещё не получена. Обычный close/TLS/reset, прочие commit/cleanup фазы и весь
T112/T113 не приняты; merge/выпуска/рабочего включения, T0 или трафика нет.

## Независимая приёмка реализации C1

16.11.2026 существующий проверяющий закончил ревью checkpoint
`37274e642820ef87ba52a6dd6e8cd8ed185fe595`: **SCOPED PASS, P1=0, P2=0**.
Основной агент полностью прочитал новое дополнение в
[отчёте проверяющего](t112-driver-close-preflight-20261116.md), сверил его
SHA-256 `fe303b41d68c2a65369d8f1635259b9d5d5e13df45d68d688a8cc1e34132acbf`,
актуальные guard/unit/contract и четыре законченных журнала с таблицей выше.
18 прежних входных хешей совпали; четыре списка требований остались
16/0+27/0+52/0+29/0=124/0 без переотметок.

Принято только предотвращение C1 при hard invalidate(None) точного собственного
открытого idle native соединения: проверенное владение, public terminate до
graceful close, прежний CancelledError/DB-first путь и сохранность чужих
ресурсов. Native доказательство включает полный ответ и освобождение задач,
сокета, backend/locks до снятия задержки, а не один closed flag. Законченный
профиль233 принят без повторного запуска: новой находки или правки кода нет.

Текущий срез сохранения заключения — docs-only в существующей high-risk-product
F273; runtime/test код не меняется. Следующая неподтверждённая граница — обычный
close и возврат соединения в пул, TLS/reset/recycle и остальные исходы. Полные
HTTP/issuance/ledger/browser/native T112/T113, restore/runtime/T0,
PR/CI/merge/выпуск, рабочий сбор, визиты, регистрации и продажи остаются открытыми.
