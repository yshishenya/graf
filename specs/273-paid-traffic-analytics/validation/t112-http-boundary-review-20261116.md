# T112 — независимое ревью внешней HTTP-границы

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `9f37adc897217ea2416cf3ebeccb4373efbe1c70`.
Полоса: существующая `high-risk-product`, только внешний foundation T112.
Поручение: `/private/tmp/graf-t112-http-review-request-20261116.txt`.

## Решение

**PASS исправленного внешнего foundation: P1=0, P2=0.**
H2 независимо перепроверен после исправления и закрыт. Все собственные
отказы используют исходный абсолютный hard deadline; новый профиль
**67 passed, 1 warning, 33.15s** включает шесть причинных случаев blocked send.
Это узкий implementation PASS внешней границы в рассмотренной области,
не полный endpoint/issuance/DB-cleanup или T112/T113 PASS. Первоначальный
REQUEST CHANGES и его доказательства сохранены ниже как история.

Проверяющий прочитал текущий diff guard полностью и оба новых тестовых файла
целиком, применимые auth/renewal/SQLAlchemy границы — по собственному чтению
этого же диалога. Прежние reviewer-owned отметки качества требований 124/0
не изменяются: H2 — ошибка реализации существующего бюджета, не новый
продуктовый вопрос. Код, требования, задачи, Git/GitHub и runtime не менялись;
проверяющий тесты не запускал. Изменён только настоящий отчёт.

## H2 — первоначальная находка, исправлена при повторном ревью

**Первоначальный P2, закрыт; описание первого снимка до исправления.**
`api/product_analytics_guard.py:232` и `:235` вызывали
`_result_view_unavailable(send, ...)` до входа в `asyncio.timeout_at(deadline)`.
Второй путь `:311` вызывает тот же helper уже после выхода из outer timeout,
в том числе после timeout самого внутреннего приложения. Helper `:183–189`
делает два обычных `await send(...)`, не получая deadline и не ограничивая их.

Конкретный триггер: POST совпадающего пути с non-JSON media type либо слишком
большим Content-Length при ASGI send, ожидающем освобождения транспорта.
Другой триггер — медленный receive/SQL/renewal, завершившийся unavailable,
после которого send задерживается. В обоих случаях caller может ждать больше
двух секунд или бесконечно. Успешный buffered response посылается внутри
outer timer, но ошибочные ответы оказываются исключением из обещанной общей
границы. Оставшийся резерв cleanup не ограничивает отправку после context.

Минимальное исправление: все собственные send используют тот же абсолютный
hard deadline, включая ранние format/declared-size отказы и fallback после
ошибки. Не создавать для fallback новый независимый timeout. При исчерпанном
остатке не начинать ещё одно неограниченное ожидание отправки. При частичной
отправке/ошибке транспорта не начинать второй response; текущий принцип
response_started следует сохранить и для общего отказного helper.

Причинная проверка исправления: ограниченный slow/blocked ASGI send для
415, объявленного413 и timeout→unavailable; измерение всего вызова guard,
один response start максимум и отсутствие живых дочерних задач. Новый
сценарий должен падать на текущем коде именно по времени, затем пройти после
исправления. В этом ревью такой тест не запускался; находка основана на
прямом управлении потоком и расположении timeout contexts.

## Что проверено без блокирующих замечаний

### Вход, маршруты и буфер

Новая ветвь срабатывает только на POST shape двух result-viewed путей;
`[^/]+` намеренно охватывает также неканонические UUID/невалидный компонент,
которые будущий string route способен принять до собственного UUID parse.
Иначе альтернативная форма идентификатора могла бы миновать guard. Остальные
пути/методы и прежние три analytics ingress сохраняют старый код. Trailing
slash оставлен штатному router redirect; каноничность будущего handler всё
равно должна совпасть с GET/proof контрактом.

Один work deadline1.5s и hard deadline2s создаются до чтения тела. Строго один
application/json media header проверяется до downstream/auth/form. Stream
считается по фактическим bytes независимо от Content-Length, body<=2048,
proof-only object, непустая ASCII строка<=1536, duplicate keys/NaN/неправильная
форма отклоняются до приложения. Повторно передаётся только принятый body.
После disconnect во время body нет ответа или downstream вызова.

