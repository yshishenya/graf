# F280 — проверка

Рабочая копия: `billing-clarity/crisp`, ветка `codex/280-payment-clarity`; source base `04768db6d3bac13ea3121b1171f605aa32062c14`. До реализации reviewer checklist PASS, analyze без CRITICAL/HIGH/MEDIUM, issues synchronized.

## Автоматическая проверка

Из корня рабочей копии; runner сам создает одноразовую PostgreSQL, запускает нужный `.venv` и удаляет контейнер после проверки:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_billing_ui.py tests/contract/test_billing_purchase_ui.py \
  tests/contract/test_billing_clarity.py tests/contract/test_billing_security.py \
  tests/contract/test_payment_history_support.py tests/integration/test_account_lifecycle.py \
  tests/contract/test_billing_safety_contract.py tests/unit/test_billing_copy_and_redaction.py \
  tests/integration/test_billing_usability.py tests/integration/test_billing_review_regressions.py \
  tests/integration/test_billing_purchase_journey.py tests/integration/test_billing_clarity.py \
  tests/integration/test_billing_return.py tests/unit/test_billing_money_path_e2e.py \
  tests/integration/test_account_merge.py tests/integration/test_web_owner_session_context.py \
  tests/contract/test_public_landing_contract.py tests/unit/test_public_landing.py \
  -q --tb=short --show-capture=no
```

Финальный повтор после последних исправлений (127 проверок текущего кандидата):

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_return.py \
  tests/integration/test_billing_clarity.py \
  tests/contract/test_billing_security.py \
  tests/contract/test_billing_safety_contract.py \
  -q --tb=short --show-capture=no
```

Более широкий набор выше запускался до последних исправлений; его результат не выдается за повтор всей текущей редакции. Подробности — в `validation.md`.

Не применять к live DB. Связанные account/auth/settings contract и unit checks перечислены в итоговом validation; измененные guards/переходы требуют их повторной проверки.

Из `apps/server`, браузерный набор с настоящими шаблонами, CSS/JS и полной оболочкой трех основных страниц:

```sh
uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
GRAF_BROWSER=webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
```

Используются установленные Playwright/Chromium/WebKit. `BILLING_VISUAL_OUTPUT_DIR=/absolute/path` сохраняет синтетические HTML fixtures и снимки. WebKit на macOS использует Option-Tab для полного обхода элементов согласно системной настройке. Проверка запускается без пользовательской сессии и реального провайдера.

Из `apps/macos`: `swift test --filter 'DesktopCabinet(RoutePolicy|NavigationRequestPolicy)Tests'` (автоматический тест без установки приложения). До любой сборки/запуска приложения прочитать `docs/agent-guidance/local-development.md`; только `/Applications/GRAF Dev.app`, `dev-harness status → build → promote → smoke`, чистый одобренный SHA.

Из корня: `git diff --check`, `python3 scripts/check_spec_kit_governance.py`; Ruff для измененных Python paths. Браузерная матрица использует установленный Playwright и синтетический HTML, не private sessions.

## Сценарии

1. Free/trial/month/year; no discount/promo valid/invalid; условия и реальный итог видны, оферта непринята, режим продления по FR-019/020.
2. Storage 5/10/15/500 ГБ; upgrade, deferred downgrade, отмена выбора, разные оплаченные периоды; future amount не скрыт.
3. Успех, unknown, pending, failed, canceled, refused, service gap, поздний ответ; реальное следующее действие и отсутствие false success.
4. Счет из истории → существующий status → refresh/continue; annual retry/manual pay сохраняет цикл.
5. Нет verified email/карты, renewal blocked, unavailable checkout; понятное действие без обхода правил.
6. Cancel/resume: срок не теряется, явное согласие, нет препятствий отмене.
7. Web desktop/mobile + embedded route tests; 320/360/768/1280, light/dark, 200%, клавиатура. Проверить runtime JS и реальные CSS; обязательные суммы/согласия видны без details.
8. Три независимых рецензента дают отдельные заключения, исправления перепроверяются. Пять людей по SC-005 — отдельно, не подменять агентами.

## Закрытие

Записать команды, время, SHA/diff и результаты в `validation.md`; запустить converge, оставить невыполненные acceptance задачи открытыми. Commit/PR exact SHA CI, release-full, установленный Dev, человеческая приемка и последующие метрики не выводятся из локальных тестов. F278 финансовая приемка остается отдельной. Реальных платежей без непосредственного согласования не выполнять.

## Дополнительная проверка промокода T014/T015

