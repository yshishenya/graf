# F280 T042/T043: подтверждённая покупка хранения и оплаченные периоды

Дата: 2026-10-03. Полный высокорисковый путь Spec Kit внутри действующей F280; новый номер фичи не создавался. Основания: [требования](spec.md), [план](plan.md), [задачи](tasks.md), [независимый допуск требований PASS17/0](review-payment-return-storage-requirements.md). T042 связан с issue #7491, T043 — с #7492. Этот отчёт фиксирует SOURCE/TEST; окончательный независимый обзор, браузер и выпуск принадлежат общему процессу F280.

## Исправление

В [маршруте кабинета](../../apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py) успешная покупка хранения читает все `BillingStorageEntitlementGrant` именно своего пространства и счёта. Периоды сортируются по началу, окончанию и ID; отображаются отдельно, через точку с запятой. Минимальная и максимальная даты не склеиваются через неоплаченный промежуток. Ни нынешний объём, ни текущая подписка не используются как доказательство старой покупки.

Для старой схемы подтверждённая связанная invoice и `storage_upgrade / succeeded_projected` позволяют прочитать применённый сохранённый период. Сохраняются ограничения штатного [проектора](../../apps/server/src/twobrain_rec_server/billing/maintenance.py): допустимый целый объём, месячный/годовой цикл, даты с часовым поясом и строго положительный срок. Принимаются старая схема без `purchase_schema` и схема1; схема2, посторонний тип, неподтверждённый счёт, неверный снимок или признаки разрыва не получают success. Текущая подписка не переоценивает историческое доказательство. Проектор и финансовые переходы не менялись; недостающие права не создаются.

В [шаблоне](../../apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html) заголовок «Оплачено», подтверждение доступа и «К встречам» используют явный проверенный `payment_applied`. Настоящий `operation_state` остаётся в `data-billing-state`, включая `succeeded_projected`; состояния оплаты не подменяются для интерфейса.

## Причинное воспроизведение через настоящий HTTP→PostgreSQL

[Интеграционные тесты](../../apps/server/tests/integration/test_billing_clarity.py) используют существующий owner fixture и настоящий кабинет; создание `YooKassaClient` запрещено. Снимок значений всех таблиц `billing_*` и `workspace_subscriptions` до/после GET подтверждает отсутствие изменений финансовых строк, включая даты и состояние. Все идентификаторы, счета и покупки синтетические. PostgreSQL каждый раз создаётся и удаляется штатным runner.

Одинаковый выбранный набор32 теста (`-k storage_return`) запущен до изменения product source и после минимального исправления:

| Прогон | Исходник | Результат |
| --- | --- | --- |
| Причинный RED | HEAD `6db16ba474b2216a720fa8006a2cebe65ea978d6`, product source без правок | 13 FAILED, 19 PASS, 39 deselected; exit1;22.29s pytest;26s focused; isolated_container_removed |
| GREEN | Исправленные route/template, тот же тестовый набор | 32 PASS, 39 deselected; exit0;22.36s pytest;26s focused; isolated_container_removed |

Все13 причинных отказов относятся к ожидаемому отображению:8 — отсутствие срока одного/нескольких storage grants;4 — отсутствие «Оплачено» у старой применённой покупки на четырёх поверхностях;1 — реальное применение существующим legacy projector с последующим истечением/изменением текущей подписки. В причинном RED нет ошибок создания данных.

До причинного RED первая подготовительная попытка дала15 FAILED/16 PASS: часть синтетических grants была отвергнута существующим PostgreSQL trigger, потому что full_period_amount_minor не совпадал с ценой каталога. Fixture исправлен на `price.amount_minor`, product source тогда оставался исходным. Эта попытка не используется как доказательство ошибки интерфейса; после исправления fixture выполнен чистый причинный RED выше. Проверки/ограничения БД не отключались.

Команда из корня репозитория; требуется Bash5 и Docker:

```sh
UV_OFFLINE=1 /opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused -q tests/integration/test_billing_clarity.py -k storage_return
```

`UV_CACHE_DIR` задавался временным локальным каталогом только для запуска; он не входит в доказательство. Полные локальные pytest журналы временны и не представлены как доступные читателю файлы. Сохраняются воспроизводимая команда, причины отказов, счётчики и контрольные суммы.

