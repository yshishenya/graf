# F280 T058 — независимый браузерный и визуальный обзор

2026-10-04. Reviewer `/root/subscription_browser_final`. Полоса `high-risk-product`, продолжение F280, T058 / issue #7527. Ownership только этот новый отчет; прежний выпускной отчет, код, проверки, требования, checklist, Git/GitHub, платежи и выпуск reviewer не меняет. Повторные наборы проверок не запускались. Другие участники работают в этой копии; их изменения сохранены.

**BROWSER/VISUAL PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM замечаний к проверяемой поправке T058.** Оба окончательных браузерных набора завершились до заключения. Оно относится к зафиксированным рабочим байтам и синтетическим состояниям; текущие CI/PR, production, реальные деньги и понимание каждым пользователем этим отчетом не подтверждаются.

## Независимая проверка окончательных доказательств

Самостоятельно прочитаны task handoff, final freeze и manifest; текущие spec/plan/tasks/quickstart/contract с T058, шаблон и его diff, Python browser fixtures, CJS assertions, UI/реальные GET проверки, отчеты требований и исполнителя. Применены `web-design-guidelines`; прочитана свежая копия Web Interface Guidelines `/tmp/f280-t058-web-interface-guidelines.md`. Другие независимые source/UX заключения учитываются как отдельные доказательства, а не заменяют личный осмотр.

HEAD на момент проверки: `8638348d13ab400323358def59ec2b9aee3e2902`. T058 еще находится в рабочих байтах, поэтому заключение связано с SHA-256, а не объявляет этот HEAD содержащим поправку. Product diff только в шаблоне подписки. CSS, JS и route неизменны.

Лично прочитаны окончательные terminal логи:

| Набор | Окончательный результат | Лог |
|---|---|---|
| Полный UI contract | 100 passed, 0 failed, 0 skipped; 0.71 с | `/tmp/f280-t058-contract-green.log` |
| Полные PostgreSQL regression + return | 254 passed, 0 failed, 0 skipped; pytest 232.81 с, runner 238 с | `/tmp/f280-t058-db-full-green.log` |
| Chromium | 16 passed, 0 failed, 0 skipped; 61.34 с | `/tmp/f280-t058-browser-chromium.log` |
| WebKit | 16 passed, 0 failed, 0 skipped; 76.37 с | `/tmp/f280-t058-browser-webkit.log` |

PostgreSQL collection: regression172 + return82; digest `18dbdf1454a964be8b043d99d4950f722ff9b9ca8dfc87fe2cb69ab02ff97c6f`, terminal `status=pass`, `postgres_test_cleanup=isolated_container_removed`. Два pytest предупреждения об уже импортированном plugin и устаревающем Starlette/httpx не являются skips. UI/DB результаты лично прочитаны как дополнительные основания; эти наборы запускал назначенный тестовый исполнитель.

В каждой окончательной браузерной папке независимо посчитаны **67 HTML состояний в pages.json и 270 PNG**. JSON обоих движков совпадают побайтно: `bd47a6d5faf436ebdd842e76cbeb39f7b8a4ad493d7f69e20000b0a76d6b90fc`. Матрица CJS действительно перебирает 320/360/768/1280, light/dark и CSS zoom100/200%: 1072 сочетания на движок. Число16 — количество pytest проверок файла, а не количество состояний или снимков.

Исторические первый DB254 и Chromium16 до окончательной фиксации/поправки expired fixture не использованы как terminal доказательство окончательных байтов. Текущий expired fixture явно передает effective label «Бесплатный», что независимо проверено в обоих pages.json и текущих снимках.

## Оценка состояния и пути пользователя

