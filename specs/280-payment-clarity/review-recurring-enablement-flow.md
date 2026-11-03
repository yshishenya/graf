# Независимая проверка автоматических списаний F280

Дата: 2026-10-02. Объект: `рабочая копия F280`, ветка `codex/280-recurring-enablement`, точный HEAD `77e6aed8ff79127d6e6b284ad18b58da5793ef51`. Рабочая директория на начале проверки чистая.

## Вывод

**PASS в пределах проверки исходного кода и существующих проверок.** Ошибок или отсутствующих требований в заданной цепочке `initial consent → save_payment_method → succeeded/saved → renewal payment_method_id → OFF` не найдено. Изменение реализации для подключения разрешения магазина не требуется: сервер уже формирует запрос на сохранение карты и поддерживает дальнейшие списания.

Это не подтверждение реального успешного платежа, чека, зачисления на банковский счет, возврата или реального повторного списания. Письмо о включении привязки карты не заменяет проверку ответа на запрос создания платежа в нужном реальном магазине. Сведения GET `/me` о включенном магазине и фискализации также не доказывают возможность recurring: этот ответ не содержит проверенного флага recurring.

Режим работы: независимо прочитаны исходные пути, официальные инструкции и тесты; реальные платежи, запросы к авторизованному API, данные рабочей БД и изменения репозитория/GitHub не выполнялись. Единственный итоговый файл этой проверки — этот отчет.

## Проверенная цепочка

| Требование | Доказательство в исходном коде | Результат |
|---|---|---|
| Пользователь видит сумму, период, дату списания, способ отключения и явно может снять галочку | `cabinet/templates/cabinet/pages/billing_checkout_content.html:42-76`: следующая сумма/период и дата, checked без required, ссылка на «Подписку» | PASS |
| Первое сохранение карты требует согласия | `cabinet/web_routes/billing.py:651-711`: строгий bool из неизменяемого снимка, `save_payment_method=snapshot["recurring_consent"]`; адаптер `billing/yookassa.py:168-204` передает redirect, capture=true, чек и ключ идемпотентности | PASS |
| Галочка OFF разрешает обычную оплату без сохранения | Обработчик `billing.py:3650-3710` использует `Form(default=False)` и не требует recurring; тот же создатель передает false. `test_billing_money_path_e2e.py:397-502` покрывает true/false/отсутствие поля для месяца/года, оплату и отсутствие новой карты/разрешения | PASS |
| Карта хранится только после подтвержденного succeeded и saved=true | `webhook_reconciliation.py:66-159`: сначала проверка суммы/связей и terminal succeeded, затем `extract_saved_bank_card`; `payment_methods.py:82` требует bank_card/saved is True; `entitlements.py:324-369` дополнительно требует согласие, ключ шифрования, текущего владельца и неизмененную версию разрешения | PASS |
| Уведомление провайдера само не выдает доступ/разрешение | `api/billing.py:88-162` сохраняет безопасный сигнал; `webhook_reconciliation.py:620-679` выполняет авторизованный GET, а payment_method.active лишь observed. `reconciliation.py:140-184` проверяет payment ID, сумму/валюту, workspace/operation/invoice, shop и test/prod | PASS |
| Продление использует сохраненный способ и текущую версию разрешения | `renewal_charge.py:1058-1150`: recurring_allowed, версия, текущий владелец и verified default method; расшифрованный reference передается как payment_method_id. `yookassa.py:190-201`: повторный платеж без redirect confirmation/save flag, capture=true | PASS |
| OFF прекращает будущие списания | `cabinet/web_routes/billing.py:3094-3136` обновляет версию разрешения и отменяет неотправленные продления; `renewal_charge.py:1058-1073` повторно проверяет разрешение непосредственно перед отправкой. `entitlements.py:596-654`: поздний success выдает оплаченный период, не восстанавливая recurring_allowed | PASS |
| Потерянные ответы/повторы не создают второй платеж | `renewal_charge.py:911,1129-1149,1199-1288`: durable send marker и стабильный ключ, unknown не переводится автоматически в повторный POST; ограниченный 429 использует тот же ключ. `webhook_reconciliation.py:267-355` восстанавливает reference через GET/list и применяет тот же проверенный success | PASS |
| Чеки есть у первого и повторного платежа; pending не считается успехом | `billing.py:678-709`, `renewal_charge.py:1126-1150` формируют receipt с точной суммой и подтвержденным контактом; `webhook_reconciliation.py:99-100` оставляет pending; `billing/receipts.py:9-77` отделяет фискальную регистрацию от success платежа и доставки письма, допускает только монотонные изменения | PASS |
| Подтверждение идемпотентно | `entitlements.py:185-241,528-542`: существующий grant дает duplicate; `test_billing_money_path_e2e.py:398-502,670-908`: повтор webhook/poll не дает повторный grant, чек/уведомление не дублируются | PASS |

