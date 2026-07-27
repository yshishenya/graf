# Quickstart

## Быстрая проверка

```bash
infra/scripts/ci-local.sh --fast
```

Этот режим не требует PostgreSQL и не является доказательством миграций/RLS.

## Полная проверка

```bash
infra/scripts/ci-local.sh --full
```

Runner сам поднимает временный loopback-only PostgreSQL, применяет миграции,
запускает тесты с 8 xdist workers и удаляет контейнер. Для более слабой машины
можно задать `GRAF_TEST_WORKERS=4`.

## Фокус на аудио/экспорт

```bash
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_meeting_access_decisions.py \
  tests/unit/test_playback_audio.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/contract/test_access_sharing_downloads_contract.py \
  tests/contract/test_cabinet_playback_contract.py
```

Команда покрывает owner default download без сохранённой policy, явные policy
overrides и отказ shared viewer без policy.

## Безопасность

Не задавайте `TWOBRAIN_DATABASE_URL` production URL для тестов. Runner принимает
только generated `twobrain_rec_test_*` database на loopback.
