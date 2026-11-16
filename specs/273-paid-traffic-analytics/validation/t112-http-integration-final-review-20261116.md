# T112 — окончательное независимое ревью HTTP-среза, 16.11.2026

Рецензент `/root/public_counter_readiness_review`. Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`; основа `dc275273e11ddedf26b9dccad647091159f951a4` плюс перечисленные рабочие изменения. Полоса `high-risk-product`, F273/T112/#7698, T113/#7804.

## Состояние заключения

**SCOPED IMPLEMENTATION PASS. P1=0, P2=0 для текущего HTTP-среза и указанных ниже 13 хешей.** P2-1 и P2-2 устранены; новый expiry-тест причинно проверен. Заключительный общий профиль без временного диагностического plugin завершился **312 PASS**, 261.17 с, runner267, EXIT0; изолированный контейнер удалён. Исполнитель сообщил terminal, рецензент независимо прочитал журнал и пересверил снимок.

Прежний HOLD по отсутствию текущего полного положительного профиля снимается именно для этого снимка и ограниченной области. Конкретного оставшегося P1/P2-блокера внутри просмотренного HTTP-среза не найдено. Это не отменяет историю красных запусков и не заменяет полную приёмку T112/T113, рабочую устойчивость, выпуск или измерение.

## Самостоятельная сверка кода и проекта

Перечитан принятый HTTP-проект SHA-256 `a03427e1b19ac587b530b102648271c7063be2118e0a17d4625a4ae8702180d4`, текущий diff и новые файлы маршрута и HTTP-тестов. Решение не переносится со старых design/admission review.

- Два настоящих POST alias используют общий обработчик, прежние Principal/Tenant/CSRF и внешний guard. Guard ограничивает тело до auth, не допускает duplicate JSON/лишние ключи/не-ASCII proof, охватывает зависимости, продление сессии и буферизацию ответа прежним сроком. Обработчик берёт исходные work/cleanup из request.state, не выдаёт второй срок или автоматический retry.
- Общий HMAC decoder ограничен длиной proof, формой, подписью, точными ключами, версией и временем. Его результат выбирает valid/expired до аналитической сессии; перед доверием к источнику полный verifier сравнивает подпись со свежим binding. Публичные JSON-поля не выбирают владельца, поверхность, период или SQL references.
- Inspection имеет точный отдельный тип `ResultInspectionSession`; наследует читающие запреты и не имеет admit_event/commit_pair. Общий `_account_transaction` повторно использует tenant/identity/session/membership/device процедуру, проверяет exact owner/db/deadline/started_at/recheck. Отказ gate делает owner/budget failed до повторного исключения; перехват callback не оживляет операцию. Возвращаемое значение inspection выдаётся после finish/cleanup; пара admission сохраняет прежний строгий commit/terminal.
- Настоящий `_result_period_context(..., inspection=False)` при обоих выборах содержит только `yield None`. Нового проверенного периода, fallback даты/config или разрешения рабочего сбора нет. Изолированные тесты подменяют этот источник явно.
- GET сохраняет исходный продуктовый review. Collector выбирает исходные result id/version, pinned outcome и fingerprint/epoch из уже прочитанных ORM/prefetch пар; новой SQL или поля публичного ответа нет. Сопоставление с fresh bindings требует исходные refs, key/type и точный digest текста. Старая версия не подписывается свежей; закреплённый итог сохраняет собственную старую версию независимо от новой расшифровки.
- Добавленная GET-фаза начинает свой срок до classifier/period/checkout. Общая `_run_result_view_operation` сохраняет уникальный владелец ContextVar, точные связи соединения/транзакции/задачи, очистку и сброс token. Повторный cancel уже отменяемой DB-задачи исключён. Продуктовый review не заменяется урезанным fresh review. Отказ аналитики оставляет обычный просмотр; отсутствие прежнего общего CSRF secret сохраняет прежний продуктовый 503.
- Бюджет 2 с, work 1.5 с, cleanup reserve 0.5 с, 128 SQL и исходные raw/row/node caps не увеличены. В синхронных digest/verifier/циклах есть checkpoint до/после и между блоками. Старый отображаемый текст ограничен до дополнительного UTF-8-кодирования, даже если свежий текст в БД уменьшился. Protocol использует числовой `candidate_count`, отдельный от списков строк.
- Browser/desktop выбирают query как существующий GET: последний summary_format, browser UUID source_result_id с прежним 422, desktop игнорирует лишний source_result_id. Known internal/automated/smoke и разрешённые nonowner-read не получают владельческого proof. Классификация external не принимается за доказательство внешнего клиента.

## Причинные проверки и границы

Самостоятельно прочитаны завершённые журналы: unit 317 PASS; browser 46 PASS; четыре причинных size-случая 4 PASS/52 deselected; admission/access/projection 131 PASS; общий диагностический профиль 312 PASS/258.32 с с удалением контейнера. Журналы не заменяют чтение кода: проверены соответствующие тела тестов и assertions.

Новые HTTP-тесты проверяют четыре GET-поверхности, нулевые аналитические INSERT/COMMIT в issuance/renewal, две durable account-вехи только в valid POST, неизменный pinned результат, запрет подписи после изменения текста или версии, настоящий закрытый период, auth/CSRF, plain/foreign/readonly/admission/unstarted/begun контексты, DML/flush/commit/raw и перехваченный gate, TTL race без второй сессии, query selection, реальные изменения source/delete/account/session, отзыв gate перед каждой записью/commit, второй INSERT и unknown commit без автоматического повтора, отказ дополнительной фазы и освобождение задач/пула. Три sync-budget случая причинно тормозят только первый digest/verifier до исходного deadline и требуют отсутствия следующего кандидата.

Полный обычный час 600+600 проходит issuance/renewal/admission без обрезания fixture и повышения caps. Поле 256 KiB проходит; +1 байт отвергается. 8335873 исходных байта near-total могут не уложиться во время: отсутствие proof принимается только при зафиксированном первом отказе checkpoint с уже истёкшим сроком, чистой Session, той же задачей и без прежнего failed. Поэтому этот тест не маскирует произвольную ошибку общим флагом и не выдаётся за положительную тройку фаз near-total. Сценарий 8691657 байт отвергается по прежнему размеру.

Предшествующие P2-1 (синхронные проверки времени/старый большой review) и P2-2 (недоказанная причина size-отказа) самостоятельно сверены в текущем коде и тестах: исправления сохраняются. Protocol с owner проверяется отдельной параметризацией bounded=False/True и точным порядком/текстом.

## Первоначальные 12 FAIL

Исходный 312-профиль дал 300 PASS/12 FAIL. Расследование `t112-http-regression-investigation-20261116.md`, SHA-256 `866f9dee95a8385f1d0678f7c2859c3ea6f6d8a65080024644bc66c236f2d35c`, не установило первопричину. Нагрузка, NullPool и утечка не доказаны; исправленный дефект не объявляется. Все 12 имён самостоятельно сопоставлены с успешными случаями общего диагностического повтора. Этот повтор использовал только наблюдатель `_refuse`, затем вызывавший оригинал; файл наблюдателя удалён и отсутствует в снимке кандидата.

Повтор без наблюдателя не прошёл один из этих 12 случаев: `second_insert` expiry. Его прежнее тело ставит expires_at=now+1s, затем внутри первого milestone ждёт истечения сессии, расходуя реальный общий deadline. По журналу получен calls=1; точная причина санитаризированного отказа пока неизвестна. Текущее изменённое тело сдвигает только аргумент времени проверки сессии после первой/второй milestone, сохраняя реальные work/cleanup deadlines; эта новая версия прошла точечный причинный профиль и заключительный общий профиль. Этот успех не восстанавливает отсутствующую причинную информацию первого сбоя и не доказывает устойчивость при любой нагрузке. Итоговый scoped PASS основан на самостоятельно прочитанном коде, причинных assertions и полном актуальном положительном наборе, а не на выдуманной первопричине или повышенных лимитах. Необъяснённый исходный запуск сохраняется как ограничение уверенности в стабильности; без конкретного текущего дефекта он не превращается в бессрочный новый блокер изолированной реализации при закрытом runtime gate.

## Причинная правка проверки истечения сессии

Самостоятельно прочитаны текущий diff `test_result_view_access.py` и настоящая `auth/sessions.py::is_session_token_valid`: она проверяет active status и `expires_at > at`. Тест сохраняет исходную функцию и делегирует ей проверку, меняя только аргумент `at` на `expires_at + 1 microsecond` после действительной первой либо второй milestone-операции. Сам результат проверки не подставляется. Полный work/cleanup clocks, размер, SQL caps, source/access путь и транзакция не меняются. До целевой фазы используется настоящий `at`.

Assertions требуют два достигнутых milestone callback, установленную фазу expired, наблюдение `(False, True)` до неё и последний `(True, False)` после неё, отказ `_accept`, предел 2.1 с и нулевой durable ledger. Поэтому отказ по неизвестному предшествующему исключению/общему deadline не удовлетворяет этому тесту. Это детерминированная проверка повторного контроля expiry на заданной фазе, а не дополнительное доказательство реального ожидания системных часов.

Прочитан `/private/tmp/graf-t112-session-expiry-causal-20261116.log`: **2 PASS / 29 deselected**, 4.96 с. Отрицательный контроль `/private/tmp/graf-t112-session-expiry-negative-20261116.log` содержит **два ожидаемых FAIL именно на `assert not await _accept`, фактически True**: при разрешающей проверке сессии тесты обнаруживают принятие. Это причинно отличает исправленное утверждение от маскировки ошибкой БД или только счётчиком. По поручению временный fault plugin удалён; его runtime-код не входит в кандидат. Первые 12 причин этим не доказаны, runtime defect не объявляется исправленным.

## Окончательный общий профиль

`/private/tmp/graf-t112-http-causal-final-20261116.log`: **312 passed, 1 warning in 261.17s**; runner267, status=pass, isolated_container_removed. Состав `collection_count=312`, digest `82e74fcfb0dce97fa3667e8cd1c62ab7ce8772acc7198217e56eff6e5b754e27` совпадает с исходным профилем. Пропусков нет. Все 12 исходных имён самостоятельно сопоставлены с PASS окончательного журнала. Два expiry-параметра используют явно описанное новое причинное тело; изменение теста не скрывается как неизменный сценарий ожидания реального времени.

13 source/test/fragment хешей снова совпали после terminal. `tests/fixtures/t112_debug_local.py` отсутствует; временных файлов T112 observer/fault в fixtures не найдено. Runtime source не исправлялся между исходными FAIL и финальным PASS. В одном из промежуточных профилей остался 1 FAIL старого смешанного time/expiry теста; он сохранён как отрицательное evidence, а не выдан за GREEN.

| Завершённое свидетельство | SHA-256 |
| --- | --- |
| Финальный общий без plugin `graf-t112-http-causal-final-20261116.log` | `a50dc22a5239a0d2327bb3d81d34392d799943a6eefaadd9a9a0a850f54af53a` |
| Промежуточный 311/1 `graf-t112-http-uninstrumented-final-20261116.log` | `09f443037ff1b19e2023b0dc8c76710974fb57f05c76eca3669fc9ead83c881f` |
| Причинный expiry 2 PASS `graf-t112-session-expiry-causal-20261116.log` | `ead3e25afee96a46e2f257a86f646b08ff4d360537e9371c0c60efd2bc27e925` |
| Expiry negative 2 ожидаемых FAIL `graf-t112-session-expiry-negative-20261116.log` | `7b1953ed12155c5b59eb5858b9078c09a8756597262cbdab3aee6cf1f1d2f6a0` |
| Unit 317 `graf-t112-http-correct-unit-20261116.log` | `ce1a2b331b1b6571c4e371cc93056f3e0a4a9afca724066a89e1e513bfc4e1ac` |
| Browser 46 `graf-t112-http-final-browser-20261116.log` | `371a64592002b9a49c670570f0a93abd3b5f98c52929df2663b47c6bbfa6b763` |
| Причинный size 4 `graf-t112-http-causal-size-20261116.log` | `1e476636bb7f05f37982492dc598546d64ad27012ad0706f9b994e1767e3231f` |
| Диагностический общий 312 `graf-t112-http-combined-observed-20261116.log` | `a19cdc5b5293f74e621c96d4d884032b6fddfa4fe1f5532d1a58e9e4e6f41fe0` |

Все перечисленные журналы находятся в `/private/tmp/` и прочитаны рецензентом; собственных запусков не было. Scope итогового PASS не включает доказательство любого поведения вне этой матрицы.

## Требования и сохраняющиеся ворота

18 исходных файлов из `/private/tmp/graf-t112-root-history-reading-20261116.json` самостоятельно сверены: 18 SAME. Четыре reviewer-owned перечня пересчитаны: requirements16/0, security27/0, privacy-measurement52/0, infra29/0; всего 124 отмечено/0 не отмечено. Отметки не менялись. Analyze SHA-256 `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` проверен; требования FR-021/025 и SC-006 сопоставлены с контрактом, quickstart и принятым HTTP-проектом.

Полная T112 остаётся открытой: ручная GRAF Dev, native/прочие обязательные matrix и ещё не принятые общие cleanup/commit исходы не объявляются выполненными этим HTTP-ревью. Общая T113/readiness/receipts/recovery/restore и точный выпускной GitHub gate не приняты. Истёкшее исключение T098 не продлевается. Текущее заключение не разрешает слияние во время freeze, новый релиз или рабочее измерение. T0, публикация Product Radar, внешний трафик, регистрации и продажи не подтверждены.

## Окончательный снимок

| Файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `51e906d57d5826241381a5381af50128da6d55d688eb6a09640806b3945b6754` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py` | `b9a25a268349afa95caf6f5384e1953bdfee44a1197453a9c526b5839439229e` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04` |
| `apps/server/src/twobrain_rec_server/cabinet/web.py` | `284d379d4383f3577c60d16e79959acbc8a8c931ba2d325bc202f80cfed7e6c2` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` | `858c2d9c25f1b50a0f315d139418653c73ef0057a006804bdf13758590b16e07` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py` | `5ae0a8c52529fec252d6269e8a2b45eb0b114b3abb9a4afd3a439fb52ca3b0b7` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `apps/server/tests/contract/test_result_view_http_integration.py` | `8b0b6676a4281e31d1fd1d6ad0a045ee708a483d379babe7c801daec19e5bfd7` |
| `apps/server/tests/unit/test_result_view_projection.py` | `65491c5358742b8f2ee4ca3a9511b886487237b8803601af56b22646de233f75` |
| `changes/unreleased/F273.yaml` | `3969470dd80c26b3e4ae13e880efbc4813e0ddbc43bf65e5cefcd8f00eadc5ae` |
| `apps/server/tests/contract/test_result_view_access.py` | `a6b0bc390d1216d7ac8c5bc10a65622bf516ce606feec20ca03bf3bb20ce6901` |

Все 13 хешей сверены самостоятельно и совпадают с `/private/tmp/graf-t112-http-final-hashes-20261116.json`. Эти хеши, а не один только base SHA, определяют проверенный рабочий снимок. Любое изменение затронутых файлов требует новой оценки относящегося к нему evidence.

Рецензент не запускал тесты, сборки, пробы БД или службы, не менял код/тесты/spec/plan/tasks/checklists/Git/GitHub, не создавал агентов и не выполнял межчатовых внешних действий. Создан только этот новый отчёт; чужие изменения сохранены.
