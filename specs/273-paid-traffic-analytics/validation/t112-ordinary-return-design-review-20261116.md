# T112 — независимый проект следующего опыта: обычный возврат и неизвестный COMMIT

16.11.2026. Рецензент `/root/public_counter_readiness_review`. Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`; принятый HTTP checkpoint `237d368b94c61908f853262ec1be545504951dc8`. Существующая `high-risk-product` F273/T112/#7698, T113/#7804. Поручение — проект опыта до тестового кода, только чтение и этот новый отчёт. Точное актуальное поручение прочитано из `/private/tmp/graf-t112-ordinary-return-request-20261116.txt`; единственный разрешённый результат этого поручения — `t112-ordinary-return-design-review-20261116.md`. Ранее подготовленный `t112-ordinary-return-preflight-20261116.md` использован как черновой источник и не изменялся.

## Решение

**TEST DESIGN PASS, P1=0/P2=0 для двух случаев ниже: normal и задержанное реальное подтверждение COMMIT аналитической пары через существующий HTTP-handler.** Это допуск ограниченного причинного опыта, не сообщение об его выполнении, implementation PASS или завершении T112. Нового подтверждённого runtime-дефекта при чтении не обнаружено. Отдельная новая ветвь ordinary reset не требуется; normal ниже — необходимый контроль нового COMMIT-опыта, а не повторная работа над уже принятым возвратом. Реализация/приёмка этой оставшейся границы пока **HOLD до опыта и независимого review**.

Отдельный «медленный ordinary reset» при текущих callers создавать не следует: по прочитанному исходнику его default ветвь после завершённого commit/rollback не содержит ожидаемого сетевого rollback. Нельзя заставить её ждать, добавив custom reset listener, raw driver transaction, иной pool setting или подменив методы. Ближайший реальный недоказанный промежуток — сервер выполнил COMMIT, обе account-вехи видны другой сессии, но SQLAlchemy/asyncpg ещё не получили ответ, и исходный work deadline отменяет ожидание. Такой опыт одновременно наблюдает нормальный default reset/return и его альтернативу после неизвестного commit, не выдавая их за одну операцию.

## Что уже доказано и не повторяется как новая работа

| Существующее доказательство | Точный предел | Что из него не следует |
| --- | --- | --- |
| `t112-close-review-20261116.md`; `test_session_close_rollback_is_bounded_in_its_real_child_task` | Настоящий rollback внутри Session.__aexit__, actual close-task handoff, handler/auth/renewal normal+fault, собственные tasks/Session/DB/metadata до teardown; foreign того же пула | Не отдельное ожидающее default reset и не нативный неизвестный COMMIT |
| `t112-driver-close-preflight-20261116.md`, принятое дополнение C1; native hard invalidate test | Точный собственный idle driver при public invalidate(None), упреждение graceful wait и завершение его socket/relay | Не обычный checkin; не разрешение уничтожать здоровый idle socket |
| `t112-pool-return-preflight-20261116.md`, окончательное N1–N3; generation test | Idle precheckout Pool.close старого поколения; exact root history, F/P same-pool, новое поколение и три normal reset/checkin после auth/tenant/renewal | Не произвольный close/reset/TLS/commit; три reset события не означают три сетевых ROLLBACK |
| Принятый HTTP-срез и его final review | Настоящие GET/renewal/POST aliases, закрытый runtime period, access/source/proof, общая пара, существующие browser/DB/unit и полный312 | Не все возможные cleanup/commit исходы |
| `test_real_http_does_not_acknowledge_partial_or_unknown_pair_outcomes[after_commit]` | Настоящий handler, server pair уже committed, public Session.after_commit искусственно бросает OSError; unavailable и следующая явная попытка сохраняют два прежних решения | Не ожидание настоящего COMMIT-ответа asyncpg и не отмена native commit в сети |
| Admission `test_unknown_commit_is_not_retried...` и `test_cleanup_timeout_after_commit_preserves_handed_off_pool_connection` | Идемпотентность после подставленного post-commit исключения; защита переданного driver при искусственно задержанном db.close | Не новый native wire outcome; не основание снова подменять close/commit |
| `test_same_pool_connection_has_no_leftover_guard` | Обычное повторное использование driver после projection rollback | Не fault real HTTP COMMIT |

Старые успешные профили не запускались повторно. История исходных12 FAIL и последующего причинного expiry-теста из HTTP-среза сохраняет свои прежние ограничения; новая гипотеза об их причине не выдвигается.

## Почему default reset сейчас не отдельное сетевое ожидание

Прочитаны текущие `db/session.py`, auth/renewal, `_account_transaction`, `ResultAdmissionSession.commit_pair`, `_result_session_context`, guard и установленные SQLAlchemy **2.0.51** / asyncpg **0.31.0**.

1. Приложение создаёт engine только с `pool_pre_ping=True`. `pool_reset_on_return`/`pool_recycle` и custom reset listener в runtime не заданы; стандартный rollback-on-return не меняется.
2. Auth `_principal_from_session_token` и `session_renewal_middleware` используют обычный AsyncSession context и `await db.commit()`. Аналитический `commit_pair` тоже вызывает настоящий `await self.db.commit()`.
3. `SessionTransaction.commit` выполняет реальный transaction.commit, после acknowledgement вызывает after_commit и close. `SessionTransaction.close` освобождает свой Connection до завершения корневого transaction lifecycle. Поэтому после успешного commit connection уже возвращается в pool; завершающий пустой Session.close не начинает ещё один сетевой close здорового socket.
4. `Connection.close` с открытой транзакцией сначала откатывает её и передаёт `transaction_was_reset=True`; default pool reset не повторяет rollback. Это rollback-путь, уже покрытый прежним native Session.close опытом.
5. При возврате после commit reset может иметь `transaction_was_reset=False`: библиотека вызовет dialect rollback-on-return, но asyncpg adapter выполняет native rollback только при `_started=True`. Его `_commit_and_discard` и `_rollback_and_discard` сбрасывают transaction/started в finally. После завершённой штатной транзакции это синхронный no-op, а не второе сетевое ожидание. Не следует читать/менять `_started` в тесте: здесь он прочитан только в исходнике библиотеки.
6. Успешный checkin сохраняет открытый idle driver/socket для reuse. Их наличие не является фоновой работой запроса. Physical `driver.close`, hard invalidate и precheckout disposal имеют другие причины и в этой паре не вызываются вручную.

Новый normal-case должен пассивно подтвердить reset→checkin именно целевой аналитической транзакции, здоровый idle driver и повторное использование. Fault «остановить custom reset» исключён. Если фактическая трасса не соответствует этому исходнику, сначала фиксируется отдельная находка и новый проект; тест не достраивает нужного caller через private API или настройки.

## Минимальный стенд и разрешённая подмена

Только синтетические собственные записи и существующая disposable PostgreSQL. Использовать `_real_app`/настоящий cabinet router и существующую test-only `http_period` boundary. Настоящий `_result_period_context` в продукте остаётся `yield None`; нового runtime caller, flag, started_at или настройку не добавлять. Запрещён старый synthetic200 endpoint `_setup` как проверяемый handler; он может оставаться технической основой существующего `_real_app`, который заменяет route настоящим.

Два случая на canonical browser POST достаточны: alias/shared-handler equivalence уже принята в HTTP312 и остаётся регрессией. Удваивать сетевой fault для встроенного alias без новой зависимости не требуется. Нормальная небольшая полная fixture достаточна; прежний обычный час/size-profile не обрезаются и не заменяются ею.

Последовательность подготовки:

1. Создать request engine за TCP relay с **pool_size=2, max_overflow=0, pool_pre_ping=True**, default FIFO/reset/recycle. Не задавать timeout/recycle/reset ради нового результата. Изолированный direct observer использует отдельный engine и пустой Context; это не foreign доказательство.
2. Настоящим GET получить proof **до удержания F**. GET может одновременно держать продуктовый db и inspection db: раннее удержание F искусственно исчерпало бы два слота и лишило бы тест proof по чужой причине. После GET дождаться штатного возврата; проверить два ещё не созданных account-решения и очищенные прежние operation owners.
3. Одновременно выдать два соединения этого request pool: F и T. Настоящими SELECT/PID/commit прогреть их, вернуть T, F оставить выданным с завершённой транзакцией. Зафиксировать точные entry/DBAPI/native driver/PID и отсутствие request owner у F. Единственный свободный slot — T. Все product auth/tenant/admission операции могут последовательно переиспользовать его.
4. Сетевые listener/relay markers регистрировать до connect либо контролируемого прогрева. Связать каждый stream с соответствующим native driver через реальные public connect/checkout callbacks и проверенную последовательность прогрева; не угадывать stream по последнему элементу при неконтролируемом конкурентном connect.
5. Получить proof из памяти и сделать один настоящий POST с существующим synthetic auth/CSRF. Один handle POST и весь набор own/observer/relay tasks сохраняются для доказательства завершения и аварийного cleanup.

## Наблюдение фазы и сетевой fault

Разрешены только публичные SQLAlchemy Engine/Session/Pool события и существующий проектный owner metadata для чтения. Native close/rollback/commit/terminate, Session/Connection методы и библиотечные внутренние состояния не подменяются. Ни искусственного sleep внутри runtime callback, ни нового product hook, private protocol/transport, прямого DBAPI COMMIT или driver transaction.

Пассивный Session/Connection observer связывает **точную ResultAdmissionSession** из test boundary с её sync Session, корневой transaction и Connection. Затем Engine.commit на этом Connection, после прежнего handoff hook, фиксирует:

- тот же request owner и project admission owner; exact entry/DBAPI/native driver/PID;
- connection/root lease identity и их actual task/Context; обе ссылки уже указывают на задачу, реально выполняющую COMMIT;
- открытый checked-out target, непротиворечивые Session/transaction связи, исходные work/cleanup deadlines;
- ровно две выполненные INSERT-попытки пары, один analytics commit-enter, отсутствие прежнего отказа; auth/renewal commits считаются отдельно;
- before/after_commit и reset/checkin/invalidate/close события как упорядоченные metadata markers, без proof, содержимого, SQL parameters или auth.

Engine.commit-enter означает вход публичного события перед настоящим dialect commit; сам по себе этот marker не доказывает отправку COMMIT. Настоящий server commit доказывается только последующей M1: обе durable строки видны независимо, ответ удержан, after_commit отсутствует. События только снимают snapshot/ставят marker и в fault закрывают gate. Assertions выполняются после callback, чтобы ошибка наблюдателя не стала подставленным SQLAlchemy отказом.

**Gate нужен на server→client данных одного target stream T, а не глобальный gate всех соединений.** У существующего relay глобальный gate затронул бы F; для нового опыта допустимо добавить необязательные test-only per-stream gate и маркер фактически удержанного ответа, сохранив прежний yield/поведение callers. F, observer и последующее новое поколение проходят независимо. Это транспортная задержка, не изменение driver.

Normal: gate всегда открыт. Fault: синхронно в exact analytics Engine.commit gate T закрывается **до передачи COMMIT-ответа**. Client→server направление остаётся открыто; реальный COMMIT доходит в PostgreSQL. Relay фиксирует, что получен и удержан server chunk, но не сохраняет/журналирует его содержимое. Target pump имеет ограниченное обычное чтение, не бесконечный буфер. Не нужно расшифровывать proof/SQL/PG payload или читать private asyncpg protocol.

Обязательная причинная точка **M1, до отмены**:

- commit-enter target произошёл ровно один раз, его task ещё не отменяется, POST ещё pending;
- целевой server→client chunk реально удержан закрытым gate, Session.after_commit для target ещё не наблюдался;
- отдельный direct observer с правильным tenant/test доступом видит **обе** durable строки именно этого синтетического аккаунта из другой транзакции; target backend ещё присутствует, idle/без xact и locks0; преждевременное исчезновение backend не принимается за эту фазу; промежуточная одиночная строка не принимается;
- F в том же request pool при всё ещё закрытом T gate сохраняет exact entry/DBAPI/native/PID и выполняет SELECT1/commit. Иначе per-stream изоляция fault не доказана.

Observer перечитывает свежий snapshot в коротком конечном окне, заканчивающемся до исходного work deadline; это тестовое наблюдение, не retry продукта. Отсутствие M1 не разрешает «PASS по unavailable»: это неправильная/недоказанная фаза опыта. Особенно запрещено принять отказ pre-ping/auth/размера/сессии как неизвестный COMMIT. Не ждать M1 после отмены и не добавлять новый срок для неё.

## Критерии normal и fault до teardown

| Контрольная точка | Normal | Fault после доказанной M1 |
| --- | --- | --- |
| Настоящий HTTP исход | Полный accepted/private-no-store, не synthetic200 | Полный unavailable/private-no-store в исходном бюджете; accepted, transport response_complete error и незавершённый ответ — FAIL |
| Бюджет | Исходные guard2s/work1.5s/cleanup0.5s, SQL<=128, lock<=250ms, statement<=500ms | Те же исходные сроки без нового retry/таймера/второй analytics Session; ответ и обязательная ранняя проверка ресурсов до исходного hard deadline |
| Analytics ledger | Ровно две durable строки, payload/keys сохранены | Тоже ровно две уже committed строки; не объявлять rollback по одному unavailable |
| Analytics commit | Один enter, один after_commit, один commit решения | Один enter; acknowledgement до отмены не получен; after_commit может отсутствовать. Самовольного второго commit/admission нет |
| Обычный return | Для exact T reset→checkin; asyncio_safe=True, terminate_only=False, transaction_was_reset=False; здоровый native driver idle/no transaction. Числа чужих auth/renewal reset не подменяют target marker | При всё ещё удержанном COMMIT-ответе exact generation нельзя считать здоровой для reuse: нужны штатная invalidation/abort/checkin(None) и полная очистка старого поколения. Не требовать normal reset на уничтоженном соединении |
| Владение | Project Session без транзакции, `_listeners=[]`; guard owner/transactions/unbound_roots и соответствующие Session.info/Connection keys очищены; нет owner tasks | То же; исчезновение metadata не заменяет отсутствие tasks/DB work/checkout |
| Ресурсы target | Slot доступен, backend idle/no transaction/locks0; живой socket пула допустим | При abort старый driver закрыт, backend/locks отсутствуют, target relay root/pumps/writers/wait_closed завершены **до gate.set/fixture cleanup**. Возврат этого driver при всё ещё удержанном непрочитанном ответе не принимается за безопасный idle-return; одна is_closed отметка недостаточна |
| Same-pool foreign | F сохраняет exact PID/native и SELECT1/commit; checkedout=1 только F | То же при закрытом fault gate, до cleanup стенда |

Нормальный здоровый socket сохраняется в контрольном случае. В fault строгость связана с доказанной M1 и непрочитанным ответом, а не с любым COMMIT-исключением: если фактический native путь разрешает неопределённость иначе до снятия gate, это отдельная наблюдённая ветвь для пересмотра проекта, а не автоматическое доказательство runtime-дефекта. Метки reset/checkin наблюдают реально пройденную фазу, но не доказывают сетевой вызов default rollback. SQLAlchemy/asyncpg source объясняет его no-op; ради более сильного названия доказательства ничего не подменяется. Публичный `is_closed()` проверяется раньше `is_in_transaction()`; на закрытом native driver последний не вызывается.

Успех не может обеспечиваться watchdog/fixture finally. Watchdog за пределами2s допустим только для выхода из RED и обязан остаться несработавшим при PASS. Не использовать общий engine.dispose, pg_terminate_backend или ручное close/rollback/invalidate для получения ранней приёмки ресурсов. После пройденной точки до teardown убрать лишь test observers; удаление listener не должно прекращать/чинить product work.

## Передача slot и отсутствие позднего воздействия

До открытия fault gate и до test teardown, после ранней точки очистки, взять B **из того же request pool**, пока F удерживает второй slot. Публичный checkout должен подтвердить тот же T entry, очищенные request keys и Context owner=None. В normal B получает тот же здоровый driver/PID; при abort — новое поколение и другой driver/PID. B выполняет SELECT1 и остаётся выданным.

Пока B выдан, повторно проверить старые owner tasks/registry, target старого поколения и F. Только затем снять fault gate как отдельную проверку позднего воздействия, сохраняя B/F; они снова выполняют SELECT/PID/commit с неизменными поколениями и остаются здоровыми. Ранние утверждения уже пройдены и не могут зависеть от этого снятия. В fault старый relay обязан быть завершён раньше, поэтому поздние сохранённые ответы не должны воздействовать на новый borrower.

Не создаётся искусственный await после checkin внутри Session.close ради нового «race». Эта часть доказывает безопасный reuse и отсутствие пережившей запрос cleanup; она не объявляется проверкой чужого borrower при намеренно незавершённом fake close. Вся ранняя приёмка target/F/B и поздняя проверка должны уложиться в исходный hard deadline; обычное финальное закрытие test-owned F/B выполняется отдельно после неё и не используется как доказательство cleanup запроса. Не требовать пустоты relay-задач здоровых F/B sockets; различать их с orphan target и owner tasks.

## Неизвестный commit и следующий показ

До явной новой попытки наблюдения должны доказать: ровно одна analytics operation/две исходные INSERT-попытки/один Engine.commit-enter, две durable строки и неизменные safe payload, ноль provider calls. HTTP200/unavailable не означает отсутствие записи. Внутри этого запроса и после deadline новых application retries быть не должно.

После ранней приёмки, здоровых F/B и штатного возврата test-held handles допустим **один явный следующий настоящий POST** с тем же действующим proof, обозначенный как новый переход видимости. Он имеет свой обычный request budget и обязан принять существующие account keys без переписывания event ID/occurred_at/payload и без новых решений/egress. Его повторные conflict INSERT не считаются автоматическим retry первого запроса: счётчики и интервалы отделены. Это проверка серверного reconciliation; browser/frame поведение уже покрыто отдельным observer и здесь не симулируется как реальный пользователь.

## Условия HOLD и порядок после проекта

Опыт остаётся HOLD при недостигнутой M1, fault в чужой фазе, заблокированном F, assertion внутри callback, искусственном reset caller, потерянном владельце, изменённом бюджете/caps, отсутствии полного HTTP ответа, неизвестных задачах/locks/checkout, доказательстве только после gate.set/dispose, либо повторе неизвестного commit без нового явного запроса.

Следующий исполнитель сначала реализует только этот тестовый стенд/два случая и получает причинный результат на неизменном runtime. Отрицательный результат допускается и сохраняется; он не означает разрешения менять guard без нового независимого проекта исправления. После PASS нужен законченный затронутый профиль (новые2 и необходимые текущие HTTP/owner регрессии без двойного счёта), точные source/test hashes и независимое implementation review. Старые120/233/294/312 не складываются в новую сумму. При test-only правке без новой находки не повторять все тяжёлые исторические опыты.

Проект не принимает packet loss до server commit, deferred COMMIT/commit error, TLS shutdown, arbitrary callbacks, AUTOCOMMIT/внешне привязанную Session, raw native transactions, весь restore/readiness/T113 или ручную GRAF Dev. Эти случаи не объявляются закрытыми нормальным reset или этим unknown-ack сценарием. Истёкший T098 не продлевается; мастер merge freeze, production collection off и Postal сохраняются. Контент/вёрстка, выпуск, T0, трафик и продажи не затрагиваются.

## Требования, происхождение и точные входы

Повторно прочитаны исходный result-visibility по частям, связанные положения activation-milestones о двух строках/unknown commit/DB drain, T112 spec/plan/tasks/quickstart, scoped analyze, применимые guidance и текущие callers/библиотеки. Прежнее собственное чтение неизменённых требований того же диалога переиспользовано по принятому порядку F273; новые применимые источники прочитаны непосредственно. Сверены все18 текущих `unchanged_inputs` из `/private/tmp/graf-t112-root-history-reading-20261116.json`: **18 SAME**. Текущий result-visibility SHA-256 `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` прочитан, а исторический80f… в старом analyze не выдаётся за его текущую контрольную сумму.

Повторная завершающая сверка всех18 картографированных входов и18 перечисленных ниже исходников/отчётов/библиотек дала SAME; это не запуск тестов.

Analyze `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` остаётся применим к FR-021/025 и SC-006 как согласованность существующего среза и открытых T112/T113. Настоящий проект конкретизирует предусмотренные timeout/unknown commit/cleanup, не добавляет новое поведение сбора, получателя или схему хранения. Старый analyze не заменяет самостоятельное тестовое проектирование и последующие source-bound проверки.

Применимые к этому T112-срезу reviewer-owned списки перечитаны для подсчёта: requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124 checked / 0 unchecked**. Отметки не менялись; это состояние требований, не приёмка реализации.

| Просмотренный текущий файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py` | `b9a25a268349afa95caf6f5384e1953bdfee44a1197453a9c526b5839439229e` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `apps/server/src/twobrain_rec_server/auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `apps/server/src/twobrain_rec_server/auth/session_renewal.py` | `0fea864d2aeb6028666e9ba8befe5c351871f5fd095328d7bc8e3b36beb81fd1` |
| `apps/server/src/twobrain_rec_server/db/session.py` | `a01c5ab2a45888fedc387dc6656defc92512707e3a485c1c5e2c8f83e616a529` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `6c1274ef26d94df8caed306bf0e8b0cef5a81f45e0d2174726c149fbed9e45f5` |
| `apps/server/tests/contract/test_result_view_http_integration.py` | `8b0b6676a4281e31d1fd1d6ad0a045ee708a483d379babe7c801daec19e5bfd7` |
| `apps/server/tests/contract/test_result_view_admission.py` | `44e51f37cad630576af337c07012d011d219f109f0d589ed9eef587015306269` |
| `apps/server/tests/contract/test_result_projection_session.py` | `c4f8880960f241d9b1b8d00587b35fff9446dfcd15c9c2ecdec0e5addf167458` |
| `specs/273-paid-traffic-analytics/validation/t112-http-integration-final-review-20261116.md` | `1d9d5e15dc98c204fc94447324db6c338b80971bf8e100456233eb0054cfd8c6` |
| `specs/273-paid-traffic-analytics/validation/t112-close-review-20261116.md` | `24e976546e6ee9bfac58d4814fe240208736e87c7085e4a4a779183e7e818e97` |
| `specs/273-paid-traffic-analytics/validation/t112-pool-return-source-20261116.md` | `b59388e936369cb1c1c1144bae2eba3412298ef0dda85eaa66428b1f536b4016` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py` | `53f38e544004d329ac38e243104bf4bbbaf7d0f0cecabd112b1923b78dde5614` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py` | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py` | `b75a4e427f453c2eaf19f04d87f66c2da644698a14f3b11880f56a73e2a0760d` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py` | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |

Никаких тестов, сборок, контейнеров, служб, сетевых проб или внешних сообщений при этом проектировании не запускалось. По последнему точному поручению Git/GitHub не использовались; выполнены только чтение, сверка контрольных сумм и запись этого нового отчёта. Source/tests/spec/plan/tasks/checklist/прежние отчёты, включая ранее подготовленный preflight, и чужая работа сохранены. Вывод — допуск будущего опыта, не автоматическая приёмка его реализации или рабочего запуска.
