# Независимый допуск к bounded delivery T113/T106 — 28.10.2026

**Gate: PASS качества действующих требований для изолированной реализации минимального dispatcher/transports. 117 checked / 0 unchecked. Блокирующих пробелов или новых решений владельца не требуется.** Это не ревью ещё не написанной реализации, не завершение T113/T106 и не разрешение внешней отправки/рабочего включения.

Проверяющий `/root/activation_requirements_gate`. HEAD основы `07186afb6af15c2c31082083280213833744eb5f`, ветка codex/273-activation-ingress; PR #7775 ещё находится в своём процессе CI/приёмки. Рабочая копия в начале чистая. Активная фича подтверждена .specify/feature.json. Lane: независимый before-code gate следующего уже запланированного high-risk среза F273. Ingress в этом назначении не меняется.

## Прямые ответы по границам участка

1. Принятый27.10 контракт достаточен: одна PostgreSQL relation, два фиксированных получателя, conditional claim + attempt_id, commit до транспорта, точные состояния исходов, свежие legal/advertising/readiness gates, существующий maintenance worker и ограничения20/1/5с/60с уже заданы. Новый broker/process/service или изменение целей не нужны.
2. «Один запрос получателю за раз» применяется к получателю в целом при нескольких maintenance-процессах. Только последовательного for внутри одного worker и claim конкретной строки недостаточно: разные процессы могли бы отправлять разные строки одному провайдеру одновременно. Предложенная короткая pg_try_advisory_xact_lock вокруг проверки существующего dispatching этого provider и нового conditional claim подходит. Commit освобождает SQL-lock **до** сети; durable dispatching резервирует слот до finish/quarantine. Все конкурирующие отправители обязаны использовать эту же границу; busy/unknown не разрешают bypass. Наименьшая реализация остаётся последовательной внутри worker. Это инженерное исполнение принятого ограничения, не новый сервис или дополнительная продуктовая цель.
3. Отдельный readback разрешено оставить следующим явно открытым остатком того же T113. Для текущего участка обязательна честная граница: HTTP2xx→submitted; точного readback нет→confirmed нигде не выставляется. Submitted/ambiguous не выбираются для повторной отправки. Отсутствие readback-кода не блокирует поэтапную реализацию dispatcher, но не позволяет закрыть T113, объявить доставку confirmed или принять полную воронку. Когда readback появится, он должен проверять точный event_id и recipient; отсутствие/ошибка чтения не означает разрешение resend.
4. Fresh-gate непосредственно на transport boundary через обёртку существующего injectable client.transport подходит. Она должна заново получить strict level2/recovery/readiness/provider/advertising решения до реального вызова transport и явно отличить отказ до вызова от неизвестного сетевого исхода. Новый общий result framework не нужен; одного старого retryable для этого недостаточно.

## Прочитанные источники и метод

Непосредственно перечитаны все117 текущих вопросов четырёх reviewer-owned списков. Целиком перечитан activation-milestones; затронутые целые разделы data-model §Устойчивое решение, plan §Продолжение T112/T113, tasks Phase13/T106, operations §Lifecycle первой вехи, quickstart §Сценарий4 и короткий analyze. Применимые legal gate/lifecycle разделы и существующие API dispatcher/transport/tenant-context прочитаны самостоятельно, без запуска и без оценки отсутствующего нового кода. Ранее прочитанные неизменные требования сверены по хешам с before-code снимком; использовано прямое разрешение пользователя на этот способ повторного чтения F273.

Общий mandatory manifest `.dev/growth/mandatory-reading-2026-10-27.sha256` проверен самостоятельно: **9/9 совпали**, файл manifest SHA-256 `8c2cd71fecd91588288148d504d0f7348507d8ae49f33ca765a7c37e7e73ffcc`. Это подтверждает содержимое документов, не готовность продукта. Полное повторное чтение всего PRD/current status и их продуктовая приёмка здесь не заявляются.

