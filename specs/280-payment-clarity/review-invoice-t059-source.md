# F280 invoice/T059 — независимый окончательный обзор кода

2026-10-04. Reviewer `/root/sdd_supplement`, полоса `high-risk-product`. Единственное владение — этот временный отчет вне git. Code/tests/canonical/checklist/другие reports/Git/GitHub/releases/deploy не менялись; наборы reviewer не запускал.

**SOURCE LOGIC PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Заключение относится к прочитанным замороженным десяти файлам и логике combined invoice/T059. Браузерная/визуальная приемка, actual post-merge rebase byte equivalence, exact-SHA/base CI и выпуск остаются отдельными воротами; на первоначальном source заключении новые браузеры еще pending.

## База и область

Прочитан полный owned product/test diff против `dfff7a71829f3bb7266e659b83f2e08f198ac6ff`, текущий local HEAD `3c18962a24954a55e60feb9a7c6c66f6b477eabb` плюс owned рабочие T059 правки. Actual7506merge `b3316ec3ba8c3ae1a4262b38eeafd2b344d2c18d` ожидает metadata rebase; его фактическая byte equivalence в этом первоначальном заключении не заявлена. Применен `$code-reviewer`; перечитаны действующие T059 canonical требования и независимый invoice checklist/requirements14/0. Прежние source/visual отчеты прочитаны как история на своих байтах, включая ранее закрытый boundary defect S001; их PASS не перенесен на текущий SHA автоматически.

Ten-file diff состоит из invoice/helper/read projection/узких CSS/status class/subscription glyph и относящихся support/browser/DB тестов. Ресурсы GRAF собственные; новые внешние assets/dependencies отсутствуют. Конфликт объединения invoice решен сохранением обоих imports, нового класса и открытого service-gap вместе с guarded receipt feedback/form F278. Shared browser сохраняет два разных JS-off цикла: подписка/ограничения и invoice disclosures/помощь; ни один не заменен другим. Canonical/changelog имеет одного writer, reviewer их не меняет.

## Инварианты Python и платежной зависимости

Сравнение нормализованных AST всех top-level функций `billing.py` с parent dfff выявило изменения только `_invoice_period_labels` (новая функция) и `billing_invoice_detail_page` (представление). Денежные функции, query и guarded receipt refresh не изменены. Дополнительно лично сравнены:

| Функция | AST результат | SHA-256 `ast.dump(..., include_attributes=False)` |
|---|---|---|
| `billing_subscription_page` | MATCH | `d4e4263125f20c10b8f6bcccfb9145c1da3d0a1d0dfadbf74210f5217c201e35` |
| `_renewal_notice` | MATCH | `89739713a6b5498cbe06445832a8593bafe0fc9bbe83df4f7feaeecc26872113` |
| `_is_paid_refused_receipt` | MATCH | `651e6359d60c613ca46ffad2230e6551a574847ebdc58fb2a5c243c4baaa3caa` |
| `refresh_billing_checkout_status` | MATCH | `08162ea4984b35aaaae4b514645af1c2ef210499f19278e075a49123fe2ad658` |

Invoice detail сохраняет owner-only/workspace-scoped lookup и прежние service-gap исключения для changed payer. Masked payment/contact и receipt URL доступны только can_manage, URL еще проверяется штатным allowlist/AVAILABLE. F278 can_refresh/can_refresh_receipt query и permission/state/provider/receipt_only guards сохранены. GET строит представление без provider/money мутации; явная receipt форма вызывает прежний защищенный POST наблюдения, а не новое списание/возврат/выдачу доступа. Отсутствие URL не придумывает документ. F278 финансы/human bank acceptance этим source review не переоцениваются.

## Даты, историческая покупка и помощь

`_invoice_period_labels` требует два timezone-aware datetime/ISO значения и start<end, возвращает nullable при некорректной/неизвестной границе. Краткие даты используют viewer-local дату, точные — ту же зону с временем. Catch ValueError/OverflowError вокруг viewer-local форматирования сохранен после S001. Существующие тесты upper9999Z/lower0001+14 и настоящего route200 с immutable financial snapshots прочитаны; нового formatter либо изменения общего `_billing_datetime_label` нет.

