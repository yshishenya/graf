# F280 — независимый обзор кода T058

Дата: 2026-10-04. Reviewer `/root/sdd_supplement`. Полоса: `high-risk-product`, продолжение US4/FR039/042/044/045. Основание требований: [review-subscription-t058-requirements.md](review-subscription-t058-requirements.md), checklist14/0 и текущие spec396–400/plan277/tasks306/contract153/quickstart313. Единственное владение reviewer — этот отдельный отчет; checklist и чужие изменения сохранены.

**SOURCE LOGIC PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Открытых замечаний к прочитанной логике T058 нет. Тестовый, браузерный, PR и выпускной допуски оцениваются отдельно; исходный полный DB254 и первый Chromium16 выполнены до окончательной защиты отсутствующего cycle и не подтверждают окончательные байты.

## Объем и основания проверки

Применен `$code-reviewer`. Прочитаны полный окончательный шаблон подписки и все пять измененных product/test файлов относительно HEAD `8638348d13ab400323358def59ec2b9aee3e2902`: один шаблон, UI contract, PostgreSQL regressions, Python browser fixture и общий CJS browser script. Среди `apps/server/src` изменен только `billing_subscription_content.html`; route/GET query/денежные обработчики/API/DB/CSS/JS/invoice не менялись в T058.

Перечитаны `_renewal_notice` и оба его вызова, `billing_subscription_page`, повторный рендер через existing early-preview error, `_page_shell`/`render_template`, effective_plan_code, общий CHECKOUT_BLOCKING_STATES, owner/session/CSRF/version/quote guards resume/cancel, early-preview и существующее запрещающее чтение operations. HTML формы, required resume_consent, hidden версия/quote/CSRF, обычные manual/early/resume ограничения и native раскрытия не изменены. Обработка первоначального выбора/FR019–020 остается прежней. Никакой денежный запрос из нового HTML не добавлен.

### Видимые причины и безопасное восстановление

Главная pending ветка заканчивается после нейтрального результата/can-complete и единственной primary ссылки существующего status либо помощи. Затем независимо выводятся причины ограничений. Для method/price используются прежние статические URL `/billing/payment-method` и `/billing/storage`; это ссылки GET. Для pending receipt шаблон сознательно не использует `_renewal_notice`, содержащий старое приглашение ручной оплаты, и выводит причину с `/billing/history#billing-help`. Без pending прежний receipt текст и checkout cycle сохраняются. Все четыре существующие suspension причины доступны без раскрытия. `late_success` ограничен `not payment_unresolved`, поэтому не подтверждает одновременно ожидающую операцию.

Query выбирает workspace-scoped invoice/operation по общему blocking набору, без фильтра kind; scheduled renewal без provider_id остается prepared. Неподтвержденность определяется по status URL/сумме либо pending/unknown/unknown_pending resolution, сохраняя прежние no-subscription/no-amount случаи. Existing manual/early/resume guards используют тот же payment_unresolved, поэтому новая ветка notices не открывает конкурирующую оплату. T051 expired/manual_resolution политика не расширена.

Subscription GET может создавать прежнее неденежное resume quote только при обычном ready и отсутствии pending invoice/запрещенной resolution. Поэтому глобальную страницу нельзя описывать как полностью свободную от записи quote; новые pending regression snapshots сохраняют отдельное требование отсутствия изменений records/states/providercreate0 в рассматриваемых сценариях. Эта граница сохранена.

### Достоверный период

`cycle_label` берет `month`/`year` непосредственно из `subscription.cycle`, с `default(None)` для отсутствующего атрибута; неизвестное значение дает нейтральное «период». Три использования — next charge, «Период оплаты» и next price — используют этот единственный mapping. Строка «Период оплаты» дополнительно требует active+subscription+known month/year. Active приходит из эффективного personal плана, поэтому free/trial/expired/no-subscription не получают текущего оплаченного периода. Устаревшее переданное subscription_cycle_label больше не определяет эти факты; default нового checkout cycle не меняется.

Окончательный contract включает отсутствие самого cycle атрибута через удаление `sub.cycle`, наряду с None/unknown/free/trial/expired/no-subscription и положительными month/year. Это осмысленная проверка compatibility guard, добавленная после исходного DB254; она не ослабляет исходные финансовые утверждения.