Spec/plan/tasks/data/quickstart/activation/operations и четыре checklist совпали с принятым before-code снимком. Analyze27.10 остаётся применимым:0critical/0high/0medium/0blocking_clarifications/0unresolved_duplications; команда analyze в этом назначении не запускалась. Вопросы глобального слота и поэтапного readback разобраны выше в пределах текущего контракта.

## Все четыре reviewer-owned списка

| Список | Checked | Unchecked | Особо проверенная применимость |
| --- | ---: | ---: | --- |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | 16 | 0 | Все16: границы/тестируемость/отказы/dependencies/success criteria достаточны; качество требований не названо выполненным dispatcher. |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | 45 | 0 | Все45; CHK013/026/030 — основания, один счёт и реальные пути; CHK031–038 — bounded/операционные gates; CHK039–045 — отдельная приёмка и отсутствие новых целей. |
| `specs/273-paid-traffic-analytics/checklists/security.md` | 27 | 0 | Все27; CHK004–009 — отзыв, два получателя/цели и post-egress limits; CHK010–020 — lifecycle/разрешённые поля; CHK026/027 неизменны и не расширяют IP scope. |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | 29 | 0 | Все29; CHK013–015 — независимость продукта и provider outage; CHK022–025 — ресурсные ограничения; backup1–10 остаётся gate включения; T098 пункты26–29 не обходятся этим кодом. |

**Всего117 checked/0 unchecked.** Неподтверждённых требований для возврата marker в `[ ]` нет. Четыре списка сохранены без изменений; подробная117-пунктовая матрица требований27.10 остаётся исходной ссылкой, текущий вывод дополнительно проверяет применимость к доставке.

## Зависимости и существующие API без обхода защит

