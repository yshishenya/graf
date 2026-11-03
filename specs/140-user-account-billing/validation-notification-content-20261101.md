# Проверка содержания уведомлений F140/T048 — 01.11.2026

Область: существующие подтверждения оплаты и включения автопродления.
Основа `125b51042ff39a1a7b1d4d051ce2503ea8d1250c`, рабочая ветка
`codex/140-notification-snapshots`; исполняемые проверки относятся к явно
записанным незакоммиченным исходникам. Окончательный PR потребует своих
трёх проверок точного SHA/основы. Порядок: существующий high-risk Spec Kit
slice с независимым requirements PASS 8/8; исходный RED выполнен до кода.

## Результаты

| Набор | Результат | Область |
| --- | --- | --- |
| Исходный внешний producer probe | 3 FAIL → те же 3 PASS | Настоящие producers, commit, новая session; внешний probe не включается в продуктовые тесты |
| Четыре существующих integration файла | 341 PASS | Return, purchase journey, review regressions, notification flow; до усиления тестовых утверждений, тот же рабочий код |
| Два unit файла после дополнений | 54 PASS | Сумма, отдельные интервалы, явная зона, неверные/личные поля, старые сообщения |
| Усиленные late renewal/storage случаи | 6 PASS | Настоящие rollback/regrant/duplicate/new-session; четыре storage варианта, корректное различение success/service gap |
| Усиленный покупательский путь | 3 PASS | Initial, early, storage и resume после последующих изменений, включая параллельные варианты |
| Resume внутри окна | 1 PASS | Реальный HTTP, due-now предложение, повтор, отмена, новая session |
| Прямые соседние callers | 102 PASS | Entitlements, money path E2E и notification preferences; права, receipts, атомарность и повторы |

Объединение по `(classname, name)` даёт **498 уникальных окончательных
PASS**, без окончательных FAIL/ERROR/SKIP; повторённые случаи не прибавлены
дважды. Все PostgreSQL запускались штатным изолированным runner и удалены.
Банковский transport синтетический; настоящих денег, почты, Dev и production нет.
Результат не подтверждает расчёты провайдера или фактическую доставку.

Первоначальные ошибки сохранены: совместная коллекция внешнего probe и
репозиторных tests загрузила conftest дважды и остановилась до запуска
контейнера; их последующие отдельные запуски прошли. Одна команда содержала
неверное имя существующего файла и не собрала тесты/не запустила контейнер;
исправленная команда дала 341 PASS. Старое точное ожидание текста в lifecycle
дало 24 PASS/1 FAIL и заменено смысловыми проверками номера и честного
направления в кабинет, после чего 25 PASS. Первая новая inside-window
проверка неверно ожидала `conflict` для уже активной подписки: прочитан
настоящий ранний guard `already_active`, исправлено только ожидание;
дальнейшая проверка подтверждает одну строку события. Продуктовые
guards и финансовые утверждения ради этих повторов не ослаблялись.

## Исполненные команды

Все пути ниже относительно корня; результаты/XML сохранены вне Git,
имена и суммы перечислены далее.

```sh
apps/server/.venv/bin/pytest apps/server/tests/unit/test_billing_notifications.py apps/server/tests/unit/test_billing_lifecycle.py -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_return.py tests/integration/test_billing_purchase_journey.py tests/integration/test_billing_review_regressions.py tests/integration/test_billing_notification_flow.py -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_return.py tests/integration/test_billing_review_regressions.py -k 'expired_pending_renewal_can_be_revoked_without_canceling_payment or partly_elapsed_storage_preserves_quote_and_opens_one_money_gap' -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_purchase_journey.py -k test_initial_storage_early_renewal_and_scheduled_downgrade_are_one_coherent_journey -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py -k test_resume_inside_window_saves_due_now_confirmation_after_cancel -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_entitlements.py tests/unit/test_billing_money_path_e2e.py tests/unit/test_notification_preferences.py -q
```

Ruff и Python compile всех девяти изменённых Python-файлов, проверки
процесса/Spec Kit и `git diff --check` прошли перед итоговым ревью. Местный fast/Full не повторяется: focused-first
и три обязательных GitHub gate для будущего PR сохраняются. Выпуском владеет
отдельный оператор, согласованное окно без новых PR/слияний сохранено.

## Сверка завершённости текущей части

Восемь групп требований сопоставлены с существующими producers, allowlist,
renderer и настоящими проверками. Нет новых таблиц, очередей, зависимостей
или финансового действия. Сумма/валюта берутся из invoice; сроки — из grant
или каждого storage segment. Resume сохраняет полную сумму consumed quote
и точное принятое описание ближайшей попытки. Получатель, event identity,
транзакция, права и согласие сохраняются. Новых пробелов реализации в этом
ограниченном срезе не обнаружено; требуется независимое кодовое ревью.
Это не полная сходимость F140. FR-105 planned interval уже остаётся в T048;
T068, реальная доставка #7524 и остальные открытые задачи не дублируются
новыми задачами и не получают фиктивные отметки. Все 87 исходных ID и их
отметки сохраняются. Исторические after-refusal шаблоны не принимаются.

## Контрольные суммы

| XML | SHA-256 |
| --- | --- |
| `notification-content-existing-integration-corrected.xml` | `d9d1ef01348227b7e4a9f9dd5a6eb68bb8767b4526a2c8ee4857d76740625335` |
| `notification-content-unit-expanded.xml` | `87800bc1b4eda60343a8dbb4cef286f558dd8c90d345f5baafc3c9580b9f9d88` |
| `notification-content-producer-regressions.xml` | `3e5171162e485ecb7c584c6bc147b410547e66cc4575b553d2b979130c697244` |
| `notification-content-journey-regressions.xml` | `9a2944864780345146a1cefd356be43d29da140b58401a406cb89e540a285ba5` |
| `notification-content-resume-window-corrected.xml` | `fc710784a29374c878967dc880943aa2751e9175133066f39c37ccc13e04e963` |
| `notification-content-entitlement-compatibility.xml` | `7dae5a5efada6059cc8fbc441ec6729a3401eb1dc197bb2fbd3ae21468e9cdfe` |

Снимок рабочего кода:

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/notifications.py` | `88475b10bbadfbcfbbacaae58df41a498563751be2557cd40a52904c14c66049` |
| `apps/server/src/twobrain_rec_server/billing/entitlements.py` | `8ff60f8a8b22c853c1b81e8a72e690beffd8ddf6ad86fa9d31d53d374bf2708b` |
| `apps/server/src/twobrain_rec_server/billing/purchases.py` | `3dd32a57abaf51cb59de3d88df69e970abee54ce6d5ca929f2583fe3b14253c8` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `60aad306996ea565f303ca90634e811acc13951b9ea3dc6918e2d79f2af0c9c9` |

## Итог независимого ревью

[Кодовое ревью](review-notification-content-code-20261101.md): APPROVE.
Проверяющий независимо пересчитал все шесть XML — 498 уникальных PASS,
без FAIL/ERROR/SKIP; четыре файла продукта совпали с рассмотренными суммами.
Принят только ограниченный срез, исходный остаток сохранён. После проверки
документируется локальный коммит; push/PR/merge остаются на паузе согласованного
выпуска, нового GitHub CI или принятия всего T048 этим итогом не заявляется.
