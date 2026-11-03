# Независимый финальный обзор исходников T060

Reviewer `/root/sdd_supplement`, 2026-10-04. Workspace `/Users/yshishenya/.codex/worktrees/billing-simple/crisp`. Единственный изменяемый reviewer файл — этот отчет; продуктовые файлы, canonical документы, Git/GitHub/release/deploy read-only. Другие исполнители работают одновременно, их изменения сохранены.

## Текущий результат

**SOURCE PASS: critical0 / high0 / исправимых medium0.** Первоначальный единственный medium по управляющим символам устранен; reviewer перечитал окончательные helper/tests, воспроизвел negative/positive проверки и сверил новый manifest16/16. Требования16/0 сохраняются. Source PASS не заменяет текущие CI/merge/release/live ворота.

Историческое замечание: первоначальный `billing/refund_email.py:11–17` проверял только decoded CRLF перед `parseaddr`. Прежняя функция допускала `\x00 <support@example.test>`, `Support\x01 <support@example.test>` и `Support%00 <support@example.test>`: все три дают нормализованный `support@example.test` и активный `mailto:support@example.test`. Reviewer воспроизвел это чистым вызовом helper под текущим Python3.13, без suites/почты/сетевых действий/записи продукта. Parser убирает имя, поэтому regex адреса не обнаруживает исходный управляющий символ. Spec414 требует не создавать ссылку для управляющих символов. Узкое исправление: отклонять C0/DEL в исходной и однократно decoded строке до разбора, сохраняя допустимые специальные символы локальной части; отдельные shared/real GET negative regression cases. Root был уведомлен. Финальный helper теперь до parseaddr отвергает любой C0/DEL в value + unquote(value). Новые четыре отрицательных параметра добавлены в shared contract и actualGET matrix. Reviewer повторно чистыми вызовами проверил исходные и encoded NUL/SOH/DEL: нормализация/mailto/account_merge→None; positive billing?cc=evil&tag и billing+tag%box сохраняют plain адрес, encoded URI без query/fragment и прежнюю strict account_merge policy. Display-name разрешен общему billing parser и остается запрещен account_merge. Замечание CLOSED по source/RED/GREEN/realGET evidence, без изменения canonical или финансового поведения.

## Границы исходников и текущая применимость

Полный owned diff рассмотрен относительно base `50e96292d96e36993436524c85829153feb27027`; T060 отдельно относительно HEAD `31a9e7c8b3eb2695d416e94171b6729121e42744`. T060 на момент финального чтения находится в dirty tree; это source review текущих bytes, не exact committed SHA/CI/merge. 16-file manifest `/tmp/f280-invoice-t060-final-hashes.json` перечитан после Ruff import-only коррекции и окончательного C0/DEL исправления,16/16MATCH. Включает прежние invoice/subscription/CSS/CJS bytes вместе с T060. Изменение любого из этих bytes требует обновления применимости этого отчета.

AST comparison всех верхнеуровневых функций route модулей относительно31a: изменены только billing_checkout_status_page, billing_history_page, _configured_support_email, account_merge_blockers, _render_fair_use_page, referrals_page. Относительно50e дополнительно изменена только invoice projection billing_invoice_detail_page и добавлен _invoice_period_labels. Финансовые POST, refresh guards, subscription query/recovery, quoted purchase helpers, auth/merge decision functions не менялись. Imports добавляют общий helper; route изменения только в аргументах шаблонов. Account merge blocker action URI заменен безопасным destination, subject/reference/self-service/default branches сохранены. Новые модели/API/зависимости/flags/config startup policy отсутствуют.

## Прослеженные контакты и URI

- `normalize_support_email` отклоняет raw/decoded C0/DEL, затем переиспользует существующие parseaddr/regex и возвращает обычный адрес либоNone. `build_support_mailto` применяет quote(address,safe='@.'): вопросительный знак, амперсанд, плюс, процент и другие допустимые локальные символы не создают URI query/fragment.
- `_payment_mailto` получает только safe destination, затем прежнюю safe invoice reference и прежние subject/body. Вопрос и возврат различаются только статическим subject_prefix. Invoice/history invoice rows используют validated builders, ValueError →None. Номер, чека/private payer guards и финансовая истина сохранены.
- History и status render contexts отделяют normalized `support_email` от encoded `support_mailto`; history показывает/копирует plain адрес только при обоих значениях. Status помощь использует safe href либо действующий history#billing-help. Нет raw URI fallback.
- Referrals и fair_use, включая desktop fair_use, передают тот же normalized/encoded pair и шаблоны используют encoded href. При invalid/missing ссылки нет; другие существующие действия/права сохраняются.
- Account_merge `_configured_support_email` возвращает адрес только при `address == (value or '').strip()`. Display-name/несколько адресов не становятся допустимыми. Без разрешенного контакта blocker дает прежний settings fallback; safe reference AM и статический subject не содержат email/внутренних IDs/meeting content. URI local-part теперь encoded. Сохраненный negative test_display_names остается неизменным.
- Полный `rg billing_support_email` проверен: raw значения в billing plans/purchase contexts не используются для mailto/copy в соответствующих templates; invoice context также не имеет raw fallback. Worker notification_copy получает настройку в существующий plain-text текст, не URI/копирование; unchanged вне scoped пяти presenters. Config.py прежний enabled-billing guard не меняется. В templates/renderers новых raw `mailto:{{ support_email }}` не осталось.