| Зависимость / API | Как применить в этом участке |
| --- | --- |
| workflows/maintenance_worker.py:run_maintenance_worker | Добавить ограниченный цикл в существующий maintenance process с исключениями, которые не останавливают calendar/billing/deletion и не блокируют event loop. Существующая startup проверка БД сохраняется. Не создавать новый сервис/брокер и не связывать этот независимый poll с успехом Temporal, если для него Temporal не нужен. |
| db/session.py:create_engine/create_sessionmaker; db/tenant_context.py:MaintenanceTenantContext/apply_tenant_context | Использовать штатные сессии и actual maintenance login. Контекст operation_name=activation_milestone_delivery, feature_area=product_analytics, непустые actor/reason; SQL0106 требует session_user=twobrain_rec_maintenance. App/superuser/BYPASSRLS и подставленный maintenance context не заменяют эту проверку. Существующий billing role verifier принадлежит billing context; его не вызывать с чужим activation operation, а сохранить startup проверку/переиспользовать её принцип реального login. |
| milestones.py:claim_milestone_delivery | Получить право только pending/pre_send_retry условным UPDATE; новый attempt_id и provider-specific state; короткий общий provider-slot guard должен охватывать проверку dispatching и claim разных строк. Claim commit обязателен до сети. Ошибка/unknown commit не разрешают транспорт. |
| milestones.py:finish_milestone_delivery | Только тот же milestone/provider/attempt_id и dispatching может закончить попытку. Использовать закрытые outcomes technical_pre_send/http_accepted/transport_ambiguous/http_ambiguous/purpose_withdrawn/payload_rejected; не превращать свободные exception/body в reason. Возврат false при утраченной/удалённой строке не разрешает новый INSERT/счёт/повтор. Узкие недостающие переходы допускаются в этой же модели без новой универсальной очереди. |
| milestones.py:quarantine_milestone_deliveries | Обычный stale dispatching>60с→ambiguous; after_restore карантинирует восстановленные неподтверждённые состояния. Это не GRAF restore verifier и не разрешение освободить слот живого зависшего транспорта и отправить вторую копию. |
| legal_basis_gate.py:activation_milestone_write_blockers | Нужна строгая проверка существующей вехи/основания/operations/recovery перед side effect. Не подменять старым legal_basis_write_allowed, у которого совместимость с отсутствующим реестром мягче. Безусловный activation_recovery_unverified сохраняется до настоящего GRAF verifier; тестовый monkeypatch не становится рабочим разрешающим флагом. |
| provider_delivery_gate.py:resolve_provider_delivery_gate | Перечитать для текущего получателя непосредственно перед фактическим transport; snapshot/admission-time ответ не заменяет свежий gate. Не обходить approvals, provider configuration, access/operations readiness. |
| YandexOfflineConversionExporter.from_settings/transfer_decision/export | Для каждого события заново получить актуальный transfer register/disclosure/отдельное рекламное разрешение. Только разрешённая offline event subset и поддержанная identity; отсутствие/отзыв не разрешают отправку. Нельзя кэшировать экземпляр с прежним register на всю жизнь worker. Export/transport сохраняют secret-file и provider gate; timeout понизить с текущего default8с до≤5с штатным параметром/узким расширением factory. |
| PostHogClientWrapper.from_settings/capture/capture_event | Сохранить configured destination, secret-file, forbidden/security fields и live/provider guards. При передаче transport identity использовать deterministic ledger.event_id; если нужен узкий аргумент envelope/insert key — расширить существующий wrapper, не собирать bypass-клиент. Не передавать внутренний source_kind/account_id. |
| Existing ProviderTransport/ProviderDeliveryResult | Injectable transport позволяет доказать момент фактического входа. Старое retryable=true при network_error/429/5xx НЕ является доказанным pre-send. После входа transport timeout/OSError/недоказанный HTTP failure→ambiguous. Dry_run/disabled/gate refusal не являются submitted. До transport доказанная ошибка приготовления может дать technical_pre_send; отзыв/unknown не выдавать за технический retry. |
| legal_basis_lifecycle.py / auth account close | Существующие category/account deletion и их deadlines не обходятся удержанным snapshot. Перед отправкой проверяется текущая допустимость/существование решения и оснований; удаление не создаёт новую строку/веху. Уже начатую передачу нельзя обещать отозвать задним числом; post-egress состояние остаётся честным. |
| data-model confirmation_ref / readback | Поля есть, готового API перехода confirmed по точному внешнему доказательству в просмотренном ledger нет. Не делать сырой UPDATE confirmed из result.status/2xx/provider smoke. Узкое readback/reconciliation расширение — следующий остаток T113, metadata-only, без response body в Git/логах. |

Объём одного прохода — не более20 ledger строк всего, а не20 на каждого получателя с удвоением scan. Каждая строка имеет только два fixed intents; один intent не выбирается снова в том же проходе после pre-send failure. Пауза60с между проходами, один активный запрос на получателя; transport timeout≤5с. Синхронные wrappers не должны замораживать event loop. Если используется thread/async cancellation, прекращение await не доказывает завершение реального запроса: нельзя открыть второй provider слот, пока старый запрос может продолжаться; такой исход ambiguous, без повторной отправки. SQL-lock/транзакция во время сети не удерживаются.

## Минимальная применимая матрица тестов

