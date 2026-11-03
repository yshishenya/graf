# F280 invoice/T060 — независимый итоговый визуальный и браузерный обзор

2026-10-04. Workspace `/Users/yshishenya/.codex/worktrees/billing-simple/crisp`; HEAD `31a9e7c8b3eb2695d416e94171b6729121e42744` с рабочим T060 diff. Reviewer `/root/ux_research`, distinct от source/DB reviewers. Ownership только `/tmp/f280-invoice-t060-final-visual.md`; tracked файлы/код/тесты/canonical/checklist/чужие reports/Git/GitHub/release не меняются. Lane high-risk-product, активный F280, FR049/052/SC016/017, T060/#7534.

**FINAL VISUAL/BROWSER PASS — 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM** в проверенной области. Оба browser лога завершены: Chromium16passed62.29s; WebKit16passed73.83s на неизменных final templates/CSS/JS/fixtures до последнего helper C0/DEL guard; текущий guard отдельно подтвержден новыми contracts/actualGET ниже. Все 16 конечных product/test fingerprints совпали с manifest. Никаких новых suites, privateprod/screens/payments/Dev действий reviewer не выполнял. Current exact-SHA/base CI/actual rebase/release-full/live — отдельные доказательства.

## Что проверено и почему интерфейс остаётся понятным

Лично прочитан current REQUIREMENTS PASS16checked/0unchecked: старые14/0 T059 notes сохранены исторически, T060 добавляет CHK015/016. Перечитаны T060 spec/plan/contract/quickstart, четырёх template diff и shared helper/передача контекста; строгий account_merge filter остается более узким, чем общий billing parser. Invoice layout/CSS/template и subscription template совпадают с ранее принятой компактной версией; изменена безопасная помощь в существующих представлениях, а не структура покупки.

History показывает обычный читаемый normalized адрес и copy value; закодированный URI используется только в href. Display-name нормализуется в plain address там, где это уже допустимо. Plus/процент/URI delimiter local-part не становится query/fragment ссылки: shared `build_support_mailto` кодирует destination c safe @/точкой. Формирование question/refund переиспользует тот же destination, статические разные темы и прежний safe invoice guard; внешнее письмо автоматически не отправляется.

При missing/malformed/CRLF/encoded CRLF shared projection дает отсутствие mailto/copy, raw config не выводится. History завершается сообщением «Контакт поддержки пока не настроен. Обращение из этого раздела сейчас недоступно» и ссылкой «Вернуться к тарифу и оплате»; status использует безопасный `/billing/history#billing-help`. Referrals/fair-use не получают неподтвержденную поддержку. Поэтому invoice fallback ведёт к конечному понятному состоянию даже при checkoutfalse/observation-only, а не к сырой mailto строке. Account_merge сохраняет прежний запрет display-name и auth/решения; encoded href не расширяет права.

Лично осмотрены 7 свежих PNG обоих движков: history320dark/1280light с plain contact/copy; referrals320light/1280dark с доступной secondary поддержкой; status succeeded_refused320dark с честным service gap; invoice receipt1280light/help focus и long intervals320dark. Текст/переносы читаются, информация не выходит горизонтально, focus и controls видны, денежная помощь не выглядит успешным возвратом. Screenshot содержит normal synthetic support@example.test: malformed/encodedURI и fair-use/account_merge правила подтверждают template/contract/realGET evidence ниже, а не фотография несуществующего кадра. Новый screenshot для этих состояний не создавался reviewer.

| Файл | SHA-256 |
|---|---|
| `/tmp/f280-invoice-t060-chromium/history-320-dark.png` | `0e002ba54a1b97a09cb7f8d6d153594b33f8c0d69fb6adf0a79f57e16d7541c1` |
| `/tmp/f280-invoice-t060-webkit/history-1280-light.png` | `292cc1f77d0d48fe5ea34cc44fd3cb8ecf5f21b92f92f00b7108ffa21bb08600` |
| `/tmp/f280-invoice-t060-chromium/referrals-320-light.png` | `6072fbaef33540938f9c569adb9332ccf66a318a8cf866588b58a5b865ff0384` |
| `/tmp/f280-invoice-t060-webkit/status-succeeded_refused-320-dark.png` | `cdbd19edc56e8d415df4709e2074cb9503d324cfe5e61350f74863ec1e7e911d` |
| `/tmp/f280-invoice-t060-chromium/shell-invoice-receipt-1280-light.png` | `347cc5b8eeeb371c8bb80adc352fb9856aeef8c2f5e7e19044877691008624cc` |
| `/tmp/f280-invoice-t060-webkit/shell-invoice-intervals-320-dark.png` | `b98015f4de6cda6dfd7062ec33071d365454668220e4e91325cf199c801ceead` |
| `/tmp/f280-invoice-t060-webkit/referrals-1280-dark.png` | `f528223ba9908fb29f21044743a9916f0d7c7395b5e02e9468638c1594336350` |