После основной доставки проверять через одноразовый PostgreSQL новый `tests/integration/test_billing_discount_presentation.py` вместе с применимыми прежними purchase/return/security наборами. История универсальной кампании должна сохранять месяц/год сохранённого счёта после изменения кампании; unknown/malformed/чужой счёт не должен давать ложный месяц. Непригодное предложение не рекламируется. HTTP-цепочка код→месяц→год→очистка проверяет цену сегодня, обычное продление и отсутствие новых платёжных записей.

Существующий browser suite `tests/contract/test_billing_accessibility.py` теперь включает годовую/неизвестную историю, результат применения/удаления и полный кабинет скидок/истории/ошибки. Запускать Chromium и WebKit с установленными Node dependencies; синтетические снимки можно сохранить через BILLING_VISUAL_OUTPUT_DIR. Точные выполненные команды и пределы — [validation-promo.md](validation-promo.md).


## Дополнение: сохранение промокода T016–T019

Сначала воспроизвести сброс в новом focused HTTP/DB наборе `tests/integration/test_billing_promo_refresh.py` на одноразовом PostgreSQL; ожидание сохранения после второго GET должно показать дефект до исправления. Не запускать against live DB, не отправлять реальный платёж и не записывать настоящий код.

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_promo_refresh.py \
  tests/integration/test_billing_discount_presentation.py \
  tests/integration/test_billing_clarity.py \
  tests/integration/test_billing_purchase_journey.py \
  tests/contract/test_billing_security.py \
  tests/contract/test_billing_safety_contract.py \
  -q --tb=short --show-capture=no
```

Матрица регрессий:

1. Применить синтетический код на месяце и годе → следовать 303 → два GET обновления: код, период и текущий итог сохраняются; нет новых invoice/operation/reservation/provider calls, оба оферта непринята, режим продления по FR-019/020.
2. Переход месяц→год→месяц и возврат на исходный checkout URL сохраняют код, но сервер вновь проверяет eligibility и цену. Нет кода, quote или согласий в URL.
3. Отклонённый код длиной до 48 символов после повторного GET остаётся доступен с ошибкой, оплата заблокирована. Отдельно malformed код, non-ASCII и управляющие символы в пределах 48 символов сохраняются через Apply→два refresh как безопасно экранированный ввод; сырых байтов в response headers нет, ошибка понятна, поле раскрыто и оплата заблокирована. Ограничение сверх 48 символов остаётся прежним.
4. Изменить условия/доступность акции между двумя GET: нет устаревшей скидки или тихой обычной цены, новый расчёт требует явного подтверждения. Quotes не переиспользуются как сохраняемое состояние.
5. Пустой preview и существующее удаление очищают текущий выбор; повторный GET без кода. Созданная/восстановленная операция использует авторитетные invoice/operation и не сохраняет выбор для следующей покупки.
6. Подменить cookie, срок или идентичность; перенести/переименовать в другой user/workspace/session; удалить session; подать старую общую raw cookie: код не читается, доступ и финансовые guards сохраняются.
7. Контролируемое время: до 300 секунд выбор читается, на границе/после срока отвергается; GET, смена cycle и ошибки start не продлевают срок. Смена cycle сохраняет code/expiry; возврат без query cycle восстанавливает saved cycle. Атрибуты HttpOnly/SameSite/Secure/path проверены, отсутствующий ключ не разрешает небезопасный fallback.
8. Три независимых заключения по текущим исходникам: путь/тексты, безопасность/финансовые состояния, браузер/доступность. Настоящая DOM-цепочка заполнить/отправить форму → 303 → GET → два reload → back/return проверяется в Chromium и WebKit с изолированной синтетической сессией и локальным тестовым сервером без провайдера; только fixture-снимки не доказывают этот путь. Цепочка включает месяц/год, malformed и исправление/удаление кода, URL без code и непринятая оферта с выбором продления FR-020. Существующие браузерные наборы из раздела выше дополнительно покрывают темы/масштаб/ширины и сохраняемый код/ошибку. Снять границы и ограничения доказательств в `validation-promo-refresh.md` и `review-promo-refresh-final.md`.

Локальные проверки, reviewer-owned PASS, issue sync и convergence предшествуют отдельным PR checks точного SHA. После merge — один новый frozen release-full, сухой прогон CD, deploy, metadata smoke и опубликованный серверный выпуск; текущий frozen кандидат не менять. Владелец уже разрешил технический выпуск. T011/T012 и F278 финансовая приёмка остаются открытыми в их невыполненной части; этот срез не является их повторной задачей.


Браузерный вход из macOS: после штатного native handoff устанавливается обычная проверенная браузерная сессия; дальнейшее применение/обновление проверяется как web-flow. Создание новой сессии handoff не наследует draft старой сессии. Изменений native route policy этот срез не требует; ручная installed macOS приёмка по-прежнему принадлежит T011, только GRAF Dev через harness. Не объявлять её пройденной из HTTP или Playwright.


Настоящий браузерный путь этого дополнения: `tests/browser/billing-promo-refresh.test.cjs` и `tests/contract/test_billing_promo_refresh_browser.py`; запускается из корня с одноразовым PostgreSQL и установленными Chromium/WebKit:

```sh
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
```

Это план проверки будущей реализации: команды ещё не запускались и не являются положительным результатом. Существующая accessibility fixture матрица из раздела выше не подменяет настоящую отправку формы.

### Точная семантика двух вкладок

При переключении периода неизмененный ввод старой формы A (promo_code == previous_promo_code) и текущий действующий подписанный выбор B используют B, сохраняя исходный expiry B. Неподписанная подсказка не разрешает скидку; новые условия B проверяются сервером. Если B уже истек/поврежден/чужой, A не возрождается и показано прежнее объяснение promo_expired. Явное Apply или действительно измененный непустой ввод — намеренная замена и новый срок; явное пустое Apply и remove — удаление. Пустая старая форма при смене периода не является командой удаления нового B.

При входе со страницы скидок без выбранного периода источник — текущий действительный цикл подписки, иначе month; оба исхода valid/invalid сохраняют его. Редактор промокода доступен до подтверждения почты, форма start и денежное действие недоступны. Проверочная матрица: year discounts valid/invalid; tabs A→B→stale A period; empty stale period; explicit A replacement; explicit empty Apply; expired B stale A; no receipt invalid→edit→clear при отсутствии start.

Дополнительная точная приемка: годовой подписчик discounts valid/invalid →303→два reload→URL без query сохраняет year. Две вкладки A/B: устаревший неизмененный/пустой A переключает период после установки B и сохраняет B с прежним expiry; отдельные явные Apply, правка и очистка работают по намерению. Неподтвержденная почта: invalid≤48→редактируемое поле→исправление→смена периода→очистка, start отсутствует и прямой start блокируется. Во всех preview-проверках invoice/operation/redemption0, вызовы провайдера запрещены.

Окончательная проверка после expiry объяснения:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_promo_refresh.py tests/contract/test_billing_ui.py \
  -q --tb=short --show-capture=no
```

