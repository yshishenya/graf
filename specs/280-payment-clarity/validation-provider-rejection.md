# F280 — проверка отказа начала оплаты

Дата: 2026-10-02. Lane: active Spec Kit slice / high-risk-product; далее release-deploy. Ветка `codex/280-payment-provider-rejection`, base `8764f29f3a3c18cc348986ee7c498e9381ec703e`. Pre-code: reviewer requirements61/0, analyze CRITICAL/HIGH0, deduplicated issue7414 canonPASS.

## Изменение и границы

Известный отказ создания сохраняет только fixed reason. UI читает авторитетные schema2/canceled/no-provider/provider_rejected/int safe HTTP; specific дополнительно initial_checkout/True/403/known reason. Старый query не перекрывает сохранённую причину. Подсказка и ссылка не создают платёж и не снимают согласие. Форма остаётся defaultTrue и required unchecked offer. Финансовые переходы, расчёты, idempotency, право владельца, CSRF/RLS и promo/budget не изменены.

Все финансовые проверки synthetic: httpx.MockTransport, настоящий ASGI и одноразовый PostgreSQL, реальные HTML-формы в Chromium/WebKit. Внешние запросы браузера запрещены. Никаких реальных платежей, чеков, банковского зачисления или возврата.

## Исторический RED и устранённые ошибки тестов

До production patch adapter/recovery:20FAIL/25PASS,0.60с; причина — отсутствие reason constructor/adapter. После patch:45PASS0.29с; независимый security reviewer повторил45PASS0.37с. Исходный fail-before сохранён в `/tmp/graf-f280-provider-tests-red.md/log`.

Первый общий HTTP профиль:31FAIL/348PASS214.86с (collection379). Тридцать ошибок — неверные новые ожидания общего CTA/unknown текста; runtime исправление не менялось ради них. Оставшийся409 вызван старой импортированной версией теста без promo_code: discounted quote сравнивался с full-price start. Переданный ownership уже содержал поправленные поля. Отдельный retry показал неверное сравнение query при idempotent redirect, затем56 случаев55PASS/1FAIL99.61с выявили семь POST при настоящем limit5/15min. Ожидания исправлены: сравнивается путь того же счёта, количество duplicatePOST сокращено до2 всего (5 startPOST), все GET/SQL/no-extra-provider assertions сохранены. Защиты цены и частоты не менялись. Подробности — [review-provider-rejection-test-repair.md](review-provider-rejection-test-repair.md).

Попытки прежних CLI исполнителей были заблокированы их средой до запуска Docker/browser. Эти результаты не заявлены PASS и не требуют пользовательского разрешения: root выполнил runner в доступной среде.

## Завершённые проверки

| Проверка | Результат |
| --- | --- |
| Общий HTTP/SQL/contract/observation/adapter/recovery/money-path |450PASS315.82с; runner322с, cleanupPASS |
| Chromium: existing promo + recurring/generic/uncertain ×320/1280 |8PASS164.24с |
| WebKit: та же матрица |8PASS233.14с |
| Accessibility Chromium, включая fixture/native JS-off |16PASS33.97с |
| Accessibility WebKit, включая fixture/native JS-off |16PASS44.48с |
| Security/entitlements |38PASS1.59с |
| Synthetic screenshot recurring320 Chromium |1PASS14.64с; оба снимка просмотрены root |
| Ruff, JS syntax, git diff --check, Spec Kit governance |PASS |

Collection8 digest обоих browser: `5aa773da6b14d426cc012272836ddff4ae7b256a008980b7f134dd4594fcb1c1`. JS-off — нативная required/serialization fixture, не полный HTTP→SQL финансовый путь. Снимки synthetic находятся только под `/tmp/graf-f280-provider-browser-screenshots/recurring/`; содержимого живого кабинета в git нет.

## Точные runnable команды

Из корня репозитория:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
 tests/integration/test_billing_review_regressions.py \
 tests/integration/test_billing_clarity.py tests/integration/test_billing_return.py \
 tests/contract/test_billing_ui.py tests/contract/test_billing_clarity.py \
 tests/unit/test_billing_purchase_observation.py tests/contract/test_yookassa_adapter.py \
 tests/unit/test_initial_checkout_recovery.py tests/unit/test_billing_money_path_e2e.py \
 -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_billing_security.py apps/server/tests/unit/test_billing_entitlements.py
```

Из `apps/server`:

```sh
GRAF_BROWSER=chromium .venv/bin/python -m pytest -q tests/contract/test_billing_accessibility.py
GRAF_BROWSER=webkit .venv/bin/python -m pytest -q tests/contract/test_billing_accessibility.py
```

Три независимых текущих PASS и хеши — [review-provider-rejection-final.md](review-provider-rejection-final.md). Не складываем перекрывающиеся counts. Предупреждения pytest прежние: rewrite PostgreSQL fixture и Starlette/httpx deprecation.

## Следующий этап

Общий профиль завершён450PASS; collection450, digest `ff6b4bf65bf14bd71c45b2b76cad8b61f7eafffc1cc59b95ffd505156ab488f1`, focused statuspass и isolated container removed. T023/T024 завершены по текущим доказательствам; source-converged, новых задач0. T025 требует exact-SHA PR checks/common validator, новый frozen release-full, dry-run/execute, runtime SHA/source hashes и publication. Подключение автоплатежей у YooKassa отдельно; живая разовая оплата False пока не подтверждена. F278/T011/T012/#7366 остаются открытыми, текущие проверки не доказывают конверсию/удержание.
