# F280 T058 — причины приостановки и настоящий период

2026-10-04 · Lane `high-risk-product` · Issue#7527 · внешние P2#4175640437/#4175640439. До изменения назначенных проверок основной исполнитель подтвердил лично прочитанный независимый requirements PASS14checked/0unchecked, scoped analyze/canon PASS. Исходный HEAD `8638348d13ab400323358def59ec2b9aee3e2902`. Тестовый исполнитель владеет только четырьмя назначенными файлами проверок и этим отчетом; продуктовый шаблон и canonical документы — за основным исполнителем.

## Причинный RED до изменения продукта

Contract17case: **13failed/4passed/82deselected**,0.79с. Шесть провалов причины приостановки: price/contact и acceptance_budget/provider_unavailable/catalog_not_approved/provider_floor скрыты ожидающим платежом. Семь провалов периода: no subscription/free/trial/expired/unknowncycle/missingcycle и настоящий year при устаревшей presentation подписи month. method_required, neutral late_success, receipt recovery без pending и active month — положительные проверки. Лог `/tmp/f280-t058-contract-red.log`.

Реальный GET `/billing/subscription`→одноразовая PostgreSQL47case: **11failed/36passed/125deselected**,37.63с pytest/42с runner. Шесть тех же скрытых причин и пять выдуманных периодов no subscription/free/trial/expired/unknowncycle. Положительные active month/year, существующие method_required и late_success с pending проходят. Collection digest `1defd54154851daa7935ab2618e1dfd186c1278cf806a4d42c0a0e6c8e7aff70`; `postgres_test_cleanup=isolated_container_removed`. Лог `/tmp/f280-t058-route-red.log`.

Во всех failing realGET cases денежные отрицательные проверки находятся **перед** новым провалившимся presentation assertion: counts operation/invoice/grant/quote и состояния operation/invoice не меняются, запрос create_payment запрещен synthetic double. Периодная матрица дополнительно сравнивает persisted plan/state/cycle/paid_through/trial_end/recurring/authority до/после GET. Прежние terminal provider_key_expired/observation_expired сохраняют существующий разрешенный manual checkout и допускают прежний nonfinancial ready resume quote максимум1; общая политика блокировки не расширена.

## Проверяемая граница

Расширена существующая реальная матрица с33до40case семью pending+restriction случаями; method_required уже проверялся до/после provider_id, остальные старые виды/состояния не удалены. Добавлена семьcase realGET матрица эффективного доступа и настоящего цикла. Full regression теперь172case, существующий return82case остается без правок. Новые проверки требуют одну primary ссылку на статус существующего платежа, отсутствие checkout/resume/early и resume quote при pending, видимую безопасную GET проверки цены/карты, receipt reason+помощь без «Оплатите», отсутствие false confirmation late_success текущего pending.

Contract проверяет все три cycle подписи по actual cycle, включая специально устаревший subscription_cycle_label. Unknown/missing cycle не становятся месяцем; row «Период оплаты» доступна только действующему оплаченному month/year. Существующее ручное receipt recovery без pending сохраняется. Старую synthetic fixture active paid подписки дополнено фактическим cycle=month: полный первый GREEN98passed/1failed выявил отсутствие поля cycle у прежнего SimpleNamespace; ни одно старое assertion не удалено/ослаблено. После дополнения полный UI99passed,0.58с. Основной исполнитель дополнительно защитил условие периода через default(None); отдельный missing-cycle case (delattr) добавлен в существующую contract матрицу. Окончательный полный UI **100passed/0failed/0skipped**,0.71с; лог `/tmp/f280-t058-contract-green.log`.

По замечанию независимого UX reviewer synthetic expired fixture получает effective label «Бесплатный», совпадающий с реальным handler; это только test-fixture correction перед окончательными браузерами, продукт2ffc/DB/UI файлы неизменны. Existing browser fixtures дополнены семью restriction и тремя cycle/access экранами; прежние trial/free/method_pending-on и off cases сохранены. Матрица320/360/768/1280,две темы,100/200%,контраст/размеры целей/фокус/клавиатура сохраняется. JS-off дополнительно проверяет7restriction и5period экранов: нативный статус GET по Enter без POST, безопасные причины, открытие условий Space и truthful year/no fabricated row. Существующие consent/CSRF/authority/quote/cancel/resume формы и120с предел запуска не ослаблены.

## Команды и текущий статус