## Прочитанное актуальное evidence

- Chromium полный16PASS62.29s и WebKit полный16PASS73.83s, terminal logs прочитаны лично. Внешний Python subprocess теперь300s; это только enclosing budget. CJS SHA0323a33... совпадает с ранее принятой версией, per-action assertions и ограничения не изменены. Product HTTP15s/automatic60s/attempts не расширяются изменением enclosing timeout; технический source reviewer проверяет их отдельным обзором.
- Current actualGET regression имеет 14 case: 7 contacts×observationFalse/True при checkoutfalse, protected invoice fallback и history/status/referrals/web+desktop fair-use. Лично прочитаны сохраненные billing rows snapshot assertions, encoded destination/plain copy/query empty/no raw invalid/no copy и status200 по всем paths. Current isolated DB log **88passed/83deselected78.96s**, runner83s/resultpass/cleanup isolated_container_removed. Это результат исполнителя, прочитанный reviewer; не собственный запуск. Account_merge stricter policy имеет отдельный contract и source evidence, не объявляется входящим в перечисленные 14 GET cases.
- Current source contract лог84PASS0.34s и copy contract2PASS0.02s прочитаны. Template contract четырёх страниц проверяет invalid и encoded '?' destination, query empty и отсутствие raw invalid/copy; shared normalize/URI contract покрывает plain display vs encoded href; account_merge contract сохраняет header/query safety и strict filter.
- Существующие accessibility assertions остаются:320/360/390/768/1280 × обе темы ×100/200%, контраст/overflow/targets/focus/nativecontrols; subscription и invoice JS-off loops сохранены, без внешнего provider/mail.200% подтвержден current assertions и complete PASS, не PNG100%. Исторические timeout логи T059 остаются историей и не выдаются за final success.

Browser fixture, template render и actual protectedGET проверяют разные границы. PNG не подтверждает реальный provider, финансовый результат или private production. Malformed-config ветки не запускались в production; only synthetic fixtures/isolatedDB. Сохранённая guarded receipt-only conditional форма/copy/helper/invoice privacy из T059 не удалены этим исправлением.

## Применимость и отпечатки

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

| Файл | SHA-256 |
|---|---|
| `/tmp/f280-invoice-t060-chromium.log` | `4e672f28903e23f9882bf1af870e33810de0e474232699ab7b5fd37c896fc6c1` |
| `/tmp/f280-invoice-t060-webkit.log` | `58e2251a8d25f8165485d1f5759b12105346f24e887a2ddfe7d5b94693239ab0` |
| `/tmp/f280-invoice-t060-db-green.log` | `b8e1c85cfcff314e04d18b254032bfceb9deb6beef65f5eee1c8b8ff9bad2273` |
| `/tmp/f280-invoice-t060-source-contract-green.log` | `a8fc69d637e6748c6c7fd4c123120e23116a5038c7e6a85cb8652802263ab6eb` |
| `/tmp/f280-invoice-t060-copy-green.log` | `64f0e9ee7693792baf26ad57f9154ed84aefd2908647bd0493e6b9cfe67bfeff` |
| `/tmp/f280-invoice-t060-chromium/pages.json` | `dbff4fa2e25276d84be8899a96dee97be0e29bf4c34d4871f666570a46295228` |
| `/tmp/f280-invoice-t060-webkit/pages.json` | `dbff4fa2e25276d84be8899a96dee97be0e29bf4c34d4871f666570a46295228` |
| `/tmp/f280-invoice-t060-final-hashes.json` | `b6263b7862a3dcaf80097647b200a1aef2e223517d28cd7515a0274daecbe886` |

| Файл | SHA-256 |
|---|---|
| `specs/280-payment-clarity/review-invoice-t060-requirements.md` | `85bad12373bde35420470c52f8b91b54d689daaa6c128d35b3bd88c52cb1e3c8` |
| `specs/280-payment-clarity/spec.md` | `61c563b547445b3ecf87320b4c76dc9da4c7f0696f1a4aa4d45d93f44ebbd0b4` |
| `specs/280-payment-clarity/plan.md` | `552d07859133e6cbc13d406d3b8a7b0fa7a5048fc3961b8cd350b74728aac981` |
| `specs/280-payment-clarity/contracts/payment-journey.md` | `d4a978458662267e4c7d48bbbae5b344c959a46d92fed81cbe8331ef57ed4d49` |
| `specs/280-payment-clarity/quickstart.md` | `9cc7e590bf3a79eb728e9935fe9116b852f3006a2cca0668011667d0f409c2df` |