| Область | Самостоятельно проверенное основание | Вывод |
|---|---|---|
| Pending + price_changed | Видимая причина и GET «Проверить новую цену»; статус существующего счета остается единственной primary | Цена не теряется; новый checkout не предлагается. |
| Pending + method_required | Прежние method-pending/on fixtures, видимая GET проверки карты, отсутствие resume/early/checkout | Карта и результат платежа различимы, путь не создает повторную оплату. |
| Pending + receipt_contact_required | Причина адреса для чека, помощь `/billing/history#billing-help`, отсутствие «Оплатите» | Понятен следующий безопасный шаг без приглашения платить снова. |
| Pending + acceptance_budget/provider_unavailable/catalog_not_approved/provider_floor | Видимая приостановка, сохраненный оплаченный срок, помощь | Внутренний код не выводится; существующий платеж остается первым действием. |
| Pending + late_success | Отсутствует «Подтверждение оплаты получено» | Нет ложного успеха одновременно с неизвестным результатом. |
| Реальный месяц и год | Один actual-cycle label; year fixture намеренно имеет stale presentation month; assertions раскрывают details и проверяют все три годовые подписи | Текущий цикл не подменяется месяцем. |
| Unknown/free/trial/expired | Нет выдуманной строки «Период оплаты»; expired заголовок «Бесплатный»; trial сохраняет дату | Экран сообщает действующий доступ, а не старый период. |
| Нет подписки / нет cycle attribute | UI contract отдельно проверяет отсутствие подписки и отсутствующий атрибут; реальные GET покрывают неизвестный цикл | Неизвестное значение безопасно; эти два состояния не приписываются отдельным браузерным страницам. |
| Обычные paid/off/no-card/prepared | Краткие факты; продление, отключение и досрочное действие сохраняют свои границы; дополнительные сведения native details | Дополнительные сообщения не перегружают обычную страницу. |

Новые seven-restriction assertions проверяют ровно один `data-billing-primary` на статус `INV-SYNTHETIC`, отсутствие competing checkout/resume/early и ложного подтверждения. Method_required проверяется существующими двумя отдельными fixtures. Исходники подтверждают safe GET ссылок цены/карты; финансовые POST и rules не менялись. В DB отрицательные counts/states/provider-create assertions стоят до presentation assertions; положительный receipt recovery без pending и месячный/годовой доступ сохранены. Reviewer не совершал настоящих платежей.

Причина приостановки и статус могут занимать два notice блока: это отдельные реальные факты. На просмотренных 320px экранах они читаются последовательно и не перекрывают главную кнопку. Сокращение текста здесь не требует скрывать причину, последствия или помощь. В обычных состояниях остаются тариф, срок, автопродление, следующее списание при необходимости и один раскрываемый уровень условий/истории. Отключение доступно непосредственно, его последствия видны рядом.

## Лично просмотренные окончательные изображения

Все ниже — локальные синтетические PNG окончательных папок, осмотренные reviewer через `view_image`, а не только перечисленные исполнителем.

Chromium, `/tmp/f280-t058-browser-chromium/`:

- `subscription-restriction-price_changed-320-dark.png`;
- `subscription-restriction-receipt_contact_required-1280-light.png`;
- `subscription-restriction-acceptance_budget-320-light.png`;
- `subscription-restriction-provider_unavailable-1280-dark.png`;
- `subscription-1280-dark.png`;
- `subscription-unknown-cycle-320-light.png`;
- `subscription-expired-1280-light.png`;
- `subscription-free-320-dark.png`;
- `subscription-trial-1280-dark.png`.

WebKit, `/tmp/f280-t058-browser-webkit/`:

- `subscription-restriction-receipt_contact_required-320-dark.png`;
- `subscription-restriction-price_changed-1280-light.png`;
- `subscription-restriction-catalog_not_approved-320-light.png`;
- `subscription-restriction-provider_floor-1280-dark.png`;
- `subscription-restriction-late_success-320-dark.png`;
- `subscription-year-1280-light.png`;
- `subscription-expired-320-light.png`;
- `subscription-method-pending-on-320-dark.png`;
- `shell-subscription-off-no-card-1280-light.png`;
- `subscription-prepared-320-light.png`.

На этих 19 снимках обе темы и обе крайние ширины лично осмотрены: факты и подписи читаются, focus виден, карточки/кнопки/уведомления не перекрываются. Year показывает «10 000 ₽ за год»; unknown не превращается в месяц; free/trial/expired не заявляют оплаченный период. Shell no-card не изображает отсутствие карты как ошибку доступа. Prepared сохраняет предупреждение о расчете и раскрываемое раннее действие. Method-pending-on позволяет отключить разрешение будущего продления, сохраняя проверку текущего платежа. Тест годовых details раскрывает/проверяет/закрывает их клавишей Space; сохраненный годовой PNG показывает закрытую секцию, а не выдается за личный снимок раскрытого периода.

## Доступность и границы доказательств