В HTTP-проверках управляемого времени Set-Cookie Max-Age проверяется до удержания того же синтетического токена в клиенте: это согласует замороженные часы сервера с тестом. Подписанный expiry и серверный отказ на t300 не изменяются. Настоящий срок браузерных cookies проверяется отдельно в DOM сценариях, где искусственные часы не используются.

Дополнительные сценарии PR7403: текущий B→GET статуса старого failed/canceled счёта→два GET checkout сохраняют B/период/expiry; stale start A после B → прямой409 offer_changed и quote_changed отображает B/его период со свежей ценой, непринятой офертой и выбором продления FR-020, повторные GET не возвращают A; expired/missing/invalid signedB не возрождает A. Финансовые записи и вызовы провайдера отсутствуют.

Смежный303: Bгод/Aмесяц→отказ start сохраняет year в location, draft и двух GET, исходный expiry/Max-Age и t300. Продолжение подтверждённой существующей операции прекращает draft; отказ продолжения не стирает несвязанное оформление.


## Выпускной договор редактора до подтверждения почты

В набор T018 включён `tests/contract/test_billing_clarity.py`: предварительный редактор/Apply связан только с `/billing/checkout/preview`; подтверждение почты доступно, но start, денежные согласия, quote/idempotency и кнопка оплаты отсутствуют. HTTP-регрессии unverified receipt остаются обязательными. Старый frozen 36798151219 завершился FAIL на прежних двух ожиданиях; он не переиспользуется как PASS. Runtime не меняется, DOM-доказательства относятся к прежним неизменным хешам кода; тестовая коррекция требует нового exact-SHA PR и нового frozen Full.


## Необязательное продление — T020–T022

Перед кодом: независимый requirements PASS `checklists/optional-renewal.md`, анализ `analyze-optional-renewal.md`, canon ensure → deduplicated issue sync → canon validate. Данные/провайдер синтетические, реальных денег/кодов/контактов в evidence нет.

