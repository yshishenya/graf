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

1. Free/trial/month/year; no discount/promo valid/invalid; условия и реальный итог видны, согласия пусты.
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
