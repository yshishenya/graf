# F280 — окончательные проверки необязательного автопродления

Дата: 2026-10-01; ветка codex/280-payment-optional-renewal, lane high-risk-product. Три независимых scoped PASS без применимых незакрытых замечаний. Реальная финансовая F278, человеческая T011/T012 и новый выпуск T022 остаются отдельными доказательствами.

## Проверки исполнителя интерфейса

# F280 — необязательное автопродление: отчёт UI

Рабочая копия: `рабочая копия F280`.
Ветка: `codex/280-payment-optional-renewal`.
Исходный HEAD: `14fa81f4fff91b2158eaf1afb456713c50692300`.
Режим проверки: активный срез F280, `high-risk-product`, T020/T021.
Статус: **UI и принадлежащие тесты заморожены. Все применимые проверки завершены. Активных тестовых процессов исполнителя нет.**

## Допуск и владение

Root разрешил реализацию после независимых checklist 51/0, optional-renewal 10/0, analyze PASS и issue #7408 sync/canon PASS. Изменены только два файла интерфейса и восемь связанных тестовых файлов из таблицы хешей. Прочие исходники, документация, чеклисты, задачи, GitHub, коммиты, приложение, выпуск и реальные платежи не изменялись этим исполнителем.

## Поведение

- Продление включено по умолчанию и необязательно; оферта остаётся непринятой и обязательной.
- При снятой галочке сводка сообщает: «Отключено — автоматического списания не будет.» Будущая дата/сумма автоматического списания скрываются.
- Без JavaScript обычная форма позволяет оба режима. Будущая сумма и дата подписаны условно: «При автопродлении» / «Списание при автопродлении».
- Существующий cabinet.js хранит только строковый true/false текущей вкладки по meta user/workspace/session. Ни оферта, ни цена, ни промокод, ни quote, ни секрет не сохраняются. Сервер получает фактическое поле формы.
- Init, HTMX afterSwap и pageshow приводят галочку и сводку к одному состоянию. Отказ sessionStorage и отсутствие scope не ломают текущую форму; перенос через полную навигацию в этих случаях не гарантирован.

## Проверки

### RED и статические договоры

До runtime-изменений новые HTML-проверки дали ожидаемые 5 FAIL за 0,19 с. Первая правка теста содержала пропущенный импорт re; он исправлен до зафиксированного RED.

Из `apps/server`:

```sh
uv run --extra dev pytest tests/contract/test_billing_clarity.py tests/contract/test_billing_ui.py -q --tb=short
```

69 PASS за 0,24 с. Эти runtime-файлы и договорные тесты после результата не менялись.

### Доступность и состояние вкладки

```sh
GRAF_BROWSER=chromium uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
GRAF_BROWSER=webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
```

Текущие тесты: Chromium — 16 PASS за 26,20 с; WebKit — 16 PASS за 32,82 с. Содержат клавиатуру, согласованную OFF-сводку, два reload, явное повторное включение, HTMX replacement, pageshow, независимую вкладку без opener, отдельные user/workspace/session, неизвестное значение, отсутствующий scope, запрет Storage.getItem/setItem и обычный submit без JS для True/False. Оферта без явного принятия блокирует обычную отправку.

### Настоящий браузер, HTTP и PostgreSQL

Из корня репозитория:

```sh
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
```

- Chromium полный набор verified/unverified: 2 PASS за 79,79 с, runner 84 с, очистка изолированного контейнера подтверждена. Это до добавления meta charset исключительно в заключительную тестовую страницу; свежий повтор verified указан ниже.
- WebKit первый полный набор: 1 FAIL / 1 PASS за 166,46 с; verified timeout до первого запроса к серверу, unverified PASS за 127,76 с. Не объявляется успешным полным запуском.
- WebKit отдельный verified затем дошёл до заключительного настоящего POST → 303, но упал на поиске текста тестовой страницы: 1 FAIL за 168,80 с. Отказы 303/409 и OFF-выбор перед этим прошли.
- Точный изолированный пример доказал причину: WebKit route.fulfill без HTML meta декодировал русский текст как windows-1251; с `<meta charset="utf-8">` — UTF-8, нужный текст виден. В настоящем base.html декларация уже есть. Добавлен meta в синтетический ответ, никаких runtime-правок по этому сбою.
- WebKit финальный verified с этой поправкой и снимками: **1 PASS за 173,89 с**, runner 182 с, очистка изолированного контейнера подтверждена.

