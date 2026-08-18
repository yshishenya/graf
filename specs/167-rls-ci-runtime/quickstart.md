# Quickstart: Надёжный RLS release gate

Все команды выполняются из корня репозитория. Пароли передаются только через
окружение текущего процесса и никогда не записываются в git, receipt или
скриншоты.

## 1. Проверить безопасный blocked path

```sh
env -u RLS_TEST_DATABASE_URL -u RLS_TEST_PROBE_DATABASE_URL \
  sh -c 'cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py'
```

Ожидаемый результат: `rls_validation_result=blocked` и
`reason=postgres_test_database_required`; миграции и probe не запускаются.

## 2. Проверить production guard

```sh
RLS_TEST_DATABASE_URL='postgresql+asyncpg://user:password@127.0.0.1:54330/twobrain_rec' \
  sh -c 'cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py'
```

Ожидаемый результат: ненулевой exit code с причиной
`live_production_database_probe_forbidden`. Пример содержит фиктивные данные;
реальный пароль не выводить.

## 3. Проверить disposable pass path

Создать отдельную loopback-базу с bounded именем, передать URL через
`RLS_TEST_DATABASE_URL`, затем выполнить:

```sh
RLS_TEST_DATABASE_URL="$DISPOSABLE_RLS_URL" \
  infra/scripts/ci-local.sh --full
```

Ожидаемый результат: server tests, lint, compile, RLS validation, compose
config и deployment evidence scan завершаются pass. После выполнения удалить
созданную базу и убедиться, что временная probe role удалена.

## 4. Focused regression checks

```sh
cd apps/server
PYTHONPATH=src uv run pytest -q tests/contract/test_rls_production_boundary.py
cd ../..
git diff --check
infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec
```

## 5. Release boundary

После focused checks и exact-SHA full gate выполнить:

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
```

Production `--execute` выполняется только после отдельного release approval и
сам повторяет полный gate на pinned SHA.
