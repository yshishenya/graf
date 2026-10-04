# F280 T057 — независимый обзор исходников и проверок

Дата:2026-10-04. Метод: `code-reviewer`, read-only source/test review. Parent HEAD: `71d12ae4b27b019f669c31714d5384d9b6b00d0f`; проверяется текущий незакоммиченный diff поверх него. Проверяющий не автор изменения подписки и не выполнял чужие runs. Product/tests/canonical/checklists/GitHub/releases не менял, browser/DB suites не запускал. Единственная запись — этот отчет.

## Заключение

Исходники продукта и текущий diff проверок: **0CRITICAL/0HIGH/0исправимыхMEDIUM**, минимальная поправка соответствует FR042/044. Замечание TEST01 к старому literal assertion в `test_billing_return.py` исправлено и независимо перечитано ниже. Готовность merge/release еще не подтверждена: полный текущий DB240 и fresh browser evidence остаются отдельными воротами.

## Что проверено самостоятельно по исходникам

1. Весь измененный product diff — одна строка `billing_subscription_content.html`: вместо условного вывода о факте отправки общий notice говорит «Результат платежа [на сумму] еще не подтвержден. Платеж еще может завершиться. Повторно платить не нужно». Сумма остается опциональной и экранируется Jinja2; ни `resolution`, ни `kind`, ни `provider_id` больше не усиливают утверждение. Показано и возможное завершение, и запрет повтора. `role=status` сохранен.
2. `payment_unresolved` по-прежнему определяется доступным `pending_payment_url`, суммой либо `pending/unknown/unknown_pending` причины. Изменение текста не меняет условие. GET `billing_subscription_page` ищет связанные invoice/operation текущего workspace через тот же `CHECKOUT_BLOCKING_STATES` для всех видов операции. `initial_checkout`, `storage_upgrade`, `renewal`, `early_renewal`, manual_resolution без providerID/с ним получают общий notice без необоснованного утверждения отправки.
3. `renewal scheduled` без providerID по-прежнему попадает в prepared, не в pending. Условие `prepared_charge_amount_label and not payment_unresolved` неизменно, разрешенный ранний preview не убран. `scheduled` с providerID, sent/unknown/manual_resolution остаются блокирующими. `provider_key_expired/observation_expired` не добавлены в shared blocking set и не становятся новым запретом из-за этой поправки.
4. Статус существующего платежа остается главным действием. При одновременном `method_required` safe GET ссылка `/billing/payment-method` не потеряна. Общие причины price/contact/provider ограничений не добавляются/меняются этой строкой; уже существующая ветка method_required и неизменный `_renewal_notice` сохранены. Нового пути checkout/resume/early при unresolved нет.
5. GET query, owner/tenant/session guards, prepared quote conditions, status route, cancel/resume/early/confirm handlers, expected authority, CSRF, quote freshness, idempotency, денежный shared set и JavaScript не изменены. В обычном подходящем GET подписки остается существующая подготовка quote; эту страницу нельзя называть глобально write-free. Для конкретных unresolved состояний условие `pending_invoice is None` препятствует подготовке resume quote, а DB regression сверяет counts/states до/после.
6. Новые два contract cases проверяют наличие/отсутствие суммы и весь нейтральный notice, сохраненный status URL и отсутствие новых действий. Новые восемь PostgreSQL cases используют действительную modern manual_resolution для четырех kind с/без subscription и providerID=None; не подменяют это успешно отправленной операцией. Сохранены before/after counts для operation/invoice/grant/quote, states и create_payment await_count0. Старые method_required before/after dispatch и expired cases не удалены.
7. Browser fixture добавляет ambiguous payment без renewal reason. Новые assertions проверяют нейтральность, возможность завершения, status/action guards; предыдущие method-required/subscription/checkout проверочные ветки не ослаблены. Их результат еще нужно подтвердить текущим run.

## Историческое замечание TEST01 — исправлено и перечитано

В `apps/server/tests/integration/test_billing_return.py`, `test_prepared_renewal_allows_early_payment_but_sent_or_unknown_still_block`, прежняя строка703 требовала `("Уже отправленный платеж" in page.text) != safe_prepared`. Это противоречило уточненному FR042/T057 для всех неподтвержденных операций. Фактический RED root исполнителя:3failed/1passed/78deselected; prepared scheduled/no-provider прошел, остальные три упали на этом literal assertion.

Окончательный diff root исполнителя заменил только этот assertion на `("Результат платежа" in page.text) != safe_prepared` и добавил `"Уже отправленный" not in page.text`. Самостоятельно перечитан весь тест: прежний early-preview только для prepared, явное prepared сообщение, число provider create, payment counts, состояние старых invoice/operation и existing status redirect сохранены без изменений. Новое contract покрытие отдельно требует «еще может завершиться». Замечание TEST01 закрыто по текущему source diff; результат полного DB run пока не выведен из этого просмотра.

## Чужие результаты, проверенные чтением текущих логов

Самостоятельно проверены окончания файлов, без переноса session/CSRF/form bytes или provider details:

| Артефакт root исполнителя | Установленный результат | Граница |
| --- | --- | --- |
| `f280-t057-contract-red.log` |2failed/80deselected| Причинные новые template cases до product поправки |
| `f280-t057-contract-green.log` |82passed,0.37s| Полный contract файл; не DB/браузер |
| `f280-t057-route-red.log` |8failed/150deselected| Новые manual_resolution/no-provider cases до поправки |
| `f280-t057-route-green.log` |33passed/125deselected,41.73s; runner PASS и isolated cleanup| Все targeted subscription cases, не полный158 regression файл |
| `f280-t057-return-red.log` |3failed/1passed/78deselected,15.63s| Исторический старый literal, исправлен текущим diff |
| `f280-t057-full-green.log` |collection240, digest308e9986d876bac980873b276331648694e17daa71d89eaccc78ffedf2c17fc1| Run начался, полного окончания пока нет; результат не приписывается |

Имена здесь — идентичности ephemeral runs вне git, без абсолютных локальных путей. Для долгосрочного validation root переносит только metadata-safe итоги и current source binding. Данные финансовой/живой/человеческой приемки в этих runs отсутствуют. Одного log summary недостаточно для exactSHA release gate.

## Fingerprints текущей редакции

SHA256 файлов при самостоятельном просмотре; изменение любого перечисленного файла требует перепроверки соответствующего вывода:

| Репозиторный путь | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `adb15750e5612a23710c42d81adb3b91c2b8070bd8938f4c65933e6f7ad2aa4e` |
| `apps/server/tests/contract/test_billing_ui.py` | `d02341d6a83f4521563bb9941a45f0938bc146d22e4a57993830695763995724` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `fcdd8f2c2fd9270fc92ba92bf60d325e49ab8c59692b48a17241861a1ec24eea` |
| `apps/server/tests/integration/test_billing_return.py` | `8b293f14dd7ffb6ad23b40d4c384c9f11f65a1ee4b4c4b79c3a153a412e88fb3` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `0d5f86bfc0592455014135184f4eeb4408beb5486069e70475ff62d758f170ab` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `954147a5109b1e3360121215af9f535f86f5da9f9f4ee7a712206f6b52ddb4cf` |

Итоговая оценка source: однострочное исправление не меняет money/read-model policy и устраняет доказанный false dispatch для общего случая. TEST01 исправлено; новые validation/review/current SHA gates должны завершиться до merge/release T048/T056. Прежние71d12ae4 проверки не относятся автоматически к этому diff.
