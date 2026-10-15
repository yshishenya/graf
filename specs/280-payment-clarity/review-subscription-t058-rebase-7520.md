# F280 T058 — независимая проверка влияния F278 #7520

Дата: 2026-10-04. Reviewer `/root/sdd_supplement`, полоса `high-risk-product`, проверка влияния обновленной зависимости. Единственное разрешенное изменение — этот новый отчет. Code/spec/plan/tasks/checklist/другие reports/Git/GitHub/releases/deploy не менялись; тесты reviewer не запускал.

**SOURCE IMPACT PASS — 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM в совместимости T058 с #7520.** Новых ограничений, ложного периода или конкурирующего действия на странице подписки не найдено. Это узкое заключение о влиянии переноса на новую базу, а не полная независимая приемка денежной функциональности F278 либо выпуск.

## Точные границы сравнения

- Текущий замороженный HEAD: `875dbacb6fba9f2da108c4c187f6369fb7ef9ce6`.
- Текущая база: `bbbdccedf1870ae7b4a7dce05f9c401ba0f8b76f`, F278 #7520.
- Исходный кандидат T058: `0ebbb00bb7ab761f261a7776b27e26bd94a8c79e`.
- Прочитанная upstream поправка: `f91a828d5027f89ac0adf619794ca76174c15622` → `bbbdccedf1870ae7b4a7dce05f9c401ba0f8b76f`.

Прочитаны upstream diff, текущие route/subscription template/invoice template/receipt reconciliation зависимости и относящиеся к чекам contract/integration тесты. Root не изменил upstream реализацию `webhook_reconciliation.py` относительно базы #7520; интеграционный код F280 в `billing.py` не меняет receipt поправку F278. Ранее опубликованные source reports остаются историческими на своих байтах.

## Структура кода и пять неизменных файлов

Сравнение AST (дерево структуры Python без номеров строк) против исходного кандидата показало полное совпадение `_renewal_notice` и `billing_subscription_page`. SHA-256 нормализованного `ast.dump(..., include_attributes=False)`:

| Функция | Результат | SHA-256 структуры |
|---|---|---|
| `_renewal_notice` | MATCH | `89739713a6b5498cbe06445832a8593bafe0fc9bbe83df4f7feaeecc26872113` |
| `billing_subscription_page` | MATCH | `d4e4263125f20c10b8f6bcccfb9145c1da3d0a1d0dfadbf74210f5217c201e35` |

Пять из семи файлов замороженного T058 совпали побайтово: subscription template, regression, return, accessibility fixture и CJS browser. Два изменившихся отпечатка объяснены upstream: `billing.py` получает отдельные receipt read/refresh projection и ветку существующего защищенного refresh; UI contract получает три дополнительных комбинации observation_enabled для receipt состояния. Требования T058, pending/cycle тесты и их финансовые assertions не ослаблены.

Прочитан весь текущий subscription template2ffc и актуальная route-проекция: эффективный personal определяет active; workspace-scoped общий CHECKOUT_BLOCKING_STATES/read всех видов сохранен, scheduled renewal без provider_id остается prepared. Receipt observation states succeeded/succeeded_projected/succeeded_refused не добавлены в blocking набор подписки. Метод/цена/контакт и четыре suspension причины остаются видимыми одновременно с pending; pending receipt идет в помощь без нового checkout, late_success подавлен при pending. Mapping three cycle uses и active+known month/year period guard не изменились. Доступные money/consent/cancel/resume/early/manual границы прежние. Global subscription GET по-прежнему может создавать существующий неденежный ready resume quote; это не новая запись от #7520 и не основание заявлять глобальную чистоту GET от всех записей.

## Новая зависимость чека и сохраненные ограничения

Invoice GET сохраняет owner-only доступ, workspace-scoped invoice, ограничения service_resolution для прежнего плательщика, маскирование реквизитов/контакта и разрешенные внешние receipt URL только при can_manage+AVAILABLE+allowlist. `_is_paid_refused_receipt` разрешает узкое наблюдение только succeeded invoice с workspace_scope_invalid и собственной renewal/early_renewal succeeded_refused operation; это не дает доступ к карточке/контакту/ссылке прежнего плательщика. `can_refresh_receipt` дополнительно требует succeeded invoice, PENDING receipt, включенное observation/checkout, собственную подходящую kind/state/provider_id operation.