1. RED: HTML две галочки — только offer required/unchecked, recurring optional/checked; HTTP month/year×True/False/missing recurring, missing offer отказ без money state. Общий creator strict bool, одинаковый idempotency при восстановлении False, save_payment_method=False.
2. GREEN: request+invoice bool совпадают; проверенный success False выдаёт один grant и один период, no renewal/no new payment method даже если fake provider возвратил saved card; True прежний успех. Уже активное продление+новая успешная False покупка выключает дальнейшее; неуспех не выдаёт права. Существующая старая отмена/owner changed/authority drift/duplicate остаются безопасными.
3. Реальный браузер Chromium/WebKit 320/1280: снять галочку → Apply valid/invalid → month/year → remove → два reload → оферта всегда unchecked, recurring False, итог свежий → offer accept → start в mock provider, False request. Проверить disabled/off summary, keyboard/focus, JS-off нормальную отправку; URL не содержит promo/quote/consents.
4. Off-choice boundary: sessionStorage содержит только true/false, отдельные user/workspace/session keys; unknown value/missing meta/storage failure не ломают текущую форму и не наследуют чужой выбор. Новая вкладка без opener→True; standard opener cloning документируется, отдельная tab identity не добавляется. Creator recovery продолжает исходный bool; no financial state на preview; прежний promo TTL300/signature/binding не меняется.
5. Запуск по существующему синтетическому pytest окружению `tests/contract/test_billing_clarity.py tests/contract/test_billing_ui.py tests/unit/test_initial_checkout_recovery.py tests/unit/test_billing_entitlements.py tests/unit/test_billing_money_path_e2e.py tests/integration/test_billing_review_regressions.py tests/integration/test_billing_promo_refresh.py` и новым сценариям optional renewal; точная команда/browser receipt записывается исполнителем в `validation-optional-renewal.md`.
6. Три независимых заключения current flow/security/browser, converge текущего spec/plan/tasks; новые exact-SHA governance-fast/macos-pr/pr-metadata/common validator, отдельный frozen release-full, CD dry-run/execute, runtime SHA и фактическая публикация. T011/T012/F278 не закрываются; real money/receipt/settlement/refund/human остаются отдельными.

## Отказ создания платежа — FR-021–023 / SC-009

Перед кодом: independent requirements PASS `checklists/provider-rejection.md`, окончательные T023–T025, consistency analyze и canon issue sync. Все финансовые тесты синтетические; реальных списаний, кодов, контактов и идентификаторов в evidence нет.

1. Adapter RED/GREEN: exact403/error/forbidden/известный recurring denied → fixed reason; другое описание403, другой code/type/status, malformed/необъектный JSON, 5xx и timeout → без specific reason. Тестовое тело содержит секретные маркеры в description/id: они не попадают в исключение, snapshot, HTML/аналитику/evidence. Прежний status_code сохраняется. Проверки расширяют `tests/contract/test_yookassa_adapter.py` и `tests/unit/test_initial_checkout_recovery.py`.
2. State/HTTP: True→known denied дает один dispatched POST, no provider_id, operation+invoice canceled с safe reason; promo/budget освобождаются прежним механизмом. Заголовок «Не удалось начать оплату», сообщение об отсутствии начатой оплаты и подсказка вернуться/снять recurring. Старый canceled403 без reason показывает только generic начало отклонено; False с reason, другое403 и подставленный query не показывают подтверждённый отказ автопродления. Existing provider cancellation сохраняет «отменен», known provider_id/unknown/manual_resolution/5xx/timeout сохраняют проверку без нового POST. Расширить существующие `tests/integration/test_billing_return.py`, `tests/unit/test_billing_purchase_observation.py`, `tests/contract/test_billing_ui.py`.
3. Chromium/WebKit, 320/1280, клавиатура: error→existing retry URL с cycle→оформление по-прежнему True, оферта unchecked→ручное False→свежий итог/оферта→явный start→один fake-provider POST/save_payment_methodFalse/redirect. GET/reload/retry сами не отправляют деньги и не меняют режим. Проверить все применимые month/year/скидка и сохранить прежние promo TTL300/binding boundaries; новая операция не возрождает истёкшую скидку и не принимает старый quote. JS-off допускает ручной False, сохранение выбора имеет уже документированные границы.
4. Точный runnable профиль исполнителя записывается в `validation-provider-rejection.md`; перечень существующих suite выше — стартовая область, не заявление о PASS. Три независимых текущих обзора flow/security/browser → устранение применимых замечаний → converge → exact-SHA required PR gates/common validator → отдельный frozen Full → CD dry-run/execute → runtime SHA/публичная страница/выпуск. Live повторное чтение допустимо без списания; реальная финансовая приёмка F278 и T011/T012 сохраняются.

Граница общего UI-признака: schema2/canceled/no provider_id/provider_rejected плюс int HTTP400/401/403/404/405/415/429. Матрица отрицаний включает schema1, bool/строку статуса, unknown class, provider_id и иной state; наличие query provider_unavailable не создаёт доказательства. Предотправочный отказ без сохранённого признака диспетчеризации не объявляется новым generic creation rejection. Для настоящей подтверждённой отмены сохраняется прежняя возможность повторить; запрет новой оплаты относится к неопределённому исходу, а не к подтверждённой отмене.