| № | Сценарий | Обязательный наблюдаемый результат |
| --- | --- | --- |
| D01 |23+ ledger rows, два intents, повтор прохода | За проход просмотрено≤20 строк, fixed intents не размножаются,60с pause без busy loop, неизменность local count/payload/event_id. |
| D02 | Два процесса, одна строка/получатель | Ровно один committed claim/transport; второй не получает attempt. |
| D03 | Два процесса, разные строки того же provider | Короткий provider-slot guard пропускает только одного; одновременно активных запросов этому provider≤1. SQL-lock освобождён до transport. |
| D04 | Claim commit failure/unknown; crash после commit до transport; после remote accept до finish commit | При непринятом claim нет сети; durably dispatching не превращается в pending. Stale/crash→ambiguous без слепого resend. |
| D05 | Доказанная preparation ошибка до transport |pre_send_retry и последующий повтор того же решения/event_id, новый attempt только после правильного claim; local count остаётся1. |
| D06 | timeout/OSError/429/5xx/недоказанный non2xx после входа transport |ambiguous даже если старый ProviderDeliveryResult.retryable=true; следующая итерация не отправляет снова. |
| D07 |HTTP2xx / dry_run / provider disabled |2xx только submitted; dry_run/disabled не submitted и не confirmed; submitted/ambiguous/confirmed/not_requested/cancelled/rejected не выбираются для отправки. |
| D08 | Успех одного получателя, сбой другого | Два независимых states; успешный не повторяется. |
| D09 | Withdraw/disable/unknown после selection, после claim/пока ждали блокировку, сразу перед transport | Свежая strict boundary останавливает side effect; нет in-memory/старого snapshot fallback. Только ad-purpose withdrawal не удаляет допустимый level2 decision. |
| D10 | Account/category case после admission или claim | Не отправляется запрещённый/удалённый snapshot; late finish не воскрешает решение; post-egress неизвестность не маскируется утверждением об удалении у provider. |
| D11 | Real app vs maintenance login; bogus context/superuser/BYPASSRLS | Штатная cross-account работа только maintenance, guards не принимают app spoof или привилегированный обход. Пустая выборка без прав не означает успешный проход. |
| D12 | Provider/DB failure, timeout/cancel loop, долгий транспорт | Другие maintenance-задачи/heartbeat продолжают работать;≤5с timeout; нет скрытого параллельного запроса/досылки после отмены. Нет fallback к прямому клиентскому вызову. |
| D13 | Неизвестные поля/unsafe payload/secrets/source_kind/raw account | Запрет до транспорта, finite reason; только безопасные counts/state/version в evidence. Deterministic event_id одинаков при всех попытках и не raw identity. |
| D14 | Обычный restart и восстановленный pending/dispatching/submitted/unknown gap | Нет автоматического replay восстановленного; quarantine и recovery_unverified удерживают сеть/admission закрытыми. Реальный restore остаётся отдельной приёмкой. |
| D15 | Статическое подключение существующего worker и вся цепочка вызовов | Новый loop действительно подключён, не создаёт новый процесс/брокер и не меняет ingress. Bounded исключения не останавливают другие задачи. |
| D16 — следующий readback-участок | Точное событие/не тот event_id/recipient, пустое/недоступное чтение | Только положительное точное доказательство→confirmed с opaque metadata reference. Отсутствие не разрешает resend; readback не переоткрывает revoked intent. В нынешнем dispatcher коде confirmed недостижим из2xx. |

Это требования к минимальной проверке, а не сообщение о выполненных тестах. Для текущего dispatcher ожидаются D01–D15 и отрицательная confirmed boundary; D16 положительный readback можно явно оставить открытым вместе с T113. Реальная provider сеть не нужна для разработки: использовать изолированную БД и fake/injectable transports, не рабочие аккаунты/credentials.

## Остатки и контроль

Полная GRAF backup/restore verification, readiness receipts, T098/T109–T111/T116/T118/T119 и правовая/операторская приёмка не требуются для написания изолированного кода, но остаются обязательными до рабочего включения. Нельзя убрать activation_recovery_unverified лишь ради успешной отправки. T112 триггеры, общий T106 по другим writers, exact-SHA GitHub/merge/release/production, трафик и продажи этим gate не закрываются.

GitHub issue sync для существующих T113/T106 основной агент проверяет отдельно; reviewer не обращался к GitHub/провайдерам и не менял tracker. Отчёт не является implementation review и не подтверждает CI PR #7775.

## SHA-256 текущих входов

