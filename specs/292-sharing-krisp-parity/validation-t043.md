# T043 — подготовка и очистка временного PostgreSQL

2026-11-17; исходная база `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, задача #8131. Действующий Spec Kit срез высокого риска: инфраструктура обязательных проверок, FR-027. Рабочий сервер, приложение и пользовательские данные не менялись.

До кода: независимый checklist `bootstrap-lifecycle.md` PASS 11/0, analyze CRITICAL 0 / HIGH 0 / MEDIUM 0, обязательный issue-canon hook PASS, T043 связана с #8131. Reviewer-owned отметки исполнитель не менял.

## Изменение

Обязанность удаления устанавливается перед попыткой запуска. После первого `TimeoutExpired` допускается один повтор после подтверждённой очистки. Для ненулевого результата удаления отсутствие доказывается успешным ограниченным запросом списка с точным собственным именем. Неопределённость и ошибки очистки всегда завершают проверку отказом; завершающая удачная очистка не отменяет уже возникший отказ. Время запуска/удаления 30 с, обычной команды 5 с и готовности 30 с сохранено. Готовность, проверка loopback-порта, миграция и тело теста находятся вне цикла повторного запуска. Ошибки subprocess не сохраняются как выводимая цепочка исключений с параметрами.

## Предметные проверки

- До исправления фикстуры расширенный существующий контракт: **10 ожидаемых FAIL / 10 PASS**, 4.73 с. Отказы воспроизвели отсутствие восстановления и подавление очистки/небезопасную цепочку диагностических исключений.
- После исправления весь `tests/contract/test_isolated_postgres_cluster.py`: **21 PASS**, 4.07 с. Покрыты временный/двойной тайм-аут, точное имя и бюджеты, подтверждённое отсутствие, неопределённая очистка, отказ удаления/списка, nonzero/OSError запуска, ready/порт, migration/body без повторов и прежний collect-only без Docker. Два прежних предупреждения инфраструктуры тестов.
- Настоящий PostgreSQL через штатный runner: **13 PASS**, 80.82 с (phase 85 с). Все 9 параметров bootstrap и 4 sender, без пропусков. `postgres_test_phase=focused-strict status=pass`, `postgres_test_cleanup=isolated_container_removed`, `postgres_test_result=pass mode=focused partitioned=true shard=none`. После завершения список `graf-postgres-test-bootstrap-*` пуст.
- Ruff двух изменённых Python-файлов: PASS. `git diff --check`: PASS. `check-development-process.py`: PASS, включая active pointer/changelog/legacy. Frozen governance требует закреплённую specify-cli 1.0.7; глобальная 1.2.6 корректно отвергнута. Повтор с уже существующим закреплённым окружением: PASS (`spec-kit-governance: OK`).

Команды из `apps/server`:

```sh
PYTHONPATH=src uv run --frozen --extra dev pytest tests/contract/test_isolated_postgres_cluster.py -q
uv run --frozen --extra dev ruff check tests/fixtures/postgres_test_database.py tests/contract/test_isolated_postgres_cluster.py
```

Из корня:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned --phases strict tests/integration/test_billing_fair_use_operator.py::test_bootstrap_rejects_changed_policy_or_missing_index tests/integration/test_billing_notification_flow.py::test_account_close_sender_bounds_retry_and_never_repeats_unknown -q
```

Использовано существующее окружение с неизменным uv.lock, без новых зависимостей. Перед Docker свободно 68 GiB, ниже критического порога 50 GiB не опускалось; крупная сборка здесь не выполнялась. Журналы и исходный failed Full сохранены отдельно у оператора без материалов встреч.

## Сходимость и оставшиеся ворота

В рамках T043 новых обязательных изменений кода не обнаружено. Все 6 уточнений FR-027/T043-A–F покрыты изменением и предметными проверками. Исходная причина задержек Docker и факт утечки в failed Full неизвестны; это исправление ограничивает восстановление и делает неопределённую очистку явным отказом, не обещая исправления самого Docker.

Независимый обзор реализации: PASS, Critical/High/Medium 0/0/0; проверены все 13 внешних модулей-потребителей и настоящие журналы. Хеши проверенных кода/контракта совпадают с текущими файлами. Сам reviewer тесты не повторял; это отдельно от исполнения и точных GitHub-проверок.

Exact-SHA/base `governance-fast`, `macos-pr`, `pr-metadata`, слияние и новый frozen candidate с одним authoritative Full остаются обязательными. Failed Full44067188639 не повторялся и не является допуском. T043 пока не отмечена выполненной, поскольку включает новые выпускные ворота. T016/T017 и остальные открытые задачи F292 сохраняются до отдельной production/native приёмки и tracker closeout. Legacy Impact: untouched.
