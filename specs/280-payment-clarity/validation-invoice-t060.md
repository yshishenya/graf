# F280 — безопасная помощь и браузерные проверки T060

Полоса high-risk-product / active Spec Kit slice, issue #7534, PR #7532. Продолжение утвержденного invoice среза; предвыбор автосписаний везде сохранен.

## Изменение

Общий существующий parser проверяет исходный и однократно декодированный адрес до parseaddr: C0/DEL отклоняются. Обычный адрес отделен от encoded mailto. Защита применяется к invoice/history/status/referrals/fair-use/account-merge; account-merge сохраняет прежний более строгий отказ display-name. Нет новой зависимости, flags, config startup политики, money/auth решений, query/API/DB/CSRF изменений. Внешний subprocess accessibility300с вместо120с; CJS assertions, отдельные пределы действий и бизнес-ожиданий сохранены.

## Причинные отказы и исправление

До основной правки: support contracts14FAIL/12PASS0.18s; real GET10FAIL/4PASS96deselected17.65s. После: support/UI/copy/accountmerge/fairuse contracts259PASS0.72s и unitcopy2PASS0.02s. Изолированный DB invoice/F278/support:88PASS83deselected78.96s, collection digest1175c1faf35342f5c500d803037aab9666ddba8087d20b24896f63719828e17d, isolated_container_removed.

Независимый reviewer нашел управляющие символы в display-name; отдельный RED4FAIL/9PASS0.10s. После узкого guard: full applicable support/UI/purchase/safety/accountmerge/fairuse+unitcopy202PASS0.68s. Actual GET без checkout, observationfalse/true:22PASS96deselected37.16s, runner41s, isolated_container_removed. Финансовые снимки до/после GET равны. Проверены None/malformed/CRLF/encodedCRLF/C0/DEL, display-name и специальные ?&+% local-part. Strict account-merge negative contract сохранен.

Промежуточные ошибки запуска (не успех продукта): неверный путь одного unit файла до initialGREEN; неверно указанные contract имена после import-only Ruff; bare paymentreturnbrowser без enableflag дал56SKIP. Ни один такой запуск не считается допускающим доказательством. Исправленные команды и реальные terminal результаты записаны отдельно.

## Браузеры

Accessibility Chromium16PASS62.29s, WebKit16PASS73.83s.77pages×5widths×2themes×2scales; native details/copy/focus/mailto, JS-off. Последний helper guard не меняет отрендерованные synthetic pages, их fixtures, templates/CSS/JS/CJS; эти результаты не называются повторным postguard прогоном. Negative helper и real GET являются отдельным новым доказательством. InitialT059120.67с timeout сохранен как история; enclosing300с не снижает assertions.

Дополнительная полная payment-return status matrix выполнена штатным изолированным PostgreSQL runner с GRAF_PAYMENT_RETURN_BROWSER=1: Chromium56PASS242.62s (runner247s), WebKit56PASS254.74s (runner259s). Каждый56collectiondigestf61d5bb9ed1bb294054f821962c07ce747e94abbc7814825dcc25616e09f4d12; каждый isolated_container_removed. Финальные helper/routes/templates использованы в обоих прогонах. Безопасные изменения help ссылки не заменяют этот обязательный quickstart gate.

## Рутинная проверка и границы

Ruff измененных Python файлов, Node syntax, Spec Kit governance, changelog fragment validator, git diff --check PASS. Требования16checked/0unchecked; independent source/visual reports привязаны к16fileSHA256manifest и перечитываются после финального исправления. Каждый текущий source/base SHA, GitHub gates и release проверяются отдельно; исторические31a checks не допускают новый коммит.

Реальные платежи/возвраты/письма/согласия/ручные права не выполнялись. GRAF Dev занят другим срезом; установленная/финансовая/человеческая приемка T011/T012/SC005/006 не заявляется. Чужой опубликованный04.4 и его архив сохранены. После ordinary merge единый оператор проводит новый frozen release-full, GO, CD dry-run/execute, public release и live read-only обеих страниц; public native assets должны сохраниться побайтово.

## Точные команды T060

```sh
# Из apps/server, existing .venv
uv run --extra dev pytest tests/contract/test_payment_history_support.py tests/contract/test_billing_ui.py tests/contract/test_billing_purchase_ui.py tests/contract/test_billing_safety_contract.py tests/contract/test_account_merge_contract.py tests/contract/test_fair_use_ui.py tests/unit/test_billing_copy_and_redaction.py -q --tb=short --show-capture=no
BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-t060-chromium uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
GRAF_BROWSER=webkit BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-t060-webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
# Из корня, одноразовый PostgreSQL
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_clarity.py tests/integration/test_billing_purchase_journey.py -k 'invoice_projection or support_help_fallback or completed_purchase_recovers_late_receipt or paid_refused_renewal_recovers_receipt or invoice_hides_receipt_refresh' -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_clarity.py -k support_help_fallback -q --tb=short --show-capture=no
GRAF_PAYMENT_RETURN_BROWSER=1 apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
```

## Исправления подготовки PR после первых GitHub запусков

Первый source fast37176174993 остановился на лишней пустой строке в конце нового requirementsreport; reviewerowner удалил ровно один newline, содержание16/0 неизменно. Новый requirementsreportSHA256cf54be0cce38fe4faf8a666aad1192b13d0aeb0723c50fe71c37b4a290fb07a1 заменяет прежний85bad только для этого форматирования. Прежние отчеты/rootreceipts сохраняются как история. Полный gitdiffcheck относительно actualbase и stagednewfiles проходит; initial локальный пустойworkingdiffcheck не покрывал untrackedreport и был недостаточен.

Следующий sourcefast37176355320 дал1FAIL/2287PASS59.24s: существующий unit direct-render emptyhistory передавал толькоsupport_email. Серверные маршруты уже передают отдельный validatedsupport_mailto, но unitfixture отстал. Локальный causalRED1FAIL/1PASS33deselected0.43s; добавлено толькоbuild_support_mailto(email) к rendercontext через существующий helper, прежние assertions/два параметра сохранены. Fulltest_cabinet_audit_fixes35PASS0.20s и RuffPASS. Производственные16bytes неизменны; manifest расширен до17 только этим unitфайлом. Product/browsers/DB повторно не запускаются из-за неизменности кода; GitHubexactnewSHA gates всё равно обязательны.

## Актуальный итог выпуска .04.5

Прежние pending записи выше исторические. Технические ворота T048/T056/T061 подтверждены [итогом выпуска](release-subscription-clarity-closeout.md) и независимыми [subscription](review-subscription-release-final.md)/[invoice](review-invoice-production-final.md) отчетами. Source e50c, exact PR/base checks, authoritative Full37180461213, GO/CD/runtime/live/tag/Release/attestation совпадают. Финансовая/человеческая/installed приемка, T011/T012/SC005/006/F278 остаются открытыми.
