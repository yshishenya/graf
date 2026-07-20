# Feature 108: local runner receipt

Дата проверки: 2026-07-20
Проверенный master SHA: `da250976a67583c63267ee5d23b6239f35c02c00`

## Команда

```sh
GRAF_TEST_WORKERS=8 bash apps/server/scripts/run_local_postgres_tests.sh \
  tests/contract/test_local_postgres_test_runner.py \
  tests/contract/test_postgres_only_contract.py \
  tests/integration/test_postgres_migrations.py \
  tests/integration/test_meeting_detection_migrations.py \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_playback_normalization_migrations.py \
  tests/integration/test_health_readiness.py \
  tests/integration/test_production_docs_exposure.py \
  tests/unit/test_config_validation.py -q
```

## Результат

- Runner выбрал `postgres_test_mode=focused worker_count=1` и использовал
  одноразовый PostgreSQL 17 на loopback-порту с сгенерированным именем базы.
- `82 passed`, `2 warnings`, `24.21s`; фаза runner завершилась с
  `postgres_test_phase=focused status=pass duration_seconds=40`.
- После завершения получен `postgres_test_cleanup=isolated_container_removed`.
- Production URL, production-секреты и удалённая база в тест не передавались;
  fallback на SQLite отсутствует.
