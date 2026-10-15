# F280 — регрессии полной проверки выпуска

Дата: 2026-10-03. Lane: high-risk-product, T045.

## Исходный отказ

Frozen candidate `rc-20261003T074537Z-9d35a3702d7c`, source `e1012f98ed268691ef251087222474708257f2ce`, release-full **37107429605 — FAILURE**. Прошли strict/performance PostgreSQL, static/governance и macOS; пять параллельных групп завершились отказом. Выкладки и публикации этого кандидата не было. Неизменённые manifest/reservation и артефакты сохранены как исторический неуспех; повторного запуска того же кандидата нет.

Из metadata timings восьми групп найдены8 failed call:6 в `test_billing_review_regressions.py`,1 в `test_billing_usability.py`,1 в `test_web_owner_session_context.py`.

## Причинное локальное воспроизведение

Настоящий изолированный PostgreSQL, source e1012f98, без изменений кода:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
 tests/integration/test_billing_review_regressions.py \
 tests/integration/test_billing_usability.py \
 tests/integration/test_web_owner_session_context.py \
 -k 'test_creation_rejection_status_uses_only_authoritative_snapshot or test_rejected_creation_releases_reservations_but_unknown_result_keeps_them or test_operation_status_does_not_offer_checkout_when_billing_is_disabled or test_personal_owner_continues_existing_checkout_without_second_operation' -q
```

**RED:8 failed /49 passed /170 deselected**,55.48с; collection57, digest `4b9f512831fdf0f28a525f295397935eb163d9028dbe48c202727c9a5e6f64f7`. Изолированный контейнер удалён. Временный журнал `graf-f280-full-failures-red.log` не представлен публичной ссылкой.

Семь отказов ожидают прежние строки «Проверить статус»/старое пояснение, заменённые FR032/036. Финансовые assertions этих проверок остаются необходимыми. Один настоящий дефект: общий guard invoice.pending заблокировал прежнее идемпотентное восстановление legacy initial_checkout при invoice.manual_resolution, отсутствующем provider_id и действующем прежнем ключе.

## Допуск и исправление

Два независимых requirements обзора разрешили только сохранение существующего legacy восстановления; checklist перечитан17/0. Новый helper одинаково применяется GET/POST, требует совпадающие invoice/operation/workspace/целочисленную сумму/RUB для manual_resolution и весь прежний _initial_checkout_can_continue. GET не пишет финансовые данные. Сервер игнорирует подставленные amount/recurring/key; повторяет прежний сохранённый запрос, второй invoice/operation не создаёт.

Fallback без provider_id показывает «Проверяем оплату», честное неизвестное состояние, основное локальное «Обновить результат» и вторичное quiet продолжение. Автоматическое создание/refresh этой ветки не включаются. Два SOURCE/TEST reviewers независимо нашли старый заголовок; исправление S1 сохранено в истории обзоров и проверено GET route матрицей.

## Проверки

- Исходный причинный набор57 после исправления: **57 passed /170 deselected**,56.68с; `graf-f280-full-failures-green.log`.
- Owner матрица25: положительные scheduled/unknown/manual_resolution/pending/отказ от recurring; отрицательные terminal invoice/operation, schema2, provider_id, kind, expired/missing key, actor, amount/currency. GET purity, CSRF protected POST, прежний ключ,1000RUB, original recurring, grant0,1invoice/operation, повтор continue без второго provider create. Окончательный набор с h2/пояснением/no success/no auto-check: **25 passed /85 deselected**,19.23с; collection25/digest `cfea8b8170aae5db3f709688f212a9543b26bc9c43d5d8ea7735fca410ed0250`, `graf-f280-t045-owner-final.log`.
- Шесть полных файлов review_regressions/usability/owner_session/clarity/return/purchase_journey: первый прогон **410 passed**,268.91с; collection410/digest `da0d7473a55bff6c01d235b47dee1d0f7d1f0a077eb59c9ebc8ee1bfcd338066`, `graf-f280-t045-full-focused.log`. Повтор на окончательном product source: **410 passed**,267.55с; тот же collection/digest, `graf-f280-t045-full-focused-final.log`. После начала этого повтора в owner тест добавлены только две дополнительные assertions no success/no auto-check; они отдельно прошли окончательный набор25. Продуктовый source не менялся во время прогона.
- Все PostgreSQL прогоны изолированы, контейнеры удалены. Два предупреждения pytest: уже импортированный fixture plugin и Starlette/httpx deprecation; проверок без исполнения/ошибок нет.
- Ruff, git diff --check, governance, fragment validation и issue-canon PASS. JS не изменён; прежние причинные Chromium/WebKit56/56 остаются доказательством неизменного контроллера, новый fallback проверяется настоящим route GET/POST.

## Независимые обзоры и выпуск

Независимые SOURCE и TEST PASS на окончательных пяти code/test SHA256: remarks0, оба P2 закрыты; история HOLD сохранена в [source](review-payment-return-release-source.md) и [tests](review-payment-return-release-tests.md). Старый candidate/run остаётся FAILURE/NO-GO. T032 открыта: новые exact-SHA PR checks, новое release-prep, новый frozen train/candidate и ровно один новый release-full → GO → CD dry-run/execute → только чтение существующего оплаченного платежа. Локальный GREEN не заменяет эти gate.


## Второй P2: основной локальный переход

TEST reviewer самостоятельно проследил primary→view=local и нашёл потерю заголовка и пояснения после подавления continue. Причинный owner RED: **5 failed /20 passed /85 deselected**,48.58с (`graf-f280-t045-local-link-red.log`); все5fail — новые local GET assertions. Добавлен только view-model awaiting_payment_result от исходных can_continue/can_refresh; он сохраняет видимый результат ожидания в read-only view, не разрешая POST/provider call/auto_check. Полный повтор410 на окончательных пяти code/test bytes: **410 passed**,264.96с; collection410/digest прежние, `graf-f280-t045-full-focused-local-final.log`; isolated_container_removed. Два финальных независимых обзора прочли завершённый410 и подтвердили remarks0; отдельные release gates ещё открыты.