## Промокод на месте — новый FR-024–030 / SC-010–012

До реализации: `checklists/promo-inline.md` independent reviewer PASS → окончательные tasks T026–T028 → current analyze zero critical/high → canon deduplicated issue sync. Новый scope не переиспользует прежние Full/DOM результаты; reviewer-owned marks заполняет независимый reviewer. Во время подготовки только документы, тесты пока не запускались.

### RED/GREEN и минимальные команды

Добавить регрессии в существующие наборы. Чистые domain tests можно запускать обычным pytest; HTTP/SQL fixtures — только штатным изолированным PostgreSQL, не рабочей БД:

```sh
apps/server/.venv/bin/python -m pytest -q apps/server/tests/unit/test_billing_purchases.py --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_promo_refresh.py tests/contract/test_billing_ui.py tests/contract/test_billing_clarity.py -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
```

При необходимости browser cases отделяются новым параметром внутри существующего harness, не новым bridge. Money path/return/provider denial regressions выполняются по прежним quickstart наборам после changes; новая RED запись обязательна до product изменения. Независимый tests worker владеет регрессиями, root production template/cabinet.js/purchases.py; пересечение заранее согласовать.

### Обязательная матрица нового поведения

1. На320/1280 в Chromium/WebKit: apply мышью/Enter, отклоненный/исправленный код, clear+apply, month/year. Доказать0 main-frame navigation неизменным window/document marker плюс event trace и0 новых history entries; summary/quote/current cycle из реального server ответа. Bridge по-прежнему может записывать preview303→GET200, XHR Playwright видит final200. Native start остается полноценной303 navigation. В адресе/analytics/storage нет code/quote/consent.
2. Исходный `/billing/checkout?cycle=year` → inline month → обычный reload сохраняет month; обратный direction также. Replace текущего URL не создает историю. Проверить сохраненный код/исходный expiry300с, no cookie TTL extension от cycle/GET; quote10мин прежний.
3. Каждый True/False × sessionStorage normal/throws × receipt verified/unverified: Apply/error/correction/remove/cycle несколько раз сохраняют bool там, где money checkbox допустима, сводка соответствует, offer всегда unchecked после нового результата. Session/workspace/user change не наследуют bool; отсутствие meta не создает authority. Unverified receipt допускает редактор, но не start/денежные согласия.
4. Delay и rapid click/start: только один незавершенный preview; input/Apply/cycle/start блокируются до ответа. Нет operation/invoice/promo reservation/provider request от preview. Отдельные wrong method/CSRF/member/owner/session tests остаются FAIL-denial, не ослабляются ради транспорта.
5. Timeout15с, sendError/500/429/swapError: ожидание снимается, есть понятная inline recovery и keyboard focus, прежний start отключен до свежего успешного ответа, offer unchecked. Ни автоматического start, ни принятой ошибочной скидки. Поздний/неожиданный auth/owner/full HTML или scope mismatch не вставляется как checkout; явное восстановление входа/кабинета доступно.
6. Synthetic closed/disabled/expired/missing acceptance campaign дает понятный public отказ без «Проверочное окно оплаты закрыто» во всех relevant callers; remove пересчитывает ordinary customer. Dedicated workspace budget остается blocked даже без promo; сообщение не обещает обход. Final lock/reserve tests подтверждают unchanged conditions и отсутствие денег.
7. Native JS-off: настоящие form POST303→GET, Apply/remove/cycle, цена/ошибка/оферта и receipt/owner защиты; не требовать unavailable междокументного storage persistence. Keyboard/focus/status/a11y и320px/200% обе темы; fixture screenshot не подменяет реальные маршруты.

### Запись доказательств и выпуск

`validation-promo-inline.md` хранит точные команды, SHA/hashes, RED и окончательные GREEN/count/duration/SQL cleanup, браузерные traces без секретов/кодов, неуспешные попытки отдельно. Три независимых текущих flow/security/browser review → исправления/перепроверка → `converge-promo-inline.md` без missing обязательной работы. После этого exact-SHA PR checks и validator, frozen release-full, CD dry-run/execute с прежним разрешением, runtime/publication evidence и `release-promo-inline-closeout.md`; публичный подписанный macOS пакет не перевыпускать этим server change. Реальные платежи/чеки/банк/возврат, GRAF Dev/люди/конверсия и T011/T012/F278 остаются отдельными, не закрываются synthetic PASS.


## Проверка возвращения после оплаты — F280 (2026-10-03)