Буфер ограничен 4096 bytes и32 сообщениями. До окончательного возврата
внутреннего ASGI вызова наружу не уходит response.start. Сохранены status и
Set-Cookie/expiry headers, собственный cache-control принудительно
private/no-store. Проверяются единственный start и завершённый body; исключение,
неполный/большой ответ не выпускают предварительный accepted. Входной proof
и exception text не отражаются в отказе, SQL/продуктовых записей этот guard
сам не создаёт.

### Владение соединениями и отмена

Checkout сохраняет owner object, конкретные DBAPI/driver и текущую задачу в
lease точного connection_record. Checkin удаляет запись до pool reuse.
Invalidate callback требует CancelledError, совпадающий owner по identity,
тот же DBAPI и current driver; используется public AsyncpgConnection.terminate,
а не private adapter API или engine.dispose. Callback обычных запросов без
owner не завершает их соединения. Регистрация сделана однократно на Pool
при импорте, новые session factories и auth shortcuts не вводятся.

Реальный DB owner task отменяется до parent ASGI task group. Это позволяет
обычному SQLAlchemy invalidation закончить bookkeeping без повторного
вмешательства родительской отмены. Join проверяет tasks с тем же ContextVar
owner по identity, исключает текущую задачу и повторяет поиск после каждого
завершённого набора, охватывая созданные во время отмены shielded tasks.
Нормальный путь тоже дожидается потомков и отвергает оставшийся checkout.

В реальных PG тестах прочитаны auth/renewal pg_sleep cancellation,
освобождение pool и успешный следующий SELECT1. Параллельный чужой connection
сохраняет backend PID и работоспособность. Малый pool при renewal получает
держателя в новом Context без owner после auth checkin; отмена следующего
ожидания не уничтожает держателя и pool работает после его закрытия.
Это полезные причинные подтверждения checked-out/return/reuse границы.

### Auth, renewal и неизвестный исход

Тестовое приложение использует настоящие Principal/WebTenant/WebCSRF и
session_renewal middleware с настоящей PostgreSQL. Cookie+CSRF и штатные
session headers положительны на обеих поверхностях; missing auth и cookie
без CSRF сохраняют401/403. Быстрый renewal действительно сохраняет expiry и
возвращает cookie/header, а не заменён заглушкой единственного positive case.
Handler при этом **синтетический и не пишет ledger**.

Тест delayed return после уже совершённого renewal commit проверяет
unavailable, единственный commit, сохранённое новое expires_at и отсутствие
повторной операции. Guard не объявляет отмену доказанным rollback и не
повторяет внутренний app/admission. Реальный ambiguous ledger commit этого
foundation-теста не моделируется; он остаётся общему service профилю.

## Первый профиль61 и исходный снимок до исправления H2 — история

Самостоятельно прочитан завершённый журнал
`/private/tmp/graf-t112-http-boundary-green-20261116.log`:
**61 passed, 1 warning, 20.60s**, runner focused pass24s,
isolated_container_removed/result pass. Основной агент отдельно подтвердил
terminal EXIT0. Старые промежуточные59 и незавершённый запуск за этот итог
не выдавались. Проверяющий не запускал повторный профиль.

| Проверенный вход | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `c62446ab6d636e40fd56c800f790e2529e0cc4ab969d54bd870fdd68d71ad723` |
| `apps/server/tests/unit/test_result_view_http_guard.py` | `4c542159a2327726a8ba154c6da2983e2697246ead55ff9bc4decacaade7d95b` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `a4b2cb347ba679964bfbc5312330f1dcc0c6b2208aa48db675c4be78029991a1` |
| `/private/tmp/graf-t112-http-boundary-green-20261116.log` | `5db529b73a6eeb10c4bb779c431ec7a5eeb855673f8aff5a1f0a04e9583dae36` |

## Пределы, которые этим профилем не приняты

- Нынешний PostgreSQL engine fixture не включает production pool_pre_ping;
  pre-ping/connect/init идут до checkout event и по прежнему preflight ещё
  требуют отдельного доказательства владения и bounded cancellation.
- Нет полноценного штатного slow-close/rollback профиля и всех исходов,
  когда второй hard timeout прерывает join. Текущий код не является общей
  гарантией завершения произвольного cancellation-resistant cleanup.
- Нет независимого PG observer для всех activity/lock исходов после
  прерывания commit; pool.checkedout0 и SELECT1 не заменяют такую проверку.
- Нет окончательных endpoints/service wiring, GET issuance/renewal/HMAC,
  render exact projection, большого review cardinality/size guard,
  browser/native наблюдения или полного атомарного ledger HTTP пути.
