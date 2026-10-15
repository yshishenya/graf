# F280 — независимая проверка требований возвращения после оплаты

Дата: 2026-10-03. Роль: reviewer-owned requirements gate, без правок реализации, задач, spec/plan, GitHub, коммитов или выпуска. Прочитаны `checklists/payment-return.md`, spec FR-031–038, plan раздел177–195, quickstart199–211, contracts/payment-journey.md101–114, research-payment-return.md, tasks.md, constitution7.1.0, guidance index/spec-kit-flow/product-gates.

**Текущий итог повторной проверки: requirements PASS, checked17 · unchecked0.** Предыдущий HOLD15/2 и замечания ниже сохранены как исторические; их закрытие зафиксировано в конце отчета. Качество требований не равно реализованной функции, платежу, чеку, банку или доступу.

| ID | Severity | Место | Замечание | Необходимое уточнение |
|---|---|---|---|---|
| R1 | HIGH | spec FR-034, plan controller/ledger, contract Scope | Клиентский контекст включает user/workspace/invoice, но не session. Другой сеанс того же пользователя/пространства/счета формально проходит этот договор ответа. | Явно включить непустую действующую session в controller identity и сверку текущего/ответного full shell; foreign/changed session останавливает последовательность и запрещает swap, не перезапускает ledger. |
| R2 | HIGH | spec:263, spec:308 и ссылки нового среза | SC-012 повторно определен для отличающегося результата. Связь criterion→tasks→evidence неоднозначна. | Новому возврату присвоить свободный criterion ID; исправить только ссылки нового среза в checklist/plan/quickstart/contracts/analyze/tasks, не переписывая исторический критерий промокода. |

## Подтвержденные требования

| Checklist | Evidence |
|---|---|
| CHK001–004 | spec FR-031/032/035, уточнение запроса; contract state table. Успех только payment succeeded + локально примененный доступ. Return/query не authority; service-gap отдельный. |
| CHK005–008 | FR-033/034/036 и plan: 6 запросов, starts в60с, ≥10с между началами, browser timeout15с, oneflight, неизменный ledger при swaps; stop на hidden/navigation/error/auth, без visible restart; abort не server cancellation, после timeout local GET и отсутствие повторного POST. JS-off/manual recovery заданы. |
| CHK010–012 | FR-035 и contract: чистый GET, existing protected POST, CSRF/owner/tenant/session, rate30/15мин, provider только сервер; stale initial continue проверяет invoice+operation; финансовые поля/согласия/idempotency/worker300с не меняются. |
| CHK014 | FR-036/quickstart6: клавиатура/focus/status announcement только при изменении, 200%, темы/ширины и существующие regressions. |
| CHK015 | research-payment-return.md: ссылки на первичные документы ЮKassa, инженерные лимиты выделены отдельно, без обещаний конверсии GRAF. Источники повторно прочитаны reviewer 2026-10-03. |
| CHK016 | FR-037, plan и quickstart7: независимые обзоры, converge, exact-SHA PR/Full/CD/runtime/publication; T011/T012/F278 и реальная финансовая/человеческая приемка отдельно. |
| CHK017 | FR-038 и plan195/quickstart211: причинное исправление существующей сверки, повторяемая транзакция/negative extra grant/payment, delayed webhook/refresh, без ручной выдачи. Scope/tasks отложены до установления причины. |

## Границы наблюдения

Root сообщил о provider succeeded10руб и локальном pending/free/grant0; reviewer не выполнял live запросов, не подтверждает эти факты самостоятельно и не копирует идентификаторы платежа. Требования правильно не принимают screenshot/return за авторитетный успех и не считают вечный service-gap исправлением серверного дефекта. Нельзя закрывать финансовую/человеческую приемку по этому обзору.

## Read-only analyze: готовность

