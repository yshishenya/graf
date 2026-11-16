# T112 — независимое ревью настоящего COMMIT и обычного возврата

16.11.2026. Рецензент `/root/public_counter_readiness_review`. Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`; исходный checkpoint `237d368b94c61908f853262ec1be545504951dc8`. Существующая `high-risk-product` F273/T112/#7698, T113/#7804. Владение рецензента — только этот новый отчёт; код, тесты, требования, списки, прежние отчёты и чужая работа не изменялись. Git использован только для чтения exact diff и сравнения исходников с HEAD; запусков тестов рецензент не выполнял.

## Решение на текущем законченном доказательстве

**IMPLEMENTATION HOLD. P1=0 подтверждённых дефектов продукта; P2=1 открытая недостающая проверка тестового доказательства.** Основной причинный опыт настоящего COMMIT, M1, ранней очистки и безопасной выдачи слота соответствует принятому проекту. Но весь новый сценарий пока не принят: в законченном общем профиле следующий отдельный POST вернул `unavailable` вместо `accepted`; причина не восстановлена. Последующая удача двух native случаев не объясняет исходный отказ.

Старый тест TTL имел доказанный дефект фазовой постановки; его минимальное исправление часов маршрута допустимо и уже внесено основным исполнителем. Оно не объясняет отдельный отказ нового сценария. Общий профиль с временным наблюдателем закончен86PASS/1FAIL; причина нового FAIL — подтверждённая коллизия диагностического наблюдателя с прежним тестом. Observer удалён; **окончательный штатный профиль двух неизменных тестовых файлов без него завершился87PASS/EXIT0/cleanup removed**. Этот GREEN принят как фактический результат данного запуска; HOLD по первоначальному неизвестному отказу и P2-01 сохраняется.

## Точный проект и границы diff

Принятый собственный проект `t112-ordinary-return-design-review-20261116.md` перечитан; SHA-256 `04f10392b802ffd769dcd95324de4f1070f125ac29385f121547475611ad9c6f` совпал. Рассмотрен реальный diff двух `apps/server/tests/contract/test_result_view_http_{budget,integration}.py` против HEAD, а не описание автора.

В budget helper добавлены только открытый по умолчанию `response_gate` и `response_held` на каждый поток, ожидание server→client gate и его освобождение в аварийной очистке. Старый глобальный gate, прежний yield и EOF-механизм сохранены. Client→server не блокируется, ограниченный read65536 не превращён в бесконечное буферирование. Здоровые потоки не объявлены утечкой.

В integration добавлены импорты и наблюдение исходных deadlines в существующей test-only period fixture, два native случая и узкое исправление старого TTL-теста. Новый native блок имеет288 строк по hunk header; весь текущий exact diff: budget+8/-1, integration+314/-5. SHA-256 текущих файлов: budget `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7`, integration `83c90ab8837ce8e3a16bd038c6b63313c2e0db4c73b6fac8a1a7c4f9a23930be`. `_result_period_context` продукта остаётся `yield None`; новых runtime caller/flag/T0 нет.

Проверены и совпали с HEAD все затронутые пути продукта: guard, result_projection_session, ingest, result_views, result_visibility, auth dependencies/renewal и db/session. В частности guard `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6`, projection session `b9a25a268349afa95caf6f5384e1953bdfee44a1197453a9c526b5839439229e`, ingest `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795`, result_views `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e`, result_visibility `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04`. Перечисленные журналы относятся к тестам, а не production.

## Соответствие нового native опыта проекту

1. Используется настоящий `_real_app`, GET и canonical POST. TCP relay и request engine имеют pool2/max_overflow0/pre_pingTrue; native/SQLAlchemy методы не подменены. GET выполнен до удержания F; два native connect прогреты последовательно с однозначным stream/generation mapping.
2. F удерживает второй слот того же request pool, имеет подтверждённые DBAPI/native/PID и работает до/во время/после fault. Direct observer — отдельный engine/Context и не выдаётся за foreign доказательство.
3. Public Engine.commit observer выбирает точный ResultAdmissionSession/Connection, снимает точные owner/root/lease/task/Context/entry/DBAPI/driver связи. Событие только наблюдает и закрывает target gate, assertions выполняются вне callback. Auth/renewal commits не принимаются за analytics commit.
4. M1 наблюдается до work deadline: удержан реальный server chunk; обе durable account-строки видны из независимой транзакции; целевой backend присутствует idle/no xact/locks0; after_commit отсутствует; POST pending и commit-task не отменяется. F выполняет native SELECT/commit при закрытом target gate. Повторные observer snapshots ограничены собственным коротким окном и не являются повтором продукта.
5. Первый запрос делает ровно две попытки INSERT и один analytics COMMIT. Normal требует accepted/private-no-store и точный commit→after_commit→reset(True,False,False)→checkin; сохраняет здоровый idle driver. Fault требует unavailable/private-no-store, сохраняет обе committed строки и завершает старое поколение/relay root/pumps/wait_closed до gate.set и до teardown.
6. В обоих случаях проверяются очищенные Session/owner/root/unbound/Connection keys и отсутствие owner tasks. До исходного hard deadline B получает тот же entry при удержанном F: normal — прежний native/PID, fault — новый native/PID. Повторные F/B SELECT/commit после снятия старого gate не чинят раннюю проверку. Watchdog3s только аварийный и не срабатывает при PASS; caps и deadlines не увеличены.
7. После окончания первой операции, возврата test-held F/B и отмены watchdog выполняется ровно один отдельный POST. Он должен принять существующую пару без изменения eventID/occurred_at/payload и без provider dispatch. Это новая видимость с собственным guard budget, а не автоматический retry неизвестного COMMIT.

Не обнаружено подставленного native commit/close, нового product hook, искусственного замедления default reset, teardown/dispose как раннего доказательства либо уничтожения здорового socket в normal. Старые native close/precheckout эксперименты не объявлены новой работой.

## Открытая находка P2-01: fault-события собираются, но их исход не проверяется

В новом fault branch callbacks `invalidate`/`checkin` сохраняют markers и `returned_dbapi`, но ранняя приёмка утверждает только closed-driver, отсутствие backend, finished-relay и pool checkedout1. **Не утверждены сам exact invalidate→checkin(None) и смена DBAPI при выдаче B**, хотя переменная `dbapi` уже получена из exact checkout. Нормальная ветвь проверяет returned_dbapi, fault — нет.

Это пробел точного причинного доказательства, а не обнаруженный дефект runtime. Остальные ресурсные утверждения сильны и сохраняются. Допустимое минимальное test-only дополнение: до gate.set/teardown проверить один целевой invalidate, последующий checkin и `target["returned_dbapi"] is None`; при B дополнить уже имеющееся native/PID сравнение DBAPI identity (fault новый, normal прежний). Assertions остаются вне callbacks, сроки/caps/fixtures не меняются. Если библиотечная фактическая трасса отличается, сохранить её и пересмотреть только конкретное ожидаемое событие с исходником; не форсировать событие методом теста.

## Два исходных отказа — раздельный причинный разбор

### TTL: входная подпись уже истекла, задуманный admission race не состоялся

`_age_proof(...,599)` подписывает issued_at=`int(datetime.now().timestamp())-599`. Поэтому остаток до TTL600 равен менее секунды и зависит от дробной части времени плюс auth/DB задержки до маршрута. Старый `AfterReadClock` добавлял5 к текущему живому времени, но никак не закреплял входные599 секунд.

В runtime result_views:101 вычисляется age; только ветвь age=`expired` на111–117 может вернуть `renewed`. Значит наблюдённый исход renewed уже доказывал иной входной путь. Диагностический законченный повтор дополнительно напечатал первым `proof_age: expired` и снова получил тот же отказ. Это причинное подтверждение неверной фазовой постановки, не предположение о нагрузке. Точный размер задержки в первом запуске не записан и не выдумывается.

Принят минимальный проект и прочитана фактическая правка: извлечь issued_at именно из переданного aged proof; только result_views.datetime.now возвращает issued_at+599 до настоящего load_fresh_result_view_bindings и +604 после завершения этого load. Настоящие proof-age/verify остаются неизменными; real auth wall clock и monotonic deadlines не меняются. Тест требует первым599 и последующим604, один admission period вместо renewal, ноль writes/commits/rows и освобождённый pool. Сдвиг привязан к завершению настоящего чтения; одного изменённого expected response для исправления недостаточно.

Завершённый observed-профиль и окончательный штатный87PASS записали route ages[599,604,604] и fresh_read_completed=True; исправленный TTL случай прошёл. Это проверка фиксированной фазовой постановки, а не случайная последующая удача старой real-time версии. **Узкая TTL-поправка принята**; настоящие verifier/load/auth/budgets сохранены.

### Новый отдельный POST: исходный отказ не объяснён

В исходном общем профиле native fault уже напечатал M1/early cleanup/F/B PASS за1.552s. Затем failed assertion относится именно к отдельному repeated JSON `unavailable`, а не к первому fault или его cleanup. Начальный baseline завершил оба случая полностью, включая этот POST. Диагностический повтор тоже завершил оба native случая, но не воспроизвёл причину исходного отказа.

Ни elapsed первой операции, ни85PASS, ни следующий PASS не доказывают причину. Не установлен первый refusing caller/exception именно исходного repeated; не доказаны timeout, caps, stale proof, retained owner, lock или внешний фактор. Отдельная ошибочная ветвь старого TTL-теста не переносится на новую свежую подпись.

Допустим следующий ограниченный диагностический проект: один законченный затронутый профиль с неизменными ожиданиями и бюджетами, наблюдающий safe metadata по отдельным операциям. Записать входной age/результат verify; первый `_refuse` конкретного owner (caller/line, monotonic deadline_remaining, same_task, failed/budget_failed, sql_count и фаза); тип/место исключения до преобразования в обобщённое ProjectionBudgetExceeded; entry/driver-generation и числовые DB locks/transaction при отказе. Не записывать proof, SQL parameters, данные встреч, payload, auth или URL с секретом. Делегировать оригиналу ровно один раз, исключение rethrow; не менять return, срок, native или product hooks.

Прочитан временный plugin `_t112_ordinary_diag.py`, SHA-256 `829c10761c455155f401e6390857dcb3d04d851009420eb882d458c70962ca7c`. Он делегирует originals, rethrow и не подменяет native операции. Его пределы: `if not owner.failed` не фиксирует первый `_refuse`, если failed установлен раньше другим путём; внешний transaction-wrapper может видеть уже преобразованное исключение из `_result_session_context:382`, а не первоначальную причину. Поэтому отсутствие диагностической находки нельзя объявить доказательством отсутствия отказа. Более подробный exception trace допустим лишь как отдельное ограниченное наблюдение при необходимости; возможное влияние наблюдателя на время нужно учитывать, сроки не продлевать.

Observed-профиль получил86PASS/1FAIL: `hour_near_total` выдал KeyError при чтении своего first_refusals[id(owner)]. Сам near-total fallback допускает безопасный отказ по времени; перед ним записано checkpoint/deadline_remaining=-0.1329. Но plugin добавил собственный `_refuse` именно на ResultInspectionSession, в то время как тест патчит ResultProjectionSession._refuse. По обычному поиску методов подкласс обошёл существующий base callback, marker не попал в first_refusals и fallback получил KeyError. Это доказанная коллизия observer, не доказательство нового дефекта runtime и не объяснение исходного repeated. Plugin теперь отсутствует на диске; конечные два тестовых файла его не импортируют. В этом observed запуске оба native случая и их отдельные POST прошли, normal1.143/fault1.589s; исходная неизвестность остаётся.

## Законченные журналы и границы их доказательства

| Журнал | Результат и область | SHA-256 |
| --- | --- | --- |
| `/private/tmp/graf-t112-native-commit-baseline-20261116.log` | native2PASS,56deselected;11.47s pytest/16s runner; normal0.778/fault1.555, teardown isolated_container_removed | `abc2cb44935541c26031ac99040a84ea6c554bb34e5428be7144116efc2f1f24` |
| `/private/tmp/graf-t112-native-commit-profile-20261116.log` | общий85PASS/2FAIL;170.28s pytest/177s runner; normal0.754/fault1.552 до отдельного POST; isolated_container_removed | `3d7afbecd7e1018be9f677a26ce6bb163794e113abff46002b141be1edf265ea` |
| `/private/tmp/graf-t112-native-commit-diagnostic-20261116.log` | native2PASS/TTL1FAIL,55deselected;13.27s pytest/18s runner; TTL initial expired, native repeated отказ не воспроизведён; isolated_container_removed | `6883a2f322d819bf955ca9049a6ab69e5d44bc22d1f8af208a8acaa4002a544e` |
| `/private/tmp/graf-t112-native-commit-profile-observed-20261116.log` | общий86PASS/1FAIL;164.41s pytest/170s runner; TTL и native+repeated прошли, observer коллизия near-total; isolated_container_removed | `4da055cc19fba584c0c267311d80c29fdd4eba51e3623a578fa7c0fcf1f287cf` |
| `/private/tmp/graf-t112-native-commit-final-20261116.log` | штатный полный87PASS;150.46s pytest/154s runner; оба native+repeated и TTL599/604/604 прошли; isolated_container_removed/resultpass, EXIT0 подтверждён исполнителем | `5bbd2af489357de43a880b7739b6f219983ecb8caf8478c833af85f16e2fa28e` |

Три промежуточных журнала остались FAIL независимо от успешных native подслучаев. Числа из разных запусков не складываются. Предыдущие312HTTP/прочие120/233/294 не заменяют новый затронутый профиль. После сообщения исполнителя о terminal EXIT0 независимо прочитаны законченный финальный лог, полный exact diff и окончательный validation автора `t112-ordinary-return-validation-20261116.md`, SHA-256 `a3b81d644d677b56189481bd4980c498854ffc6be945ea9698bdb1541e18c61f`. Прежняя прочитанная редакция validation имела69b539…; новый hash относится именно к окончательной прочитанной редакции, а не к старому snapshot.

Финальный лог имеет collection87/digest `6d62f13844d8b8bd0585c7b7032e595806dc81de0189e50d55d7a7a46a85b28d`, один прежний PytestAssertRewriteWarning, без skipped/deselected и `postgres_test_result=pass`. Normal0.992/fault1.550 до ранней точки/F/B, watchdogFalse, следующие отдельные POST также прошли. Near-total в этом запуске законно использовал предусмотренный прежним тестом over_work fallback; marker теперь получен без диагностического subclass override. Source budget/integration побайтово совпал с указанными выше f12c9615/83c90ab8; plugin отсутствует. Diff всего apps/server/src и changes относительно HEAD пуст, отдельно сверены18inputsSAME и124/0. Рецензент terminal самостоятельно не опрашивал и тестов не запускал.

Собственный validation автора сохраняет HOLD и неизвестность repeated. Для точного учёта: **P2-01 этого независимого отчёта — отсутствие assertions точного fault invalidate/checkin(None)/DBAPI**, а первоначальный repeated отказ — отдельное неразобранное основание HOLD. Одно не объясняет другое; его не следует называть установленным P2-дефектом продукта.

## Требования, checklist, следующий шаг

Завершающая сверка18 `unchanged_inputs` из `/private/tmp/graf-t112-root-history-reading-20261116.json` дала18SAME. Сохранены применимые result-visibility§5/activation-milestones: полный2s, work1.5/cleanup0.5, lock250ms, statement500ms, SQL128, пара атомарна, unknown commit не повторяется автоматически. Старый analyze `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` применим к существующим FR-021/025,SC-006 и открытым T112/T113; он не принимает новую реализацию вместо законченного тестового доказательства.

Применимые reviewer-owned списки перечитаны/посчитаны без изменения: requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124 checked /0 unchecked**. Это состояние требований, не закрытие T112.

Окончательный source/hash и законченный профиль без plugin получены. До implementation PASS остаются P2-01 и отдельное причинное решение об исходном repeated отказе. Если первоначальная причина не получена, она остаётся явно неизвестной и HOLD не снимается просто новым зелёным запуском. Минимальный проект test-only исправления P2-01 выше допустим; его ещё нет в принятом source и87PASS его не проверяет. Для неизменного кандидата новых прогонов не требуется. Ограниченное дальнейшее наблюдение имеет основание только в конкретном завершённом отказе и сформулированном новом причинном вопросе; массовые повторы не предлагаются. Изменение runtime этим ревью не разрешается.

Полный runtime T112/T113, restore/readiness, ручная проверка GRAF Dev и выпуск этим отчётом не закрыты. Production collection off, Postal, контент/вёрстка, T0 и master merge freeze до принятия измерения сохраняются; трафик и продажи не заявляются.