Reviewer перечитал финальный отчёт после записи; все 36 указанных fingerprints повторно совпали; вывод относится к этим фактическим рабочим байтам. Дальнейшие code changes требуют нового применимого evidence; metadata-only rebase допускает отдельное подтверждение file identity. Независимый source/security, exactSHA/base PR CI, frozen release-full/dry-run/execute/live, установленный GRAF Dev, реальная финансовая и человеческая приемка остаются отдельными. Конверсия/возврат/банк/чек/live readiness этим обзором не обещаются. Изменён только данный temp report.


## Узкий окончательный refresh после C0/DEL защиты

2026-10-04. Reviewer лично перечитал последние три файла: shared normalize_support_email и две parameterized contact matrices. Guard до parseaddr отклоняет любой C0 символ (`ord<32`) и DEL (`ord==127`) как в исходной настройке, так и после одного unquote. Новые четыре отрицательных контакта — raw NUL/raw SOH/encoded%00/encoded%7f — дают None destination и отсутствие raw mailto/copy. Действующие plain/plus/query delimiter/display-name положительные cases сохраняются. Это устранение source finding о parser, который мог нормализовать control-bearing display name в допустимый адрес; визуальная иерархия и денежное поведение не меняются.

Лично прочитан новый complete `/tmp/f280-invoice-t060-controls-green.log`: **202passed0.68s**. Лично прочитан `/tmp/f280-invoice-t060-controls-db-green.log`: **22passed/96deselected37.16s**, runner41s/resultpass/cleanupisolated_container_removed. ActualGET matrix теперь11contacts×2observation flags при checkoutfalse, на тех же5sibling paths плюс invoice fallback. Assertions требуют no rawconfig/mailto/copy для отрицательных случаев, safe query-empty destination/plain-copy для положительных, status200 и неизменные billing rows snapshots на каждом GET. Account_merge строгий display-name filter не ослаблен.

Прежний log88PASS в разделе выше относится к более раннему read-only/invoice/receipt набору и не называется повторным прогоном на final guard. Accessibility Chromium16PASS62.29s/WebKit16PASS73.83s получены до последней helper поправки; templates/CSS/CJS/browser fixtures не изменились. После refresh все 16 manifest files совпали; изменение относительно preguard только helper+две tests matrices, остальные 13 файлов стабильны. Поэтому PNG и законченная браузерная доступность применимы к неизменной геометрии/шаблонам/fixtures; rawC0/DEL конфигурации доказываются final helper contracts и настоящимиGET, а не screenshot обычной адресной fixture. Нового browser прогона reviewer не выполнял и не объявляет прежний16×2 тестированием новой control-config ветки.

FINAL VISUAL/BROWSER PASS —0CRITICAL/0HIGH/0исправимыхMEDIUM — сохраняется в указанной области с этой точной границей. Дополнительная полная payment-return56matrix, которую выполняет координатор, ещё отдельное evidence; её результат здесь не предполагается. Final source/security/CI/release/live gates также отдельны. Reviewer менял только данный temp report.

| Файл | SHA-256 текущего refresh |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/refund_email.py` | `37ecc82661b7a5defbaf8cadd1e3420ad17853e25f6bd0be1571cfe1934a3397` |
| `apps/server/tests/contract/test_payment_history_support.py` | `597bea20f985b312e77dee7882d44438bce12ae94d1e383a99097bf6b4fd6b58` |
| `apps/server/tests/integration/test_billing_clarity.py` | `0efa05b8fb9f2b7942bc09256e079d711c854ad50cb11ba4c5fbee9f7949e563` |
| `/tmp/f280-invoice-t060-controls-db-green.log` | `076a2e2bb684ed9c451df101812655cc50586a83e2eefe6aafb8b722735cf2cd` |
| `/tmp/f280-invoice-t060-controls-green.log` | `be65f84771867a58bb9fd1c7b6d5fb09153e17083c7c0cc5a1dca1d15cd47651` |
| `/tmp/f280-invoice-t060-final-hashes.json` | `b6263b7862a3dcaf80097647b200a1aef2e223517d28cd7515a0274daecbe886` |

После записи reviewer перечитал новый раздел: все 16 manifest и 6 refresh отпечатков повторно совпали; предыдущие hash tables сохраняются как зафиксированное историческое evidence.