CJS проверяет отсутствие горизонтального переполнения в каждой из 1072 комбинаций/движок, видимые основные controls минимум24px и достижимость видимой primary после прокрутки. Контраст текста вычисляется в light/dark при1280px/100%. Проверки focus/keyboard и native consent из прежнего набора сохраняются; новые recovery ссылки получают focus. Native `<a>`, `<button>`, `<details>/<summary>`, labels и семантические факты остаются; в T058 нет новых динамических controls или анимаций.

NoJS дополнение реально выполняет 12 случаев: семь restriction плюс free/trial/expired/unknown/year. Enter по статусу дает только два GET, без денежного POST; Space открывает условия и показывает настоящий год либо отсутствие выдуманной строки периода. Прежние NoJS consent/CSRF/version/quote/cancel/resume проверки сохранены. Этот новый NoJS branch загружает HTML **без CSS**: он доказывает нативное действие и содержимое, не styled reflow или контраст при отключенном JavaScript. Styled responsive evidence получено отдельной основной матрицей; CSS T058 не меняет.

200% здесь — `document.body.style.zoom=2`, не реальное системное увеличение текста/браузерного интерфейса. Subscription200% подтвержден assertion матрицей, отдельного лично просмотренного subscription200% PNG нет. Из270 снимков на движок268 — 67 состояний × 2ширины × 2темы при100%; оставшиеся2 — shell-checkout200%. Не заявляется личный просмотр всех540 PNG, физического сенсорного устройства, VoiceOver или live кабинета Krisp.

Исторические официальные Krisp/исследовательские материалы и текущий GRAF reference отчет дают основания для иерархии и раскрытия сведений; этот scoped reviewer не наблюдал заново частный Krisp кабинет и не измерял конверсию/удержание. Заключение означает отсутствие оставшихся исправимых браузерных/визуальных замечаний в проверенном T058, а не гарантию желания оплатить или отсутствия любых будущих проблем у каждого пользователя. Реальные чеки, банковское зачисление, возвраты, автосписания, production и exact-SHA/base PR gates остаются отдельными доказательствами основного исполнителя.

## Независимо пересчитанные SHA-256

После terminal обоих браузеров повторно пересчитан manifest: **7/7 совпадают, дрейф0**. Browser assets также совпадают с ранее прочитанными неизменными байтами.

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `2ffc49465a9a7c4e11c95cb6780d5c1afde145fc755ea101878128e36c0353ca` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` |
| `apps/server/tests/contract/test_billing_ui.py` | `4dffa5ed2c8a467cad62aff9cf49da865cb931024dcb7df12c87d19ff7e6c1a9` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `fe2910b7f482f9992e848fc8e4242c1b653c0c11d2edb843177a574920020f27` |
| `apps/server/tests/integration/test_billing_return.py` | `8b293f14dd7ffb6ad23b40d4c384c9f11f65a1ee4b4c4b79c3a153a412e88fb3` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `cde38c77bc51bf7d4fb8855e10ec1b88550f3b5e1a77e44eebb61420445e5f91` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `2ba6a6e5cb4c750d37c2b62ddc92cc90c5d923c6cb0afb01e3a346ca59e88b17` |
| `cabinet/static/cabinet/cabinet.css` | `24074ca3bc01545a1ab794c8df222e36622fa1cbe171a6a327dfe840fe200a64` |
| `cabinet/static/cabinet/cabinet.js` | `1d1e115497bc028e9f1b1b9c8ca05eaf896186ea0a544d27eac8f05f2997db4b` |

| Окончательный лог | SHA-256 |
|---|---|
| UI contract | `3ba122baeeddb39ca5d2a80b153a44c1703428f1c33e44f335043f6acf9a3640` |
| PostgreSQL | `5facda74c8ae195cfe9a4e130550514b9cfdd5a24a7b5dc3124699de1c5f7d89` |
| Chromium | `265d32226dcc01bab2d24a70012e331c87f5bbbea7e032c3175f8a6cf6d2df39` |
| WebKit | `8a93b6ca8da40dca21aae3b5970dd050ae1f97ed52bcf59e66ecea80dd5f27e6` |

Перед передачей основной исполнитель получает этот самостоятельный PASS и его явные границы. Checklist не менялся, прежний release report не заменялся; commit/merge/deploy reviewer не выполнял.
