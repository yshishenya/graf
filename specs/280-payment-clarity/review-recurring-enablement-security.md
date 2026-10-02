# F280 — независимая проверка существующего автопродления

Дата: 2026-10-02, Europe/Istanbul. Рабочая копия `release-f280/crisp`, ветка `codex/280-recurring-enablement`; HEAD **`77e6aed8ff79127d6e6b284ad18b58da5793ef51`**. Рецензент `rejection_security_review`. Lane: read-only review активного high-risk-product среза. Код, specs, tasks, GitHub, данные и выпуск не менялись. Live provider/DB/payment requests не выполнялись. Старый отказ магазина 403 не принят как текущий факт.

**PASS для безопасности рассмотренного существующего пути; блокирующих дефектов кода в рассмотренной области не найдено.** Это статическое заключение и чтение существующих проверок, не подтверждение текущей внешней возможности автоплатежей или реальных списаний.

## Путь и защитные границы

1. Начальное оформление: POST `/billing/checkout/start` остаётся с CSRF, проверкой personal workspace/current owner, блокировкой пространства и строки подписки, актуальными ценой/офертой/quote и idempotency. `offer_consent` не выбран по умолчанию; `recurring_consent` приходит отдельным bool, сохраняется в снимках operation/invoice и не заменяется параметром retry/ответом провайдера. `_create_initial_checkout_payment` (`cabinet/web_routes/billing.py:652–710`) требует фактический bool и передаёт его в `save_payment_method`. При False нет скрытого перехода к True. Ключ/счёт/бюджет/резерв промокода сохраняются до одного POST.

2. Факт оплаты: оба production callers `apply_confirmed_purchase` — inbox `_reconcile_event` и `reconcile_pending_initial_checkout_operations` — получают GET у YooKassa; worker activity также получает provider truth перед проекцией. Сигнал browser return или webhook body не предоставляет доступ или recurring authority самостоятельно. `payment_method.active` лишь наблюдается; не сохраняет карту и не включает автопродление.

3. `validate_purchase_payment` (`billing/reconciliation.py:140–180`) для schema 2 сверяет invoice/operation/workspace, конкретный provider id, сумму/валюту, metadata operation/workspace/invoice, recipient shop, test/production, сохранённые shop/environment. Ошибка переводит к reconciliation gap, не выдаёт доступ/карту. `apply_confirmed_purchase` вызывает initial grant только для authoritative terminal succeeded; canceled освобождает соответствующие резервы, pending не выдаёт доступ.

4. Сохранение карты: `grant_confirmed_payment` (`billing/entitlements.py:145–386`) ограничен initial_checkout и одноразовым grant. Duplicate не создаёт вторую карту/доступ. `extract_saved_bank_card` требует bank_card, `saved is True`, ограниченный provider ref и ровно четыре цифры last4; в GRAF переносится зашифрованный provider ref и masked label, не PAN/CVV. Новая карта и recurring authority допустимы только при фактическом `recurring_consent is True`, неизменной версии разрешения, действующем personal owner, совпадении исходного billing actor/current owner и наличии ключа шифрования. Более поздняя отмена/смена владельца не восстанавливаются этим поздним первоначальным платежом. False или отсутствующее согласие не сохраняют новую карту/разрешение, даже если провайдер вернул saved card.

5. Автоматическое списание: реальный planner/charge caller — `workflows/worker.py` recurring maintenance loop. `plan_due_renewals`, `pending_renewal_charge_candidates`, `charge_renewal_operation` в `billing/renewal_charge.py` используют стабильный ключ paid period/attempt, ограниченные окна, current personal owner, разрешение/authority version, принятые текущие цены и активную verified default карту того же billing owner. Проверка полномочий предшествует дешифрованию и POST. Существующая uniqueness `(workspace_id,idempotency_key)` и workspace/row locks сериализуют новые операции. Processing marker и бюджет сохраняются до dispatch: только scheduled/no-provider операция допускается к mutation; processing/sent/unknown/известный provider id не отправляются вновь. Timeout/неоднозначный ответ оставляют unknown/manual и резервы для GET/list/manual recovery; planner не открывает следующий ключ, пока попытка может завершиться. Повторный 429 использует ту же операцию и ключ в прежнем ограниченном окне. Достоверный merchant/request reject не считается подтверждённой банковской отменой или исчерпанной попыткой карты.

6. Отмена/удаление: POST cancel/delete/resume защищены CSRF и session auth; `_billing_owner_subscription` проверяет actual personal owner, membership и billing owner под workspace/subscription lock. Cancel сравнивает authority version, отменяет только scheduled/no-provider renewals, повышает версию и оставляет оплаченный срок. Уже processing/sent/unknown операция продолжает проверяться: отмена не является обещанием отозвать уже начатый запрос. Поздний succeeded предоставляет оплаченный доступ ровно один раз, не включает recurring и не меняет карту старого разрешения (`entitlements.py:594–619`). Удаление допускается только после отключения recurring, отзывает default активный метод в GRAF и повышает version; это отзыв GRAF authority, а не удаление банковских реквизитов у YooKassa. Зашифрованная историческая запись не становится доступной charge selection после revoked. Возобновление требует unchecked отдельное согласие, актуальную version/quote/цену и active verified owner card; молчаливого возобновления нет.

