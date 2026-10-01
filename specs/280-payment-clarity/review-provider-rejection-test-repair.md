# F280 — исправление ожиданий новых integration проверок

Ownership: только `apps/server/tests/integration/test_billing_review_regressions.py`, текущая рабочая копия `/Users/yshishenya/.codex/worktrees/release-f280/crisp`. Production, GitHub, commits и документация не менялись. Lane: active Spec Kit slice / high-risk-product.

## Что исправлено

- CTA различается по доказанной причине: specific recurring — «Вернуться к оплате», generic rejection — «Попробовать снова».
- Unknown/manual сохраняют существующее объяснение «Подтверждение еще не получено. Повторно платить не нужно.» и кнопку проверки статуса, без нового пути оплаты.
- Idempotent replay сравнивает путь того же счёта через urlsplit: первый отказ дополняется старым query result, повтор восстанавливает тот же invoice path без query. Query не влияет на сохранённую причину отказа.
- Retry сохраняет две проверки GET до и после manual и два повтора original POST (один до manual, один после), вместо четырёх избыточных повторов. Всего пять POST укладываются в настоящую защиту `billing_checkout_start:5/15min`; защита не отключалась и не изменялась.
- Для первого POST assertion дополнен response.text, чтобы возможный409 был объяснён существующим экраном offer_changed/quote_changed.

## Причина прежнего409

В журнале автора `/tmp/graf-f280-provider-tests-agent.log` старые варианты `first_fields`/`manual_fields` (строки7324/7363 и повторения до13855/13894) строились через `checkout_start_fields`, который возвращает только cycle/idempotency_key/quote_id/offer_version. Промокод из скрытого поля в POST отсутствовал: сохранённый quote имел скидку, новый POST рассчитывал полную сумму, сервер правильно отказал409. Затем автор добавил явный `promo_code:SYNTHFIRST` (14302/14343 и далее). Root379 запуск начался во время работы автора и выполнил ранее импортированный код; несовпадение номера строки traceback с текущим source подтверждает последующую правку файла. При нашей передаче ownership эти поля уже исправлены; production не нуждается в ослаблении quote validation. `_approved_personal_catalog` читает PostgreSQL при каждом вызове, кэша нет; test client очищает cookies/headers/settings/storage между тестами.

## Выполненные проверки

1. `/tmp/graf-f280-provider-repair-retry.log`: отдельный retry1 дошёл после начального POST303 до следующего ошибочного equality query; 409 не повторился. Результат1FAIL, не PASS.
2. `/tmp/graf-f280-provider-repair-focused.log`: все56 новых случаев —55PASS/1FAIL,99.61s. Единственная оставшаяся ошибка — KeyError Location в последнем duplicate:7POST превышали существующий limit5. Исправлена количеством повторов без обхода защиты.
3. Ruff и git diff --check принадлежащего файла —PASS.
4. Полный прежний379 профиль +money_path_e2e71: **450PASS/0FAIL**, 2 прежних предупреждения,315.82s (runner322s), exit0. `/tmp/graf-f280-provider-repair-combined.log`; exec session96148 завершена. Collection450, digest `ff6b4bf65bf14bd71c45b2b76cad8b61f7eafffc1cc59b95ffd505156ab488f1`. Все56 новых случаев и yearly retry успешно проверены вместе с остальными тестами. Runner подтверждает `postgres_test_result=pass mode=focused partitioned=false shard=none` и `postgres_test_cleanup=isolated_container_removed`.

Команда:
```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py tests/integration/test_billing_clarity.py tests/integration/test_billing_return.py tests/contract/test_billing_ui.py tests/contract/test_billing_clarity.py tests/unit/test_billing_purchase_observation.py tests/contract/test_yookassa_adapter.py tests/unit/test_initial_checkout_recovery.py tests/unit/test_billing_money_path_e2e.py -q --tb=short --show-capture=no > /tmp/graf-f280-provider-repair-combined.log 2>&1
```

Current SHA256: bb88bb3272f7cce9afb195cf265580d87e77db2753b6d37555d6131c9077cc1d

Все проверки synthetic, одноразовый PostgreSQL и httpx.MockTransport. Реальных платежей/финансовой приёмки нет.

READY_GREEN_HTTP_COMBINED_450