Предусловие реализации: независимый PASS `checklists/payment-return.md`, окончательные T029–T031, анализ и canon issue sync. Настоящая база PostgreSQL, сервер ASGI и synthetic provider; production payment за пользователя не создавать. Проверять текущую реализацию, не статическую подставную страницу.

1. Chromium и WebKit, 320/1280 CSS px: существующий pending → provider succeeded, локальный доступ применен. После return страница сама показывает «Оплачено», действительный тариф/сумму/срок и «К встречам». Проверить постоянный document marker, отсутствие document navigation и новых payment/invoice/operation/provider create calls.
2. Provider pending: первичное «Проверяем оплату»/«Повторно платить не нужно», один POST, максимум6/60с, начала≥10с. После исчерпания — ручная проверка, допустимый continue вторичен; swap/reinit счетчик не сбрасывает. Двойное нажатие/инициализация не дают пересекающихся запросов.
3. Pending → canceled и provider succeeded → непримененный доступ: разные достоверные экраны, автоматическая проверка остановлена, нет повторной оплаты/ложного активного тарифа. Stale POST continue проверять для первоначального и остальных типов покупки; завершенная invoice с прежней pending operation тоже не переходит к провайдеру.
4. Network/HTTP401,403,429/error/неправильный контекст/поздний HTML: остановка, понятная ручная помощь, чужой/неожиданный экран не вставлен. Уход/hidden/возврат visible прекращает прежнюю sequence. Длинный запрос вызывает15с timeout; сервер может продолжить, поэтому до безопасного локального чтения/явного восстановления новый POST не отправлен. Проверить отрицательные финансовые эффекты.
5. JS-off: native POST refresh/303/GET показывает тот же подтвержденный успех или честное ожидание; CSRF/owner/tenant/rate protections реально проверены. Обычный GET return/status не делает provider call/финансовых записей.
6. Клавиатура/видимый focus, status announcement без повторной озвучки одинакового pending, 200%,light/dark; существующее применение промокода без reload и выключенное продление проходят regressions.
7. Три независимых обзора и повторная проверка исправлений, converge; точные PR checks/Full/CD/runtime/publication по общей процедуре. Считать отдельно технический выпуск и доступные факты настоящей оплаты владельца. Не закрывать T011/T012/F278 из browser/provider тестов.

Для FR-038 после установления причины повторить delayed webhook/refresh на существующем succeeded payment: локальный статус и доступ должны согласоваться через штатную транзакцию, повторная сверка не создает дополнительный grant/payment. Отдельно проверить live read-only evidence после выпуска; симуляция не закрывает наблюдавшийся настоящий разрыв.

Дополнительная projection regression: invoice/operation success без связанного grant не показывает обычный paid экран; исторический success с grant и истекшей текущей подпиской остается «Оплачено» с исходным оплаченным периодом. Для storage проверяется существующий факт применения покупки, а не несуществующий subscription grant.


T035 дополнительно: шестой protected refresh начинается около50с; подтверждение приходит после60с, но до собственных15с — результат принят, grant1, нового payment/invoice/operation и седьмого автоматического старта нет. Отдельно ответ после собственных15с отвергается и остается локальное GET восстановление. Проверить оба engine/ширины, один запрос и неизмененный document.


T036: после пяти начал0/14/28/42/52с и последнего pending ответа53с пересечь60с без запроса в работе; автоматическое ожидание должно явно закончиться, ручная проверка видима, новых POST нет. Causal RED/GREEN Chromium/WebKit320/1280 фиксируются в validation-payment-browser.md.


T037: ответ pending после14с должен естественно отправить следующий POST только подготовленной форме; никакого ручного reinit в тесте. Сохранить настоящие HTTP/SQL/контекст/документ и финансовые отрицательные проверки. Сначала подтвердить устранение причинного RED T037, затем получить самостоятельный idle deadline RED T036 до изменения его callback.


T038/T039 дополнительно: быстрый pending ответ оставляет честно недоступную до10с ручную кнопку с видимым пояснением; после интервала и окончания автоматической последовательности ручной protected POST действительно отправляется. Проверить фокус continue/details/invoice/billing/help, перенос фокуса внутри и вне main во время запроса, раскрытые details непосредственно перед swap и исчезновение continue при реальном синтетическом success. Окончательная browser→ASGI→PostgreSQL матрица T038–T040 содержит28групп ×320/1280 в каждом Chromium/WebKit; прежние сценарии сохранены. Каждый окончательный прогон привязать к неизменным SHA256 cabinet.js/template/Node test/Python bridge; смешанный исходник или прерванный прогон не PASS.