Invoice cycle подписывается только известными month/year; неизвестный сообщает «Период не указан». Исторический/будущий invoice не получает active badge текущей подписки. Storage segments сохраняют несколько положительных capacity intervals; для неверных дат появляется «Срок не указан», без выдуманных границ. Booleans не принимаются как byte capacity/discount, процент ограничен1–100. Создание подписано «Дата создания платежа», не settlement. Значимый service_gap вне details.

Общий `_payment_mailto` сохраняет existing refund wrapper/default callers, добавляет собственный статический question subject, проверяет email/safe invoice и encoded CRLF. Адрес percent-encoded с safe `@.` предотвращает query injection из допустимого local-part; subject/body кодируются отдельно. Raw support fallback удален: при invalid address обе ссылки отсутствуют и есть действующая помощь. В mailto только проверенные support/ref/static text, без карточки/provider IDs/meeting content. Открытие письма не отправляет запрос и не оформляет возврат; автопродление отдельно.

CSS scoped `.billing-invoice-page`:720px, компактные card gap/padding/row и bounded margins/list; глобальные настройки/подписка/status правила не изменены. Status diff — единственная замена dl класса на `billing-order-summary`, без изменений data/status/live regions/форм/лимитов/poll JS/финансовых слов. Новый visual gate принадлежит отдельному reviewer.

## T059 точные изменения и тестовые ограничения

Receipt текст нормализован к «е»; прежние condition/form action/method/CSRF/quiet submit сохранены. Subtemplate сравнено побайтово с parent после единственной replace «Проверить платёж»→«Проверить платеж»: MATCH. Три exact CJS selector literals адаптированы к этой подписи; URL/порядок/assertions/guards прежние. Pending notices/three truthful cycle uses T058 не меняются.

Support contract теперь проверяет фактический rendered HTML для missing can_refresh_receipt, false, unavailable+false и true; count0 либо1. Единственная форма должна иметь exact `POST /billing/checkout/status/INV-SYNTHETIC/refresh?return_to=invoice`, hidden csrf единственным именованным input, один submit «Проверить чек». Наличие других форм или formaction не допускается; секция помощи вообще не содержит form/submit, refund API отсутствует. Это осмысленный whitelist, а не ослабление запрета новой оплаты ради зеленого теста. True+receipt-refresh-failed может сохранять законную кнопку повторного наблюдения по настоящему can_refresh_receipt — это отдельный серверный guard, не денежный retry.

Добавленные DB25 invoice проверки охватывают viewer-local/historical/future/boundary/invalid/noURL/privacy/storage/support/correct discount, до/после billing_rows_snapshot одинаков. Browser fixtures используют actual templates/CSS/shell; native disclosures/copy synthetic stub/question/refund href и JS-off не отправляют внешнюю почту/денежные POST. Existing consent/CSRF/quote/authority guards/assertions и120s предел сохранены. Дополнения расширяют ширины до390, не убирая320/360/768/1280; themes/100/200%/targets/contrast/keyboard прежние.

## Фактически прочитанные доказательства

- Причинный `f280-invoice-t059-red.log`:3 failed/80 passed,0.20s — blanket form и две copy страницы; разрешенная F278 форма не должна удаляться ради старого теста.
- `f280-invoice-combined-contract.log`:1 failed/114 passed,0.53s, старый blanket no-form assertion. Координатор также сообщил промежуточную ошибку undefined synthetic fixture во время правки теста; отдельный ее журнал reviewer не прочитал, поэтому она не заявлена как независимо повторенный product дефект. Текущий rendered negative fixture и final terminal перечитаны.
- Окончательный `f280-invoice-t059-green.log`: **186 passed,2 warnings,0.59s**. SHA-256 log `92c064967939683fc73bdbae6d00fd0317ed1d36959a4da474bd5cbbb24750ad`.
- `f280-invoice-combined-db.log`: **74 passed,83 deselected,2 warnings,54.09s**, runner59s, cleanup isolated_container_removed; collection digest `ca5f807ccc7f29fc3a867b50de3f342d494e65bc201fdb5d719342cdbaf46dc7`, result pass. SHA-256 log `231b1f9c50bcd927b090294630a321dcad714cfa31e9c16b757401982e0715f2`. Набор25invoice+49F278 selected выполнен до text/guard-test/sub glyph поправок; денежный/read projection/DB код неизменен, но результат честно не называется post-fix повтором всех current bytes.
- Окончательные combined Chromium/WebKit16×2 в момент первоначального source заключения ожидались. Их текущие terminal результаты приведены в узком дополнении ниже; первоначальная ожидательная запись сохранена как история. Actual rebase equality еще не подтверждена.

