# T112: независимая приёмка одного normal и проект одного fault/M1

2026-11-17. F273/T112/#7698, T113/#7804. Полоса `high-risk-product`.
Проверяющий: существующий `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Ветка и HEAD сообщены автором: `codex/f273-result-visibility-20261116`,
`734ffb1509e88e7ea0f2f59bc19b4f3e48e23cde`. Git не вызывался;
HEAD/публикация независимо не проверялись. Фактические файлы сверены по SHA-256.

## 1. Итог завершённого normal

**SCOPED NORMAL VALIDATION PASS. P1: 0. P2: 0.**

Принимается один завершённый локальный опыт `[False]`: исходная цепочка
GET/HTML → POST1/COMMIT → ранняя очистка/здоровые F и B → POST2/неизменная пара
прошла полностью. Авторская ограниченная интерпретация результата корректна.
Это приёмка данного опыта по первичным материалам, а не новый запуск и не
повторное ревью уже принятой реализации или команды запуска.

Прочитан авторский отчёт `t112-native-normal-validation-20261117.md`;
хеш совпал. Оба закрытых raw-журнала прочитаны программно без печати целиком.
Хеши совпали с квитанциями; JSON наблюдения из native-журнала буквально равен
наблюдению в native-квитанции. Независимо проверены безопасные сводки runner,
pytest, исходный ранний native print, все поля наблюдения и исходные native
assertions, на прохождение которых ссылается автор. Исходные данные встреч,
proof, токены и содержимое запросов в отчёт не переносились.

| Граница | Проверенное доказательство |
| --- | --- |
| Сбор до БД | EXIT0, один точный `[False]`, inventory_only, container_not_started, наблюдений нет, временная копия удалена |
| Штатный запуск | EXIT0, wrapper 19.160003 s; pytest 1 passed/1 warning, 8.06 s; focused phase 13 s; разные интервалы не смешиваются |
| GET/HTML | HTTP200; два исходных вызова parser, по два proof; прежние проверки пустой пары и pool0 пройдены |
| POST1 | entered/returned по1; start attempted/completed по1, HTTP200; body attempted/completed 2/2; terminal body completed1; app returned1; ошибок нет |
| COMMIT и ранняя очистка | commit/after_commit/reset/checkin по1, invalidate0; прежние accepted/private-no-store, writes2/commits1, owner/Session/context/keys/tasks/pool, idle/no transaction/locks0 assertions пройдены |
| F и B | Исходные проверки до/после открытия gate пройдены; F — отдельное здоровое соединение того же request pool, B получает прежнее здоровое normal-поколение |
| POST2 | entered/returned по1; start HTTP200 completed1, terminal body completed1, app returned1; исходный JSON accepted и полное равенство двух сохранённых строк пройдены |
| Конец | early_cleanup/beforegate/open/aftergate/post2_json/post2_rows/scenario_complete по1; provider_calls0, pool0; ошибок наблюдения/сценария нет, watchdogfalse |
| Внешняя очистка runner | isolated_container_removed и runner pass; временная копия фактически отсутствует; девять source pins после опыта совпали |

28 подробных записей, dropped0. В финальном снимке post/observer/db_task
завершены, cancelling0; last_stage=scenario_complete, test/snapshot/target/run
error отсутствуют. Остатки actual work/hard POST1: 0.058190/0.558190 s;
POST2: 0.822613/1.322613 s. Для обоих hard-work=0.5 s. Это остатки в момент
снимка, а не длительности запросов и не продление срока POST1 вторым запросом.

Ранний print elapsed0.764 s расположен до POST2 и подтверждает только префикс.
Полный PASS основан также на независимых POST2/terminal markers и неизменных
проверках сохранённых данных. Normal stream done=false до явного finally —
ожидаемое живое здоровое поколение; это не утечка и не M1. Поздние cumulative
return_count5/checkout offsets[0,1,2,3,5] не заменяют раннее точное окно
возврата первоначальной операции с checkin1.

Единственное предупреждение — PytestAssertRewriteWarning уже импортированного
модуля фикстур; оно не является отказом или дополнительным выполненным тестом.
Сообщение автора о пустом `git diff` не перепроверялось через Git: независимо
подтверждены сохранение всех девяти закреплённых исходных файлов и четырёх
дополнительных зависимостей, а не состояние всего дерева Git.

### Предел normal-приёмки

Нет причинного A/B, поэтому этот PASS не объясняет исторические repeated HOLD,
normal response_complete=false или fault response_held timeout и не исправляет
их задним числом. Причины tracing/нагрузки/окружения не установлены. Unknown
repeated HOLD остаётся открытым. Допуск normal уже использован; повтора normal
или автоматического True/87 из этого результата не следует.

Настоящий `_result_period_context` остаётся `yield None`; локальный
`http_period` — разрешённая изолированная тестовая подстановка. Это не рабочая
admission boundary, browser/native видимость или приёмка всего T112/T113.
Postal остаётся почтой ГРАФ. Публичная Метрика в этой проверке не читалась;
вывод о её полном выключении не делается.

## 2. Выбран ровно один следующий необходимый опыт

**SCOPED NEXT TEST DESIGN PASS. P1: 0. P2: 0.**

Выбран один исходный параметр **`[True]` того же native COMMIT-теста**:
настоящий PostgreSQL принимает единственную целевую COMMIT, а его настоящий
ответ удерживается исходным per-stream gate. Это минимальный следующий случай:
normal уже полностью пройден, но он не проверяет неизвестный клиенту исход
COMMIT, безопасное удаление старого поколения и reconciliation после такого
исхода. Не добавляются второй fault, другой режим, V4, 87 или новый normal.

**Это проект, не допуск к исполнению True.** Нынешний normal helper принимает
только точный False и не реализует этот проект. Требуются отдельные конкретная
реализация, selfcheck, независимый implementation FINAL и отдельный invocation
FINAL для новых точных файлов/хешей. Прежние GET/V4/normal-допуски не переносятся.

### Неизменная основа и минимальный прибор

Подготовить отдельную инертную диагностическую копию точного исходного
integration-модуля с SHA-256 `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0`.
Оригинальные integration, budget helper и runtime не меняются. Сохраняются
imports/globals/fixture linkage, маркеры и исходная параметризация; отдельный
диагностический конструктор разрешает только `fault is True`. Из-за того, что
фикстуры исполняются раньше конструктора, это не заменяет collection gate
с ровно одним полным идентификатором `[True]`.

Переиспользовать подход принятого normal-прибора: два прозрачных POST,
request-local ContextVar, обёртка только app у этого ASGITransport, attempted
перед исходным send и completed после его возврата, app/post return/raise,
получение proof-count из результатов двух исходных вызовов parser, редкие
метки исходного сценария и снимок первым действием явного scenario finally.
Все аргументы/объекты/исключения/отмена передаются без изменения и ровно один
раз; ContextVar сбрасывается в finally. Никаких диагностических json/text/body
чтений или нового парсинга HTML. Это новая реализация, поэтому соответствие
старому приёму должно быть доказано заново по полному diff и AST.

**Relay не копировать, не подменять и не инструментировать.** Точная исходная
`_postgres_response_gate` уже содержит достаточное причинное свидетельство:
`response_held.set()` выполняется только внутри непустого server→client
`source.read(65536)`, когда per-stream response_gate закрыт, непосредственно
перед ожиданием этого gate. У target до COMMIT gate открыт, а held не установлен;
его закрывает исходный target COMMIT callback. Поэтому успешное существующее
ожидание target response_held при всё ещё закрытом gate доказывает удержание
настоящего блока данных на нужном потоке. Оно не означает распознанный протокол
COMMIT по байтам; серверный исход доказывается отдельно исходными DB-чтениями.
Не читать/сохранять data и не добавлять отдельный relay callback/Event/listener.

Observer создаётся, как прежде, с пустым `Context()`. Его метки вызываются
явно через локальный объект наблюдения: request ContextVar не должен
переименовывать независимый observer в POST1 или требовать смены его контекста.
Новых задач, task factory, трассировки, stack polling, listeners и подмен
asyncio/SQLAlchemy/native driver нет.

### Точные редкие метки M1

Все дополнительные операции ниже синхронные и сохраняют только безопасные
числа/bool/None/фиксированные имена/type-module исключения. Исходные await,
assertions, callback conditions, SQL и их порядок сохраняются.

1. **commit_enter.** После существующих markers.append(commit)/entered.set
   записать счётчик и текущие признаки target correlation/checks, gate closed,
   held, target task cancelling/done и post pending. Не менять тело/порядок
   исходных проверок COMMIT callback и не добавлять listener. Если имеющийся
   snapshot_error появился, он остаётся отказом, а не диагностическим успехом.
2. **m1_window.** Сохранить точный срок уже создаваемого исходного
   `asyncio.timeout_at(min(work_deadline-.1, loop.time()+.9))`. Допустима
   синхронная прозрачная внешняя обёртка над уже созданным Timeout, читающая
   его `.when()` и возвращающая тот же объект. Исходное выражение вычисляется
   один раз в том же месте; нового now+.9, нового timeout, нового await и
   пересчёта/перезапуска окна нет. По AST удаляется только эта точная обёртка.
3. **hold_wait_enter/held_observed.** Поставить метки непосредственно до и
   после существующего `await stream[response_held].wait()`. После await
   сохранить held=true, gate closed, commit1, after_commit0, post pending,
   target task not cancelling/donefalse и остатки исходного M1/work/hard.
   Ранее установленное held при открытом gate или чужой stream не принимается.
4. **durable_idle_observed.** В существующем цикле независимой direct session
   не добавлять SQL/итераций/сна. Для диагностики достаточно фиксированного
   счётчика исходных итераций и последней границы pair/activity/locks, без
   подробной записи каждого прохода. Сразу внутри исходного успешного условия,
   до break, сохранить: rows_count2, activity_present, idle=true,
   xact_start_none=true, locks0, исходные остатки сроков. Строки/ID/PID/SQL,
   activity objects и backend/socket объекты не сохраняются.
5. **m1_foreign_enter/returned.** Отметить только существующий
   `await foreign_healthy()` внутри observer после исходных pending/no-cancel/
   after_commit/gate assertions. Он проверяет F того же request pool по
   неизменным исходным native driver/PID/SELECT1/commit assertions. Нового
   foreign_healthy и новых SQL не добавлять.
6. **m1_complete.** Сразу после исходного присваивания target m1_pair/m1_at,
   внутри того же Timeout, сохранить m1_at, точный исходный срок окна и
   признаки всей цепочки. Повторно только синхронно прочитать: post всё ещё
   pending, target task donefalse/cancelling0, commit1/after_commit0,
   held=true/gate closed, F вернулся, watchdogfalse. M1 принимается, только
   если эти признаки верны и m1_at/момент метки строго раньше исходного
   M1 deadline и work_deadline; потеря признака за время F означает HOLD.
   Не переносить M1 после отмены, HTTP-ответа, открытия gate или cleanup.

Существующее ограниченное DB-наблюдение в исходном while сохраняется; оно не
даёт разрешения на дополнительные диагностические запросы, retry либо новый
опрос после завершения/истечения окна. Наблюдения отдельных исходных запросов
образуют причинную последовательность внутри этого окна; они не выдаются за
одну атомарную SQL-фотографию. При закрытом target gate и pending/non-cancelling
задаче до завершения F целевой поток не освобождён прибором.

### Полный causal M1 — обязательная приёмка

| Условие | Достаточное свидетельство в исходном окне |
| --- | --- |
| Точная целевая операция | Один исходный target COMMIT, все owner/session/root/lease/task/generation checks истинны, writes2/commits1 |
| Удержан настоящий ответ | Target server→client непустой chunk вызвал исходный response_held; target gate закрыт до и после наблюдений, after_commit отсутствует |
| Операция ещё ждёт | POST pending, target task не done и cancelling0 до/после проверки F; M1 до отмены |
| Сервер принял пару | Исходная независимая direct session видит ровно2 строки, target backend существует idle, no transaction и locks0 |
| Изоляция F | Исходный F того же pool здоров при закрытом target gate; не подменён прямым engine или другим пулом |
| Время | Полное m1_complete строго внутри того же min(work_deadline-.1, entry_now+.9), без пересчёта или увеличения |

Невыполненный response_held или истёкшее окно — **HOLD на первой границе**,
а не неизвестный-COMMIT PASS. Поздняя durable пара или здоровый F после
cancellation/gate.set не восстанавливают отсутствующий M1.

### Продолжение после полного M1

Сохраняется вся исходная последовательность True. Первый POST должен вернуть
исходный HTTP200 JSON unavailable с private/no-store и полным completed ASGI
start/terminal body; app и исходный POST должны вернуться без ошибки транспорта.
Нельзя синтезировать unavailable после HTTPX response_complete AssertionError.
Сам JSON unavailable без завершённой передачи недостаточен.

Существующие markers и проверки доказывают ровно один invalidate перед ровно
одним checkin(None) в точном окне исходного checkout. Редкая метка после
исходных fault-cleanup assertions фиксирует их успех, закрытый gate и исходную
корреляцию; поздние cumulative returns не заменяют это окно. До штатного
открытия gate должны быть доказаны закрытие target driver, завершение root/
pumps/wait_closed/writers старого relay и отсутствие старого backend/locks.
Отметки ставятся только после существующих assertions и существующего
stream done.wait; дополнительных ожиданий, SQL и driver replacements нет.

Затем сохраняются исходные F и B до/после штатного gate.set. B должен занять
тот же pool entry уже с новым DBAPI/driver/PID, без старых owner/context keys;
F сохраняет своё здоровое поколение. Gate открывается только в исходной
точке. Спасательное finally/watchdog/dispose не является доказательством
успешного закрытия старого поколения до открытия gate.

После закрытия исходных F/B допускается только уже существующий явный POST2
как тест следующего самостоятельного показа/reconciliation: accepted,
отдельный исходный request budget, completed ASGI start/terminal/app/post и
полное равенство saved rows исходной M1-паре. Он не добавляет новый GET/proof,
не становится retry первого запроса, не заменяется третьим POST. Прежние
len(http_period), provider_calls0 и pool0 assertions обязательны.

### Хранение наблюдений, ошибки и неизменные пределы

Максимум48 подробных записей; M1/POST1/POST2/cleanup fixed summaries и final
snapshot обновляются независимо от cap. Все существенные M1 timestamps/сроки
и результаты сохраняются вне подробного буфера. При dropped>0 недостающая
причинная граница не достраивается. Диагностические ошибки фиксируются и
не превращают исходный отказ в успех. Ошибка/отмена observer передаётся
без подавления; при необходимости её type/module снимаются локальным
прозрачным try/except с bare raise, без нового Task или повторного await.

Snapshot остаётся первым действием исходного явного scenario finally,
до armed=False, watchdog.cancel, gate.set, task.cancel и ручного close/dispose.
Он дополняется уже накопленной M1-summary, последней границей observer,
состояниями target gate/held/done, post/observer/db_task done/cancelling,
исходными work/hard/M1 remaining, маркерами и watchdog. Snapshot может быть
после естественного выхода внутренних context managers; он не называется
снимком до всей автоматической очистки. POST/app ошибки дополнительно
отмечаются на собственных границах до распространения. JSON выводится один
раз после исходной очистки `_run`; очистка внешнего runner подтверждается отдельно.

Сохраняются guard2 s/work1.5 s/cleanup0.5 s на каждый исходный POST,
SQL<=128, lock<=250 ms, statement<=500 ms, прежние body/proof/response caps,
request pool_size2/max_overflow0/pre_ping, два sequential warm соединения,
пустой Context независимого observer, native сеть/драйвер и неизменные routes,
_real_app/http_period. Watchdog3 s — прежнее аварийное освобождение неуспешного
теста; успешный опыт требует watchdogfalse. Здоровые F/B sockets не объявляются
утечкой target. Никакого global settrace/profile/monitoring или стекового опроса.

### Следующие отдельные ворота

1. Представить конкретные инертные probe и selfcheck. Полный diff/AST должен
   после строго перечисленного удаления диагностических вставок/обёрток
   восстановить исходный модуль/тест: все native assertions, 45 исходных awaits,
   их порядок, SQL, исходные callbacks, Timeout expression и cleanup буквально
   прежние. Нельзя произвольно удалять assertions/arguments/statements ради
   успешного сравнения. Helper True-only, никакого запуска при импорте.
2. Отдельный чистый selfcheck без HTTP/SQL/PG проверяет прежнюю прозрачность
   POST/app/send/parser/ContextVar/cancel/identity, cap и частичные snapshots,
   а также новый Timeout wrapper: возвращается тот же объект/тот же .when,
   выражение вычисляется один раз, срок не меняется. Проверить M1 summary при
   отсутствующем target/сбое/таймауте/переполнении и отбрасывание неполной либо
   поздней M1, без реального ожидания .9 s. Selfcheck не доказывает causal M1.
3. Независимый implementation FINAL по новым точным хешам и отдельный
   invocation FINAL: новые эксклюзивные paths/журналы/квитанции, все source и
   dependency pins, исходный runner, текущая среда без pytest additions/-O,
   общий venv без sync, reserve>=80GB. Старые использованные normal-файлы
   не очищаются/не перезаписываются для обхода запрета повтора.
4. Только после этих FINAL допускается назначить один отдельный collect-only
   с точным новым полным `[True]`, числом1/отпечатком и container_not_started.
   Сохранить явный `-p tests.conftest`, не выбирать одновременно `tests/`.
   Затем принять полную квитанцию и отдельно назначить один native True.
   Ни команды запуска, ни фактического исполнения настоящим отчётом нет.
5. После первого исхода сохранить закрытый raw log, безопасное observation,
   receipts/hashes и подтверждение удаления своего контейнера/временной копии.
   Разобрать первую непройденную границу. Не повторять опыт, не увеличивать
   окно/бюджет и не исправлять runtime автоматически до нового предметного gate.

## 3. Проверенные материалы и точные хеши

| Материал | SHA-256 |
| --- | --- |
| Авторский normal-отчёт: `t112-native-normal-validation-20261117.md` | `7c30f553db3a5028f64bc53a5e1ab4f13620bf60272721a63fe0d4a95553e517` |
| Принятое normal implementation review: `t112-native-normal-implementation-review-20261117.md` | `65dbb8557d407953acef697d058b9be3f54771cf40283f6c6391a18c1e958bd0` |
| Принятое normal invocation review: `t112-native-normal-invocation-review-20261117.md` | `dce7edb8aae7ec59a2ff25753fc8a56e784ff3a56fc520668dba69b9303714ec` |
| Принятый предшествующий design: `t112-native-response-next-design-20261117.md` | `8f59e2eacbe72fb0dcf3a553869c001141eeeb4fac6032f4938e449f137c1e3d` |
| Инертная normal-команда: `graf-t112-native-normal-invocation-20261117.py` | `bbe0e009f93ace302d1c01c212275ce97cff56b08da4d00ab9e0a87b82742f49` |
| Collection receipt: `graf-t112-native-normal-invocation-20261117-collection.json` | `86a9923ea2663c3979b480ab3d2bcda3e68e19d595c310f4675d9e96750b285d` |
| Collection log, закрытый: `graf-t112-native-normal-invocation-20261117-collection.log` | `dc71166a2b0e6f99e897ae0756b77cc6a207ab012307de1489c88c312087cf3a` |
| Native receipt: `graf-t112-native-normal-invocation-20261117-native.json` | `9596a6f698a9d4cb46bdaacabf06823dc7b4e8537324d83c768fce985aa671bf` |
| Native log, закрытый: `graf-t112-native-normal-invocation-20261117-native.log` | `1b4fe28a50b536b4c3b79f4bcc7bd4cc340cee5aa484dcd58c6c0415d84bceb6` |

Raw logs и receipts находятся вне Git под `/private/tmp/`; их содержимое целиком
не публикуется. Normal collection node+newline digest:
`08511b1a31e0a192e0df21cc6e8ee7a488d3b53fb4a4770d375e4bc83519d5ee`.
Оба receipts содержат тот же node и одинаковые девять pins. Все девять
независимо сверены с текущими файлами: SAME.

| Путь относительно рабочего дерева | SHA-256 |
| --- | --- |
| `apps/server/scripts/run_local_postgres_tests.sh` | `b5858c56db899be16cdf842c42ecd87aa1984cac94f56015051eeb4e96240d07` |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| `specs/273-paid-traffic-analytics/validation/t112-native-normal-probe-20261117.py` | `20bf2ba1455156bf6863f2eac6123c1fae25b897e7260aa94793afc1de94a83b` |
| `specs/273-paid-traffic-analytics/validation/t112-native-normal-selfcheck-20261117.py` | `dc1e6edabc1f8d98dd43911106ed71d9c6698ebcc63f55d290c25152f1ad00d2` |
| `apps/server/tests/conftest.py` — дополнительная зависимость | `0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793` |
| `apps/server/tests/fixtures/test_resources.py` — дополнительная зависимость | `27b6994b848eddd4e2f95dcc827cb5a78946b27fba3e7972e5cfad7580a4a578` |
| `apps/server/tests/fixtures/postgres_test_database.py` — дополнительная зависимость | `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b` |
| `apps/server/pyproject.toml` — дополнительная зависимость | `711b51675fa997a2bbb509d641da36b2771566f6ad3088644cec2ba781d73ce7` |

## 4. Требования, происхождение чтения и незакрытые границы

Это продолжение того же независимого просмотра и прежнего собственного чтения
неизменных требований, отражённого в принятом предыдущем design и invocation
report. README и document-reading перечитаны; по карте
`/private/tmp/graf-t112-root-history-reading-20261116.json` свежим сравнением
совпали18 неизменных входов. Карта автора используется для сверки содержимого,
а не как доказательство чтения требований проверяющим.

Самостоятельно восстановлены в оригиналах: result-visibility §5 целиком
(2 s/unknown COMMIT/no retry/две строки), activation-milestones §«Одно решение
в PostgreSQL» (идемпотентность/неизменность payload), plan §T112, tasks
уточнение T112/T113, quickstart §T112 целиком; constitution VI/VII/platform/
workflow и product-gates §Audio, Artifacts, And Diagnostics/Server boundaries;
spec-kit-flow lanes/implement/converge. Остальные ранее полностью прочитанные
неизменные требования того же диалога не переопределяются этим узким проектом.
Применимость: изолированная диагностика, неизменность исходных сроков,
закрытые метаданные, синтетические данные, неизвестный COMMIT и отдельная
рабочая admission/release-приёмка. Требований новой площадки/публикации/релиза
этот проект не добавляет.

Четыре исходных checklist свежим подсчётом: requirements16/0, security27/0,
privacy-measurement52/0, infra29/0 — **124 отмечено / 0 не отмечено**. Маркеры
не менялись. Это сохранённое состояние списков, не закрытие эксплуатационных
или коммерческих критериев.

Настоящий просмотр не выполнял тесты/selfcheck/collection/HTTP/SQL/PG,
не запускал контейнеры/приложения, не менял Git/GitHub, код/spec/plan/tasks/
checklists, production/почту/аналитику и не отправлял внешние сообщения.
Создан только этот новый отчёт. Независимой runtime-приёмки True пока нет.

T112, T113, T098, restore/readiness/T0, ручная/native видимость, внешние
аккаунты, трафик и продажи остаются открытыми. Неизвестные числа не
подменяются нулями. Один будущий локальный fault PASS также не примет эти
границы и не докажет причину исторического repeated HOLD.