## Прочитанные существующие проверки и минимальная повторная проверка

Ничего не запускалось в ходе обзора; ниже точные существующие проверки для root. Unit используют fake DB/provider; живую БД или провайдер подставлять нельзя.

Из `apps/server`:

```sh
.venv/bin/pytest tests/unit/test_billing_entitlements.py::test_saved_card_requires_true_consent_and_current_authority tests/unit/test_renewal_charge.py::test_charge_uses_saved_method_and_authority_snapshot tests/unit/test_renewal_charge.py::test_charge_rejects_boolean_authority_version_before_decrypt_or_provider tests/unit/test_renewal_charge.py::test_transport_unknown_never_retries_without_provider_id tests/unit/test_renewal_charge.py::test_planner_never_starts_a_second_key_while_one_attempt_is_unresolved tests/unit/test_renewal_charge.py::test_rate_limit_retries_same_attempt_and_key_without_decline_notice tests/unit/test_billing_renewal_workflow.py::test_late_success_after_cancellation_grants_paid_access_without_reenabling_recurring tests/unit/test_billing_renewal_workflow.py::test_confirmed_renewal_extends_paid_through_once tests/unit/test_billing_purchase_observation.py::test_new_purchase_requires_exact_provider_scope_and_invoice tests/unit/test_payment_methods.py tests/contract/test_billing_security.py -q --tb=short
```

Для штатного одноразового PostgreSQL HTTP пути достаточно существующих:

- `tests/integration/test_billing_purchase_journey.py::test_initial_storage_early_renewal_and_scheduled_downgrade_are_one_coherent_journey`: initial True + synthetic saved card authoritative success, cancel/resume/версия/новая quote, оплата/доступ при отмене во время отправленного запроса.
- `tests/unit/test_billing_money_path_e2e.py::test_confirmed_renewal_is_atomic_and_replay_safe` и `::test_expired_unknown_v2_renewal_blocks_new_money_and_recovers_late_success`: настоящие SQL проекции на одноразовой базе, replay/unknown/late success.
- `tests/integration/test_billing_review_regressions.py::test_cancel_unsent_renewal_releases_only_retriable_reservation`: scheduled против unknown/sent, сохранение резервов неопределённых исходов.

Удаление карты проверено чтением production handler и UI guard; найденный `test_payment_method_delete_guard_remains_visible_when_renewal_is_enabled` — проверка шаблона, не доказательство полного authenticated HTTP deletion. Если root не располагает уже полученной полной deletion evidence, эту границу нельзя объявлять проверенной HTTP/живым клиентом.

## Точная область и источники

Просмотрены direct callers функций выдачи, dispatch и cancellation; `YooKassaClient`, методы saved bank card, reconciliation validators, subscription control, соответствующие route/template guards и существующие тесты перечисленных ветвей. Широкий аудит репозитория не выполнялся.

SHA-256:

| Файл относительно `apps/server/src/twobrain_rec_server` | SHA-256 |
| --- | --- |
| billing/entitlements.py | `83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b` |
| billing/renewal_charge.py | `4322d7a4be80aa1ed6f0ba9020839cc37d0f9043b57106f34b7c7a28a9603810` |
| billing/reconciliation.py | `56549e38984e6698d57814f10615037d94feb124abd249c266f00d94fa532b83` |
| billing/webhook_reconciliation.py | `15b7b220c202b5582487823a6796f9b12863addc63971d3a4dc2f0e30b4b47b8` |
| billing/payment_methods.py | `51c0d747daa8ddb5f1b9362ece0123575af8522be72cfc3981af3e933a75e4ef` |
| cabinet/web_routes/billing.py | `60151eb2a2c5d46bff9314eb5e10fbfd0eedeb939029d6fa4fbd9eab53a4dd12` |
| workflows/worker.py | `79a8fa7278179e5924f8333b095ea1dd14883d1a4c2689850d2f66b481e5c21b` |

Непроверенные внешние границы: актуальное подключение магазина, фактическое создание платежа True, succeeded/saved bank card в production, реальный последующий merchant initiated charge, его receipt/settlement/refund. Сообщение пользователя о включении привязки принято как новый контекст; старый 403 не применяется как текущий блокер. Этот обзор не превращает включённую привязку или GET account capability в доказательство полной финансовой приёмки.

## Дополнительная pre-run проверка диагностического payload

Прочитан `/tmp/graf-f280-recurring-state-payload.py`, SHA-256 `aff8f414d8421d8fb0c661d44111813ea502c4b74c9fc62ad43b02d4707fd15e`. **Нужна одна обязательная исправляющая правка перед запуском:** `BillingSubscription` не экспортируется `db.models`; модель называется `WorkspaceSubscription`. Заменить импорт и два обращения к модели в count-query. Без этого скрипт завершится ImportError до диагностики.

