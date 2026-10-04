# F280 invoice/T059 — окончательный независимый визуальный обзор

2026-10-04. Reviewer `/root/ux_research`. Workspace `/Users/yshishenya/.codex/worktrees/billing-simple/crisp`, HEAD `3c18962a24954a55e60feb9a7c6c66f6b477eabb` + T059 рабочие изменения. Lane high-risk-product, active Spec Kit slice. Ownership исключительно `/tmp/f280-invoice-final-visual.md`; tracked source/reports/canonical/checklist/Git/GitHub/release не меняются. Отчёт вне git сохраняет проверяемые bytes и не создаёт нового commit.

**FINAL VISUAL PASS — 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Десять конечных product/test fingerprints совпали с `/tmp/f280-invoice-combined-final-hashes.json` до и после обзора. Последовательный повтор WebKit завершился16PASS при прежнем120s пределе; initial timeout сохранён как исторический неуспешный прогон. Byte-equivalence после фактического переноса/слияния пока отдельный следующий шаг; текущие exact-SHA/base CI/release/full/live не объявлены PASS этим обзором.

## Проверенная понятность и согласование

Закрытый invoice1280 показывает короткий заголовок/ссылку истории, компактную карточку720 с назначением покупки, суммой, состоянием, кратким оплаченным сроком, объёмом и чеком. Технические сведения/помощь доступны по одному нативному раскрытию; обычная помощь не выглядит предупреждением. В320 подписи над значениями, длинные значения переносятся; warning service-gap остаётся на виду вне details. Уплотнение по прямому решению владельца «Сделать карточку плотнее» сохраняет gap12/padding16×20/rows8, шрифт и размер целей не уменьшены.

Открытые сведения сохраняют точную локальную дату/зону, дату создания, safe number, маскированный fixture способ оплаты и длинный synthetic контакт. Несколько оплаченных storage интервалов читаются без обрезки. Копирование остаётся отдельным quiet элементом. Документ — ссылка, вопрос/возврат различимы, пояснения не обещают отправку или возврат, автопродление отдельно. Фокус на help ссылки и native раскрытиях заметен. Стандартные кадры открытых сведений местами прокручены вслед за фокусом; header не объявляется исчезнувшим. Closed captures из saved final pages.json подтверждают первоначальное состояние обоих движков.

Сочетания подписки pending+price/contact/generic reason сохраняют одно primary «Проверить платеж», правдивую неопределённость и secondary safe помощь/проверку; повторный checkout/early/resume не предлагается. Наблюдаемая glyph замена «платёж»→«платеж» не меняет URL, порядок, условие или смысл. Year next-charge показывает «за год», expired показывает «Бесплатный» без активного paid badge. Общая геометрия/палитра/фокус согласованы с invoice, но исторический документ не копирует статус активной подписки.

## T059/F278 и пределы изображения формы

Прочитан текущий REQUIREMENTS PASS14/0 в `review-invoice-t059-requirements.md`, spec403–409, planT059, contractT059, quickstartT059, исторические invoice source/visual отчёты. Текущий invoice template сохраняет существующую conditional quiet форму проверки чека только при `can_refresh_receipt`, exact `POST /billing/checkout/status/{safe_number}/refresh?return_to=invoice`, CSRF и status feedback «Оплата остается подтвержденной». Это наблюдение чека, не новое списание/возврат/выдача доступа. Helpers/money permissions оценивает отдельный source reviewer.

Лично прочитан current support contract: rendered None/False/failed/True cases,0или1exact form, единственный csrf input/submit; help секция не получает форму возврата. Contract186PASS подтверждён логом. Лично прочитан focused DB74PASS54.09s/83deselected/runner59/cleanup removed, включая receipt recovery/permission/service-gap cases. DB выполнялся до mechanical copy/testguard/glyph без изменения money/route bytes; поэтому используется как scoped receipt/invoice доказательство с этой явно указанной границей. Не переобъявляется новым финальным release-full.

