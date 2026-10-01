# F280 — независимая проверка отказа начала оплаты

Дата: 2026-10-02. Lane: active Spec Kit slice / high-risk-product.

Три независимых текущих обзора: [flow](review-provider-rejection-flow.md), [security](review-provider-rejection-security.md), [browser](review-provider-rejection-browser.md). Каждый PASS в указанной области, конкретных незакрытых замечаний CRITICAL/HIGH/MEDIUM/LOW0. Рецензенты не изменяли код, деньги, GitHub или выпуск. Требования: provider-rejection10/0, reviewer-owned53/0, все61/0.

Три файла продукта сохраняют финансовые переходы, согласия, idempotency, CSRF/owner/RLS и резервы. Авторитетный snapshot выбирает точный/общий отказ; query не подменяет причину. Неизвестный результат не разрешает новую оплату. Только вручную выбранный False и новая принятая оферта создают один новый запрос без сохранения карты.

Браузерный обзор прочитал завершённые Chromium8PASS/WebKit8PASS, accessibility16/16 и текущие исходники. JS-off означает проверку нативной формы/сериализации на fixture, не полный финансовый путь. Root дополнительно выполнил один recurring320 со снимками:1PASS14.64с, оба синтетических снимка просмотрены; текст/главная кнопка видимы, горизонтальной прокрутки нет, OFF явно сообщает отсутствие списаний.

| Файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/yookassa.py` | `5988391c8a034cab8eb959e53f988eb0fef3b131ed5f845382792f61358157ce` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `60151eb2a2c5d46bff9314eb5e10fbfd0eedeb939029d6fa4fbd9eab53a4dd12` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a2b98b75bb090e84a28e8c9e9479f909bc8fcf29e41e2f763a13d4e1c4437385` |
| `apps/server/tests/contract/test_billing_promo_refresh_browser.py` | `59852e799cc9a1a51a85d0a9c97108a3515c5ed5d40f5429c169a037a20a6eec` |
| `apps/server/tests/browser/billing-promo-refresh.test.cjs` | `fe25017951377b0e802c661a2c13b443e49d774c6a2253c163ae1173a1eb53b4` |

Полный итог HTTP/PostgreSQL фиксируется в [validation-provider-rejection.md](validation-provider-rejection.md), сходимость — [converge-provider-rejection.md](converge-provider-rejection.md). PASS обзоров не заменяет эти проверки, exact-SHA CI и новый выпуск T025. Подключение автоплатежей, реальные деньги/чеки/банк/возвраты F278, T011/T012 и umbrella7366 остаются отдельными. Реальная разовая оплата False пока не подтверждена.
