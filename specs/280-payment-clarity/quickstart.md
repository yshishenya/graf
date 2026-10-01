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