Просмотренные invoice browser fixture кадры не включают can_refresh_receipt=True; наличие/условность quiet receipt формы подтверждены template/render contract и DB, не фотографией. JS-off invoice0mutation assertions относятся к его fixture чтению/раскрытию, не запрещают законную пользовательскую receipt-only POST. Такое разделение сохраняет F278 без ложного blanket «никаких форм».

## Браузерные доказательства и личный осмотр

Chromium полный combined16PASS63.49s; WebKit initial1failed/15passed120.67s с subprocess.TimeoutExpired после120s. Никакого assertion визуального дефекта initial лог не содержит, но не объявлен успешным. Его лог сохранён `/tmp/f280-invoice-combined-webkit-timeout-history.log`. Полный последовательный повтор без изменения10bytes/assertions/лимита: WebKit16PASS97.35s. Reviewer лично прочитал оба terminal лога и history; собственных suites не запускал. Два warnings среды не являются skips.

Лично перечитаны обе current JS-off loops: root subscription7restriction+5access/cycle GET/Enter/Space/noPOST и invoice3variants native disclosures/document/help/noPOST; обе сохранены. Существующий checkout predselection/optional recurring и обязательная оферта, resume required-unchecked/CSRF/version/quote/cancel проверяются другими сохранёнными assertions. Прямое принятое решение владельца о предвыборе в новом оформлении повсюду этим срезом не меняется.

Текущий CJS проверяет320/360/390/768/1280 × обе темы ×100/200%, overflow/width720/min target24px/contrast/primary reachable; native copy/Space/focus/help.200% доказан current assertions+complete16×2, не PNG100%. Synthetic contacts/cards/invoices только example.test/INV-SYNTHETIC/masked fixture. Внешняя почта, provider, приватный контент и GRAF Dev не использовались reviewer.

Лично осмотрены следующие 13 конечных изображений; дополнительно initialWebKit кадры были осмотрены до timeout, но final PASS основан на успешном repeat и его кадрах:

| Файл | SHA-256 |
|---|---|
| `/tmp/f280-invoice-combined-chromium/shell-invoice-future-closed-1280-light.png` | `541e3ce34d09b169b8ad4211d67c78b376c4f03352b8c5ea9359b3beadb6c211` |
| `/tmp/f280-invoice-combined-webkit-repeat/shell-invoice-future-closed-1280-light.png` | `5edb635d24ff5c2fda4a7afc492f3056a57bc41a3697dd0dc79b5eaf8dee2f34` |
| `/tmp/f280-invoice-combined-chromium/shell-invoice-service-gap-closed-320-dark.png` | `cfe33203eaf89e2dec385d749473bade32ab559dbefeb69d75e852f382f05179` |
| `/tmp/f280-invoice-combined-webkit-repeat/shell-invoice-service-gap-closed-320-light.png` | `2bf86621b2d0d937288f976026650ceb135bf183dd6019191e072ed5d7684e27` |
| `/tmp/f280-invoice-combined-chromium/shell-invoice-receipt-1280-light.png` | `347cc5b8eeeb371c8bb80adc352fb9856aeef8c2f5e7e19044877691008624cc` |
| `/tmp/f280-invoice-combined-chromium/shell-invoice-service-gap-320-dark.png` | `46317aac3f2286d065b244826eed816de54393300345aac5628b4a3992d70733` |
| `/tmp/f280-invoice-combined-webkit-repeat/shell-invoice-intervals-320-dark.png` | `b98015f4de6cda6dfd7062ec33071d365454668220e4e91325cf199c801ceead` |
| `/tmp/f280-invoice-combined-webkit-repeat/shell-invoice-receipt-1280-light.png` | `a243c5799e3072b05fdc2fc2cad6c8a74744d40f59c07e645d63df4bdb516c20` |
| `/tmp/f280-invoice-combined-chromium/subscription-restriction-receipt_contact_required-320-light.png` | `9af6c54d84f13218793382ee3ce885b6a3e15184d2777107be5c6b0cb13cb81f` |
| `/tmp/f280-invoice-combined-chromium/subscription-year-1280-light.png` | `69dc5f85b9550d08a488b0689e43e998091c905a1bea59df4aea38da981f4b83` |
| `/tmp/f280-invoice-combined-chromium/subscription-expired-320-dark.png` | `8d02fb6217e7ded088b494aab282958d2b6e2f7e974f6453ec21a8a61954a30f` |
| `/tmp/f280-invoice-combined-chromium/subscription-restriction-price_changed-1280-dark.png` | `f99a19e5b9b73cedd6c92e832e93685efafd82d59dffb60f1ebd634d3e89d6ae` |
| `/tmp/f280-invoice-combined-webkit-repeat/subscription-restriction-receipt_contact_required-320-light.png` | `90d0e7f23e2e874cfb68855c6be04dc35234280adbb73a1f1aeba66826b5b917` |

