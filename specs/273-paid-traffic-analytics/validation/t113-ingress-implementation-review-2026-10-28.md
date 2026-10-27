**Актуальное решение повторного ревью: SCOPED PASS, R1/R2 исправлены. См. дополнение в конце; исходный FAIL сохранён как история. Swift исполнение и выпускные проверки ещё обязательны.**

# Независимое ревью ingress T113 — 28.10.2026

**Решение: REQUEST CHANGES / scoped FAIL.** Найдены два исправимых замечания: P1 в новом переносе авторизационных заголовков desktop-клиента и P2 в свежести admission gate после ожидания блокировки аккаунта. T113/T106/T112 и рабочее включение остаются открытыми.

Проверяющий `/root/activation_requirements_gate`, навык code-reviewer прочитан и применён. Ветка `codex/273-activation-ingress`; HEAD основы `4604cb2a616374903773a200330e8606deae59c1` (merged #7774). Проверен текущий незакоммиченный diff14 файлов (включая own fragment) и новый test_activation_milestone_ingress.py; exact SHA основы не обозначает изменённые байты. Изменять разрешено только этот отчёт/reviewer checklist; проверяющий изменил только отчёт. Lane: independent code review активного high-risk Spec Kit среза.

## R1 — P1: auth headers уходят на произвольный endpoint из конфигурации

Место: `apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift:55–56` вместе с выбором endpoint44/50; зависимость `ProductAnalyticsDirectProviderConfig.allowsPostHogDirectRoute` в Shared/Sources/Models/ProductActivationAnalyticsModels.swift.

До изменения directPostHogRequest не переносил credentials клиента. Теперь весь headers, включая X-Auth-Session/Authorization/Cookie, копируется в URLRequest к config.posthogCaptureEndpoint. Разрешающая проверка конфигурации требует только непустой URL и флаги согласований; она не сравнивает origin с client.baseURL, не требует защищённый транспорт и не ограничивает путь first-party proxy. Поэтому при разрешённых флагах и endpoint `https://analytics.example.invalid/capture` получается запрос с сессионным секретом GRAF на другой узел; при http endpoint возможна и передача без TLS. Это следствие текущего конструктора запроса, для него не требуется настоящая отправка или секрет. Утечка на рабочем сервере/в установленном приложении не наблюдалась; наличие рабочего вызывающего пути этого метода не подтверждено (поиск обнаружил конструктор и тесты). Тем не менее изменённая публичная функция сама не соблюдает границу credentials и готовит опасный запрос при ошибке конфигурации.

Минимальная коррекция: перед копированием auth headers разрешать только точный first-party `/api/v1/product-analytics/posthog-desktop-capture` того же доверенного GRAF origin, со сравнением scheme/host/effective port и без userinfo/непредусмотренных query/fragment; либо строить URL из доверенного baseURL и отклонять несовпадающий config endpoint. Не отправлять auth headers на PostHog host или произвольный route. Обычный desktop маршрут и его формат сохраняются. Нужны локальные Swift проверки: свой endpoint сохраняет auth/compatibility headers; другой host, изменение scheme/port и чужой path не создают запроса с credentials. Существующий тест проверяет только положительный пример, несмотря на имя AllowsOnlyFirstParty.

Это реализационное нарушение уже принятой first-party/auth/egress границы; недостаточность требований не выявлена, reviewer117 checklist не возвращается в незавершённое состояние.

## R2 — P2: повторная проверка основания предшествует ожиданию account lock

Место: `product_analytics/ingest.py:132–138`, зависимость `product_analytics/milestones.py:287–331`.

Caller обновляет gate после соединения, но затем admit_account_milestone выполняет await SELECT UserIdentity FOR SHARE. Этот запрос может ждать чужой FOR UPDATE; после получения lock код не перечитывает withdrawal/readiness/provider решения и исполняет INSERT по прежним значениям. Воспроизводимый порядок: другая транзакция удерживает user row lock без смены active; ingress проходит gate и ждёт; оператор отзывает основание или выключает writer; первая транзакция освобождает строку; ingress записывает решение, хотя текущее основание уже запрещает запись. Аналогично начальные provider intents вычислены до ожидания и могут устареть. Безусловный recovery blocker сейчас удерживает рабочий путь закрытым, поэтому это не утверждение о рабочей записи после отзыва. Но проверяемый auth-backed admission с открытыми тестовыми receipts уже содержит окно, и устранение его нужно до снятия этого blocker.

Минимальная коррекция: добавить узкий trusted callback свежей проверки после получения account lock и непосредственно перед составлением/INSERT решения; он повторно проверяет admission blockers и заново вычисляет разрешённых получателей. Примитив по-прежнему не отправляет сеть/не коммитит. Если закрыт level2/общий writer — refusal/rollback; если отозвана только рекламная цель — локальная разрешённая веха может сохраняться, но её provider intent не должен стать pending. Перечитывание до вызова примитива этого ожидания не покрывает. Не нужен новый сервис, реестр или расширение задачи. Время accepted_at разумно брать после этого ожидания.

Профильная проверка: настоящая задержка FOR SHARE за другой транзакцией, изменение withdrawal/выключателя во время ожидания, отпускание строки и подтверждение отсутствия нового решения; отдельно отзыв только provider цели сохраняет допустимый local decision без соответствующего pending intent. Предыдущая проверка отзыва после соединения/до primitive lock не покрывает этот порядок.

## Остальные проверенные выводы

| Область | Независимый вывод |
| --- | --- |
| Общая граница | Оба API вызывают ingest_authenticated; server-auth использует тот же метод. Прежний синхронный ingest только валидирует и возвращает trusted_context_required, не считает и не отправляет. ParallelMeasurementRouter и default in-memory guard из него удалены. |
| Principal/identity | HTTP получает existing get_optional_principal, а не identity из body. Server-auth строит principal из результата завершённой авторизации. Псевдоним body и одноимённое свойство сравниваются с серверным build_safe_identity(UUID). Workspace выбирается из principal, не body. |
| Триггеры | first_open без trusted install key отвергается; account_connected через HTTP отвергается и допускается только source_kind=server. Browser source и result/value пока trigger_unverified, что честно сохраняет отдельный T112. source_kind caller-owned, не client JSON. |
| Tenant/RLS | Новый session использует WorkspaceAuthContext(auth_bootstrap) с проверенными organization/workspace/user. Уже рассмотренная0106 разрешает account branch только account_id=rec_current_user_id; maintenance bypass не вводится. Ledger повторно проверяет active identity FOR SHARE. Нового интеграционного ingress теста под отдельным реальным app login нет; текущие HTTP fixtures используют разрешённые dev headers, а отдельный ledger role test сохранён. |
| Commit/rollback | Admission открывает отдельную сессию, создаёт immutable решение+states, строит ответ из сохранённой строки и только затем commit. Ошибка commit возвращает безопасный отказ и close сессии откатывает транзакцию; нет provider вызова до/после commit. Аналитическая транзакция не является транзакцией sign-in. |
| Gate freshness | До открытия БД и после получения соединения/tenant context читается activation_milestone_write_blockers. Проверка после ожидания account lock отсутствует — R2. Withdrawal/file-errors/unknown/выключатели закрывают admission в момент чтения; provider resolver определяет начальные intents. Delivery-fresh gate ещё не реализован, потому что delivery отсутствует. |
| Recovery | activation_milestone_write_blockers безусловно добавляет activation_recovery_unverified. Даже пустой operations.blockers и одобрения не разрешают новый writer. Это явная честная блокировка до настоящего GRAF DB verifier, а не PostHog-only обход. |
| Provider side effects | Ни service, ни desktop API, ни server-auth не вызывают provider transport. Web-autocapture API сохраняет собственный существующий путь; он не принимает first-вехи и не объявлен частью этого среза. Dispatch/readback ещё не реализованы и не приняты. |
| Auth behavior | OAuth scheduling после auth commit; email background task выполняется после ответа/route commit. Обычный `/meetings` больше не считается desktop connected; маршруты `/desktop/...` и non-browser OAuth классифицированы сервером. Это выбранный auth path, не доказательство установленного/запущенного приложения. Тест email подтверждает две ветви; отдельного нового OAuth real-flow теста нет. |
| Legal reader | Непригодная и повторная распознанная запись теперь дают file_errors вместо молчаливого пропуска. Для нового activation gate это refusal. Другие старые writers не приняты как завершённый T106. |

## Проверки и их границы

Самостоятельно прочитан первый завершённый журнал `.dev/growth/t113-ingress-focused-20261028.log`:2failed/88passed/2warnings/11.67s, runner15с, isolated_container_removed. Две неудачи относятся к тестовым строкам с неверным префиксом withdrawal вместо установленного basis_withdrawal; в текущем новом тесте префикс исправлен. Старый FAIL сохранён как история.

Самостоятельно прочитан новый законченный `.dev/growth/t113-ingress-focused-v2-20261028.log`: **107 passed,2 warnings in24.14s**, runner28с, collection_count107/digest `ed5bf58531bfdf28ec44f0a77b2998c251f2609727010afa0f5b38eb967d1255`, isolated_container_removed, postgres_test_result=pass. Журнал включает новые ingress проверки и существующий ledger/role набор. Warnings: pytest fixture import rewrite и Starlette/httpx deprecation.

Новый тест непосредственно проверяет5 конкурентных admissions, оба HTTP формата→одна строка, отсутствие/подмену account, неготовые триггеры, отзыв между соединением и записью, rollback при commit failure, server-auth duplicate, закрытость missing/invalid/withdrawn recovery gate. Provider dispatch/capture monkeypatched с AssertionError — неожиданный вызов сломал бы прогон. Рабочие receipts заменены только локальным monkeypatch теста, а не runtime переключателем.

Старые чисто синхронные тесты честно теперь проверяют форму/отказ без trusted context, а не имитируют успешную воронку. DB дедупликация проверяется новым/ledger набором. Это промежуточная серверная приёмка, не сквозная первая ценность и не доставленная конверсия. После журнала исполнитель перенёс построение server-auth payload внутрь существующего try и уточнил комментарии/fragment; новый код независимо перечитан, это расширяет безопасный отказ без изменения модели, но107 PASS относятся к снимку до этого переноса. Swift тесты в этом журнале не исполняются; самостоятельный запуск тестов/сборки проверяющим не выполнялся. R1 не покрывается положительным Swift тестом и не снимается107 зелёными Python тестами.

`git diff --check` выполнен независимо: PASS. Полные CI/exact-SHA/base, converge, выпуск, production, реальные аккаунты/встречи/платежи не проверялись. Вне текущего среза остаются bounded dispatcher, transport classification/readback, настоящий GRAF recovery verifier/receipts и последующий T112.

## SHA-256 проверенного снимка

Code+inspected dependency digest (compact sorted JSON path→SHA256): `f75f07122c3f921c6b4ffdaee1cd20a17b3fb21fbac768de764a321959203c2e`.

- `apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift` — `3eef6a99f01afc80623031a5b79f1e40cecd7276d138967c74b8ba5c7bdb9cea`
- `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift` — `0e066fda177952aa44a08384a8e5d4a86f9e1cdc5e05be8d3b83034557db1f97`
- `apps/server/src/twobrain_rec_server/api/auth.py` — `78defae4b1f7b86acd0f24a2a75c3fc18ad5a70435a73859285adf6f450dd6dc`
- `apps/server/src/twobrain_rec_server/api/product_analytics.py` — `93e5212a6499568e77a51feed18af69987e7861a08e98d4959701f6b13572898`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py` — `1060270acb7e83a4c4cf9ec1777b199222219a3deb49b2c0c19edf91a3fa8f82`
- `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` — `465c4e27ddb7216b6b63cfcc2a2dc8237beecf703f3d557c84a3a53e461382b2`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py` — `e2d010bb4f04c4150016df1367e926376e8f49c7210fe8738d538280198272ad`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` — `cd327c89d1804db75f424ff38836f55c3b5b9ca918fbb52411990f91cf8d3693`
- `apps/server/tests/contract/test_product_analytics_registration_handoff_contract.py` — `414b897176d35a55c6333db28750d0de43c6ab93d8b52c320d4acdd47f9554e8`
- `apps/server/tests/integration/test_product_activation_analytics_rollout.py` — `ea20b4b4723c65852e4d53e0f0a57ef59faaf1ef60a60c93fdd705616c7e30e2`
- `apps/server/tests/unit/test_product_analytics_activation_funnel.py` — `6db86f46394747b2fcbc4dab1ad6b927df9db53009417a0e755368873609d52b`
- `apps/server/tests/unit/test_product_analytics_conversion_campaign_labels.py` — `51073a5996145d76635b8d302ebd33bc519c9f49fc1ec888be88599f69b86849`
- `apps/server/tests/unit/test_product_analytics_milestone_dedupe.py` — `e0e9cd250b5ca4a0ba9ff056de79de120148e849bf4cc97479bf2dfeb881d7bc`
- `changes/unreleased/F273.yaml` — `1a38a53e643f8eb45c56381afb42a58e2b670c9df5224e62728c6b8a5e475f64`
- `apps/server/tests/contract/test_activation_milestone_ingress.py` — `491b5236a261d3b0c824dc345d8081dba6807c0c4f24c81abc4bbb45514b754e`
- `apps/macos/Shared/Sources/Models/ProductActivationAnalyticsModels.swift` — `1cd1d6ce7fd7c9633dc29acf9213e0be5416dbd27ea0574316969ff478e021c2`
- `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` — `66cfaf82dbecba8bd52b1136d5eafe107715cb70314d50c630f4c0b20c37f3f9`
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py` — `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`
- `apps/server/src/twobrain_rec_server/auth/dependencies.py` — `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311`
- `apps/server/src/twobrain_rec_server/auth/context.py` — `0948549680aeacdf9c7c832e80c24fdd87e9124e8e007824660cc1437ea1d1f8`
- `apps/server/src/twobrain_rec_server/cabinet/auth_return.py` — `7e3847aadcd9768dc47e3aa6afc77f7a4b8b7c4a572efd05249c91a9385c8b7b`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/validation/t113-ingress-before-code-2026-10-28.md` — `e84e492ed2f02c38a31eaaf2cc2ed80f8b9d04a00b2c40783c07b608dab6b048`
- `.dev/growth/t113-ingress-focused-20261028.log` — `0e706c2b77197572011c2291f19a431ad887b7faf0aec0ad4cd1368226c38735`
- `.dev/growth/t113-ingress-focused-v2-20261028.log` — `baac86947e2a0e4bda3639eadb83eb3d3c344559cdd9b4d086b909613f8e936b`

- `changes/unreleased/F273.yaml` — `1a38a53e643f8eb45c56381afb42a58e2b670c9df5224e62728c6b8a5e475f64`

До и после записи отчёта хеши входов совпали. Проверяющий не менял код, тесты, spec/plan/tasks, checklist markers, Git/GitHub, приложение, рабочие flags или данные. Единственный изменённый им файл — этот отчёт. После устранения R1/R2 нужны повторное узкое ревью и актуальные проверки изменённых байтов.


## Повторное независимое ревью исправлений R1/R2 — 28.10.2026

**Текущий итог: SCOPED PASS статического ревью и рассмотренной серверной локальной проверки. R1 и R2 закрыты в текущем снимке. Новых блокирующих замечаний не обнаружено.** Исполнение Swift остаётся непроверенным здесь и обязательным в macos-pr; GitHub/exact-SHA, converge, релиз и рабочее включение не принимаются. Первоначальный FAIL выше сохранён как история и не является текущим решением.

HEAD основы остаётся `4604cb2a616374903773a200330e8606deae59c1`, ветка codex/273-activation-ingress; рассмотрены незакоммиченные исправления. Предыдущий отчёт до этого дополнения имел SHA-256 `ce204066a5a424e1a7da1b8713e373ff710b34937889fdeabab9a7434d15db24`. Проверяющий независимо прочитал текущий diff, пять изменившихся после предыдущего ревью входов, полный новый ingress test, новые Swift проверки, Yandex constructor/transfer_decision, fragment и добавление в growth plan. Хеши остальных ранее рассмотренных входов сопоставлены; исходные ограничения и открытые остатки сохранены.

### R1 — закрыто по коду; выполнение Swift остаётся gate

До переноса headers directPostHogRequest теперь требует scheme/host/effective-port того же baseURL, точный `/api/v1/product-analytics/posthog-desktop-capture`, отсутствие query/fragment/user/password. BaseURL собирается URLComponents с сохранением порта и отказом userinfo. Чужой origin, downgrade схемы, другой порт и произвольный путь не достигают копирования credentials. Конфигурация PostHog сама по себе больше не открывает другой адрес.

Новый Swift тест содержит8 отрицательных endpoint (host, scheme, default-port вместо8443, другой explicit-port, path, query, fragment, userinfo), разрешённый8443 и проверку сохранённого порта eventURL. Положительный прежний тест проверяет X-Auth-Session и X-Client-Version для собственного endpoint. Это подтверждённое чтением покрытие source; нативного запуска/компиляции здесь не было. Закрытие R1 в code review не подменяет обязательный macos-pr и не доказывает установленное приложение.

### R2 — закрыто; реальный lock-wait проверен

admit_account_milestone получает узкий синхронный before_insert callback. Он вызывается только после завершения await SELECT UserIdentity FOR SHARE и проверки active, непосредственно перед составлением INSERT. Caller в нём заново читает activation_milestone_write_blockers, provider resolver и Yandex transfer_decision(event); PermissionError превращается в admission_blocked и session rollback. Callback не вызывает транспорт/commit. Transfer exporter constructor/transfer_decision самостоятельно прочитаны: чтение конфигурации/реестров/раскрытия и решение без сетевой отправки; export не вызывается.

При отзыве уровня2 нет нового решения. При отзыве только рекламной цели локальное разрешённое решение сохраняется, PostHog остаётся pending, Яндекс получает not_requested. Оба исхода проверяются реальной блокировкой строки другой транзакцией: тест дожидается pg_stat_activity.wait_event_type=Lock, затем меняет решение и освобождает строку. Это не mocked admission и не только gate до соединения. Последний now для accepted_at/updated_at перенесён после lock/callback; текущий тест дополнительно требует accepted_at>=release time.

Предел: чтение файлового реестра и SQL commit не объявляются одной распределённой транзакцией. Исправлено конкретное длительное ожидание account lock; свежая проверка перед будущим provider side effect всё ещё принадлежит следующему dispatcher/T106 срезу. Никакой exactly-once доставки этим callback не заявляется.

### Прочитанные завершённые журналы

- `.dev/growth/t113-ingress-review-fixes-20261028.log`: **110 passed,2 warnings in24.58s**, runner29с, collection_count110/digest `d68790aa759cfe96e0c48e5b9dedb4ad664685b73cac388087aad5b03aa4a795`, isolated_container_removed, result=pass. Это исправления R1/R2, новый builder failure case и прежний ledger набор; Swift в этот Python профиль не входит.
- После110 перенесён только now за ожидание/добавлен timestamp assert. Текущий законченный `.dev/growth/t113-ingress-lock-final-20261028.log`: **12 passed,2 warnings in5.49s**, runner9с, collection_count12/digest `4499f7bb8cd3e095e4da5b5a6bb7bdf3281f26d5bbccd00c211ac646600d9385`, isolated_container_removed, result=pass. Это полный текущий test_activation_milestone_ingress.py, включая обе реальные lock-wait ветви и timestamp.110 не выдаются за повторный полный прогон финальных байтов.

Warnings прежние: pytest fixture import rewrite и Starlette/httpx deprecation. Проверяющий тесты не запускал, независимо прочитал законченные журналы и соответствующий текущий код. Журналы не являются exact-SHA GitHub receipts; после commit SHA-bound проверки обязательны.

### Требования и границы

Четыре checklist не изменялись: requirements16/0, privacy-measurement45/0, security27/0, infra29/0; **117 checked/0 unchecked**. Их текущие SHA-256 совпадают с before-code snapshot; spec/plan/tasks/data/activation/operations/quickstart/analyze также совпадают. Новых пробелов качества требований нет. Отчёт before-code остаётся применим; current code PASS не закрывает T113/T106/T112.

Auth builder находится внутри try, что сохраняет best-effort background поведение. API/server-auth по-прежнему не отправляют провайдерам и не используют in-memory fallback. Runtime gate по-прежнему безусловно закрывает admission через activation_recovery_unverified. Реальные GRAF DB verifier/backup/restore/deletion replay, bounded delivery/readback и T112 ещё предстоят. Growth plan оставляет G013–G019/T113/T112/T110 и AC01–AC06 открытыми; ссылки на локальные проверки не объявляют трафик или продажу. Указанные там107 тестов — исторический промежуточный результат, а текущие110/12 зафиксированы выше.

### SHA-256 повторного снимка

Digest code+inspected dependencies, compact sorted JSON path→SHA256: `d0aed6ad33f8935778256a21a788e08ace935bf6e6e457de22c3226d2d6118da`.

- `apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift` — `0dd7692eb1dd60e99f18f042d6b3b226c9f65da684aa3176f0a93afb8eab8fce`
- `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift` — `aacafdb4606e7dd95dc089c47f454b24d17d1fd9ac9bbc168d5d9d5156f5858b`
- `apps/server/src/twobrain_rec_server/api/auth.py` — `78defae4b1f7b86acd0f24a2a75c3fc18ad5a70435a73859285adf6f450dd6dc`
- `apps/server/src/twobrain_rec_server/api/product_analytics.py` — `93e5212a6499568e77a51feed18af69987e7861a08e98d4959701f6b13572898`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py` — `1060270acb7e83a4c4cf9ec1777b199222219a3deb49b2c0c19edf91a3fa8f82`
- `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` — `14a635f75ec4749af8b96e4bc405612358918c8fa86f51e66e5d68a91bf1bab5`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py` — `e2d010bb4f04c4150016df1367e926376e8f49c7210fe8738d538280198272ad`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` — `cd327c89d1804db75f424ff38836f55c3b5b9ca918fbb52411990f91cf8d3693`
- `apps/server/tests/contract/test_product_analytics_registration_handoff_contract.py` — `414b897176d35a55c6333db28750d0de43c6ab93d8b52c320d4acdd47f9554e8`
- `apps/server/tests/integration/test_product_activation_analytics_rollout.py` — `ea20b4b4723c65852e4d53e0f0a57ef59faaf1ef60a60c93fdd705616c7e30e2`
- `apps/server/tests/unit/test_product_analytics_activation_funnel.py` — `6db86f46394747b2fcbc4dab1ad6b927df9db53009417a0e755368873609d52b`
- `apps/server/tests/unit/test_product_analytics_conversion_campaign_labels.py` — `51073a5996145d76635b8d302ebd33bc519c9f49fc1ec888be88599f69b86849`
- `apps/server/tests/unit/test_product_analytics_milestone_dedupe.py` — `e0e9cd250b5ca4a0ba9ff056de79de120148e849bf4cc97479bf2dfeb881d7bc`
- `changes/unreleased/F273.yaml` — `1a38a53e643f8eb45c56381afb42a58e2b670c9df5224e62728c6b8a5e475f64`
- `apps/server/tests/contract/test_activation_milestone_ingress.py` — `8e8c5aafd98cb16939c447e77cb4722adfee797d5ead04c6b13360ad14b6615a`
- `apps/macos/Shared/Sources/Models/ProductActivationAnalyticsModels.swift` — `1cd1d6ce7fd7c9633dc29acf9213e0be5416dbd27ea0574316969ff478e021c2`
- `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` — `31dbd96d855632e806cc17e18c918f15a1b7fe5bb019ed8350edb9ee25b8de78`
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py` — `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`
- `apps/server/src/twobrain_rec_server/auth/dependencies.py` — `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311`
- `apps/server/src/twobrain_rec_server/auth/context.py` — `0948549680aeacdf9c7c832e80c24fdd87e9124e8e007824660cc1437ea1d1f8`
- `apps/server/src/twobrain_rec_server/cabinet/auth_return.py` — `7e3847aadcd9768dc47e3aa6afc77f7a4b8b7c4a572efd05249c91a9385c8b7b`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/validation/t113-ingress-before-code-2026-10-28.md` — `e84e492ed2f02c38a31eaaf2cc2ed80f8b9d04a00b2c40783c07b608dab6b048`
- `.dev/growth/t113-ingress-focused-20261028.log` — `0e706c2b77197572011c2291f19a431ad887b7faf0aec0ad4cd1368226c38735`
- `.dev/growth/t113-ingress-focused-v2-20261028.log` — `baac86947e2a0e4bda3639eadb83eb3d3c344559cdd9b4d086b909613f8e936b`
- `apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py` — `bdd980f0cd9d6d35f001f469cbbfe5c2bd9edb17cfd01f5f1297c7b88d8fee63`
- `docs/growth/organic-growth-plan.md` — `d3e7eec84008036cdd3d38855670e95813db8abf4e41fe071150572a9fb7d92a`
- `.dev/growth/t113-ingress-review-fixes-20261028.log` — `d1283d9fd6d06883254ea2466c132da9a7229885ca020192972f51b66267cdea`
- `.dev/growth/t113-ingress-lock-final-20261028.log` — `7b5a271e0fe946f6c6cf2414cd61a84bdf5292c5e1b639effbcfe2ec5e17d7f8`
- `specs/273-paid-traffic-analytics/checklists/requirements.md` — `b10a19943d788e9b8f5b3c9e322f6a614eb60f1cb8ea6cb207404bf82c3f3c30`
- `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` — `42f018d295b3c7fe50873612eeff9ec94c71a8d8b810060edb78a59ed7800b38`
- `specs/273-paid-traffic-analytics/checklists/security.md` — `d9c8078134a53d3a89c1171826a24b3271488fc2ff48687ad6a8bbf95eaf6678`
- `specs/273-paid-traffic-analytics/checklists/infra.md` — `ea43c13bb2ed6acba078bb6b511bcd6b981ac5db03d652548948b346ecfda87e`

До и после записи дополнения входные хеши совпали. Повторно сверены checkbox markers и их117/0. git diff --check выполнен независимо. В этом повторном назначении изменён только этот отчёт; code/spec/plan/tasks/checklists/Git/GitHub/релиз/runtime/данные проверяющий не менял. Рекомендация: продолжить штатную exact-SHA CI/PR приёмку этого промежуточного среза; рабочее включение сохраняется закрытым.
