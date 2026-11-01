# F140/T048 — проверка напоминания до продления, 01.11.2026

Полоса: active Spec Kit slice, серверные финансовые события. Legacy Impact:
untouched. Исходная задача — #4903; общая T048 остаётся `[ ]`.
Основа реализации: `887ad8095c97ca80b360f2157e13b8c6541db6bc`.

## Результат

Существующий planner при создании первой допустимой попытки в окне
[−72h, −48h) сохраняет одно обязательное уведомление в прежней очереди.
Проверка текущего личного пространства и активного владельца повторяется
после блокировки. Идентификатор связан с пространством, плательщиком и концом
периода; номер попытки, операция и версия согласия его не меняют.
Уведомление и счёт/операция коммитятся или откатываются вместе.

Сумма берётся из принятого каталога и форматируется целыми числами без
потери копеек. Произвольный masked_label не передаётся: допустимы только
четыре ASCII-цифры точной маски. Исторический текст остаётся правдивым
после поздней доставки. Новые службы, зависимости, таблицы и миграции не нужны.
Платёж, согласие, доступ, provider dispatch и расписание попыток не изменены.

## Причинность и проверки

До исправления настоящий PostgreSQL planner не создавал напоминания:
`reminder-test-red.log/xml` содержит ожидаемый отказ. Первый проход реализации
дал 198 PASS / 1 FAIL: тестовый PagedDb не обслуживал новый scalar-запрос
владельца. Исправлен только fake DB; продуктовые проверки не ослаблены.
Исходные журналы сохранены.

После исправления непосредственно проверены XML и журналы трёх наборов:

| Набор | PASS | FAIL / ERROR / SKIP |
| --- | ---: | --- |
| reminder-focused-v2 | 208 | 0 / 0 / 0 |
| reminder-adjacent | 231 | 0 / 0 / 0 |
| reminder-lifecycle | 15 | 0 / 0 / 0 |

Имена тестов сверены по `(classname, name)`: **454 различных проверки**,
пересечений между наборами нет. Каждый журнал подтверждает штатное удаление
одноразового PostgreSQL контейнера. Предупреждение pytest об уже импортированном
fixture не является пропуском тестов. Внешний HTTP запрещён fixtures;
provider transport синтетический, настоящая почта/оплата не вызывались.

Команда каждого набора использует существующий runner
`apps/server/scripts/run_local_postgres_tests.sh --focused -q` и общий
подготовленный Python environment. Состав:

- focused-v2: `integration/test_billing_renewal_planner_postgres.py`,
  `unit/test_renewal_charge.py`, `unit/test_billing_notifications.py`;
- adjacent: `integration/test_billing_notification_flow.py`,
  `integration/test_billing_webhooks.py`, `integration/test_billing_purchase_journey.py`,
  `integration/test_billing_purchase_quotes.py`, `integration/test_billing_purchase_storage.py`,
  `unit/test_billing_renewal_workflow.py`, `unit/test_billing_purchases.py`,
  `unit/test_billing_purchase_observation.py`;
- lifecycle: `integration/test_subscription_controls.py`,
  `integration/test_renewal_lifecycle.py`, `contract/test_renewal_resolution.py`,
  `e2e/test_billing_test_shop.py`, `unit/test_notification_preferences.py`.

Локальные доказательства:
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/`.
Точные суммы исходников и первых двух наборов зафиксированы независимым
[ревью реализации](review-renewal-reminder-implementation-20261101.md).
SHA256 рассмотренного пятифайлового diff:
`5d72be33bb0bd772022e323dab5844de38c5814a190baf0307fa4e1160683601`.

## Ограниченная сверка реализации с требованиями

`$speckit-converge`: проверены 6 групп принятых требований CHK001–006,
3 решения плана (существующий planner/транзакция, прежняя очередь, безопасный
исторический текст), применимые ограничения конституции на полномочия,
изоляцию, сохранность, секреты, независимость capture и точность приёмки.
В этой части gaps missing/partial/contradicts/unrequested — 0; новых задач — 0.
Исходный tasks.md оставлен без изменений; пустая фаза сходимости не добавлялась.
Неподдерживаемый `--require-spec` из инструкции навыка не обходился:
spec прочитан непосредственно, действующая prerequisite-команда
`--json --require-tasks --include-tasks` прошла. Hooks converge не настроены.

Reviewer-owned checklist требований: **6 отмечены / 0 открыты**;
независимое ревью реализации: **P1 0 / P2 0**, покрытие 6/6.
Основной агент сверил полный diff и его SHA256 с отчётом.
Итоговый lifecycle-профиль проверен отдельно основным агентом после ревью.

## Границы

Это локальные проверки рабочего изменения, а не exact-SHA CI receipt.
Обязательные GitHub governance-fast/macos-pr/pr-metadata и общий валидатор
нового PR SHA/основы ещё предстоят. Родительский PR #7861 принимается отдельно.
Полная T048/#4903, T068/#4922, остальные 58 пунктов общих checklist F140,
фактическая доставка #7524, публичный запуск и финансовая приёмка не закрыты.
GRAF Dev, release, Full CI и production не запускались.