## Текущие отпечатки и итоговые границы

| Файл | SHA-256 |
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

| Файл | SHA-256 |
|---|---|
| `/tmp/f280-invoice-combined-chromium.log` | `a51251bb6ef17432372cfefa2973208a2b3909dc194c93011c7f0e088d178c4c` |
| `/tmp/f280-invoice-combined-webkit.log` | `315582a332081132e0363b4a10778b8f326c88b2c6dbc3bc949bdf577890f7b4` |
| `/tmp/f280-invoice-combined-webkit-timeout-history.log` | `2aad5e8024952a9d7c7c2cecd39450659cd9ead190185c5b9f4fbc0160ce2953` |
| `/tmp/f280-invoice-t059-green.log` | `92c064967939683fc73bdbae6d00fd0317ed1d36959a4da474bd5cbbb24750ad` |
| `/tmp/f280-invoice-combined-db.log` | `231b1f9c50bcd927b090294630a321dcad714cfa31e9c16b757401982e0715f2` |
| `/tmp/f280-invoice-combined-chromium/pages.json` | `dbff4fa2e25276d84be8899a96dee97be0e29bf4c34d4871f666570a46295228` |
| `/tmp/f280-invoice-combined-webkit-repeat/pages.json` | `dbff4fa2e25276d84be8899a96dee97be0e29bf4c34d4871f666570a46295228` |
| `/tmp/f280-invoice-combined-final-hashes.json` | `4d456fb224bd69503b81c1c273a09ccd04765b2538123428b5b86eb17d6ed691` |

| Файл | SHA-256 |
|---|---|
| `specs/280-payment-clarity/spec.md` | `2c447b13d08064d77b9fd7657252cb9c96438bed9e8c763f9e8520f3230883e5` |
| `specs/280-payment-clarity/plan.md` | `5f75a2932b18aa4a2083d847815033ae45408ce3f8e3c47f8bfd30a2b692119b` |
| `specs/280-payment-clarity/contracts/payment-journey.md` | `48b6d3f514f16c32b9c3e283a1c55a9c5d2405bc1358bb1c1b257c70d6d6cdf1` |
| `specs/280-payment-clarity/quickstart.md` | `d5b0de1efeb1382f68ffbd4ae75df649c40141a8ed6c7a46d8ae5bec4824ae02` |
| `specs/280-payment-clarity/review-invoice-t059-requirements.md` | `67237dd4ee693bfbb2a497dc7de85d054851217276423ebe7b6b163196ce110f` |


Документ перечитан после записи; все 36 отпечатков перечисленных source/test/log/pages/PNG/docs повторно совпали. Coordinator сообщил closedcapture terminal exit0 для обоих движков; лично осмотренные четыре closed кадра доступны в final artifact dirs. Проверка 10 файлов final manifest снова совпала. Новых применимых визуальных замечаний не обнаружено. Source/security reviewer, actual rebase byte-equivalence, current PR exact-SHA/base checks, общий frozen release-full, deployment/live, установленный GRAF Dev и человеческая/реальная финансовая приёмка остаются отдельными доказательствами. Конверсия или эффективность реальных оплат этим обзором не обещаются. Старые tracked reviews сохранены как история, новые bytes/repeat evidence зафиксированы здесь.