- Настоящий T113 readiness остаётся закрытым; runtime restore/local_only/T0,
  exact-SHA CI/merge/release, реальные визиты/регистрации/оплаты не приняты.

Эти границы были явно оставлены в поручении и проекте; они не скрыты за
61/67PASS и не отмечаются выполненными. H2 исправлен и принят ниже; остальные
границы сохраняются до соответствующей отдельной приёмки.


## Повторное независимое ревью исправления H2 — окончательный текущий снимок

Прочитано дополнение поручения, весь актуальный diff и новые шесть тестов.
Guard и unit-файл изменились только в описанной области H2; DB test имеет
прежний SHA-256. Проверяющий не запускал успешный профиль повторно и не
изменял код/требования/задачи/списки/Git/runtime.

`_result_view_unavailable(send, deadline, status)` теперь:

- проверяет текущий loop.time до первой отправки и возвращается без новой
  попытки, если исходный hard deadline уже исчерпан;
- выполняет оба await send под `asyncio.timeout_at(deadline)` с тем же
  абсолютным значением, а не новым сроком;
- после TimeoutError/OSError завершается без второй попытки response.

Все три места вызова — ранний415, объявленный413 и fallback после
аналитической ошибки/timeout — передают первоначальный deadline. Обычная
отправка собранного успешного ответа остаётся в прежнем outer timeout и
сохраняет защиту response_started от второго ответа. H2 больше не найден;
дополнительных P1/P2 в рассмотренном изменении не обнаружено.

Новый параметризованный тест причинно покрывает media415, declared413,
work timeout→unavailable, для каждого блокируя response.start либо body.
В blocked send ожидается Event, cancellation отмечается в finally; watchdog
2.3s только ограничивает ошибочный старый код. Проверяются законченный guard
с elapsed<2.15s, один start, ожидаемый статус, отменённый send, отсутствие
downstream на ранних отказах и отсутствие оставшихся asyncio tasks.
Допуск0.15s относится к измерительной погрешности теста; код продолжает
использовать2s. В GREEN журнале все шесть случаев занимают2.00s.

Самостоятельно прочитан RED журнал
`/private/tmp/graf-t112-http-send-red-20261116.log`: первый blocked
response.start/media case действительно остановлен watchdog, `completed=False`,
**1 failed,41 deselected,1 warning,2.42s**. Это воспроизведение H2 на прежнем
коде, не ошибочная fixture. Основной агент подтвердил EXIT1.

Самостоятельно прочитан **новый**, а не прежний61-test, завершённый журнал
`/private/tmp/graf-t112-http-boundary-h2-green-20261116.log`:
**67 passed,1 warning,33.15s**, runner37s, isolated_container_removed,
postgres_test_result=pass. Основной агент отдельно подтвердил terminal EXIT0
в поручении. Предупреждение — прежний PytestAssertRewriteWarning fixture,
не новая ошибка поведения. Runner collection_count67 и collection_digest
`fb5ed1ead6ac17c8b8cae2d414061e5a0f633b4f50ab110cd86e0ec00e12eedb`.
Ruff/diff-check заявлены основным агентом; независимо не повторялись.

| Текущий проверенный вход | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `c28b32cbfb4cbb5f204d19b8380c3e1beee7ebeedb56a1e6a4fad0fffaeab512` |
| `apps/server/tests/unit/test_result_view_http_guard.py` | `3ea958d8233c1364c4b5589d1bc9acf73ac981691f972268d02fb08afecb31fa` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `a4b2cb347ba679964bfbc5312330f1dcc0c6b2208aa48db675c4be78029991a1` |
| `/private/tmp/graf-t112-http-send-red-20261116.log` | `76292c2cedf8ec63cfcc62b6659b9e3f8325bae806cbf7ecc910349516d17184` |
| `/private/tmp/graf-t112-http-boundary-h2-green-20261116.log` | `84452d4b2d19489b923adb846db61928ac734da9b26e63b6885ffb619a9656e2` |

**Окончательное решение: scoped PASS foundation, P1=0/P2=0.** Прежние
124/0 requirements marks сохраняются без правки. Slow-close/pre-ping/connect,
полная cleanup приёмка, реальный ledger endpoint, issuance/renewal/render
и большой review, browser/native, T113/runtime/T0/выпуск и коммерческие
критерии остаются открытыми. Синтетический non-ledger handler в этих тестах
не выдаётся за готовый продуктовый trigger.