Обычный invoice GET читает данные и рисует quiet форму, без provider вызова, нового invoice/operation/grant или денежного POST. Новая форма использует существующий защищенный POST refresh с CSRF, rate limit, owner/session/tenant проверками и `return_to=invoice`; этот POST явно инициирует наблюдение, поэтому не называется чистым чтением локальной БД. Receipt-only query включает только succeeded-семейство с pending receipt/provider_id. Внутренняя ветка использует provider GET, сверяет scope/payment с succeeded и меняет receipt observation/timestamp/существующее notification; она не выполняет повторную выдачу доступа, mandate или budget settlement. Без действующего owner provider не вызывается; ошибочный receipt refresh не превращает paid state в manual_resolution. Эти новые действия принадлежат F278 и не вызываются подписочным GET T058.

Прочитанные upstream тесты отдельно охватывают nonrecoverable operation, прежнего owner, отсутствие CSRF, чужой invoice, member/revoked owner, receipt_only без финансового fallback и отсутствие повторной проекции. Они служат source evidence намерений и ограничений; их фактический полный текущий F278 PASS этим reviewer не заявлен.

## Лично прочитанные текущие terminal результаты

| Набор после обновления базы | Terminal результат | SHA-256 журнала |
|---|---|---|
| `f280-t058-rebase-7520-ui.log` | 103 passed, 2 warnings, 0.43s | `2797c311d6677cd15877735f087ba867c1df5693bfe3448c705b5cf43a24b798` |
| `f280-t058-rebase-7520-route.log` | 47 passed, 125 deselected, 2 warnings, 32.49s; runner37s; result pass; isolated_container_removed | `6adfc26e1e34ef8419d01f0bd4e1cecc94045e336f75502fbb8687d77bff340f` |

Targeted47 collection digest: `1defd54154851daa7935ab2618e1dfd186c1278cf806a4d42c0a0e6c8e7aff70`. Это реальные synthetic GET сценарии pending/cycle с прежними counts/states/providercreate0 assertions. Текущие UI103/targeted47 не заменяют новую полную проверку всех финансовых зависимостей. Предыдущие DB254 и Chromium/WebKit16×2 выполнены до #7520, остаются историческими и не выдаются за current CI/newdeps evidence. Новый exact-SHA/base PR, merge, полные применимые проверки, frozen release-full/CD/live остаются отдельными воротами.

## Отпечатки прочитанных окончательных байтов

Все семь строк соответствуют `f280-t058-rebase-7520-hashes.json`; пять неизменны относительно исходного T058, два — описанные upstream изменения.

| Путь | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `2ffc49465a9a7c4e11c95cb6780d5c1afde145fc755ea101878128e36c0353ca` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `66e09e1f751ddb9c405d65891a07d6a5d66854c9d2794b8226fda4b963ed84ec` |
| `apps/server/tests/contract/test_billing_ui.py` | `52b235300cb8a3bd474f53c882e55bd62267c514e1ec33b522c524b874a7f78e` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `fe2910b7f482f9992e848fc8e4242c1b653c0c11d2edb843177a574920020f27` |
| `apps/server/tests/integration/test_billing_return.py` | `8b293f14dd7ffb6ad23b40d4c384c9f11f65a1ee4b4c4b79c3a153a412e88fb3` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `cde38c77bc51bf7d4fb8855e10ec1b88550f3b5e1a77e44eebb61420445e5f91` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `2ba6a6e5cb4c750d37c2b62ddc92cc90c5d923c6cb0afb01e3a346ca59e88b17` |
| `apps/server/src/twobrain_rec_server/billing/webhook_reconciliation.py` | `651f42f67fcc0f27bc7f5872bdecf83cead737c17982eb8d283abce84573d808` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html` | `41ef0356ed7db21bea83900fe7592e549702e9c830b650e8436bdd76f4d0dd95` |

После записи reviewer перечитал отчет, повторно сверил HEAD/девять hashes и AST двух функций; дрейфа нет. `git diff --check` по этому отчету прошел. Незакрытых source-impact findings0; границы partial tests и прежних browser/full DB доказательств сохранены. Работа была только read-only investigation/report; полного product/payment functionality либо production допуска из этого результата не следует.