По безопасности остальных путей: существующий maintenance operator_diagnostics context, READ ONLY, SET LOCAL timeout, SELECT и rollback; provider-вызов один `list_payments` → GET `/v3/payments`, одна страница max100, без mutations. В успешный вывод идут counts, статусы/виды, timestamps и фиксированные labels; объекты/идентификаторы/карты/контакты/amounts/metadata/credential fields не печатаются. Глобальные enabled subscription/method counts не ограничены 24ч; это глобальный snapshot, тогда как recent counters/list ограничены окном. Это предел интерпретации, не новая операция над данными. Полный текущий магазин- или recurring-статус скрипт не доказывает.

Для устойчивого безопасного счётчика желательно guarded dict для nullable/malformed provider_failure/payment_method и преобразование неизвестных states/kinds/status к фиксированному `other`; это не требует новых библиотек/запросов. С текущим trusted provider ответом known statuses не раскрывают персональные поля, однако произвольные внешние status strings сейчас становятся ключами JSON. После исправления обязательного импорта повторно проверить точный payload hash; запуск не выполнялся.

## Повторная проверка финальной диагностики и записей

2026-10-02: **PASS безопасности финального диагностического скрипта и точности границ текущих записей. Новых блокирующих замечаний нет.** Историческое замечание выше относится к первоначальному скрипту; оно исправлено до зарегистрированного запуска и не является текущим блокером.

Повторно прочитан `/tmp/graf-f280-recurring-state-payload.py`, актуальный SHA-256 **`837a048671ba850b4c5d476f3ec44be7bbd1ef538ed6d3475f3aaa27047517cd`**. Импорт и запрос используют существующую `WorkspaceSubscription`. `obj()` ограничивает вложенные failure/payment_method фактическими словарями; неизвестные состояния, виды операций и provider statuses преобразуются в фиксированный `other`. Полные внешние значения не становятся произвольными ключами итогового JSON. Синтаксис повторно проверен локальным AST parse, без исполнения main или сетевых/SQL запросов. Read-only transaction, штатный maintenance-контекст, локальный timeout, SELECT, rollback и одна страница GET `/v3/payments` сохранены; mutation-пути не добавлены.

Прочитаны `validation-recurring-enablement.md`, `evidence/recurring-enablement-verification.json` и сохранённые `/tmp/graf-f280-recurring-{runtime,account,state}-current.json`. Без повторных живых запросов машинно сверено:

- Секции runtime/account/state в evidence точно равны соответствующим безопасным исходным JSON; hash финального скрипта совпадает с evidence.
- Все 11 сохранённых billing hash каждой из трёх служб совпадают с текущими локальными исходниками: 33 сравнения. Общий runtime SHA `e750ad90facf1f6ffa4aca341136474870a5a003` указан отдельно от source `77e6aed8ff79127d6e6b284ad18b58da5793ef51`; равенство ограничено перечисленными billing-файлами и не объявляет общие SHA одинаковыми.
- Runtime record показывает public checkout и observation enabled, production/expected shop для всех трёх служб; API/processing healthy, maintenance running с `health=null`. Отсутствующий health не назван успешной отдельной health-проверкой maintenance.
- GET `/v3/me` record показывает 200, enabled production shop, configured account match и bank_card в доступных method types. Capability field names и фиксированные flags сохранены без значений merchant account/ITN; нет отдельного recurring capability flag. Запись не выдаёт этот GET за успешную новую оплату или автосписание.
- State record от `2026-10-02T19:03:25.293027+00:00`: окно 24ч/max100 содержит одну прежнюю canceled initial_checkout/403, без provider binding; recent grant/webhook counts 0, provider list items 0 и `more_pages=false`. Это чтение истории, не новый отказ магазина и не попытка её повторения. Новая успешная оплата в этом окне не наблюдается; независимая оплата после сообщения YooKassa этими записями не подтверждается.
- Global current snapshot имеет recurring enabled count 0 и verified active method count 1. В evidence есть `global_counts_scope=all_time_current_snapshot`; историческая карта не представлена как новая сохранённая карта после подключения. Эти два счётчика не названы счётчиками за 24ч.
- В evidence provider/production DB/payment attempts/deploy/configuration mutations указаны 0. Рассмотренный скрипт действительно содержит только чтение и не печатает номера/идентификаторы/суммы/контакты/снимки/ответы/карты/ключи. Рецензент независимо сверил безопасные записи и код, но не повторял журнал исполнения на host; live действия и итоговые синтетические test counts записаны основным агентом, не выполнены рецензентом заново.

Последняя часть validation и `not_proven` в JSON точно сохраняют открытыми новую оплату True, authoritative succeeded/saved bank_card, фактическую recurring authority после неё, последующее живое списание, receipt/settlement/refund, человеческую приёмку и zero-amount binding. Старый 403 классифицируется только как история; новые данные не обосновывают его сохранение в качестве текущего внешнего блокера. T011/T012/F278/umbrella не объявлены завершёнными.

Редактировался только этот принадлежащий рецензенту отчёт. Код, tasks, прочие документы, GitHub, конфигурация, платёжные/production данные и выпуск не менялись. Live запросы не повторялись.
