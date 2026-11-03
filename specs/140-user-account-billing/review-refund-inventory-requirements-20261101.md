# Независимый допуск требований F140/T077: наблюдения возвратов — 01.11.2026

Результат: PASS только по качеству требований O11/R1–R6.
Предметный checklist: 10 отмечены / 0 открыты. Содержательных замечаний нет.
Это не приёмка реализации, чеков, финансовой сверки или полного T077/O6.
Исполнитель /root/f140_notification_content_review, тот же дочерний диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594; область O11/R1–R6, high-risk-product/repository-audit.
Ветка codex/140-observation-refunds; base/HEAD 1d92f88e587f52a9f452d41976e5faacc06d8a68.

## Собственное полное чтение изменённых оригиналов

Все семь оригиналов прочитаны в текущем назначении полными неусечёнными
отдельными выводами sed/cat. Локатор — путь и диапазон команды в журнале
этого диалога; совмещённые усечённые попытки исключены.

| Оригинал | SHA-256 | Диапазоны полного собственного чтения |
| --- | --- | --- |
| spec.md | `cadfdaf843487512a774f79eef89e2e3b3c2290904e44045fc9041e832f75818` | 1–125;126–250;251–370;371–470;471–610;611–750;751–866 |
| plan.md | `f711fe18badb22d0f73553e22921222eabc49323b2710ee39c6d5b6d40b93fd1` | 1–215;216–420;421–545 |
| tasks.md | `aa7b983a096370377d2b2d036acf5338b4bf49e106480080444e10c9f8466911` | 1–215;216–436 |
| quickstart.md | `704e31e671bbff92546bf34708012ce9363bc18f2a7f7193f8fcca66f194d6a7` | 1–230;231–460;461–650;651–766 |
| data-model.md | `41c0c0341a5199cefd1027aff0586b0fe829a92b075191403490374313ae577d` | 1–215;216–418 |
| research.md | `f13dc79b559299a4a8d3dc1b88c09a72ce651861e5e63bdbb6dab4bd88c55521` | 1–215;216–435 |
| contracts/operator-observation.md | `1e950b5f60a6b13cdf9eb25994a55118d6f4400b001b7c96651fb1d25f94540f` | 1–352 |

Журнал: /Users/yshishenya/.codex/sessions/2026/11/01/rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl.
Проверяемый локатор — фактические неусечённые outputs соответствующих
команд sed/cat текущего назначения в этом журнале.

## Проверка фактических выводов чтения

- spec.md: 1–125: строка журнала 5985, call_3aadc2b2b93843c6b728d284fcc12453; 126–250: строка журнала 5990, call_f39d779516d54b468f21bba7cf34e4b9; 251–370: строка журнала 5995, call_5450478afc424e249869e5701e9a9aee; 371–470: строка журнала 6000, call_39e8a11d4317424d934b328608342abc; 471–610: строка журнала 6005, call_5efd688da12e48e7992ace40d4ed9440; 611–750: строка журнала 6012, call_f2f45ad259444839b2526abb9c19b7f8; 751–866: строка журнала 6017, call_b5df9fc56c304dfd8ad6e183c116aa86. Полное совпадение с текущим оригиналом.
- plan.md: 1–215: строка журнала 6022, call_fd0f4c1482844a2e84373c4624908caf; 216–420: строка журнала 6027, call_145e8d951a49410f896e283053239fdc; 421–545: строка журнала 6032, call_c0f075bfbe49413dba166439b38bdd4b. Полное совпадение с текущим оригиналом.
- tasks.md: 1–215: строка журнала 6037, call_9a6775af51ec4f9196de4cd57d6f91db; 216–436: строка журнала 6042, call_c1c37c0c6fc04068a5fe096b74fcc453. Полное совпадение с текущим оригиналом.
- quickstart.md: 1–230: строка журнала 6049, call_0a2917a4b5b4408cb5bccf68c68b8c47; 231–460: строка журнала 6054, call_58bfac12409f48b5af9365530938b500; 461–650: строка журнала 6059, call_9ce4a30d36c54eb69334f1b13092a619; 651–766: строка журнала 6064, call_0201cd8b60924fcca5509a9d94e517a1. Полное совпадение с текущим оригиналом.
- data-model.md: 1–215: строка журнала 6069, call_09ea57cb5d0c441996eaf693b5e46951; 216–418: строка журнала 6074, call_0baf49a982fc42bb97e558e2c9da1bfb. Полное совпадение с текущим оригиналом.
- research.md: 1–215: строка журнала 6079, call_6a54bec0f5b745969c24d3d3c26bfdce; 216–435: строка журнала 6084, call_9395f13310fb4bbbaa1178aea7b53bc1. Полное совпадение с текущим оригиналом.
- contracts/operator-observation.md: 1–352: строка журнала 5964, call_9a8412db6d914960824658bc7a2dbe44. Полное совпадение с текущим оригиналом.

