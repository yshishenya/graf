# T112 — независимое ревью normal-диагностики

17.11.2026. Проверяющий `/root/public_counter_readiness_review`, F273/T112/#7698, T113/#7804, существующая полоса `high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`. Исходный HEAD в полном поручении `d33d9cfc49253bea4a3f207c1000ec56a5d55c85`; текущий по окончательному сообщению исполнителя `25c033bfc8b7a968f6d6823f081252b409c8a9a2`. Git не вызывался; содержимое проверено независимо по SHA-256, сведения HEAD получены от исполнителя. Область — конкретная реализация принятого `t112-native-response-next-design-20261117.md`, SHA-256 `8f59e2eacbe72fb0dcf3a553869c001141eeeb4fac6032f4938e449f137c1e3d`. Окончательное поручение `/private/tmp/graf-t112-native-normal-implementation-review-request-20261117.txt` и авторский отчёт прочитаны целиком.

**Окончательное независимое ревью реализации.** Первоначальные `ad16ab16.../2670d3cc...` после сообщения исполнителя о lint не рассматриваются как окончательный кандидат. Исправленные файлы полностью сверены с окончательными хешами, прочитан итоговый log; исполнитель подтвердил завершённый EXIT0 после последних исправлений. Ни тестов/selfcheck/collect-only/HTTP/БД/служб, ни Git/GitHub проверяющий не запускал и не менял. Записан только этот новый отчёт; другие файлы и отметки checklist сохранены.

## Статический результат и отдельный вход исполнения

**SCOPED IMPLEMENTATION PASS, P1=0/P2=0** для точной окончательной пары probe/selfcheck ниже. Принятый проект реализован в границах normal-инструмента. Проверка реализации отделена от следующего invocation gate: точная команда, временная копия, выбор единственного False, окружение и текущие pins должны быть проверены перед исполнением. Этим ревью native-опыт не запускался и конкретная invocation не назначена. Implementation PASS относится только к прозрачности инструмента и сохранности native-теста, не к результату GET/POST, прежней причине repeated отказа, fault/M1, рабочему T112 или выпуску.