- `specs/273-paid-traffic-analytics/spec.md` — `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d`
- `specs/273-paid-traffic-analytics/plan.md` — `86991b85ebeed9a9c3d7d2d50a980b4eb827796734fa0b4bd6df7f92c08e79ec`
- `specs/273-paid-traffic-analytics/tasks.md` — `f5fe73b9847ac10d05029af9ed93ef939e119cf46e4b1cdd8c1cbdcf6fe48787`
- `specs/273-paid-traffic-analytics/research.md` — `a9b5331c68424cd86f47119b8994db442da4250cc536683695d9488fe9b6f46b`
- `specs/273-paid-traffic-analytics/data-model.md` — `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be`
- `specs/273-paid-traffic-analytics/quickstart.md` — `c8fdc2c68ffc8e3aa86ed32b250603022e643df4e4f3ede3091a073fe1b05479`
- `specs/273-paid-traffic-analytics/legal-basis.md` — `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/contracts/operations.md` — `f696f7b87024783dad0a28ab84af0c7b3dc2329a595eb470c256232a3797c0fb`
- `specs/273-paid-traffic-analytics/checklists/requirements.md` — `b10a19943d788e9b8f5b3c9e322f6a614eb60f1cb8ea6cb207404bf82c3f3c30`
- `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` — `42f018d295b3c7fe50873612eeff9ec94c71a8d8b810060edb78a59ed7800b38`
- `specs/273-paid-traffic-analytics/checklists/security.md` — `d9c8078134a53d3a89c1171826a24b3271488fc2ff48687ad6a8bbf95eaf6678`
- `specs/273-paid-traffic-analytics/checklists/infra.md` — `ea43c13bb2ed6acba078bb6b511bcd6b981ac5db03d652548948b346ecfda87e`
- `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py` — `e53d4573d0d6094962afebc8862232b6958ab7dd3e76c5fbdc069144aa2928a4`
- `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` — `31dbd96d855632e806cc17e18c918f15a1b7fe5bb019ed8350edb9ee25b8de78`
- `apps/server/src/twobrain_rec_server/product_analytics/posthog_client.py` — `c5041ee216a9fde6121efbfd51c466aea50c841a543ac3be6de5e7d6b7f6aa20`
- `apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py` — `bdd980f0cd9d6d35f001f469cbbfe5c2bd9edb17cfd01f5f1297c7b88d8fee63`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py` — `e2d010bb4f04c4150016df1367e926376e8f49c7210fe8738d538280198272ad`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` — `cd327c89d1804db75f424ff38836f55c3b5b9ca918fbb52411990f91cf8d3693`
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py` — `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`
- `apps/server/src/twobrain_rec_server/db/tenant_context.py` — `a7dc09e2b153344d5d3cf2f71dedaffba875995460d13342ad19389885b1762c`
- `apps/server/src/twobrain_rec_server/db/session.py` — `a01c5ab2a45888fedc387dc6656defc92512707e3a485c1c5e2c8f83e616a529`
- `apps/server/src/twobrain_rec_server/billing/database.py` — `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f`
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0106_activation_milestones.py` — `7e464638f72e3fb240e2af048bcdb25022cb9101df3405aaa14068e7b1386898`
- `specs/273-paid-traffic-analytics/validation/t113-analysis-2026-10-27.md` — `0dec601b9e919ba582a61539125e14fa2b199fdceeb74307487fd19dbac90690`
- `specs/273-paid-traffic-analytics/validation/t113-ingress-before-code-2026-10-28.md` — `e84e492ed2f02c38a31eaaf2cc2ed80f8b9d04a00b2c40783c07b608dab6b048`
- `.dev/growth/mandatory-reading-2026-10-27.sha256` — `8c2cd71fecd91588288148d504d0f7348507d8ae49f33ca765a7c37e7e73ffcc`

До и после записи хеши входов совпали; текущий HEAD и117/0 повторно проверены. git diff --check выполнен независимо. Проверяющий изменил только этот новый отчёт; checklist markers, code/spec/plan/tasks/governance/Git/GitHub/приложение/рабочие данные не менялись. Тесты, provider сеть, выпуск и выкладка не выполнялись.