## Восстановление неизменного контекста

Прежние собственные чтения сверены по записям того же исполнителя и диалога
в review-free-projection-requirements-20261101.md и
review-credit-ledger-requirements-20261101.md. Это указатели на оригинальные
выводы, не чужое заключение и не замена нового ревью. Контрольные суммы
неизменного корпуса совпали. Для PRD и current-product-status дополнительно
проверены сами исходные output-блоки: строки42/75/142 журнала,
call_10637b7ccba74d8c981ba819ecc3fb5b / call_a2212eb8b63549c9bb27b94fe012e440 /
call_8d96fe89ade44fa5a623776881199f94. Точный текст PRD1–1100/1101–1750/
1751–2474 и status1–2385 совпал с текущими оригиналами; усечения нет.
В текущем назначении заново прочитаны применимые оригиналы по карте ниже.
Исторический пропуск чтения до кода PR7884 не исправляется задним числом;
весь O8 не объявляется PASS.

| Оригинал | Текущее собственное чтение и применимость |
| --- | --- |
| Constitution89–191/300–367/405–530 | I/II/III boundary, IV/VI, platform/workflow/governance: capture/Stop, приватность, независимый checklist и последовательность до кода. Принципы не меняются. |
| PRD1–150/349–374/688–844/1031–1101/1578–1777/2035–2072/2278–2326/2471–2474 | Общие обещания, диагностика без частного содержимого, сервер/изоляция, audit/privacy, полнота наблюдения, отдельные приёмки, приоритет заменяющей спецификации. |
| current-product-status179–217/451–470/529–622 | F272/F150/F140/F199: реальные границы tenant, отдельные runtime/payment доказательства, удалённые stop/runtime gates не возвращаются. |
| README/document-reading/product-gates/spec-kit-flow/development-process/tracker-policy | Полные собственные повторные чтения: карта guidance, чтение по происхождению, независимые отметки, analyze/issue sync до кода, Refs для неполного результата. |
| release-and-validation171–244/410–443/646–692/758–770 | Выбор полосы, новые профильные проверки и exact-SHA/base GitHub gates, отдельный выпуск/Full, fragment/legacy, сохранение чужой работы и metadata-only evidence. |
| operations-reconciliation/registry-operator-import/security-privacy-compliance/billing-lifecycle | Полные собственные повторные чтения. Scope магазина importer не переносится на inventory; реакция/сроки/authority/RLS, отсутствие финансовой mutation и внешняя refund boundary. |
| F278 spec158–203/295–302 | Полный раздел Functional Requirements (в двух неусечённых частях) и единый учёт приёмки: FR009/012/014/041, оплаченный срок после отзыва и реакция≤24ч сохранены. |
| Семь изменённых оригиналов, O1–O11 | Полные собственные чтения выше. Непосредственные R1–R6 сравнивались с общими O1–O8/O6 и прежними O9/O10. |

Все прямые зависимости нового среза разрешены этими чтениями. Исторические
ссылки на merchant canary/выпуски/macOS не дают нового действия: в назначении
нет приложения, live денег, источников встреч, выпуска, миграции или deployment.

## Контрольные суммы неизменных входов