T040: текущие session/user/workspace/invoice меняются на том же физическом main во время удержанного ответа; без искусственного reinit отклонение должно дать явный alert, блокировку старых форм и local GET. Уже заменённый main не меняется старым запросом. Реальная операция на сервере может завершаться штатно; браузерное отклонение HTML не отменяет финансовую обработку. Проверить также native disabling исходной кнопки → пользователь фокусирует другой элемент → latest focus сохраняется; CSS/readable disabled appearance и aria-describedby до/после разрешённого начала. Новую финальную матрицу привязать к точным неизменным bytes после T040;44+44 v4 относятся к промежуточному срезу.

T040: во время удержанного ответа изменить по отдельности текущего пользователя, пространство, сессию и счёт без reinit. На том же физическом main ответ отвергается, немедленно видны alert и локальная GET-ссылка, формы заблокированы и нового POST нет. Если main уже заменён настоящей другой страницей, прежний ответ не меняет новый узел. Дополнительно проверить вычисленные прозрачность/курсор кнопки и aria-describedby; исходную отключённую кнопку → пользовательское перемещение фокуса → сохранение последнего выбора. Историческая матрица54/54 описана в validation-payment-return-t038-t040-browser.md; окончательная56/56 после T041 — в validation-payment-return-t041-browser.md.


## Простое управление подпиской — US4, FR-039–045 / SC-014

До кода независимый reviewer полностью проверяет `checklists/subscription-clarity.md`. Затем окончательные T046–T048, analyze и GitHub issue sync. Проверки используют синтетический аккаунт/одноразовый PostgreSQL, реальные templates/CSS и установленные Chromium/WebKit. Не использовать live payment provider или частную сессию; не проводить новые платежи/списания/возвраты/grants.

Из корня, focused HTTP/DB регрессии в существующих clarity/purchase/security наборах:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_clarity.py \
  tests/integration/test_billing_purchase_journey.py \
  tests/contract/test_billing_security.py \
  tests/contract/test_billing_safety_contract.py \
  -q --tb=short --show-capture=no
```

Из `apps/server`, существующий browser accessibility набор для обоих движков:

```sh
uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
GRAF_BROWSER=webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
```

1. Зафиксировать исходный active/auto-off/no-card synthetic HTML baseline a7553db61b2625e767b3afa147c7b61c097fe918; подсчитать видимые поясняющие слова при закрытых details, исключая labels/числа/даты/навигацию. После изменения сравнить тот же fixture: ≥50% сокращение. Карточка и main CTA согласованы с SC-014; месяц/год сохраняются в GET href, точная локальная дата доступна.
2. Route→DB проверяет active off/no method и trial/free/expired/неизвестный срок; реальная effective plan проекция. GET не создает invoice/operation/provider calls и не включает recurring; существующая подготовка resume quote при ready не считается денежной операцией. Resume/cancel/early сохраняют authority version/quote/CSRF/owner/tenant и предыдущие финансовые assertions.
3. On: сумма/дата попытки и отмена доступны без раскрытия; off/ready: раскрыть resume, увидеть сумму/полную дату/карту и непринятое required consent. Stale version/quote/чужая сессия/роль отвергаются; пропущенное согласие не включает списание. Ошибка early-preview раскрывает existing форму; выбранный следующий объем и подготовленное списание правдивы.
4. Pending/unknown/unknown_pending/key expired с pending amount и без него для renewal/early_renewal/initial_checkout/storage_upgrade, price/contact/method restrictions и отключенная оплата: реальные notices/пути проверки сохраняются, нет доступных новых/manual/early/resume действий при неподтвержденном списании. Не скрывать неопределенность либо утверждать «не списано».
5. Реальные браузеры320/1280, светлая/темная тема, клавиатура/видимый фокус и200%; main CTA не перекрывается, нет общей горизонтальной прокрутки. Native details keyboard и JS-off позволяют раскрыть сведения, открыть карту/историю и использовать защищенные формы. Синтетические снимки подтверждают только перечисленные условия.
6. Три независимых текущих обзора (понятность/тексты, финансовые состояния/guards, браузер/доступность), исправление и повтор замечаний; затем converge. Evidence в `validation-subscription-clarity.md`, `review-subscription-clarity-final.md`, `converge-subscription-clarity.md`; release evidence отдельно. Проверить `git diff --check`, governance и применимый Ruff; exact-SHA PR checks и новый frozen release-full/CD/tag/runtime/publication после этого.

SC-005/006/T011/T012/F278 остаются отдельными; эта проверка не доказывает реальные будущие списания, чек/банк/возврат, человеческую приемку либо рост конверсии. Для ручного/сквозного macOS допускается только GRAF Dev и штатный harness по `local-development.md`; изменение native route policy не требуется.

### T049: прежняя сквозная проверка полного срока

Перед окончательными PR gates выполнить существующий изолированный денежный набор:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_money_path_e2e.py -q --tb=short --show-capture=no
```