Точная команда финальных повторов verified, сначала WebKit, затем Chromium:

```sh
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit GRAF_PROMO_BROWSER_SCREENSHOTS=/tmp/graf-f280-optional-ui-screenshots apps/server/scripts/run_local_postgres_tests.sh --focused 'tests/contract/test_billing_promo_refresh_browser.py::test_promo_survives_real_submit_reload_and_return[verified]' -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium GRAF_PROMO_BROWSER_SCREENSHOTS=/tmp/graf-f280-optional-ui-screenshots apps/server/scripts/run_local_postgres_tests.sh --focused 'tests/contract/test_billing_promo_refresh_browser.py::test_promo_survives_real_submit_reload_and_return[verified]' -q --tb=short --show-capture=no
```

**Финальный verified Chromium: 1 PASS за 82,45 с; runner 91 с, очистка изолированного контейнера подтверждена.** Оба финальных verified повтора используют одни и те же исходники и тестовый документ с UTF-8.

Каждый verified-сценарий проверяет 320/1280 px: выключить продление → Apply valid/invalid → month/year → очистка → два reload → back/return → чужая вкладка → discounts. На 1280 px дополнительно отсутствующая оферта → 303 и устаревшая оферта → 409 сохраняют False и возвращают непринятую оферту; затем обычный submit отправляет год и принятую оферту без recurring field.

До каждого start в БД отсутствуют operation/invoice/redemption и вызовы провайдера. После одного разрешённого start: ровно одна operation и invoice на 900 000 копеек за год, оба snapshots recurring=False, offer=True, один запрос fake provider c save_payment_method=False.

Verified: 33 POST preview → 303, 4 POST discounts → 303, 1 отказ POST start → 303, 1 POST start → 409 и 1 разрешённый POST start → 303; 38 вспомогательных submit → 303 и один проверенный provider redirect. Unverified: 32 POST preview → 303, 4 POST discounts → 303, start — 0, финансовых записей/вызовов провайдера — 0. Запросов браузера во внешнюю сеть — 0.

Первоначальные неуспешные попытки заключительного provider handoff: вымышленный yookassa.test не разрешался через DNS после браузерного redirect. Исправление теста отправляет фактический POST через route.fetch(maxRedirects=0), проверяет 303 и строго синтетический Location, затем показывает локальный тестовый документ. Это доказывает серверный переход и финансовый запрос, **не открытие внешней страницы провайдера и не реальный платёж**.

### Код и ограничения

Ruff шести изменённых Python-тестов, node --check обоих браузерных тестов и cabinet.js, git diff --check — PASS. В наборах остаются два прежних предупреждения PytestAssertRewriteWarning и Starlette/httpx deprecation.

Общий серверный HTTP/SQL набор, независимые финальные обзоры, convergence и выпуск ведёт root. Установленный GRAF Dev, человеческая оценка удобства, фактическая конверсия/удержание и финансовая F278 не заменяются этими тестами.

## Снимки

Синтетические снимки и размеры формы: `/tmp/graf-f280-optional-ui-screenshots/verified/`.

- `promo-refresh-webkit-320-applied.png` — сводка с OFF и отсутствующей датой будущего списания.
- `promo-refresh-webkit-320-applied-consents.png` — компактные согласия и кнопка оплаты.
- Соответствующие Chromium, 1280 px, cleared, error и annual-discounts снимки создаются тем же тестом.

Исполнитель визуально проверил два указанных WebKit-снимка: текст разового режима виден, оферта и продление сняты, кнопка доступна, наложений в форме нет. Автоматическая проверка отсутствия горизонтального переполнения проходит при каждом verify.

## SHA256 принадлежащих файлов