## Прочитанные замороженные SHA-256

Все десять файлов лично сверены с `f280-invoice-combined-final-hashes.json`; они остаются фактическим source gate, пока не меняются байты.

| Путь | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/refund_email.py` | `abf37fbc463143c4b5f1d354713b55a22f757381500d1a008a6c802a4447282b` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `59db39d4a4f1b6f7ba64f97f9725997a491bbd0ccd73ae2e0c819d55a6ee45ac` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html` | `d59cc28d1608f1dd3f3783f2d8a621503b80f4fcdb836ab888f4bad7fbf3f9a4` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `fedac5cd47b383c0ac7479b509ac6b7d3c5ac48064462cd9bba2e971c0c6f9a9` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `34523d26edfff86ccd9044c70013ccd392fbbd716b5221411e77f8ef15f38aa8` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `144b3649d73a02cf5b6634bc80c87b6e9162433aa561f2346a6739a9568e752d` |
| `apps/server/tests/contract/test_payment_history_support.py` | `76dec3bcf3ee0afc5bc4a7e39accc47fd6857c96171e046755fc14070f17f44c` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `9ff3421aef4e5b0a04f5bffdb97f59b0607b9a42bdb127cb2793e04cdd46162c` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `0323a33b53baf743bb6d2763db98fd607a1bdc5a7be514c357405359ce113d7a` |
| `apps/server/tests/integration/test_billing_clarity.py` | `8a7fca155a15cef6aa9aad3d8a474e7fa008747b955b1352e75193f5d4102450` |

После записи reviewer перечитал отчет, повторно сверил10fingerprints и AST инварианты; дрейфа0, `git diff --check` owned app diff прошел. Открытых source findings0. Исторические и текущие допуски разведены; source PASS не заменяет exactSHA/base PR/currentCI/merge/frozen release-full/CD/live, установленный Dev и человеческую/финансовую приемку. Дальнейшее узкое дополнение разрешено по terminalbrowser/equivalence сигналу.

## Узкое дополнение окончательных браузеров — 2026-10-04

По новому terminal signal reviewer лично прочитал оба current combined browser logs и исторический timeout WebKit:

| Набор | Фактический terminal результат | SHA-256 журнала |
|---|---|---|
| `f280-invoice-combined-chromium.log` | 16 passed,2 warnings,63.49s | `a51251bb6ef17432372cfefa2973208a2b3909dc194c93011c7f0e088d178c4c` |
| `f280-invoice-combined-webkit.log` | 16 passed,2 warnings,97.35s | `315582a332081132e0363b4a10778b8f326c88b2c6dbc3bc949bdf577890f7b4` |
| `f280-invoice-combined-webkit-timeout-history.log` — история | 15 passed,1 failed,120.67s; внешний subprocess TimeoutExpired120s в общем keyboard browser case | `2aad5e8024952a9d7c7c2cecd39450659cd9ead190185c5b9f4fbc0160ce2953` |

Повтор WebKit прошел с тем же120s пределом/утверждениями; десять product/test hashes снова лично вычислены и совпали с final manifest, дрейфа0. Исторический timeout не скрыт и не подменен нынешним PASS. Эти terminal результаты подтверждают выполнение synthetic combined браузерных наборов; отдельное независимое визуальное заключение не подменяется чтением журналов.

После дополнения отчет перечитан и все десять fingerprints в его таблице повторно совпали. Исходный **SOURCE LOGIC PASS0CRITICAL/0HIGH/0исправимыхMEDIUM** сохраняется без нового исследования логики; current browser tests больше не pending. Actual post-merge rebase byte equivalence, exact-SHA/base CI/merge и frozen release-full/CD/live остаются pending, их PASS не присвоен. Reviewer изменил только этот временный отчет, suites не запускал.