Короткая локальная дата остается в основных фактах, полный срок/время/зона в закрытом native «Способ оплаты и условия»; не ослаблять webhook/reconcile/paid-through/recurring и первую попытку72h. Причинный RED179/1 и окончательный full71PASS сохранены в validation-subscription-clarity.md, независимый review-subscription-t049.md.

T050: `apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_return.py -q --tb=short --show-capture=no` — full82PASS0skips. Не ослаблять проверку off состояния, возможности завершения старого платежа, отсутствия ложного обещания и exact result-link. Независимый review-subscription-t050.md.

T051: expired ключ сам по себе не вводит новый запрет; provider_key_expired/observation_expired сохраняют действующую общую политику, manual_resolution остается блокирующим. Проверить method_required с manual_resolution и provider_id None/известным: проверка карты и результата видны, утверждения отправки нет, новые действия/quote/provider calls отсутствуют. Реальный PostgreSQL и оба браузера; RED/GREEN и независимый refresh требований/source review.

## Продолжение «Платеж и чек», 2026-10-04

На одноразовом PostgreSQL, не live DB, выдуманные номера/контакты/карты, никаких действующих payment provider/mail/refund операций:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_clarity.py \
  tests/integration/test_billing_review_regressions.py \
  tests/integration/test_billing_return.py \
  tests/contract/test_payment_history_support.py \
  tests/contract/test_billing_purchase_ui.py \
  tests/contract/test_billing_safety_contract.py \
  tests/unit/test_billing_copy_and_redaction.py \
  -q --tb=short --show-capture=no
```

Дополнить имеющийся тестовый файл focused invoice projection/read-only cases, если он не покрывает требования; не делать параллельную систему fixtures. Сначала причинный RED для неправильной темы и отсутствующей даты/краткого периода; GREEN после изменения. Фактические результаты и точные команды записать в `validation-invoice-consistency.md` (новый canonical report), не объявлять весь старый набор свежепройденным.

Из `apps/server`:

```sh
uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
GRAF_BROWSER=webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short
```

Дополнить существующие `tests/contract/test_billing_accessibility.py` и `tests/browser/billing-accessibility.test.cjs` invoice synthetic contexts, если ещё отсутствуют. Матрица320/390/768/1280, light/dark,200%, клавиатура; native details, оба mailto намерения без отправки, номер copy, service-gap вне details, receipt/no-URL, long masked fields и множественные storage intervals. Отдельный HTTP JS-off подтверждает доступность документа/помощи/раскрытий без client money mutation. Если status template меняется, повторить действующий `tests/contract/test_billing_payment_return_browser.py` в Chromium/WebKit через его штатный documented runner и полный текущий status matrix, не ослабляя assertions/лимиты.

Сверить число финансовых записей до/после GET, как минимум owner/foreign workspace/changed owner privacy, malformed period/unknown cycle, UTC-cross-midnight и viewer-local date. Не использовать реальные данные карточек/кодов/встреч в evidence.

Рутинно: `git diff --check`, Ruff по измененным Python файлам, `python3 scripts/check_spec_kit_governance.py`. До кода: независимые требования PASS, separate analyze0/0/0fixablemedium, canon issues sync. После кода: независимые требования/source/browser обзоры с фактическим current SHA, converge. GitHub checks на точном PR SHA и base через текущий validator.

GRAF Dev занят другим срезом; не собирать/не запускать/не promote без согласования. Web synthetic и серверные проверки не объявлять установленной приемкой. После обоих merged PR release оператор выбирает новый незанятый CalVer, замораживает один candidate, получает release-full PASS, выполняет dry-run и авторизованный execute, проверяет публичное/live здоровье и текущий защищенный UI только чтением, записывает `docs/deployments/2brain-rec/release-v<selected-CalVer>.md`. Прежний/чужой draft не изменять. Любая новая code change инвалидирует прежний SHA-bound gate.

T057: на existing regression fixture добавить modern manual_resolution без provider_id для initial_checkout/storage_upgrade/renewal/early_renewal, has-subscription True/False. Перед/после GET counts/states одинаковы, create provider0, безопасный status URL виден, новые checkout/resume/early скрыты; causal RED→GREEN. Изолированный targeted+full regression file, полный test_billing_return82 после только semantic literal исправления, contract UI, Chromium/WebKit и independent source/browser/UX. Не менять денежные assertions или retry limits. T051 historical evidence сохраняется, новый SHA требует своего PR proof.
