# Quickstart: полноценный Dev runtime GRAF

Проверка Feature 229 после реализации. Live-команды выполняются только на
macOS, с loopback origins и явным Dev state; production не запускается и не
изменяется.

## Предварительные условия

- checkout чистый и находится на проверяемом exact SHA;
- Docker Desktop/Compose v2, `uv`, Swift 6/macOS 14+ и локальная signing
  identity доступны;
- `/Applications/GRAF.app` не является Dev destination;
- нет активной операции с общим GRAF Dev state; занятый lock сначала читается
  через `status`, а не удаляется;
- provider credentials не нужны для базового smoke и не экспортируются в app или
  evidence.

## 1. Проверить sources и pointer

```sh
git status --short --branch
git rev-parse HEAD
python3 scripts/validate-agent-context.py --root .
python3 scripts/check_spec_kit_governance.py
```

Ожидается чистый branch checkout, `source_sha` pointer равен `HEAD`,
`feature_id=229`, `base_sha=836cbba8f1c53695dd9e06a21f58bf74365286ef` и отсутствие
изменений за пределами owned paths.

## 2. Выбрать изолированный Dev state

```sh
export GRAF_DEV_STATE_DIR="$(mktemp -d /tmp/graf-dev-229.XXXXXX)"
export GRAF_DEV_COMPOSE_PROJECT="graf-dev"
export GRAF_BACKEND_ORIGIN="http://127.0.0.1:8081"
export GRAF_FRONTEND_ORIGIN="$GRAF_BACKEND_ORIGIN"
```

Adapter должен сам проверить namespace; переменные не должны позволять выбрать
production-looking path, origin или volume.

## 3. Build exact-SHA candidate

```sh
SHA="$(git rev-parse HEAD)"
./infra/scripts/dev-harness.sh build --sha "$SHA" --feature-id 229 --live
```

Ожидается manifest в `GRAF_DEV_STATE_DIR` с одним `source_sha`, component
identities, resolved migration head и Dev boundary. Active pointer на этом шаге
ещё не меняется.

## 4. Promote and live smoke

```sh
MANIFEST="$(find "$GRAF_DEV_STATE_DIR/manifests" -maxdepth 1 -name 'dev-*.json' -print | sort | tail -n 1)"
./infra/scripts/dev-harness.sh promote --manifest "$MANIFEST" --live
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh smoke --json --live
```

Smoke PASS обязан содержать `backend_health`, `frontend_reachability`,
`auth_session_bootstrap`, `representative_api`, `database_readiness`,
`storage_readiness`, `migration_readiness`, `temporal_readiness`,
`processing_worker_readiness`, `media_worker_readiness`, `app_identity` и
`exact_source_sha`.

Открыть `http://127.0.0.1:8081/login` и убедиться, что server-rendered frontend
использует тот же backend origin. Единственный Dev app —
`/Applications/GRAF Dev.app` с bundle ID `pro.2brain.graf.dev`; production app
не изменяется.

## 5. Migration mismatch

Использовать только disposable isolated state или metadata-only fixture:

```sh
GRAF_DEV_EXPECTED_MIGRATION_HEAD=current-head \
GRAF_DEV_OBSERVED_MIGRATION_REVISION=old-head \
  ./infra/scripts/dev-migration-preflight.py --json
```

Ожидается `blocked` до API/worker readiness, observed/expected metadata и
инструкция создать новый Dev namespace. `alembic stamp`, прямое редактирование
`alembic_version`, `docker compose down -v` и удаление старого state запрещены.

## 6. Атомарность и rollback

Создать второй valid candidate обычным `build`, затем внедрить ошибку на
staging/install/runtime/smoke в test fixture. Проверить:

```sh
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh rollback --dry-run
./infra/scripts/dev-harness.sh rollback --live
./infra/scripts/dev-harness.sh smoke --json --live
```

После ошибки прежние active manifest, app и owned runtime должны быть
восстановимы. Rollback разрешён только после checkout exact target SHA и
ownership-проверки; чужой PID не сигнализируется.

## 7. Contract and repository validation

```sh
python3 -m pytest tests/governance/test_dev_runtime.py tests/governance/test_dev_migration_preflight.py
docker compose -f infra/docker-compose.dev.yml config --quiet
python3 -m compileall -q scripts infra/scripts
infra/scripts/ci-local.sh --fast
```

Fast lane выполняется на exact implementation SHA и не является доказательством
release-ready Full CI. Full CI запускается позже один раз для frozen release
candidate по правилам F227.

## Evidence and cleanup

Сохранять только metadata-only manifests, receipts, check results и digests под
`.dev/ci-evidence/` или разрешённым Dev state. Не сохранять raw audio,
transcript text, credentials, tokens, signed URLs, private paths или meeting
content. Останавливать только namespace Feature 229 штатным adapter-путём;
старый local и production state не трогать.

## Expected blocked states

- `processing_enabled=false` или отсутствующий worker/Temporal readiness — не
  PASS; исправить runtime adapter.
- stored migration revision отсутствует в graph — не stamp и не reset; создать
  новый изолированный state после явного operator decision.
- active pointer/lock/runtime record повреждён или PID не подтверждён — не
  удалять автоматически; провести ownership-проверку.
- app identity/signing requirement/origin drift — не заменять установленный app;
  вернуть предыдущий кандидат или остановить promotion.