Фактическая branch `codex/280-payment-return`; штатный prerequisites с `SPECIFY_FEATURE=280-payment-clarity --json --require-tasks --include-tasks` вернул существующий spec folder. Установленный script не поддерживает skill flag `--require-spec`, поэтому использован поддержанный эквивалент с наличием spec, plan, tasks отдельно проверенным. before/after_analyze hooks отключены.

Окончательные T029–T031 еще отсутствуют, analyze-payment-return.md сам обозначен предварительным. Поэтому завершенный `$speckit-analyze` не объявляется выполненным. После устранения R1/R2 и появления причинного scope/финальных tasks требуется новый независимый read-only coverage review FR-031–038 и нового SC с конституцией. Нельзя подменять missing task coverage историческими завершенными T026–T028.

Checklist после изменений перечитан:15 checked /2 unchecked; код и документы вне двух разрешенных файлов не изменялись.

## Архитектурная рекомендация по установленной root причине — повторная проверка

На момент этого чтения docs еще содержат прежние FR-034/SC-012 и «причина исследуется»; окончательные задачи отсутствуют. Root передал новый факт: maintenance role видит pending webhook, processing app role не видит его; несколько завершенных Temporal запусков применили0. Это сообщение root, не самостоятельное live чтение reviewer. Исходный код независимо подтвержден: maintenance_worker.py запускает scheduler billing reconciliation/renewal, но workflow Worker consumers зарегистрированы в processing `run_worker()` на строках2760–2774. Оба billing activity создают engine из текущего процесса `get_settings()`; compose processing использует app role, maintenance — maintenance role.

Рекомендуемый минимальный причинный scope для requirements agent:

1. В maintenance_worker.py зарегистрировать оба существующих consumers `BillingReconciliationWorkflow`/`BillingRenewalWorkflow` и activity names на существующих отдельных queues через `billing_reconciliation_task_queue(settings)`/`billing_renewal_task_queue(settings)`. Не менять queue/workflow/activity names, workflow IDs, bounded payloads, retry/timeout contracts или bucket300с: сохраненные/ожидающие задания должны быть совместимы. Свою queue здесь уже имеет каждый billing workflow; новая queue не нужна.
2. Удалить регистрацию этих двух consumers из processing `run_worker`; его app role/SQL grants/RLS policies не расширять. Functions activity допустимо оставить в существующем модуле и импортировать: важна регистрация/исполнение maintenance process, не механическое перемещение больших функций. Если вводится отдельный небольшой billing worker модуль, его точные paths/dependencies должны попасть в plan/tasks.
3. Добавить отдельный narrowly-named billing identity guard в db/session.py/соответствующем billing module: реальный DB `current_user == twobrain_rec_maintenance`, `row_security == on`, запрет superuser/BYPASSRLS. Проверка строки DSN сама по себе недостаточна. Нельзя использовать prompt-optimization helper с чужим operation/context: он только существующий пример паттерна. Guard до регистрации/polling на старте, и перед activity scan/apply: неправильная role должна дать явный fail-closed diagnostic, а не успешный0. В RLS контексте сохранить существующую `billing_reconciliation` maintenance operation и feature_area billing.
4. Сохранить maintenance restart/outage cancellation: оба Worker.run lifecycle привязать к существующему Temporal client; при connection/outage cancel/await всех consumers/reconcilers, не оставить detached workers и не удвоить consumers при reconnect. Самостоятельная calendar/notification работа имеет существующий outage invariant; нельзя незаметно уничтожить его переподключением billing.
5. Regression должна проходить реальный PostgreSQL FORCE RLS: один и тот же pending webhook app role не видит, maintenance с approved context применяет штатным путем, повторное применение не создает второй grant/invoice/payment. Неверная роль guard падает до scan/provider call/write. Проверить startup registration consumers на maintenance и отсутствие их на processing, cancellation/reconnect без дублей, существующий renewal observation path и delayed webhook+refresh race/idempotency. Обновить старый contract `test_billing_reconciliation_workflow.py`, который сейчас прямо требует registration в processing run_worker.
6. Выпуск проверяет отсутствие старых processing consumers и наличие maintenance consumers на тех же queues. Не редактировать роли/RLS/денежные historical records и не запускать новую оплату. После выпуска отдельное metadata-only чтение настоящего существующего платежа должно показать согласованные provider/invoice/operation/subscription/grant facts; synthetic tests не заменяют это доказательство. Возможные уже завершенные0 jobs не переотправлять через ручные изменения финансовых записей: существующий следующий reconciliation bucket/owner protected refresh с штатной транзакцией являются допустимыми путями восстановления.

