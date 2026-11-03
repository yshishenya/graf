# F280: независимая проверка безопасности отказа начала оплаты

Дата: 2026-10-02 (Europe/Istanbul). Рецензент: `rejection_security_review`. Рабочая копия: `release-f280/crisp`, ветка `codex/280-payment-provider-rejection`; базовый HEAD `8764f29f3a3c18cc348986ee7c498e9381ec703e`. Область: FR-021–023, SC-009, T023/T024. Проверка только чтением; изменён лишь этот отчёт вне репозитория. Lane: active Spec Kit slice / `high-risk-product`.

**Результат: PASS для безопасности трёх файлов продукта. Замечаний CRITICAL/HIGH/MEDIUM: 0/0/0.** Это заключение о рассмотренном коде, а не допуск выпуска или подтверждение реального платежа.

## Основания

1. `billing/yookassa.py:20–27,263–286`: известная причина возникает только при HTTP 403, объекте JSON, `type=error`, `code=forbidden` и точном известном описании отказа в автоплатежах. Сходное описание, добавочный пробел, другой код/тип/HTTP, пустое/повреждённое тело и таймаут не получают этот признак. В `YooKassaProviderError` переносится только фиксированное значение `recurring_not_available`; исходное описание и идентификатор ответа в него не копируются. Обычный текст исключения содержит лишь HTTP status. Прежние успешные ответы и сетевые исключения не менялись.

2. `cabinet/web_routes/billing.py:546–581`: сохранение `provider_failure` повторно ограничивает reason известным значением, даже если атрибут исключения изменён вызывающим кодом. Сохраняются прежние безопасные class/observed_at/http_status. Нет копирования полного ответа, description, provider request ID, контактов или произвольного текста исключения в снимок. Новых журналов или аналитических событий нет. Существующая политика `product_analytics/page_inventory.py:311–328` блокирует аналитику страницы статуса и автоматический сбор её содержимого.

3. `cabinet/web_routes/billing.py:2017–2146`: выбор нового заголовка/причины выполняется по workspace-scoped сохранённым invoice/operation, после прежней проверки прав владельца/управляющего оплатой. Требуются schema 2, совпадающие canceled состояния, отсутствующий provider_id, сохранённый class provider_rejected и настоящий целочисленный HTTP из безопасного списка. Конкретная подсказка дополнительно требует initial_checkout, сохранённое `recurring_consent is True`, 403 и фиксированный reason. Старый общий 403 даёт только общее объяснение. Query result/reason/creation_rejected не участвуют в этих предикатах; исторический result=provider_unavailable не перекрывает достоверный отказ. Новые поля шаблона — bool, исходный ответ не передаётся.

4. `billing_operation_status_content.html:8–52`: новая подсказка сообщает, как вручную выбрать один период; CTA — обычная ссылка на существующее оформление. Она не отправляет POST, не сохраняет согласия и не изменяет финансовую запись. Неопределённые состояния сохраняют `can_refresh_payment` и прежнюю кнопку «Проверить статус», с текстом о недопустимости повторной оплаты. Уже известный provider_id исключает новое утверждение об отказе создания. Подтверждённая отмена провайдером без сохранённого доказательства отказа создания остаётся прежней отменой.

5. Просмотрены реальные callers `_create_initial_checkout_payment`, `_record_initial_checkout_failure`, `_persist_initial_checkout_failure`, POST `/billing/checkout/start`, `/billing/checkout/status/.../continue`, покупка хранения/раннего продления, `billing/renewal_charge.py` и `billing/webhook_reconciliation.py`. Diff не изменяет финансовые переходы, dispatch, idempotency key, release_invoice_promo, settle_acceptance_budget, locks, CSRF, роли или разделение пространств. В schema 2 продолжение не повторяет первоначальный POST; повтор того же ключа восстанавливает прежний счёт. Новый платёж остаётся за явным POST с актуальной принятой офертой. Неизвестная операция блокирует оформление и старт через прежний `_blocking_payment_operation_query`.

6. Возврат сохраняет месяц/год в существующем retry URL. Форма оформления по-прежнему включает галочку по умолчанию; новая подсказка не снимает её. Реальный POST сохраняет булево согласие в immutable snapshot операции и счёта; `_create_initial_checkout_payment` требует настоящий bool и передаёт его как `save_payment_method`. Отказ меняет только failure metadata/прежнее финансовое состояние; не меняет сохранённое согласие или режим подписки. Это не создаёт скрытого True→False fallback.

## Независимая проверка

Команда из `apps/server`:

```sh
.venv/bin/pytest tests/contract/test_yookassa_adapter.py tests/unit/test_initial_checkout_recovery.py -q --tb=short
```

Результат: **45 passed, 2 warnings, 0.37s**, exit 0. Warnings относятся к прежнему pytest import/rewrite и устаревающему сочетанию Starlette/httpx. Среди проверок — exact и соседние ответы, отсутствие раскрытия synthetic private description/request ID, повторное ограничение произвольного reason на границе снимка, прежнее восстановление/отклонение/неизвестный результат. Это синтетические проверки без реальных платежей.

Прочитаны новые FR/SC/plan/tasks/quickstart, `checklists/provider-rejection.md` и требования рецензента. Новый чеклист: **10 checked / 0 unchecked**; перечитаны все чеклисты: **61 checked / 0 unchecked**. Отметки не менялись; они подтверждают качество требований, не реализацию или выпуск.

## SHA-256 рассмотренных файлов

| Файл от корня репозитория | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/yookassa.py` | `5988391c8a034cab8eb959e53f988eb0fef3b131ed5f845382792f61358157ce` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `60151eb2a2c5d46bff9314eb5e10fbfd0eedeb939029d6fa4fbd9eab53a4dd12` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a2b98b75bb090e84a28e8c9e9479f909bc8fcf29e41e2f763a13d4e1c4437385` |

## Пределы заключения

В этом обзоре не запускались PostgreSQL HTTP и браузерные сценарии; их новый итог должен быть приложен основным агентом независимо. Не проверены реальные деньги, чек, зачисление, возврат или фактическое подключение автоплатежей в магазине YooKassa. Разовая живая оплата с False этим отчётом не подтверждена. Проверка не закрывает T011/T012/F278/umbrella и не заменяет exact-SHA CI, frozen release-full, dry-run/deploy, runtime и publication evidence. Если один из трёх хешей изменится, обзор требует повторной проверки соответствующего изменения.