### Измененные проверки

UI contracts используют настоящую `_renewal_notice`, проверяют причины вне закрытых details, единственный primary status, отсутствие нового checkout/resume/early, отсутствие ложного late_success; отдельно сохраняют receipt recovery без pending. Period tests проверяют все три подписи, включая stale label и missing attribute. Existing DB matrix дополнена price/contact/suspension/late_success и эффективными period состояниями, сохраняя сравнение counts/states и create_payment0. Старые method_required/expired/manual_resolution/terminal финансовые assertions не удалены и не ослаблены.

Browser additions только расширяют existing fixture/matrix: год при намеренно устаревшей месячной label, отрицательные period состояния, ограничения одновременно с pending, keyboard focus безопасной цены, JS-off status navigation только GET и native details. Общие размеры, темы, масштаб, assertions, временные пределы и recovery policies не ослаблены. Настоящую визуальную/UX приемку этот source reviewer не дублирует.

Независимый UX reviewer сообщил отдельную неточность synthetic expired fixture: оно наследовало подпись «Личный» вместо реального effective «Бесплатный». Узкий повторный обзор прочитал исправленную строку `subscription-expired`: `active=False, subscription_plan_label="Бесплатный"`. Она согласуется с реальной effective проекцией и не меняет продукт либо финансовые assertions. **Этот отдельный synthetic fixture concern закрыт**. На том промежуточном refresh браузерные результаты ожидались; окончательные результаты подтверждены отдельно ниже, а не выведены из одного исправления подписи. UI/DB/product повтор из-за одной синтетической подписи не требовался.

## Прочитанное тестовое evidence и его предел

- Причинный `f280-t058-contract-red.log`: 13 failed, 4 passed, 82 deselected; старый шаблон теряет price/contact/suspension причины и выдумывает период. `f280-t058-route-red.log`: 11 failed, 36 passed, 125 deselected, включая реальные GET. Это подтверждает причинность целевых тестов, а не нынешнюю готовность.
- Первоначальные UI99, DB254 и Chromium16 — исторические для редакции до окончательного missing-cycle guard/case; PASS окончательного кандидата из них не выводится.
- Reviewer лично прочитал текущий terminal `f280-t058-contract-green.log`: **100 passed, 2 warnings, 0.71s**, включая добавленный missing-cycle case в прочитанном текущем тесте. При узком refresh final freeze подтверждает привязку UI100 к окончательным template2ffc/UI4dff байтам; остальные проверки координатор фиксирует отдельно.
- На момент первоначального заключения окончательные PostgreSQL254/return и Chromium/WebKit16×2 еще ожидались. Их последующий результат фиксируется только в узком дополнении ниже; первоначальная ожидательная запись не является текущим DB gate.

Сами наборы reviewer не запускал; реальных payment/provider/DB/browser операций не выполнял. `git diff --check` по пяти измененным product/test файлам прошел.

## Отпечатки прочитанного окончательного среза

Все семь файлов повторно совпали с окончательным `f280-t058-input-hashes.json` после исправления missing-cycle contract и expired fixture; прочитан отдельный `graf-f280-subscription-tests-final-freeze.txt`. Изменился только fingerprint Python accessibility fixture. Дополнительные fingerprints неизменных shared guards фиксируются ниже.

