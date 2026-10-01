# Проверка необязательного автопродления F280

Дата: 2026-10-01. Ветка: `codex/280-payment-optional-renewal`. Базовый SHA: `14fa81f4fff91b2158eaf1afb456713c50692300`. Режим: `high-risk-product` и последующий `release-deploy`.

Допуск требований: reviewer-owned43/0 +builtin8/0, итого51/0; [независимое заключение](review-optional-renewal-requirements.md). [Анализ](analyze-optional-renewal.md) выполнен после окончательной генерации T020–T022, findings0. Task-to-issue sync: поиск feature280/T020–T022 и результата не нашёл дублей; [#7408](https://github.com/yshishenya/graf/issues/7408) покрывает T020–T022. Обязательные canon ensure и canon validate выполнены, последний PASS300. Umbrella7366 и F278/T011/T012 не закрываются.

## Исходная проверка

До изменений production на `002c15d34975edff3b8029a0dc496952188ad165`: public checkout включён, YooKassa production и ожидаемый магазин подтверждены безопасной проверкой настройки. Три службы running; rec-api и rec-processing-worker healthy; rec-maintenance без healthcheck. Эти сведения относятся к прежнему выпуску v2026.10.01.1 и не подтверждают новую реализацию.

## Новая реализация и проверка

Изменены четыре существующих исходника: optional default checked в форме; actual bool в снимках и save_payment_method; строгий True для записи нового способа оплаты; визуальный bool в sessionStorage текущей вкладки по user/workspace/session. Оферта required/unchecked. Шаблон без JavaScript обозначает будущую сумму условно. Общий HTTP/PostgreSQL набор выполнен после объединения. Окончательные браузерные проверки записаны ниже; независимые обзоры и PR/Full/CD/runtime/publication записываются отдельными этапами; прошлый выпуск их не подменяет.

## Серверные регрессии T020

До исправления: recovery/entitlements RED8 FAIL/33 PASS за0.47с по ожидаемым причинам — False отвергался общим создателем, а неожиданная saved карта записывалась без строгого разрешения. После исправления:

```sh
cd apps/server
.venv/bin/python -m pytest tests/unit/test_initial_checkout_recovery.py tests/unit/test_billing_entitlements.py tests/unit/test_billing_lifecycle.py -q --tb=short --show-capture=no
```

GREEN49 PASS за0.22с; два прежних предупреждения fixtures/Starlette-httpx. Ruff для пяти backend Python paths и diff check PASS. Коллекция money-path71 прошла, но отдельно не считается исполнением. Money-path дополнен month/year×True/False/omitted, saved-card surprise, противоположным выбором повторного POST до/после результата и переходом из продлеваемого месяца в разовый год с сохранением остатка/прежней карты. Изменённые source SHA256:

- billing.py: `bf6d4cfbeb154eb875063d7e200fec83801fcce4ff066b614a53793594dc083d`
- entitlements.py: `83f43809f9ec736e028a9d1bcbd9311afa19d7fb0cad195676fba27c1ad0b14b`

Общий HTTP/PostgreSQL запуск выполняется на одноразовой БД и синтетическом провайдере:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_billing_money_path_e2e.py tests/integration/test_billing_review_regressions.py \
  tests/integration/test_billing_promo_refresh.py tests/integration/test_billing_discount_presentation.py \
  tests/integration/test_billing_return.py tests/integration/test_billing_purchase_journey.py \
  tests/integration/test_billing_clarity.py tests/contract/test_billing_clarity.py \
  tests/contract/test_billing_ui.py tests/contract/test_billing_security.py \
  tests/contract/test_billing_safety_contract.py -q --tb=short --show-capture=no
```

Первый прогон:465 PASS/2 FAIL за324.45с (runner330с), collection467/digest2252f37f96c07260384e0dfe915ff82eb375ae42841ce7f38df3e10157de9f06. Оба отказа — прежнее ожидание пустых обеих галочек после подтверждения почты в test_billing_return.py:172, варианты web/embedded. Прежний assert заменён отдельными проверками required/unchecked offer и optional/checked recurring; проверки свежего годового периода и отсутствия денег сохранены. Runtime не менялся. Повтор всего test_billing_return.py:82 PASS/2 прежних warnings за63.73с, runner69с, collection digest355468009a2a415ee678c6b52e5aaf6aca2ecc32382c033337be12cf75e5ebba. Две ошибки исправлены и перепроверены; первый прогон не называется467 PASS. Обе изолированные БД удалены. В живую БД тесты не направлялись; реальных provider requests нет.

## Статические проверки и подготовка проверки установленного модуля

Ruff всех изменённых Python-файлов, Node syntax check cabinet.js и двух browser scripts, git diff --check, check_spec_kit_governance.py и validate-changelog-fragments.py — PASS. Синтетическая проверка initial helper: False/True × два вызова сохраняют выбор и исходный ключ, null/числа/строки отвергаются до провайдера — PASS; БД/реальных provider calls0. Первоначальный проверочный скрипт не задавал синтетический налог и был отвергнут receipt guard; скрипт исправлен явными tax_system_code2/vat_code1, production код не менялся. Проверка после развёртывания остаётся отдельной.

## Окончательные проверки интерфейса T021

UI RED:5 ожидаемых отказов до изменения исходников. Текущие clarity/UI:69 PASS. Accessibility и состояние вкладки: Chromium16 PASS26.20с; WebKit16 PASS32.82с. Проверены клавиатура, OFF сводка, два reload, явное повторное включение, HTMX/pageshow, отдельная обычная вкладка, user/workspace/session, неизвестное сохранённое значение, отсутствие scope, отказ storage и native submit без JS в обоих режимах.

Настоящие DOM→HTTP→PostgreSQL verified сценарии на320/1280: окончательный Chromium1 PASS82.45с/runner91с; WebKit1 PASS173.89с/runner182с. Перед start финансовых записей/provider вызовов0. Отсутствующая оферта303 и устаревшая оферта409 сохраняют False; затем один разрешённый start создаёт ровно одну operation и invoice900000minor/year с recurring=False, offer=True, один synthetic provider request save_payment_method=False. Unverified сценарии также прошли: финансовая форма/операции/provider отсутствуют. Chromium первоначальный полный verified/unverified2 PASS79.79с, WebKit unverified127.76с; пересекающиеся наборы не суммируются.

Исторические отказы UI bridge: DNS после перехода на синтетический yookassa.test устранён перехватом настоящего POST, проверкой303/Location и локальным тестовым документом без внешней сети; WebKit startup timeout до первого HTTP и финальная windows-1251 декодировка документа не объявлены PASS. Последнее воспроизведено отдельно, в тестовый документ добавлен meta charset UTF-8; реальный base.html уже UTF-8. Никаких product source изменений по этим сбоям. Финальные повторы обоих браузеров прошли с одинаковыми frozen bytes. Очистка одноразовых БД подтверждена. Подробный отчёт исполнителя и SHA25610 файлов перенесены в review-optional-renewal-final.md; никакого реального платежа этими результатами не доказано.

Повторный независимый requirements review после уточнения FR003/contract/namespace: текущий51/0, reviewer-owned43/0; UX CHK003 согласован независимым reviewer. Отчёт review-optional-renewal-requirements.md сохраняет исторический и текущий снимки отдельно.

## Независимые заключения и состояние задач

Три независимых reviewer, не авторы исходников: optional_renewal_trace (flow), optional_renewal_security (финансовая/защитная логика), promo_unavailable_browser (DOM/снимки/JS/noJS) — scoped PASS, конкретных незакрытых замечаний0. Полные заключения и frozen source hashes сохранены в review-optional-renewal-final.md. T020/T021 завершены; T022 открыт до новых exact-SHA PR/Full/CD/runtime/publication. Реальные F278/T011/T012 не закрываются.

## Дополнительное статическое ожидание после PR проверки

Первый exact-SHA governance-fast36908074789 на83bf12da81e622ae3d46b6c0b302f1c667905d3e завершился FAIL:100PASS/1FAIL в test_cabinet_static_assets_contract.py::test_cabinet_js_keeps_fragment_state_ephemeral, устаревший literal15 вместо17 sessionStorage после разрешённого FR020. Отказ не игнорировался. Узкая test-only коррекция выделяет renewal block: ровно2get/set вызова, strict true/false, существующие3scope, только String(checkbox.checked), noJSON.stringify; вне блока прежние15 и все остальные guards сохраняются. Product source/browser tests не изменились.

После исправления полный static-assets/settings набор101PASS3.34с,2 прежних warnings; Ruff изменённого файла PASS. Три независимых узких заключения и новый PR SHA/CI записываются ниже; старый failed run не используется для допуска.

Узкие независимые flow/security PASS: статический тест сохраняет прежний лимит вне блока, строгий bool/scope/get/set/noJSON внутри; все runtime hashes прежние. Оба отчёта сохранены в review-optional-renewal-final.md. Новых требований/изменений кода0; converge актуализирован.
