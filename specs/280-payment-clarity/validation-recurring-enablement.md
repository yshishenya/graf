# F280 — проверка после подключения привязки карт YooKassa

Дата: 2026-10-02, Europe/Istanbul. Пользователь сообщил новое подтверждение YooKassa: привязка банковских карт для рабочего магазина включена. Прежний статус «менеджер проверяет» больше не является текущим внешним блокером. Письмо принято как сообщение владельца; независимая живая привязка карты ещё не подтверждена.

Lane: read-only investigation и docs-only / mechanical для этой записи. Реализация не меняется; применяется существующая high-risk-product F278/F280. Владелец явно разрешил публичную оплату и технический выпуск. Это решение о доступности оформления не подтверждает незавершённые финансовые пункты F278; они остаются открытыми до живых доказательств. Новый флаг, переписывание оплаты и повторное развёртывание не нужны: необходимый серверный путь уже установлен. Старые отказы и принятые согласия не пересчитываются, деньги автоматически не отправляются.

## Проверенный работающий сервер

Три службы rec-api/rec-processing-worker/rec-maintenance работают на `e750ad90facf1f6ffa4aca341136474870a5a003`, опубликованный [v2026.10.02.5](https://github.com/yshishenya/graf/releases/tag/v2026.10.02.5). Во всех: публичная оплата TRUE, production/ожидаемый магазин, provider observation TRUE. API/processing healthy; maintenance running без отдельного health статуса. Public live/ready HTTP200.

Хеши 11 исходников оплаты в каждой службе совпали с проверенной рабочей копией HEAD `77e6aed8ff79127d6e6b284ad18b58da5793ef51`: адаптер, создание оплаты, карта, права доступа, продление/списание, сверка/обслуживание, покупки, cabinet route и checkout template. Разные общие SHA не выданы за одну версию: billing-файлы сравнены по байтам. Их SHA256 находятся в [безопасной записи](evidence/recurring-enablement-verification.json).

Живой GET `/v3/me`: HTTP200, account matches configured shop, status enabled, test false, bank_card доступен, fiscalization enabled. Ответ не содержит отдельного recurring capability flag. Этот GET доказывает доступ к нужному активному магазину; не доказывает successful save_payment_method=true или сохранение карты. Секреты, полное тело, налоговые данные и идентификаторы не выводились.

## Официальный контракт и существующая реализация

Прочитаны текущие официальные страницы: [автоплатежи](https://yookassa.ru/developers/payments/recurring-payments), [сохранение во время оплаты](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/save-payment-method/save-during-payment), [повторная оплата](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-with-saved), [без сохранения](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-without-saving).

- Начальная оплата передаёт реальное согласие bool в save_payment_method, redirect/return_url и устойчивый ключ. Галочка включена по умолчанию, оферта не принята по умолчанию. Ручной False сохраняется и передаётся провайдеру.
- Возврат из браузера не подтверждает деньги. Webhook/poll сверяют authoritative GET, operation/invoice/workspace/сумму/валюту/магазин/окружение. Доступ выдаётся один раз только после succeeded.
- Сохраняется зашифрованная ссылка на bank_card только при saved=true, актуальном владельце, согласии True и неизменной версии разрешения. Номер карты/CVV не поступают в GRAF. False не сохраняет новую карту и не включает продление даже при неожиданном saved ответе.
- Продление отправляет payment_method_id без redirect/save_payment_method, проверяет разрешение, текущую карту, цену и срок. Неопределённый исход не создаёт новый денежный запрос. Отмена/удаление отзывают разрешение в GRAF; поздний успех не включает его заново.
- YooKassa предлагает два варианта привязки: во время оплаты либо без списания. Текущая реализация использует первый; отдельная нулевая привязка этим продолжением не добавляется и не заявляется проверенной.

Два независимых read-only обзора: [flow/provider-contract](review-recurring-enablement-flow.md) и [security](review-recurring-enablement-security.md) — PASS существующего пути, без применимых блокирующих дефектов. Это проверка исходников и договоров, не живое списание.

## Новые выполненные проверки

| Набор | Результат |
| --- | --- |
| Адаптер, карта, доступ, списание, workflow продления | 176 PASS, 1.38с |
| Checkout/renewal integration, штатный isolated PostgreSQL runner | 6 PASS, 0.04с; collection digest51b788a6ee0e37c2bac0b09bfe4728e158185a26546f5e85e8049b9f0fa1efa4 |
| Восстановление initial checkout и сверка платежей | 30 PASS, 0.14с; повторная проверка после замечания review |
| Полный money_path HTTP→PostgreSQL с заменой только сети провайдера | 71 PASS, 63.06с; runner69с; digest730f03bf1a6c92701a74b5cfb5e5d06beb3a869edf81ec91a992e5541ea5d026 |

Все финансовые тесты синтетические. PostgreSQL cleanup PASS. Первый общий запуск ошибочно включил SQL-backed money_path без штатного PostgreSQL окружения: 176 PASS/71 setup ERROR с явным TWOBRAIN_DATABASE_URL required. Это ошибка запуска, не доказательство ошибки продукта. После разделения профилей money_path полностью прошёл в штатном isolated runner; пропуски/ожидания/защиты не менялись. Пробный неверный health URL /health/ready вернул404; настоящие маршруты /api/v1/health/live и /ready затем оба200. Ошибки не объявлены PASS.

Команды из корня:

```sh
apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_yookassa_adapter.py apps/server/tests/unit/test_payment_methods.py apps/server/tests/unit/test_billing_entitlements.py apps/server/tests/unit/test_renewal_charge.py apps/server/tests/unit/test_billing_renewal_workflow.py --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_checkout_yookassa.py tests/integration/test_renewal_lifecycle.py -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_money_path_e2e.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest -q apps/server/tests/unit/test_initial_checkout_recovery.py apps/server/tests/unit/test_billing_reconciliation.py --tb=short --show-capture=no
```

## Живое чтение и оставшаяся приёмка

2026-10-02T19:03:25Z: SELECT в штатном maintenance-контексте, транзакция READ ONLY, timeout10с, rollback. Последние24ч, максимум100 операций: одна прежняя canceled initial_checkout с403/no provider id; новых grants/webhooks0. Одна страница GET списка платежей YooKassa в том же окне: items0, следующей страницы нет. Существующие разрешения продления0; одна проверенная active карта — глобальный исторический снимок, не доказательство новой привязки после письма. Диагностический импорт модели исправлен на существующую WorkspaceSubscription до запуска; nullable словари защищены, неизвестные статусы сводятся к other. Полные объекты/карты/суммы/контакты не выводились. Production DB/provider mutations0.

Нужна новая явная оплата банковской картой через [оформление](https://rec.2brain.pro/billing/checkout): применить промокод, проверить итог, оставить автоматические списания включёнными, принять оферту и оплатить. После неё read-only сверка должна подтвердить succeeded/saved bank_card/один период доступа/актуальное recurring authority/чек. Старый отказ остаётся историческим, GET не отправляет его повторно. Данные карты/промокод не запрашиваются в чате.

Реальная новая оплата, привязка, последующее списание, receipt/банковское зачисление/возвраты и человеческая приёмка не выполнены этим проходом. T011/T012/F278/#7285 и umbrella#7366 остаются открытыми; задача исправления текста#7414 не переоткрывается. Документы требуют собственных exact-SHA PR gates, продуктовый Full/deploy не повторяются для записи неизменённого поведения.