Эти рекомендации не являются реализацией или финальным gate. Требуются обновленный причинный plan/quickstart/FR-038 и окончательные tasks перед независимым coverage analyze.

## Повторный независимый gate после исправлений

Requirements PASS17/0; независимых незакрытых замечаний к требованиям0. R1: непустая session включена в spec FR-034, controller ledger plan и contract; текущие/incoming meta сравниваются, смена/отсутствие session отвергает swap и не перезапускает sequence. R2: новый criterion SC-013, прежний SC-012 сохраняется. Checklist ссылки обновлены reviewer, markers только по этому evidence.

Причинный FR-038 теперь прямо задает перенос reconciliation consumer из processing в maintenance на прежней queue с неизменными workflow/activity IDs/payloads/cadence. Только reconciliation переносится в этом scope: прежняя рекомендация рассмотреть оба billing consumers не является разрешением переносить renewal; plan обоснованно сохраняет его до отдельно доказанной причины. Guard фактической роли/RLS/attributes до poller и activity, отсутствие расширения grants/RLS, cleanup/reconnect и production read-only agreement названы. Это проверка качества дизайна; при реализации нужно проверить реальные роли базы и штатное применение существующего платежа.

Независимо прочитанный исходный код подтверждает registry mismatch; live факты передал root, reviewer самостоятельно production не читал. Метаданные root о completed0 не подменяют применение доступа.

Документы зафиксированы на момент PASS:
- `spec.md`: `bcc0d0615f0658d9d6af7354f237e8ef85260ae03989abbc87e500e5eb3aeabf`
- `plan.md`: `7f53a7c374edf5c9354bf35a178c38171c3ba31ff2f19dd965dac708425ecabd`
- `quickstart.md`: `12b601e74768d947bf6adfd9b9f44307fefa2fa096267f439bf5f0b454c7a3b1`
- `contracts/payment-journey.md`: `59b9b815fa99076b23aa396e39bd258f4067088d34156e6b41386769194a2f3e`
- `research-payment-return.md`: `dc1e787873305f6a32c5108eb818d9dd1f72c40c33c7517280c19128ca941443`
- `tasks.md`: `3a1fdbc2d1b0d7f1c532bb16e1b7d158811d47a4a22b076c46fdc645e1808756`

Окончательные T029–T031 еще не появились. Финальный read-only analyze после tasks ожидается отдельным этапом; данный gate не приписывает покрытие несуществующим задачам. Pre/post_analyze hooks выключены, task prerequisite route поддерживается. Historical notes в analyze о еще исследуемой причине superseded отдельным causal paragraph и текущими FR-038/plan; дальнейший analyze должен заменить предварительный статус фактической coverage matrix.

Reviewer перечитал полный измененный checklist:17 checked,0 unchecked. Изменены только checklist и этот отчет.

## CHK001 — независимое повторное чтение уточнения FR-031

2026-10-03: перечитаны текущие FR-031, T029 и plan после финального analyze/issue sync. CHK001 остается `[x]`: успех initial/renewal/early связан с BillingEntitlementGrant именно этой покупки, срок берется из grant; текущая active subscription не заменяет доказательство grant и ее истечение не отменяет оплату исторического счета. Storage использует подтвержденный штатный признак применения этой покупки. Succeeded без grant отображается service-review, а не «Оплачено». Это делает критерий успеха проверяемым и не ослабляет авторитетность данных. Gate остается requirements PASS17/0; не подтверждает реализацию/live grant.