| Путь | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `2ffc49465a9a7c4e11c95cb6780d5c1afde145fc755ea101878128e36c0353ca` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` |
| `apps/server/tests/contract/test_billing_ui.py` | `4dffa5ed2c8a467cad62aff9cf49da865cb931024dcb7df12c87d19ff7e6c1a9` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `fe2910b7f482f9992e848fc8e4242c1b653c0c11d2edb843177a574920020f27` |
| `apps/server/tests/integration/test_billing_return.py` | `8b293f14dd7ffb6ad23b40d4c384c9f11f65a1ee4b4c4b79c3a153a412e88fb3` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `cde38c77bc51bf7d4fb8855e10ec1b88550f3b5e1a77e44eebb61420445e5f91` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `2ba6a6e5cb4c750d37c2b62ddc92cc90c5d923c6cb0afb01e3a346ca59e88b17` |
| `apps/server/src/twobrain_rec_server/billing/operations.py` | `f121492003d242d148703b559692c201571aec18bd792dae87878c524a4a844a` |
| `apps/server/src/twobrain_rec_server/billing/entitlements.py` | `83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b` |

Требования spec/plan/tasks/contract/quickstart повторно совпали с fingerprint таблицей независимого requirements отчета T058; tasks сохраняет связь с #7527. После записи reviewer перечитал этот отчет и повторно сверил девять перечисленных source/test fingerprints. Изменен только данный отчет; независимые browser/UX, exact-SHA/base PR и T048/T056 release gates остаются отдельными. SOURCE LOGIC PASS не снимает их HOLD и не подтверждает production.

Узкий evidence refresh 2026-10-04 закрыл synthetic expired label concern и подтвердил final UI100. Затем по terminal signal координатора reviewer лично прочитал окончательный `f280-t058-db-full-green.log`: **254 passed, 2 warnings, 232.81s**, runner238s, result=pass, cleanup=`isolated_container_removed`; collection count254, digest `18dbdf1454a964be8b043d99d4950f722ff9b9ca8dfc87fe2cb69ab02ff97c6f`. SHA-256 этого log: `5facda74c8ae195cfe9a4e130550514b9cfdd5a24a7b5dc3124699de1c5f7d89`. Это новый окончательный DB254 для template2ffc, а не исторический DB254/345.40s до guard. Финансовые утверждения и return contracts входят в прочитанный source набор; реальные финансовые операции не выполнялись.

На том промежуточном refresh окончательные Chromium/WebKit16×2 еще ожидались; reviewer их не запускал и тогда не присвоил PASS. История ожидания сохранена, текущие результаты приведены ниже. Checklist14/0 и canonical/product/test/Git/GitHub/release поверхности не изменены reviewer.

## Последний refresh окончательных проверок — 2026-10-04

После final terminal signal reviewer лично прочитал все четыре журнала и [validation-subscription-t058.md](validation-subscription-t058.md). Результаты согласуются с отчетом исполнителя и окончательно замороженными семью байтами; исходные mixed-source/предварительные результаты не использованы как final evidence.

| Окончательный набор | Прочитанный terminal результат | SHA-256 журнала |
|---|---|---|
| `f280-t058-contract-green.log` | 100 passed, 2 warnings, 0.71s | `3ba122baeeddb39ca5d2a80b153a44c1703428f1c33e44f335043f6acf9a3640` |
| `f280-t058-db-full-green.log` | 254 passed (regression172+return82), 2 warnings, 232.81s; runner238s; cleanup removed | `5facda74c8ae195cfe9a4e130550514b9cfdd5a24a7b5dc3124699de1c5f7d89` |
| `f280-t058-browser-chromium.log` | 16 passed, 2 warnings, 61.34s | `265d32226dcc01bab2d24a70012e331c87f5bbbea7e032c3175f8a6cf6d2df39` |
| `f280-t058-browser-webkit.log` | 16 passed, 2 warnings, 76.37s | `8a93b6ca8da40dca21aae3b5970dd050ae1f97ed52bcf59e66ecea80dd5f27e6` |

Validation фиксирует0 failed/0 skipped во всех окончательных наборах, последовательный запуск браузеров после final freeze, неизменный120s предел и отсутствие реальных денег/provider действий. DB collection digest и cleanup совпали с лично прочитанными строками выше. Reviewer повторно вычислил все семь final hashes из `f280-t058-input-hashes.json`: дрейфа0; template2ffc и fixturecde38 соответствуют таблице этого отчета. Сведения о первоначальном DB254/345.40s и Chromium16/76.16s остаются историческими.

**Окончательный SOURCE LOGIC PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM на actual final bytes.** Отчет перечитан, девять source/test fingerprints повторно совпали, `git diff --check` отчета прошел. Source reviewer подтверждает прочитанные terminal доказательства, но не подменяет отдельные независимые визуальные/UX заключения. Текущие exact-SHA/base CI, merge, frozen release-full/CD и live production остаются отдельными воротами; их PASS этим отчетом не заявлен. Reviewer изменил только этот отчет, матриц не запускал.