| Путь | SHA-256 |
| --- | --- |
| AGENTS.md | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| .specify/memory/constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| docs/prd-voice-layer-final.md | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| docs/current-product-status.md | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| docs/agent-guidance/README.md | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| docs/agent-guidance/document-reading.md | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| docs/agent-guidance/product-gates.md | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| docs/agent-guidance/spec-kit-flow.md | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| docs/agent-guidance/development-process.md | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| docs/agent-guidance/tracker-policy.md | `9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472` |
| docs/agent-guidance/release-and-validation.md | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| specs/140-user-account-billing/contracts/operations-reconciliation.md | `23a4e9d8aee95b39efaeda39eecc577e737426a20cd4661874208fa543b95ed2` |
| specs/140-user-account-billing/contracts/registry-operator-import.md | `297bfe6c3acb063d70a6ef634c287a901fc9c342549270eaeec2c15a35c5b0a5` |
| specs/140-user-account-billing/contracts/security-privacy-compliance.md | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` |
| specs/140-user-account-billing/contracts/billing-lifecycle.md | `1d3e8fe3a672a34a4bc7a34bb6135800781d840e6e9350e0659bd142c5931ff7` |
| specs/278-production-billing/spec.md | `d452d625cf5035edcdd144c34561aeb2c5d1a19c29826c61505801a3dd53e09c` |

## Решение по всем десяти пунктам

| Пункт | Решение и конкретное основание |
| --- | --- |
| CHK001 | PASS. O11 R1 даёт точные source=observed_provider_refunds, scope=database_inventory, kind=current_state. Count — все доступные строки одного снимка, не платежи, заявки или сумма; несколько частичных возвратов одного invoice допустимы. Spec670–687, plan83–106, research354–378 и model204–212 согласованы. |
| CHK002 | PASS. R1 прямо исключает фильтры report_date/environment/observed_at и ложное proven_current_shop. Модель221–241 и migration0044:228–240 имеют shop_environment, но не shop_id. Server Settings не восстанавливают историческую привязку; O3 и O4 это уже разделяют. |
| CHK003 | PASS. R2 распознаёт совместно succeeded/provider_observation. Иное значение любого поля, включая NULL, идёт в одну безопасную status=unrecognized. Непустые группы отсортированы по status; count=sum(groups.count). Plan требует CASE совместной пары и DB count/group/order, а не фильтрацию неизвестных строк. |
| CHK004 | PASS. R2 и research отделяют транспорт webhook/poll/registry от сохранённого source. Прочитанный writer497–580 создаёт только source=provider_observation/status=succeeded; extractor211–229 допускает succeeded, caller706–778 получает GET и вызывает writer. Это статическая сверка объявленного пути, не live inventory, динамическая полнота writers или актуальная достоверность провайдера. |
| CHK005 | PASS. R3 всегда partial, оба values.receipts/reconciliation_gaps=null, unrecognized приоритетнее receipts_and_reconciliation_uninstrumented. Успешный пустой источник: count0/groups[], оба null, partial; нет unavailable/финансового PASS. O2/O3 и R3 сохраняют отказ всего отчёта при ошибке доступа/схемы/БД, без нулевой подстановки. |
| CHK006 | PASS. R4 явно не выбирает observed_at и не выводит ни возраст, ни invalid_time_count; NULL/будущее/выбранный день не меняют inventory. now() реальной миграции — локальное начало транзакции, не время возврата/банка/последней проверки. Отсутствие строки не доказывает отсутствие возврата или корректность чека; немедленный canceled и pending3дня сохранены O6/R4. Это специальная семантика нового семейства вместо generic age/future-invalid O3. |
| CHK007 | PASS. R5 разрешает одну DB агрегацию только status/source/count. IDs/связи, суммы/валюта, shop_environment, observed_at, invoice JSON/payload/контакты исключены. Writer/reversal/provider/почта/analytics запрещены. O1/O2/O5 сохраняют реальный maintenance guard, forced RLS, один UTC as_of/READ ONLY RR, общий15с/statement5с/lock2с,500gaps/64KiB, rollback/close. Новых схем/служб/прав/зависимостей нет. |
| CHK008 | PASS как достаточность плана, не выполненные тесты. R6 и quickstart87–119 задают RED, реальные PG/CLI/guard/forced RLS, empty/совместные известные и неизвестные пары, несколько частичных строк, environment/date/NULL/future, старый RR/новый процесс, no-write/fingerprint/privacy/ошибку схемы/роли. NOT NULL status/source не ослабляется: отказ INSERT проверяется отдельно, SQL NULL-защита отдельно формой запроса. Cleanup только своего одноразового стенда через finally, XML/log/hashes. |
| CHK009 | PASS. Все семь документов согласованы с source/migration/writer. Data-model отдельно уточняет исторические дополнительные поля и несуществующую BillingReceiptState: реальный receipt map в BillingInvoice.plan_snapshot (reconciliation324–410, cap16), отдельно от legacy receipt_registration. O11 не читает его и не принимает чеки/CSV/API/ledger сверку. Generic _groups требует timestamp и поэтому обоснованно не переиспользуется. |
| CHK010 | PASS. O6/O8/R6 и plan/tasks/quickstart требуют независимый checklist PASS, scoped analyze и исходную #4932 до кода, после — реальные профильные проверки, независимые review/converge и три exact-SHA/base gates. Все87 полных task lines побайтно совпали с HEAD, T077[ ]; только Refs4932. Восемь старых checklist побайтно равны HEAD,162отмечены/58открыты; полный O6/FR089 и сроки не исключаются и не переносятся. |

## Сверка фактических предпосылок

- ObservedProviderRefund: модель221–241 и migration0044:228–240. Unique —
  shop_environment/provider_refund_id; invoice не уникален по возврату.
  source/status обязательны; migration observed_at nullable/default now().
  ORM-аннотация не подменяет nullable реальной миграции. Поиск по последующим
  миграциям не выявил изменения refund-таблицы или отдельной receipt table.
- record_observed_refund497–580 проверяет operation→invoice, сумму/валюту,
  duplicate и совокупный refund total; пишет известную пару и вызывает
  reverse_credit_for_payment. Поэтому наблюдение не должно его вызывать:
  это writer с финансовыми последствиями, а не безопасный reader.
- _reconcile_event706–778 получает provider.get_refund, сверяет object id,
  затем extractor/record. Транспорт не сохраняется в refund source.
- merge_receipt_observation_snapshot324–410 хранит карту до16 записей в
  invoice.plan_snapshot; payment registration обновляет отдельную старую
  проекцию. Refund inventory не доказывает состояние/доставку чека.
- billing_monitoring CLI полностью перечитан. READ ONLY REPEATABLE READ и
  driver server_settings заданы до connection/hooks, UTC as_of фиксируется
  один раз; таймер terminate ограничивает cleanup. database.py целиком
  проверяет реальные login/current_user, row_security и отсутствие bypass.
- monitoring.py1–103/231–285: guard до источников, refunds пока not_connected.
  Generic _groups читает timestamp и выводит invalid_time_count; R4 требует
  отдельную узкую агрегацию. Общий отчёт уже partial и таким остаётся.
- Migration0044 включает refund table в BILLING_TABLES, enable/force RLS и
  tenant/maintenance policy; rls_validation.py содержит её в inventory.
  Это статическое подтверждение предпосылки, не новый runtime/RLS PASS.

| Фактический исходник | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/billing/reconciliation.py | `e4d0203d9aa7e2d8dea3aa35a43c76f5a0199722a191fc46ccec791c4c1de64c` |
| apps/server/src/twobrain_rec_server/billing/webhook_reconciliation.py | `ac4e031c610cb9a76c3f5f1866b3879cde7a4563bfab145c263a6774aaa83e66` |
| apps/server/src/twobrain_rec_server/db/models/billing.py | `146c5c83debc274027de8e6630c7389a6a16c6ba018b48e446fd78b4f07f24bb` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py | `9e6f237ecb0d6ebd787014dc3b533b535a40fec94a9d49aee5a829ab9cc9cf1b` |
| apps/server/src/twobrain_rec_server/billing/database.py | `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f` |
| apps/server/src/twobrain_rec_server/cli/billing_monitoring.py | `68ca13c2e36f1958124d2a60300b326941d73f34d481f4834afe18abac1aab55` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `c8080e43f07580e423925f2360814ddc8214909a5641d04fd8bfdf46b2b19f6f` |

## Сохранённые ограничения и остаток

Все58открытых пунктов восьми прежних checklist прочитаны в исходных строках.
Применимы authority/RLS/metadata-only/error/owner/deadline требования:
O1–O6/R1–R6 сохраняют их для нового reader. Широкие продуктовые,
финансовые, эксплуатационные и ручные проверки этими десятью отметками
не принимаются. Старые stop/no-retry/Free/catalog конфликты не превращаются
в актуальные требования из-за нового среза: F272/F199/F278 имеют приоритет.

Фактические количества отмечены/открыты: requirements17/8,
operations10/8, security11/6, payments14/6, launch-readiness32/8,
post-plan-readiness25/15, product-market36/4, ux17/3. Итого162/58;
все восемь файлов побайтно равны HEAD и не редактировались.

T077[ ] сохраняется. #4932 должна оставаться OPEN по назначению/контракту;
GitHub live state в этом ревью не запрашивался и не менялся. Не принимаются:
все остальные источники, постоянные counters попыток/ошибок/повторов,
регулярность/heartbeat, тревоги/повтор и сохраняемая реакция полного O6/FR089.
Transient15мин/24ч, fair-use≤24ч, canceled receipt немедленно,
pending receipt3дня, registry/F278FR041 реакция≤24ч сохраняются. F278
оплаченный срок после отзыва не отменяется. T075/реальная финансовая сверка,
чеки, T068/#7524, ручная/финансовая/приватностная и выпускная приёмки отдельно.

## Граница решения

CRITICAL0/HIGH0/MEDIUM0 новых содержательных замечаний в R1–R6.
Достаточность требований PASS; отдельный scoped analyze и issue sync
основного исполнителя всё ещё обязательны до RED/реализации. Затем нужны
реальные сценарии quickstart, независимые code review/converge и новые
три exact-SHA/base GitHub gates. Только Refs #4932; не закрытие полной задачи.
Legacy Impact untouched; нет новых путей совместимости.

Изменены только назначенные checklists/refund-inventory.md и этот отчёт.
Код/spec/plan/tasks/governance/Git/GitHub/данные не менялись. Тесты,
PostgreSQL/Docker/продуктовый CLI, Dev, Full/CD/commit/PR/release не запускались.

Итоговое собственное перечитывание: весь фактический checklist и отчёт1–100/101–конец
в двух отдельных неусечённых выводах. Прямой подсчёт:10отмечены/0открыты.
Повторно проверены все30SHA-256 входов (7изменённых оригиналов,16неизменных
инструкций/зависимостей,7исходников):30/30совпали. git diff --check и отдельная
whitespace-проверка двух новых файлов PASS; продуктовые тесты не запускались.