## Общий бюджет и прежний invoice срез

T060 CJS diff относительно31a пустой. В browser contract единственное изменение исполнения — subprocess timeout120→300; две synthetic context вставки support_mailto сохраняют прежнее доступное действие помощи. Нет снижения assertions/action timeout5s/HTTP15s/window60s/attempts или разбиения/config. Полный baseline CJS diff добавляет invoice native keyboard/copy/mailto/receipt/720-width checks,390px ширину и JS-off3invoice states; прежние утверждения не удалены.

Полный invoice diff сохраняет can_refresh_receipt exact receipt-only POST/CSRF/conditional visibility, доступ владельца и private payer receipt/method/contact. Новые даты имеют short/exact local representation, unknown/reversed/naive/extreme guard; service_gap/recovery не скрываются; nonzero true discount и cycle only month/year. CSS только invoice width720/resetdd/backlink, без global subscription/checkout политики. Subscription manifest byte сохранен с предыдущей narrow glyph correction, дополнительных T060 изменений нет.

## Проверки и ограничения доказательств

Прочитаны реально существующие логи, не запускались reviewer suites:

- `/tmp/f280-invoice-t060-contract-red.log`:14failed/12passed0.18s — unsafe URI/templates/account_merge причинный RED.
- `/tmp/f280-invoice-t060-db-red.log`:10failed/4passed17.65s/runner22s, isolated cleanup — настоящие GET help при checkoutfalse/observationFalse/True.
- `/tmp/f280-invoice-t060-contract-green.log`:259passed0.72s; `/tmp/f280-invoice-t060-source-contract-green.log`:84passed0.34s; `/tmp/f280-invoice-t060-copy-green.log`:2passed0.02s.
- `/tmp/f280-invoice-t060-db-green.log`:88passed78.96s/runner83s, isolated_container_removed. Scoped invoice25 + support14 + F27849; billing snapshots equality и owner fixture `YooKassaClient` fail-on-contact, реальные invoice→history/status/referrals/fair_use/desktop GET. Strict account_merge проверяется pure blocker/существующими contract regressions, новый actual account_merge auth mutation не запускался.
- `/tmp/f280-invoice-t060-chromium.log`:16passed62.29s. `/tmp/f280-invoice-t060-webkit.log`:16passed73.83s, терминальный лог прочитан reviewer после завершения. Это browser fixtures до control correction; их применимость основана на неизменных a11y template/CSS/JS/fixtures и обычном safe synthetic support адресе, а не на отрицательных новых contact случаях.

Первоначальные наборы не охватывали C0/DEL display-name пробел. После correction reviewer прочитал `/tmp/f280-invoice-t060-controls-red.log`:4failed/9passed0.10s (четыре точных новых случая); `/tmp/f280-invoice-t060-controls-green.log`:202passed0.68s; `/tmp/f280-invoice-t060-controls-db-green.log`:22passed/96deselected37.16s/runner41s, isolated cleanup. Новая реальная GET матрица повторяет все11support вариантов в двух observation состояниях и сохраняет snapshots/provider fail guard. Final а11y fixtures/CJS/templates/CSS/runner не изменились при correction; normal synthetic support email не содержит rejected controls, его URI/текст после correction совпадают. Поэтому terminal16+16 browser evidence применим к неизмененной матрице оформления; control-specific proof дают новые202contracts+22actualGET. Root дополнительно выполняет отдельную полную statusmatrix обоими движками; ее future PASS здесь не объявлен. Logs не сами по себе доказывают полный current SHA/base CI или deployed state. Production flags/данные, реальные платежи/письма/возвраты, человеческая приемка/installed GRAF Dev reviewer не проверял и не изменял.