```sh
cd apps/server
.venv/bin/python -m pytest tests/contract/test_billing_ui.py -k 'pending_preserves_restrictions or receipt_recovery_without_pending or period_is_only' -q --tb=short --show-capture=no
.venv/bin/python -m pytest tests/contract/test_billing_ui.py -q --tb=short --show-capture=no
cd ../..
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py -k 'subscription_existing_payment_of_every_kind or subscription_real_get_period' -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py tests/integration/test_billing_return.py -q --tb=short --show-capture=no
apps/server/.venv/bin/ruff check apps/server/tests/contract/test_billing_ui.py apps/server/tests/integration/test_billing_review_regressions.py apps/server/tests/contract/test_billing_accessibility.py
node --check apps/server/tests/browser/billing-accessibility.test.cjs
git diff --check
cd apps/server
BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-t058-browser-chromium .venv/bin/python -m pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-t058-browser-webkit GRAF_BROWSER=webkit .venv/bin/python -m pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
```

UI100PASS. Первый PostgreSQL254case прошел254passed,345.40с/runner352,cleanup removed,digest18dbdf1454a964be8b043d99d4950f722ff9b9ca8dfc87fe2cb69ab02ff97c6f, но во время него шаблон изменился только защитой default(None). Исторический лог сохранен в /tmp/f280-t058-db-full-green-history.log; не объявляется неизменным final snapshot. Предварительный Chromium16passed,76.16с также сохранен в /tmp/f280-t058-browser-chromium-history.log: source final, но до окончательной фиксации всего назначенного набора. Окончательный полный PostgreSQL **254passed/0failed/0skipped** (regression172+return82),232.81с pytest/238с runner, тот же digest18dbdf1454a964be8b043d99d4950f722ff9b9ca8dfc87fe2cb69ab02ff97c6f, cleanup isolated_container_removed; лог /tmp/f280-t058-db-full-green.log. Hashes после terminal DB совпали с окончательной фиксацией. Окончательный Chromium **16passed/0failed/0skipped**,61.34с; WebKit **16passed/0failed/0skipped**,76.37с. Запущены последовательно после final freeze;120с предел не изменен. Логи /tmp/f280-t058-browser-chromium.log и /tmp/f280-t058-browser-webkit.log. Fresh screenshots и pages.json находятся /tmp/f280-t058-browser-chromium/ и /tmp/f280-t058-browser-webkit/. Тестовый исполнитель лично просмотрел Chromium receipt_pending320dark и activeyear1280light: одна primary проверка платежа и честный год, без переполнения/конкурирующего checkout. Полный независимый визуальный вывод остается за назначенным reviewer. Проверки кода ruff/node syntax/diff-check PASS. Предыдущие pytest imported-plugin и Starlette warnings не являются skips. Реальных оплат, списаний, возвратов, пользовательских данных и provider действий нет; все состояния и изображения synthetic. Release/PR/checklist/source/browser/UX reviews и точные SHA/base gates ведет основной исполнитель.

## SHA-256 проверяемых байтов

Окончательная фиксация GREEN `/tmp/f280-t058-input-hashes.json` после защитного default(None) и missing-cycle case; прежняя фиксация сохранена `/tmp/f280-t058-initial-hashes.json`. Первый полный DB начат на template7f65767d; после сообщенного root изменения первый результат сохранен как история и повторяется полностью на template2ffc4946. Product source changes template-only. После terminal всех окончательных наборов hashes перечитаны: все7файлов совпадают с final snapshot, дрейфа нет. Старые mixed-source DB/browser результаты сохраняются только как история. Назначенные тестовые файлы и отчет переданы основному исполнителю; дальнейших правок здесь нет.

| Файл | SHA-256 |
|---|---|
| subscription template | `2ffc49465a9a7c4e11c95cb6780d5c1afde145fc755ea101878128e36c0353ca` |
| billing.py | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` |
| contract/test_billing_ui.py | `4dffa5ed2c8a467cad62aff9cf49da865cb931024dcb7df12c87d19ff7e6c1a9` |
| integration/test_billing_review_regressions.py | `fe2910b7f482f9992e848fc8e4242c1b653c0c11d2edb843177a574920020f27` |
| integration/test_billing_return.py unchanged | `8b293f14dd7ffb6ad23b40d4c384c9f11f65a1ee4b4c4b79c3a153a412e88fb3` |
| contract/test_billing_accessibility.py | `cde38c77bc51bf7d4fb8855e10ec1b88550f3b5e1a77e44eebb61420445e5f91` |
| browser/billing-accessibility.test.cjs | `2ba6a6e5cb4c750d37c2b62ddc92cc90c5d923c6cb0afb01e3a346ca59e88b17` |
