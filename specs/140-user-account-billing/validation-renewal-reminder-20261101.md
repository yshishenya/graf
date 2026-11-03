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


## Совместная приёмка после исправления родительской гонки

PR #7861 слит в `9de7feeaaaacaf7cfa1ad6618501eb4fd4edd4ed`; точный source
`7d7e21377e6a1ac49f905011ffced668e1fe1b68` и base
`aab1387785e1fc430de150ffa9cae2e5e6dc97a7` прошли общий валидатор до/после
слияния. Его новая регрессия покрывает ответ canceled после POST/lock,
включая уже сохранённый Free/UNKNOWN. Старые hashes/454 выше — история.

Два собственных коммита reminder перенесены поверх исправленного родителя.
Разрешены два конфликта: в PostgreSQL цепочке сохранены attempt-late и
все4варианта родителя плюс _assert_upcoming_notice; в changelog сохранены
оба результата. Из14файлов прежнего reminder11побайтно совпали; отличаются
только renewal_charge.py, planner PostgreSQL test и fragment — ожидаемое
исправление родителя и совместная проверка. Остальные продуктовые bytes
не менялись. Новая source логика не добавлялась при разрешении конфликтов.

На `b89ac05084057ce0d3beb49f5999ea9a31b15c5c` выполнен объединённый набор
всех18существующих файлов профиля родителя и reminder через прежний
`run_local_postgres_tests.sh --focused -q`: **711 различных PASS /0 FAIL /
0 ERROR /0 SKIP**,219.27s. XML сравнен с race-profile-v2 и всеми3старыми
reminder наборами: сохранены все актуальные ID; один прежний
непараметризованный three_confirmed_declines расширен4вариантами.
Непредусмотренных удалений/дубликатов/новых ID0. Эти711 не суммируются с
прежними476/454; разрешение реального HTTP/почты не расширялось. Временный
PostgreSQL удалён штатно.

Затем выполнен окончательный перенос двух reminder-коммитов на фактический
squash master. Получен `0adfecf1fe1e290ccf051fab4d726c055c1ffc37`, base
`9de7feeaaaacaf7cfa1ad6618501eb4fd4edd4ed`. **Всё Git-дерево до/после переноса
совпало**, tree `6335b0115834ad6115a07f7b43c5d1bf1cee7009`; все14проверенных
файлов также совпали. Повторять711 без изменения кода не требуется. После
этого добавляются только текущие документы приёмки и reviewer-owned отметка;
новый окончательный SHA потребует трёх обязательных GitHub checks и общего
валидатора на действительной основе.

Доказательства в прежнем закрытом локальном каталоге:
reminder-combined.log/xml, reminder-on-fixed-parent-hashes.json,
reminder-post-squash-transfer.json. Основной агент самостоятельно разобрал
XML/ID и проверил tree/14hashes. Независимый reviewer фиксирует окончательный
вывод переноса в существующем review-renewal-reminder-implementation-20261101.md.
Ruff пяти Python-файлов и git diff --check PASS; governance/process выполняются
после записи этих документов. Настоящие платежи/доставка, общая T048/#4903,
T068/#4922/#7524,58общих открытых пунктов, Dev и выпуск остаются открытыми.
