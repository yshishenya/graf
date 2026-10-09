# Quickstart

## Preconditions

Проверить свободное место на Mac: `df -h /Users/yshishenya`. Использовать существующий Python 3.13 с зависимостями, добавить текущие `apps/server` и `apps/server/src` в PYTHONPATH. Docker должен работать. Для существующего окружения задать UV_PROJECT_ENVIRONMENT и UV_NO_SYNC=1; не устанавливать зависимости заново. Не использовать рабочую базу или реальные встречи.

## Causal regression and focused validation

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned -q tests/integration/test_playback_normalization_postgres.py tests/integration/test_billing_purchase_storage.py tests/integration/test_storage_package_catalog.py tests/integration/test_billing_review_regressions.py tests/integration/test_rls_postgres_policies.py tests/unit/test_storage_packages.py
```

Для FR-006 дополнительно выполнить существующие проверки повторов, защиты от дубликатов и квоты:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned -q tests/integration/test_playback_normalization_retry.py tests/integration/test_playback_normalization_idempotency.py tests/integration/test_storage_quota.py
```

До исправления новая personal-проверка получает отказ доступа; после исправления все выбранные тесты проходят без пропусков. Проверка использует реальные миграции и ограниченную роль, синтетический источник и существующий управляемый имитатор медиаоперации; это доказательство разрешений/квоты, не новая аппаратная аудиоприёмка.

```sh
python3 scripts/check_spec_kit_governance.py
python3 -m ruff check apps/server/scripts/bootstrap_runtime_database_roles.py apps/server/src/twobrain_rec_server/billing/purchases.py apps/server/tests/fixtures/postgres_test_database.py apps/server/tests/integration/test_playback_normalization_postgres.py apps/server/tests/integration/test_rls_postgres_policies.py apps/server/tests/unit/test_storage_packages.py
```

Критерии: publication ready + завершённое резервирование; матрица сохранённой квоты; рабочая область/контекст/лишние поля/запись защищены; две настройки дают точные права; исходный отказ воспроизведён. Runner удаляет только свой временный контейнер. Сохраняем журналы результатов и суммы файлов, а не зависимости/аудио/дампы.

## Release gates

Независимое ревью → convergence → разрешение на commit → PR exact-SHA/base governance-fast/macos-pr/pr-metadata → frozen release-full → cd dry-run → отдельное production-разрешение → rollout и синтетический smoke под реальной медиаролью. До этого постоянное исправление на рабочем сервере не объявляется установленным.