## Отпечатки окончательной просмотренной версии

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/refund_email.py` | `37ecc82661b7a5defbaf8cadd1e3420ad17853e25f6bd0be1571cfe1934a3397` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `5a9b6356db31644fb3bbfd1c523d64f3c1ccac10c25e9d80cf981c093b9d254e` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html` | `d59cc28d1608f1dd3f3783f2d8a621503b80f4fcdb836ab888f4bad7fbf3f9a4` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `7b4a66abcdf5665f5ab703dc58f4de057ceafce111ba8f96cc677ee6ac5ac71a` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `34523d26edfff86ccd9044c70013ccd392fbbd716b5221411e77f8ef15f38aa8` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `144b3649d73a02cf5b6634bc80c87b6e9162433aa561f2346a6739a9568e752d` |
| `apps/server/tests/contract/test_payment_history_support.py` | `597bea20f985b312e77dee7882d44438bce12ae94d1e383a99097bf6b4fd6b58` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `8a000b09b7e975c12f426f7e98e781d283c2c980d0afef3cfcfd6a2f490b1fbc` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `0323a33b53baf743bb6d2763db98fd607a1bdc5a7be514c357405359ce113d7a` |
| `apps/server/tests/integration/test_billing_clarity.py` | `0efa05b8fb9f2b7942bc09256e079d711c854ad50cb11ba4c5fbee9f7949e563` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html` | `63febd67a39a6018df4853c986bae4029fd7691f4a62749b58a4a9170b623a0e` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/referrals.py` | `bb57616e1f23c48e7ac73bf303baff8fcec775be6d7075e40b3c6ee5bd8ad542` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/referrals_content.html` | `2fb1eaf8c639850274d5f66b9ab5d62dcc2db7a6976b55a36323200b2b4f1604` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/fair_use.py` | `d4357442d8abfd4430f3f3e478046e2aa5b09a3e2bab8d981e69409513e08c64` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/fair_use_content.html` | `757c47cb9f92892f8a688f2d0db8993df7cf8691108c94b29d01c23a1d12defb` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py` | `306adcdc212b3cbd4ec1b5a06abfe79870935e19d2fd038ee21912013ba6f2c3` |


Финальный reread отчета и manifest:16/16MATCH; незакрытых SOURCE findings0/0/0. Изменен только этот внеgit отчет. Любой последующий product/test byte change требует refresh применимости.

## Узкое дополнение: данные direct-render unit test после actualfast

2026-10-04, независимый read-only обзор перед test-only commit. На момент просмотра HEAD `5e38bff3aaea02d988b7028f155ff94d1773c4cd`; dirty только `apps/server/tests/unit/test_cabinet_audit_fixes.py`. Root сообщает GitHub actualfast37176355320:1FAIL/2287PASS; этот GitHub run лично reviewer не загружал, его результат здесь атрибутирован root. Локальный причинный лог прочитан лично: `/tmp/f280-invoice-t060-unit-context-red.log` —1failed/1passed/33deselected0.43s, единственный отказ valid support@graf.test из-за отсутствующего support_mailto в прямом synthetic render context.

Diff только названного unit файла добавляет локальный импорт существующего build_support_mailto и аргумент `support_mailto=build_support_mailto(email)` в render_template. Это соответствует настоящему route projection: передает обычный адрес и отдельно encoded destination. None остаетсяNone; допустимый support@graf.test дает прежний expected mailto. Ни продукт, ни template safety guard ради теста не меняются.

AST comparison с HEAD: изменена только функция test_empty_history_has_real_help_or_honest_unavailable. Все **7 assertions совпадают**, параметры `[None, "support@graf.test"]` и decorators совпадают; проверки наличия realhelp, unavailable текста и запрещенного invitation не ослаблены/не удалены. Другие unit функции неизменны. Terminal `/tmp/f280-invoice-t060-unit-context-green.log` прочитан: **35passed0.20s**, две прежние предупреждающие записи; suites reviewer не запускал.

Новый manifest `/tmp/f280-invoice-t060-final-hashes.json`: **17/17MATCH = прежние16/16 побайтно неизменны + один новый unit файл**. Прежний SOURCE0/0/0 и source/browser/DB применимость к16 файлам сохраняются; новый unit file SHA-256 `6d4763abbc5755b3d73769160deaf67ea78eebfbc8be5afa0921a4c409ab0e27`. Это поправка только тестовых данных, без изменения assertions, параметров или исполнения продукта.

**NARROW SOURCE PASS: critical0 / high0 / исправимых medium0.** После дополнения reviewer перечитал diff, оба terminal logs и17manifest. Этот PASS не объявляет старый actualfast успешным, не заменяет будущий новыйSHA/base CI, слияние либо выпуск. Reviewer изменил только это дополнение внеgit отчета; tracked code/spec/tasks/checklist/Git/GitHub read-only.