Покрытие: один grant; два несмежных grant, созданные в обратном порядке; историческая подписка free с другой датой/циклом/ёмкостью; старая применённая покупка без нового grant; её реальное применение неизменённым projector; web, desktop, local и desktop_local. Отрицательные случаи: нет grant, grant другого invoice, grant другого workspace, чужой invoice, неприменённая старая операция, схема2 с projected, другой kind, pending invoice, malformed start, missing end, naive start/end, reversed/нулевой период, неверный цикл, bool/неизвестный объём, reconciliation marker и service marker. Без доказательства нет «Оплачено», оплаченного срока и «К встречам»; GET не меняет финансовые строки.

## Окончательная фиксация исходника

После GREEN убрана только лишняя пустая строка перед новым helper. Функциональные байты и тесты неизменны. Финальная фиксация перед общим регрессионным и независимым обзором:

| Относительный файл | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `0af48ddb2d628815dc0626d4cbd7e7a84328b3b2e37512ac2daaff09fdb787d5` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a33426dee1cb1ea7d12d94d1752a46ebac91dd073e37dd9754f773dbfc4b27c1` |
| `apps/server/tests/integration/test_billing_clarity.py` | `0d34024119097888e56b81370d6c6acd8b93783d6aaffffb4c0e160501cf3a45` |

Исходные product hashes причинного RED: route `f924f09e633b82bb66b12dc08f0ffb3259a08670891c32377f4c7d0ad3d0a1c6`, template `d3248713af17aa17cc9bd27a95bf51dcebf500a458e2161b9e88ebc226c27dba`. Тестовый hash уже совпадал с финальным. Collection digest причинного RED/GREEN: `0f815cad4e680ea563eef994d167c5a4753da44472fb43ed7035cee63b2bade3`.

## Регрессии и границы достоверности

Окончательный регрессионный набор выполняется на зафиксированных байтах:

```sh
UV_OFFLINE=1 /opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused -q tests/integration/test_billing_clarity.py \
  tests/integration/test_billing_return.py tests/unit/test_billing_maintenance.py
```

Фактический итог финального набора157: **155 PASS / 2 FAILED**, exit1,91.65s pytest/96s focused, collection digest `40bef34546117b4fc0a93958f5da132047e66e27503d900aed1a6d06aaf2ed25`, isolated_container_removed. Все32 новые проверки прошли на окончательной фиксации, остальные123 проверки также прошли. Два отказа — `test_storage_terminal_retry_reopens_same_volume_with_fresh_calculation[failed]` и `[canceled]` в [старом return наборе](../../apps/server/tests/integration/test_billing_return.py), строка292: `payment_card.count('role="status"') == 1`, фактически2. Причина — существующие главный status и скрытый `billing-status-message` из T039. Оба узла уже есть в HEAD `6db16ba4` (шаблон строки17,74) и не меняются данным slice; failed/canceled branches не относятся к новым трём success-проверкам. Владелец общего return набора должен согласовать проверку видимого status со скрытым полем, затем повторить общий набор; этот исполнитель не менял неподвластный тест и не выдаёт157PASS. Ruff для изменённых Python файлов, governance и `git diff --check` проходят. Известные2 предупреждения исходного набора: pytest assertion rewriting уже импортированного fixture и Starlette/httpx deprecation. Они не являются пропуском теста или ошибкой БД.

Ни JS, ни существующая браузерная матрица, ни reconciler, ни миграции/БД схема, ни чужие файлы не менялись. Этот SOURCE/TEST отчёт не подтверждает production, банк, чеки, возврат, реальные автосписания, GRAF Dev, человеческую приёмку или независимый окончательный PASS. Commit, GitHub, отметки tasks/checklist, release и deployment этим исполнителем не выполнялись.


## Последующая проверка общего набора основным исполнителем

Исторический отказ155/2 выше сохранён. В общем [return наборе](../../apps/server/tests/integration/test_billing_return.py#L292) исправлена устаревшая проверка: требуется ровно один видимый `role="status"`, а отдельное поле ожидания/ошибки обязано оставаться скрытым. Проверка по-прежнему запрещает двойное видимое сообщение; наличие скрытого поля не ослабляет её. Product source, контроллер и новые storage tests не изменены.

Тот же набор157 выполнен повторно: **157 PASS, failed0/skipped0**, exit0,94.51s pytest/99s focused; исходный collection digest `40bef34546117b4fc0a93958f5da132047e66e27503d900aed1a6d06aaf2ed25`; isolated_container_removed. Журнал `graf-f280-storage-regression-final.log` — временный локальный артефакт, не опубликованная ссылка.

SHA256 общего return test: `8cbc3adc32069cdb0eb32732ac996beb991032f666e627f22d29640f41b4c046`. Окончательные product/storage hashes выше сохранены. Независимый обзор и браузерная матрица имеют отдельные доказательства.