- `cd40bdb77e07b978eb13e98f17a24c40d0af5c93eaf4e9d1e300bf08947e4cb4` — `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- `a690a666515d7c9cb2c53595d4527240e57005d3b6be200e85334547a76bfa95` — `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`
- `1fd9e0ff39e4bc3180110eccaf92e8da1a9986522a7b7330f90fb4254faaa893` — `apps/server/tests/browser/billing-accessibility.test.cjs`
- `5cffd741bac5fd96e968f87dfacbc2e5ec1df2eab6557bd823954b4658991f2c` — `apps/server/tests/browser/billing-promo-refresh.test.cjs`
- `36bfbca53c8a56d8a00464f1185a0528869043889942057e47f2728d495fa3f5` — `apps/server/tests/contract/test_billing_accessibility.py`
- `527fc31a781fad4fbf3c6c1a02ba37bf2adad1e31e44768a5c64e309c0f057be` — `apps/server/tests/contract/test_billing_clarity.py`
- `b49a01ab9f5117004521b20e1d483004146d64a7967bb494dd29e9200d905417` — `apps/server/tests/contract/test_billing_promo_refresh_browser.py`
- `eee97567d5afe35d1cf49ff22bed71b48d5e054aee02e08bde21e4409226b052` — `apps/server/tests/contract/test_billing_ui.py`
- `6ab03c3f3b4695bc4e2e718c150919d8a15a133aefac026bc3a85b9bb7b86773` — `apps/server/tests/integration/test_billing_discount_presentation.py`
- `17dc8308b66e0122eae98e6316fdd59c7fe0d5d0fb09e16f3e20cdff67a526f5` — `apps/server/tests/integration/test_billing_promo_refresh.py`

Freeze UTC: `2026-10-01T18:29:45+00:00`.

## Независимая трассировка

# F280 — независимая трассировка необязательного автопродления

Дата: 2026-10-01. Проверяющий: optional_renewal_trace. Рабочая копия: `рабочая копия F280`, ветка `codex/280-payment-optional-renewal`. Проверен замороженный исходный код и получены окончательные UI receipts. Автор обзора не менял код, tasks, checklist, GitHub, коммиты или production.

## Вывод по исходному коду

**PASS: конкретных неисправленных нарушений FR-019/020 в четырёх изменённых исходниках не найдено.** Финальные local UI receipts и три независимых flow/security/browser заключения подтверждены на одинаковых исходниках; выпуск T022 остаётся открытым.

1. `billing_checkout_content.html:75`: recurring checked по умолчанию, без required. Оферта на предыдущей строке unchecked/required. Native форма поэтому допускает оплату без recurring, но требует принятия оферты.
2. `cabinet.js:1794–1843`: только визуальный bool в sessionStorage, ключ `graf-checkout-renewal:<user>:<workspace>:<session>`. Три scope берутся из существующих meta. Допускаются только строки true/false. Init, HTMX initCabinet и pageshow связывают checkbox со сводкой. При OFF дата скрывается, сводка явно сообщает отсутствие списания; кнопка оплаты остаётся доступной. Ошибка storage не ломает текущую форму. Нет помещения promo/quote/offer/цены в JS storage.
3. `billing.py:3638`: отсутствующий recurring field становится False. Серверное требование оферты сохранено; прежний запрет False удалён. `billing.py:3945/3988` фиксирует actual bool в request/invoice snapshots. Предварительная скидка остаётся отделена от денежного действия.
4. `billing.py:667/706`: initial creator отвергает missing/malformed snapshot bool до провайдера и отправляет save_payment_method равным исходному снимку. Повтор операции использует прежнюю operation/idempotence, визуально изменившаяся галочка не изменяет старый денежный режим.
5. `entitlements.py:331/361`: новую карту можно записать только при строгом True и текущем владельце/authority. False выдаёт оплаченный месяц/год, не сохраняет неожиданную saved карту и выключает recurring_allowed при неизменной authority. Уже оплаченный остаток сохраняется. Поздняя старая операция не отменяет более новое решение authority. Повторное подтверждение не выдаёт второй период.

Уточнения FR-003/contract согласованы: разовая checkout-покупка показывает сумму/срок/OFF; будущая цена обязательна при ON. Существующие экраны подписки/хранения сохраняют условную будущую цену. Plan теперь соответствует фактическому namespace. Два промежуточных документальных замечания закрыты перечитыванием актуального текста.

## Проверки и границы

Серверные recovery/entitlements/lifecycle: RED8 FAIL/33 PASS, затем GREEN49 PASS. Объединённый PostgreSQL/HTTP набор:465 PASS/2 FAIL; оба старых ожидания unchecked recurring исправлены, полный файл return повторён:82 PASS. Первый запуск не переименовывается в467 PASS. Money-path содержит month/year × True/False/omitted, неожиданную saved карту, противоположный повтор POST до/после success и recurring-month→one-off-year с сохранением остатка/прежней карты.

Окончательный `/tmp/graf-f280-optional-ui.md`, freeze UTC2026-10-01T18:29:45+00:00: contracts69 PASS; accessibility Chromium16 PASS26.20с/WebKit16 PASS32.82с; настоящие verified browser→HTTP→PostgreSQL Chromium1 PASS82.45с, WebKit1 PASS173.89с. Unverified прошёл в прежнем полном наборе каждого браузера. Финальные verified используют одинаковые runtime/test bytes с UTF-8 в синтетическом provider document; первоначальные DNS/charset/test-expectation отказы сохранены в хронологии и не называются успешными запусками. На320/1280px False сохраняется через Apply valid/invalid, month/year, remove, два reload, back/return, отдельную вкладку и discounts. Offer-required303/stale-offer409 также сохраняют False; финальный submit отправляет год/принятую оферту без recurring field. В БД ровно одна operation/invoice900000коп. с False в обоих снимках, один fake-provider create с save_payment_methodFalse; до каждого start money state0, внешних browser requests0. Это подтверждает реальный серверный303/параметры запроса, но не открытие живой ЮKassa и не реальное списание.

`optional_renewal_requirements_final` повторно перечитал исправленные документы и пять checklist: reviewer-owned43/0, built-in8/0, общий51/0, без противоречий; текущие spec/plan/tasks/contract hashes совпадают с разделом ниже. Исторический допуск больше не используется как единственное основание.

Окончательные независимые `/tmp/graf-f280-optional-security.md` и `/tmp/graf-f280-optional-browser.md` прочитаны целиком. Оба scoped PASS, неисправленных применимых замечаний0, четыре source hashes совпадают. Security самостоятельно трассировал creator/recovery/confirmation/grant/renewal planner/authority/cancel/resume; browser независимо оценил настоящие DOM-сценарии, HTTP/SQL мост и шесть текущих Chromium/WebKit снимков320/1280px. Итог трёх независимых обзоров текущего среза: flow PASS, security PASS, browser PASS, CRITICAL/HIGH/MEDIUM/LOW0/0/0/0. Локальная часть T021 не имеет остающихся pending receipts/reviews; отметка самой задачи принадлежит root. Новые тесты этим reviewer не запускались.

Fallback без JS: native POST передаёт False корректно; межстраничное сохранение выбора недоступно и явно ограничено spec/plan. Базовые будущие подписи условны «При автопродлении». Обычная новая вкладка без opener имеет True; браузерное клонирование sessionStorage при opener — задокументированная граница. Нет дополнительных tab IDs/TTL/API.

Настоящие провайдерские списания, банковское зачисление, возвраты, человеческая приёмка, installed GRAF Dev, exact-SHA CI, Full и production этого нового кода не доказаны этим отчётом. T022, T011/T012/F278 остаются отдельными обязательствами.

## Снимок проверенных файлов SHA256

- billing.py: `bf6d4cfbeb154eb875063d7e200fec83801fcce4ff066b614a53793594dc083d`
- entitlements.py: `83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b`
- billing_checkout_content.html: `a690a666515d7c9cb2c53595d4527240e57005d3b6be200e85334547a76bfa95`
- cabinet.js: `cd40bdb77e07b978eb13e98f17a24c40d0af5c93eaf4e9d1e300bf08947e4cb4`
- spec.md: `d0e028ca63f1a9507dccf80e7b0584bce03e344aa6ff505dc9e50a3e98ce898d`
- plan.md: `7f9fa8bce8b5170647eccf7f358890dccde36a707364aae38c56b0e1712b0309`
- tasks.md: `22599a3f882888dd11594df30b0cdb54860d164d574f660f6e8ad870f89af926`
- contracts/payment-journey.md: `18e874d0549bf5102b701b222e4a6a4f1ebcfccfaca98e32c827d6d42bae220c`

`git diff --check` PASS. Дальнейшие изменения исходников требуют нового scoped review; изменения только тестов требуют окончательных receipts.

## Независимый обзор браузеров

# F280: независимый обзор необязательного автопродления

Вердикт: **PASS в проверенных границах; применимых незакрытых замечаний 0**.

Я не автор изменений. Независимо прочитаны текущий diff выполняемых исходников, браузерные сценарии, серверный мост, спецификация FR-019/020, договор пути оплаты и окончательные отчёты исполнителей. Просмотрены актуальные снимки Chromium/WebKit. Новые браузеры, тесты или базы не запускались; исходники, tests/docs/checklists/GitHub/CI/production не менялись. Создан только этот отчёт. Применён подход уже прочитанного навыка Playwright: оценка настоящего DOM и действий с явным разделением визуальных и финансовых доказательств.

## Замороженные исходники

После окончательных результатов повторно сверены SHA256:

| Файл | SHA256 |
|---|---|
| cabinet/web_routes/billing.py | bf6d4cfbeb154eb875063d7e200fec83801fcce4ff066b614a53793594dc083d |
| billing/entitlements.py | 83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b |
| cabinet/pages/billing_checkout_content.html | a690a666515d7c9cb2c53595d4527240e57005d3b6be200e85334547a76bfa95 |
| cabinet/static/cabinet/cabinet.js | cd40bdb77e07b978eb13e98f17a24c40d0af5c93eaf4e9d1e300bf08947e4cb4 |
| cabinet/static/cabinet/cabinet.css | 397a66835149e7614dd75a201e4c57676dc2485d632641ba5f2f2990684fc934 |

Пути относятся к `apps/server/src/twobrain_rec_server/`. Тестовые файлы также совпадают с окончательным отчётом UI:

- `billing-accessibility.test.cjs`: `1fd9e0ff39e4bc3180110eccaf92e8da1a9986522a7b7330f90fb4254faaa893`.
- `billing-promo-refresh.test.cjs`: `5cffd741bac5fd96e968f87dfacbc2e5ec1df2eab6557bd823954b4658991f2c`.
- `test_billing_promo_refresh_browser.py`: `b49a01ab9f5117004521b20e1d483004146d64a7967bb494dd29e9200d905417`.

## Независимый разбор поведения

Свежая форма имеет два разных условия: `recurring_consent` checked/not-required, `offer_consent` unchecked/required. Снятие продления не препятствует обычной отправке при принятой оферте. Точное сегодняшнее значение на кнопке остаётся серверной ценой; JS не меняет цену, quote или право создать платёж. Предварительная форма промокода остаётся отдельной от денежной формы.

`cabinet.js` сохраняет только literal `true`/`false` в sessionStorage по существующим meta user/workspace/session. Оферта, код, сумма, quote и платёжные полномочия туда не записываются. Init, `htmx:afterSwap` через `initCabinet` и `pageshow` восстанавливают явный выбор текущей вкладки. Смена scope сбрасывает состояние к defaultChecked при отсутствии соответствующей записи. Неизвестная запись не интерпретируется как согласие. Ошибка Storage или отсутствующий scope не блокируют текущую нативную форму.

При False сводка показывает «Отключено — автоматического списания не будет», будущая автоматическая сумма и строка следующего списания скрыты; сумма сегодня, срок, скидка и кнопка оплаты сохраняются. Обновление состояния сообщает сводку через aria-live. Обязательная оферта не переносится вместе с визуальным выбором продления.

Без JS работает обычная HTML-форма: отмеченное продление отправляет true, снятое не отправляет поле, серверный Form default превращает отсутствие в False. Базовые подписи «При автопродлении» и «Списание при автопродлении» условны; они не обещают списание при снятой отметке. Сохранение предпочтения между полной навигацией без JS или при запрещённом Storage не гарантируется — это явно указано в FR-020, а не скрытая регрессия. Новая вкладка без opener независима; возможное штатное копирование sessionStorage через opener также документировано.

Сервер сохраняет actual bool в operation/invoice и требует strict bool в общем creator. `save_payment_method` равен принятому bool. Entitlements сохраняют карту и включают recurring только при strict True и прежних authority/owner guards. UI-предпочтение не переписывает уже принятую операцию при повторе того же ключа. Эти выводы подтверждены просмотром diff и существующего серверного отчёта; мой обзор не является отдельным новым выполнением денежных тестов.

## Окончательные выполненные доказательства

Прочитан замороженный `/tmp/graf-f280-optional-ui.md` — SHA256 `92bba9d1709e8d082dbe9aa14ddef2c2027cc00d075cab8db450bbd06f368d69`, freeze `2026-10-01T18:29:45+00:00`. Исполнение принадлежит UI-агенту; я независимо проверил смысл сценариев и их соответствие текущим байтам.

- Accessibility: **Chromium16 PASS за26.20с; WebKit16 PASS за32.82с**. Сценарий охватывает клавиатуру, required offer/optional recurring, false→reload×2, явное повторное включение→reload, HTMX replacement, pageshow, отдельную вкладку, каждый scope-компонент, invalid value, missing scope, отказ Storage, обычную отправку без JS при True/False. Проверяются 320/360/768/1280px, светлая/тёмная темы, 100/200%, достижимость основной кнопки и отсутствие горизонтального переполнения. Это автоматическая оценка, не ручная проверка физическим экранным диктором.
- Реальный HTTP/SQL verified Chromium, окончательный повтор: **1 PASS за82.45с**, runner91с, очистка контейнера подтверждена.
- Реальный HTTP/SQL verified WebKit, окончательный повтор: **1 PASS за173.89с**, runner182с, очистка контейнера подтверждена.
- Отдельное прежнее выполнение unverified: Chromium полный verified/unverified **2 PASS79.79с**, WebKit unverified **PASS127.76с** внутри запуска с неуспешным verified. Это отдельные результаты; полный неуспешный WebKit не переименован в PASS и результаты не складываются.

Каждый окончательный verified-сценарий проверяет320/1280: initial True→явный False→Apply/invalid/cycle/clear/reload×2/back/return/discounts и независимая вкладка. На1280 также настоящий missing-offer POST303 и changed-offer POST409 сохраняют False и возвращают непринятую оферту. Конкретная новая DOM-проверка409 здесь — offer_changed; общее восстановление предпочтения на других409 следует той же инициализации, но не называется отдельно исполненным новым browser-кейсом.

До start мост проверяет отсутствие финансовых записей и запросов fake provider. Финальная отправка с принятой офертой не содержит recurring field, возвращает настоящий серверный303 на строго синтетический адрес. Затем проверены ровно одна operation/invoice, год,900000minor, bool False в обоих snapshots, offer True и единственный fake-provider запрос с `save_payment_method=False`. На verified:33previewPOST303,4discountsPOST303,1отказstartPOST303,1startPOST409 и1разрешённыйstartPOST303. Unverified не создаёт start, денег или provider requests. Внешних запросов браузера0.

Синтетический handoff проверяется через route.fetch(maxRedirects=0) с настоящим POST: приложение получает запрос, а браузер не открывает внешнюю страницу провайдера. Предыдущие отказы DNS, timeout и текстового декодирования сохранены в отчёте как отказы. Поправка `<meta charset="utf-8">` затронула только финальный тестовый документ; настоящий `cabinet/base.html` уже содержит UTF-8. Проверки303, конечной суммы, OFF, запросов и финансовых снимков не ослаблены.

Также прочитан общий `/tmp/graf-f280-optional-http.log`: **465PASS/2FAIL324.45с**, оба отказа — старые ожидания обеих снятых отметок в return. Исправление ожиданий затем проверено всем `/tmp/graf-f280-optional-return.log`: **82PASS63.73с**, runner69с, cleanupPASS. Это не называется467PASS; общий новый exact-SHA CI остаётся обязанностью выпуска. Серверный recovery/entitlements/lifecycle отчёт отдельно содержит49PASS0.22с.

## Просмотр актуальных снимков

В `/tmp/graf-f280-optional-ui-screenshots/verified/` независимо открыты:

- `promo-refresh-webkit-320-applied.png`;
- `promo-refresh-webkit-1280-applied.png`;
- `promo-refresh-webkit-320-cleared-consents.png`;
- `promo-refresh-webkit-1280-annual-discounts.png`;
- `promo-refresh-chromium-320-applied-consents.png`;
- `promo-refresh-chromium-1280-annual-discounts.png`.

При False видимое отключение продления согласовано со снятой отметкой. Сегодняшние900/9000/10000₽ соответствуют выбранному месяцу/году и состоянию скидки; кнопка повторяет текущую сумму. Два условия различимы, оферта отдельно, основной путь оплаты один. На узком экране текст продления переносится внутри своей строки, не перекрывает отметки или кнопку; на широком карта содержит понятный итог и действия. Для мобильной страницы нужна обычная вертикальная прокрутка. Новых применимых визуальных замечаний не найдено.

## Границы PASS

Это независимый обзор нового optional-renewal diff и текущих локальных доказательств, а не авторское самоодобрение. Конкретных оставшихся замечаний по этому срезу нет. Старые браузерные PASS других версий не используются как доказательства новой реализации.

Обзор не подтверждает новый exact-SHA PR CI, frozen Full, production deploy, установленный GRAF Dev, реальную форму YooKassa, реальное списание/чек/банковское зачисление/возврат, физическую проверку экранным диктором или рост конверсии/удержания. Решение включить продление по умолчанию — принятое требование владельца; автоматические проверки доказывают согласованность выбора и пути, не желание каждого человека оплатить.

## Независимый обзор безопасности

# F280 — независимый обзор безопасности и финансовой логики

Дата: 2026-10-01. Проверяющий: `optional_renewal_security`, не автор реализации. Рабочая копия: `рабочая копия F280`; ветка `codex/280-payment-optional-renewal`; исходный HEAD `14fa81f4fff91b2158eaf1afb456713c50692300`. Режим: read-only обзор текущего high-risk-product среза T020/T021. Изменён только этот отчёт вне репозитория; исходники, документация, checklists, задачи, GitHub, коммиты, deployment и реальные платежи не менялись.

## Заключение

**Scoped PASS: конкретных неисправленных нарушений безопасности или финансовой логики FR-019/FR-020/SC-008 в проверенном изменении не найдено.** Проверены четыре runtime diff и окружающие checkout/start/continue, quote binding, confirmation/reconciliation, grant и renewal planner/authority пути. Дополнительных изменений для данного среза по результату обзора не требуется. Это допуск независимого финансового обзора к дальнейшим PR/release gates; не подтверждение реального зачисления или завершённого production-выпуска.

## Прослеженная логика

1. **Фактический выбор и граница согласия.** `billing.py:3638` объявляет recurring_consent как серверный bool с default=False. Отсутствующий unchecked field становится False. POST сохраняет actual bool одновременно в immutable operation и invoice snapshots (`3945/3988`); удалён лишь запрет False. `offer_consent` по-прежнему default=False, сервер требует его True. В HTML recurring checked и не required; offer required и не checked. Предвыбранное значение интерфейса само по себе не создаёт платёж.

2. **Запрос провайдеру.** `_create_initial_checkout_payment` (`650–708`) проверяет snapshot Mapping, initial kind, связь invoice/operation/workspace, personal/cycle, offer exact True, recurring exact bool, совпадение суммы и RUB до создания provider client. Missing/null/числа/строки не достигают dispatch. Для False передаётся `save_payment_method=False`; `yookassa.py:165–197` записывает именно этот False в JSON hosted payment. Initial helper не передаёт старый payment_method_id. Цена, чек и первоначальный idempotence key остаются серверными.

3. **Повтор и продолжение.** Повтор POST с прежним ключом ищет уже созданную operation и возвращает её разрешённый hosted URL/статус, не переписывает recurring по новой форме и не рассчитывает второй платёж. Continue (`2220–2375`) читает operation snapshot и общий helper; актуальная роль/owner, включённость checkout и provider key expiration проверяются. Purchase_schema2 не возобновляет недиспетчеризованный платёж обходным legacy путём. Сменившаяся галочка не меняет разрешение старой операции.

4. **Реальное основание выдачи.** `webhook_reconciliation.py:80–162` сначала проверяет provider GET payload против purchase/invoice/scope и terminal outcome. Сам сигнал webhook не является основанием. `grant_confirmed_payment` блокирует workspace/operation/invoice, проверяет kind/amount/currency и duplicate immutable grant. Лишь затем добавляет оплаченный месяц/год поверх max(подтверждённое начало, ранее paid_through), сохраняя остаток и storage entitlement.

5. **False и неожиданная saved карта.** `entitlements.py:328–368` запись нового BillingPaymentMethod и замена старого default допускаются только при snapshot recurring exact True, подтверждённой текущей owner/authority и encryption key. False/missing/null/0/1/string не проходят этот новый барьер, даже если provider сообщает saved card. При неизменной authority False устанавливает recurring_allowed=False и увеличивает authority version; старую активную карту не заменяет. Наличие ранее сохранённой карты не означает разрешения на автоматический платёж.

6. **Более позднее решение пользователя и дубли.** Owner actor сравнивается с актуальным owner; authority snapshot сравнивается с текущей версией. Если пользователь отменил продление после создания платежа или сменился owner, старый результат не записывает карту и не восстанавливает True. Duplicate branch возвращается до новой выдачи, замены карты и изменения recurring. Cancel/resume (`3080–3240`) по-прежнему требуют session/CSRF/current owner и совпадение expected authority version; resume требует отдельное consent, current quote и verified active owner card.

7. **Последующие автоматические платежи.** `renewal_charge.py:290–355` выбирает только recurring_allowed=True, current active owner и personal paid subscriptions; затем повторно проверяет разрешение под блокировкой. Pending initial_checkout/storage_upgrade/early_renewal блокирует планирование; checkout отменяет unsent renewals (`billing.py:3880`). После успешной разовой покупки version меняется, recurring=False; старая карта сама по себе не попадает в планирование. Поздние decline/result paths сохраняют существующие authority fences. Уже отправленный ранее платёж остаётся отдельной финансовой историей — галочка не переписывает принятую операцию.

8. **Сохранившиеся защитные условия.** CSRF dependency, tenant scope, current personal workspace owner и membership, public checkout gate, rate limit, verified receipt email, approved catalog, offer_version и validate_purchase_quote остаются в start. Quote сверяет server current price/catalog/discount/storage и owner/workspace/purpose; скидка ниже provider floor запрещена. Нет нового API, изменения цен/лимитов, обхода offer/quote/receipt или сохранения цены в браузере. Preview и применение/удаление promo остаются без создания operation/invoice/reservation.

9. **Состояние интерфейса.** `cabinet.js:1794–1843` хранит только строки true/false в sessionStorage текущей вкладки под ключом user/workspace/session. Restore принимает только эти строки; не хранит промокод, quote, сумму, принятие оферты, cookie или bearer token. Init/HTMX/pageshow синхронизируют отображение с native checkbox. Storage failure не блокирует checkbox. OFF скрывает будущую автоматическую дату/цену и явно объясняет отсутствие списания. Сервер получает форму, а не доверяет этому preference. Без JS native checkbox остаётся рабочим; межстраничное сохранение визуального выбора в этом fallback ограничено и отражено в FR-020. Клонирование sessionStorage браузером при opener также документировано.

## Доказательства и предел проверки

Прочитан полный diff новых recovery/entitlements/money-path тестов и relevant browser start/assertions. Money-path действительно проверяет month/year × True/False/omitted, provider JSON, snapshots, unsolicited saved card, ровно один grant, opposite retry до/после success и recurring-month → one-time-year с прежней картой/оплаченным остатком. Entitlements matrix включает True/False/missing/null/numeric/string × unchanged/newer-cancellation/different-owner, проверяет новую карту/старую карту/authority. Recovery проверяет malformed snapshot отказ до dispatch.

Численные execution receipts взяты из отчётов исполнителей и root validation; этот reviewer не повторял широкие тесты. Backend: RED8 FAIL/33 PASS → GREEN49 PASS. PostgreSQL/HTTP:465 PASS/2 старых assertion FAIL; после обновления ожиданий полный return file82 PASS при неизменном runtime. Не объявляется первоначальный467 PASS и не суммируются перекрывающиеся проверки.

Прочитан окончательный `/tmp/graf-f280-optional-ui.md`: Chromium/WebKit accessibility16/16 PASS; финальные verified реальные браузерные HTTP+SQL сценарии1/1 PASS с native unchecked omitted field, safe303/409, discount preview, no-money-before-start и одной synthetic provider operation после start. Первый WebKit failure и исправление UTF-8 исключительно тестового документа не скрыты. Провайдерская страница подменена синтетическим документом после проверки реального server303, поэтому ни данный отчёт, ни эти тесты не доказывают внешний провайдерский интерфейс/настоящий платёж.

Самостоятельно вычислены четыре runtime SHA256 и выполнен git diff --check — PASS. Хеши совпадают с frozen flow/backend/UI reports. Дополнительных широких тестов, сетевых запросов к магазину или денежных действий не было. Последующие runtime изменения требуют повторного scoped review.

Exact-SHA CI, authoritative Full, CD dry-run/execute, deployed runtime proof, публикация релиза — отдельный T022. Реальные чеки/банк/возвраты F278, installed GRAF Dev, человеческая приёмка T011/T012, измерение конверсии и удержания не доказаны этим техническим обзором и остаются открытыми там, где требуются.

## Проверенные runtime SHA256

- billing.py: `bf6d4cfbeb154eb875063d7e200fec83801fcce4ff066b614a53793594dc083d`
- entitlements.py: `83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b`
- billing_checkout_content.html: `a690a666515d7c9cb2c53595d4527240e57005d3b6be200e85334547a76bfa95`
- cabinet.js: `cd40bdb77e07b978eb13e98f17a24c40d0af5c93eaf4e9d1e300bf08947e4cb4`