Ограничение отмены: уже отправленный провайдеру платеж нельзя предотвратить последующим снятием разрешения; позднее подтверждение такого платежа должно дать оплаченный период и сохранить OFF. Это предусмотрено существующим кодом и не является основанием заново включать продление.

## Официальные первичные источники

Прочитаны актуальные публичные страницы YooKassa:

- https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/basics — реальному магазину нужно подключение менеджером; согласие/расписание/отключение организует продавец.
- https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/save-payment-method/save-during-payment — продавец предупреждает об использовании карты и получает согласие; save_payment_method=true; дождаться succeeded (при capture=true) и проверить payment_method.saved=true.
- https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-with-saved — сумма/описание/payment_method_id, без дополнительного подтверждения; при схеме «сначала чек, потом платеж» ответ может быть pending, нужно уведомление или чтение статуса.
- https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-without-saving — даже при подключенных автоплатежах save_payment_method=false позволяет обычную оплату без сохранения.

Двухстадийная привязка на минимальную сумму и нулевая привязка не входят в действующий контракт GRAF: первый платеж amount-bearing/capture=true. Отсутствие этих альтернатив не является недостатком проверенной реализации.

## Минимальный профиль проверок

Самостоятельно тесты не повторялись: основной агент уже запускает нужные наборы. Для нового технического подтверждения достаточно существующих suites, без создания новых тестов:

1. `tests/contract/test_yookassa_adapter.py` — exact save true/false и renewal payload без confirmation/save flag; recurring denial и конфиденциальность.
2. `tests/unit/test_initial_checkout_recovery.py` — strict bool, стабильный ключ, отказ/unknown/expiry.
3. `tests/unit/test_payment_methods.py`, `tests/unit/test_billing_entitlements.py`, `tests/unit/test_renewal_charge.py`, `tests/unit/test_billing_reconciliation.py` — шифрование, смена владельца/версии, OFF, сохраненная карта, unknown/retries, подтверждение/чек.
4. **Через изолированный PostgreSQL**: `tests/unit/test_billing_money_path_e2e.py`, `tests/integration/test_checkout_yookassa.py`, `tests/integration/test_renewal_lifecycle.py` — реальный HTTP→SQL путь с заглушкой провайдера, ON/OFF/omitted, grant/replay, poll/webhook, чек и продление.

На момент чтения переданных отчетов `локальный артефакт graf-f280-recurring-unit-check.log` содержал `176 passed, 71 errors`: ошибки SQL-backed набора возникли при setup, потому что `TWOBRAIN_DATABASE_URL is required; run bash apps/server/scripts/run_local_postgres_tests.sh`. Их нельзя записывать как product FAIL либо как PASS. `локальный артефакт graf-f280-recurring-sql-check.log` содержал `6 passed` для двух integration suites. Финальные результаты повторного SQL запуска и обязательные проверки основного агента остаются его ответственностью.

## Что еще доказывает только контролируемая проверка у провайдера

В правильном production shop нужно увидеть успешное создание первого платежа с true (без 403/forbidden), затем авторизованный GET succeeded с bank_card/saved=true, одну выдачу периода и active saved method. Отдельно проверить OFF с false и отсутствием нового разрешения/сохранения. Для фактического продления нужен разрешенный контролируемый повторный платеж payment_method_id и подтверждение его статуса/чека. Фискальная регистрация, доставка чека, банковское зачисление и возврат — отдельные доказательства, не вытекающие из письма о подключении или зеленых тестов.