| Вход текущего статического чтения | SHA-256 |
| --- | --- |
| `validation/t112-native-normal-probe-20261117.py` | `20bf2ba1455156bf6863f2eac6123c1fae25b897e7260aa94793afc1de94a83b` |
| `validation/t112-native-normal-selfcheck-20261117.py` | `dc1e6edabc1f8d98dd43911106ed71d9c6698ebcc63f55d290c25152f1ad00d2` |
| Исходный `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Принятый проект `validation/t112-native-response-next-design-20261117.md` | `8f59e2eacbe72fb0dcf3a553869c001141eeeb4fac6032f4938e449f137c1e3d` |
| Итоговый `/private/tmp/graf-t112-native-normal-selfcheck-20261117.log` | `2fafadd84fa42033034c09bad2da8d8219f8a98b64103621aa0ebbd7e05df5e7` |
| Авторский `validation/t112-native-normal-implementation-20261117.md` | `314f019a30b747954fc323ba048733ca71c286e3548f2c3b1af57cc1fdedc940` |

## Точная обратимость native-теста

Полный diff сравнен с принятой integration-копией. Helper footer прочитан целиком, весь selfcheck прочитан целиком; неизменный префикс и изменённая последняя функция сопоставлены программным статическим сравнением. Сам selfcheck не выполнялся проверяющим.

Независимо извлечены AST literals `EDITS`: **ровно14** уникальных пар. При обратной замене только этих точных фрагментов получено **побайтовое равенство исходному integration и равенство AST**. Это не нормализация, удаляющая произвольные assert/await. Число `await` в целевой функции до и после — **45/45**; helper footer отдельно содержит два import, два безопасных определения и класс, без автоматически выполняемого опыта.

Сохранены исходные imports и прочие тесты; `http_period`, `_real_app`, `_postgres_response_gate`, два warm native соединения, pool_size2/max_overflow0/pre_ping, независимый Context() observer, все настоящие SQL, COMMIT, F/B и assertions. Никаких новых HTTP/SQL/listeners в diff нет. По умолчанию файл в validation не является автозагружаемым conftest/plugin. Два исходных POST только делегированы прозрачным помощникам; новые POST не добавлены.

Метки `early_cleanup`, borrower_before/after_gate и post2_json/rows стоят после соответствующих исходных assertions, а не вместо них. `early_cleanup` не означает прохождение всех последующих backend/F/B проверок: для полного префикса нужны исходные assertions, borrower markers и результат теста. Родной `native_commit_ack_fault` print расположен до POST2 и доказывает только префикс; для полного normal нужны post2_json, post2_rows, scenario_complete и отсутствие исходного исключения.

## Normal-only и сохранность границ

`_NormalObservation(fault)` — первое действие тела целевого теста. Проверка `fault is not False` отказывает до provider monkeypatch, создания scenario и его GET/POST. Строго False, не просто false-like значение. Однако **pytest создаёт запрошенные фикстуры раньше вызова тела**: этот конструктор не является запретом выделения PostgreSQL для ошибочно выбранного True. Полная копия также содержит другие прежние тесты и исходный декоратор False/True. Поэтому будущий адресный выбор именно `[False]` и inventory ровно1 до БД обязательны; нельзя запускать весь файл или обе параметризации.

Оригинальные guard2s/work1.5s/cleanup0.5s, SQL128, lock250ms, statement500ms, caps, порядок locks, watchdog3s как выход из RED, F/B и cleanup не изменены. Снятие gate, отмена задач и dispose не перемещены для получения PASS. Fault/M1 код в копии остаётся исторической частью оригинального теста, но True не входит в допускаемую будущую выборку и отвергается в теле. Общий87, новые условия fault и повтор до зелёного отсутствуют.

## Прозрачность и данные наблюдения

- `proofs` вызывает переданную исходную функцию один раз с тем же HTML, читает только длину её настоящего list-результата и возвращает тот же объект. HTML/значения proof не сохраняются. Исходный short-circuit HTTP200 сохранён: если разбора не было, proof_count остаётся None, а не0. Вторая исходная выборка первого proof тоже сохранена; её результат не заменяется.
- `post` вызывает тот же bound method один раз с прежними args/kwargs, возвращает исходный response, ловит BaseException только ради type/module и делает bare raise; исходная отмена не подменяется. ContextVar сбрасывается в finally. Номер1 и2 задан явно в двух исходных call sites; состояние запросов не объединено.
- `app` оборачивает только аргумент app одного ASGITransport в этом тесте. Для GET без POST marker исходные scope/receive/send передаются напрямую, return сохраняется. Для POST исходный app вызывается один раз, receive не читается прибором, каждый message передаётся исходному send ровно один раз и тем же объектом. Нет глобальных monkeypatch httpx или трассировки.
- attempted записывается до await send, completed — только после его успешного возврата. При ошибке/отмене send completed не добавляется; app записывает type/module и распространяет то же исключение. App return не выдаётся за terminal-body completion. Тело, headers, URL/path/query, SQL и response.json/text не читаются помощниками. JSON/durable проверки остаются прежним native-кодом.
- Буфер деталей ограничен48, dropped считается отдельно. GET summary, фиксированный набор stage counts, POST1/POST2 summaries и final_snapshot обновляются независимо от заполнения records. Это устраняет потерю финальных данных при переполнении старого V4. Если существенных данных всё же нет, полный причинный вывод запрещён.
- Сроки берутся только из actual scope state соответствующего POST. Отсутствующее/нечисловое значение остаётся None, исходные даты не пересчитываются от старта прибора. POST1 final remaining может использовать только его target facts; POST2 — только его собственные наблюдённые scope deadlines. Ранние scope значения могут отсутствовать до входа guard; None допустим и не означает нулевой бюджет.

Snapshot первым действием исходного явного scenario finally сохраняет метаданные до `armed=False`, watchdog.cancel, gate.set, task.cancel, close/dispose. Inner context managers к этому моменту могли выйти — это ограничение указано в исходнике и проекте. `.done()`/`.cancelling()` читаются только у уже известных задач; никаких стеков или новых запросов нет. Snapshot хранит только числовые/bool признаки, известные type/module и None, не ссылки на task/owner/DBAPI/frame/exception. Неполный target обрабатывается; внутренняя диагностическая ошибка оставляет `snapshot_error`, а не обеспечивает PASS или пропуск native cleanup.

`finish` стоит во внешнем finally вокруг исходного `_run`. JSON печатается после его штатного выхода и cleanup engine/relay; если cleanup сама упадёт, пишется тип действующей ошибки, а полной очистки отчёт не обещает. Внешний runner/container cleanup происходит позже — его нужно подтвердить отдельно. У native raw traceback при отказе могут быть синтетические HTML/сессия; первичный лог хранить вне Git, публиковать только безопасную квитанцию и hash.

## Что проверяет pure selfcheck

Статически прочитаны: точный обратный набор14 и проверка исходного SHA; отрицательные мутации исходного HTTP assertion, await foreign и удаления обязательной диагностической метки; отказ True; identity response/args/kwargs, raised error и фактической task cancellation, nested ContextVar reset; proof result identity/count без итерации/индексации значений; GET pass-through; send start и terminal-body ошибки/отмены; app error/cancel; разделённые POST deadlines; summaries после cap; empty/partial target, task statuses, checkout offsets, diagnostic snapshot error; JSON без sentinel private текста.

Main импортирует инертный полный модуль, но не выполняет pytest fixtures, выбранный тест, HTTP или SQL. Проверяемый инструмент не импортируется как автоматически активный плагин. Проверяющий сам main не исполнял. Итоговый log целиком содержит строку PASS для source/AST restoration,3 rejected mutations, wrappers/context/ASGI/proof/cap/snapshot. Окончательное сообщение исполнителя подтвердило EXIT0 этого запуска после последних lint-правок; точная команда приведена в прочитанном авторском отчёте и использует существующий Python3.13, PYTHONDONTWRITEBYTECODE, явный PYTHONPATH и инертные файлы. Это законченная pure-проверка, не HTTP/PG-приёмка. Ранний draft PASS и итоговый не складываются.

Последние отличия от первоначальных хешей — адресные noqa E402 у двух footer imports и lint-исправления selfcheck (порядок imports, явное связывание loop values в defaults, strict zip); исходный префикс и семантика probe сохранены. Сведения Ruff PASS/selfcheck и отсутствие новых findings сверх четырёх исходных I001 взяты из авторского отчёта; проверяющий Ruff не исполнял и не выдаёт эти сведения за свой запуск.

## Следующий invocation gate — отдельный шаг

После этого implementation PASS оператор должен заново сверить исходные hashes, точную команду/окружение и побайтовую временную root-level копию. Сам пробник не содержит внутренней проверки всех source pins — её нельзя опустить во внешней подготовке. Выбор только полного node ID данного теста `[False]`, явный `-p tests.conftest`, без соседнего выбора `tests/` и без наследуемых дополнительных pytest selectors/plugins/repeat/xdist.

Предварительный collect-only обязан закончиться EXIT0/inventory_only, collection_count1 с единственным False и container_not_started. Только отдельный принятый invocation gate может назначить затем один native normal опыт с изолированной PostgreSQL. Это не возобновление использованного one-GET допуска. Никаких True/M1/V4/87, дополнительных GET/POST или runtime исправлений при любом результате. Temporary copy снимается в finally только после проверки её SHA; runner удаляет только свой контейнер. Сохраняются лог/receipt/hash/cleanup.

Успех оценивается по исходным native assertions и отдельным metadata: GET200/proof2; completed ASGI start200 и terminal body каждого POST, app/post return; ранние T/F/B в hard budget; POST2 accepted и полные прежние saved rows; provider_calls0, итоговый pool0, watchdogfalse, cleanup. Один app_return, HTTP200 или ранний native print этого не заменяют. При ошибке — первая недостигнутая граница и исходный тип, остановка без третьего POST/повтора. Полный новый PASS всё равно не объяснит исторический repeated отказ причинно.

## Требования и открытые границы

В этом проходе все18 `unchanged_inputs` карты `/private/tmp/graf-t112-root-history-reading-20261116.json` независимо SAME. Все6 source pins принятого GET receipt также свежим вычислением SAME, включая integration `1a326735...`, budget `f12c9615...`, guard `7f2887f1...`, result_views `232d6c1f...`, ingest `69a930d6...`, result_visibility `ecaac3c0...`; полные суммы закреплены в принятом next-design выше и совпавшем receipt `49e6e818d9e9c7a3bab0aae8c35d5203fafd6920f3e6cea7e869dde288e5d662`. Собственное применимое чтение оригиналов в том же диалоге переиспользовано по document-reading; новый проект, весь diff/helper/selfcheck и относящиеся к ним источники прочитаны непосредственно. Дополнительно заново прочитаны применимые development-process и scoped analyze. Requirements16/0, security27/0, privacy-measurement52/0, infra29/0: **124 отмечено / 0 не отмечено**; marks не менялись, это не новая полная приёмка реализации F273.

Настоящий `_result_period_context` по-прежнему `yield None`, Postal — почта GRAF. Не утверждается, что вся публичная Метрика выключена. Unknown repeated HOLD, T112/T113/T098/restore/readiness/T0, ручная/native приёмка, внешний трафик/аккаунты/продажи остаются открытыми. Production, внешние события, публикации, почта, выпуск и выкладка этим ревью не затрагивались.