## Итоговая независимая сверка после разделения профилей

2026-10-02: перечитаны `validation-recurring-enablement.md`, `evidence/recurring-enablement-verification.json`, все три итоговых журнала тестов и текущие безопасные снимки runtime/account/state. HEAD остается `77e6aed8ff79127d6e6b284ad18b58da5793ef51`. Первый запуск с 71 ошибкой подготовки PostgreSQL выше сохранен как история; его замечание о необходимости повторного SQL-запуска закрыто результатами ниже. Тесты этим проверяющим не запускались заново.

| Итоговый профиль | Проверенный журнал | Результат |
|---|---|---|
| Адаптер, карта, права доступа, списание и workflow продления | `локальный артефакт graf-f280-recurring-unit-final.log` | 176 PASS, 1.38 с; ошибок нет |
| HTTP→PostgreSQL, заменена сеть провайдера | `локальный артефакт graf-f280-recurring-money-path-check.log` | 71 PASS, 63.06 с; штатный runner 69 с; cleanup: isolated_container_removed |
| Checkout/renewal integration | `локальный артефакт graf-f280-recurring-sql-check.log` | 6 PASS, 0.04 с; cleanup: isolated_container_removed |

Collection digest набора из 71 проверки `730f03bf1a6c92701a74b5cfb5e5d06beb3a869edf81ec91a992e5541ea5d026` и набора из 6 проверок `51b788a6ee0e37c2bac0b09bfe4728e158185a26546f5e85e8049b9f0fa1efa4` совпадают в журналах и evidence JSON. Два предупреждения pytest о переписывании импортированного модуля и устаревающем интерфейсе TestClient не являются ошибками проверок. Все данные платежей в этих тестах синтетические.

Сверка безопасных снимков:

- `evidence.runtime` точно равен `services` из `локальный артефакт graf-f280-recurring-runtime-current.json`. Для каждой из трех служб самостоятельно пересчитаны SHA256 всех 11 локальных billing-файлов: все 33 сравнения совпадают с записанными хешами. Source SHA служб `e750ad90facf1f6ffa4aca341136474870a5a003` отличается от HEAD проверяемой рабочей копии; совпадение относится именно к этим 11 файлам, а не ко всему серверному исходному дереву. API и processing healthy, maintenance running; отдельный health у maintenance не заявлен. Публичная оплата, production/ожидаемый магазин и наблюдение провайдера включены в каждой службе.
- `evidence.account_read` точно равен `локальный артефакт graf-f280-recurring-account-current.json`: GET `/v3/me` HTTP200, нужный enabled-магазин, test=false, fiscalization=true, bank_card среди доступных типов. Отдельного признака подключения recurring нет; вывод о живой привязке из этого ответа не сделан.
- `evidence.state_read` точно равен `локальный артефакт graf-f280-recurring-state-current.json`. Снимок на `2026-10-02T19:03:25.293027+00:00`, режим `READ ONLY rollback`, последние 24 часа: один исторический canceled initial_checkout с 403 без provider ID; новых grants/webhooks нет. GET списка платежей: 0 результатов, следующей страницы нет. Recurring-разрешений 0; одна verified active saved method — глобальный исторический счетчик, который не доказывает новую привязку после сообщения менеджера.
- Безопасная запись содержит 0 изменений провайдера, рабочей БД, попыток платежа, развёртывания и конфигурации. Независимый проход проверил сохраненные снимки и локальные байты; сам к рабочей БД/авторизованному API не обращался и финансовых операций не выполнял.

**Окончательный вывод: PASS исходного пути и перечисленных 253 проверок (176 + 71 + 6), применимых блокирующих дефектов или расхождений в документах подтверждений не найдено.** Приемка реального нового платежа после подключения, succeeded/saved bank_card/нового разрешения, реального повторного списания, чеков/банковского зачисления/возвратов и пользовательской понятности/конверсии остается недоказанной. Историческая карта и письмо менеджера не закрывают эти пункты. Нулевая привязка не входит в проверяемый путь. Обновлен только этот отчет; код, другие документы, tasks, GitHub и развёртывание не менялись.
