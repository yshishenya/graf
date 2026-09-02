# Quickstart: полноценный Dev runtime GRAF

Проверка Feature 229 после реализации. Live-команды выполняются только на
macOS, с loopback origins и единым repository-global Dev state; production не запускается и не
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
`feature_id=229`, hardening base равен
`b0c06935bc1af90be6f92981357a61af3d80bb19` и нет изменений за пределами
owned paths.

## 2. Проверить единый repository-global Dev state

```sh
unset GRAF_DEV_STATE_DIR
export GRAF_DEV_COMPOSE_PROJECT="graf-dev"
export GRAF_BACKEND_ORIGIN="http://127.0.0.1:8081"
export GRAF_FRONTEND_ORIGIN="$GRAF_BACKEND_ORIGIN"
DEV_STATE="$HOME/Library/Application Support/GRAF Dev/$(basename "$(git rev-parse --show-toplevel)")/harness"
./infra/scripts/dev-harness.sh status --json || true
```

Все worktree используют один lock, один runtime и один state. Live adapter
обязан отклонить отдельный `GRAF_DEV_STATE_DIR`. Старый state не удаляется;
архивировать или заменить его можно только отдельным явным operator action
после проверки ownership и остановки runtime.

## 3. Build exact-SHA candidate

```sh
SHA="$(git rev-parse HEAD)"
./infra/scripts/dev-harness.sh build --sha "$SHA" --feature-id 229 --live
```

Ожидается manifest в `$DEV_STATE` с одним `source_sha`, immutable image ID для
каждого Compose service, component identities, resolved migration head и Dev
boundary. Active pointer на этом шаге ещё не меняется. Pre-hardening manifest
остаётся читаемым, но не может использоваться для live rollback без полного
набора image IDs; такой переход блокируется до остановки runtime.

## 4. Promote and live smoke

```sh
MANIFEST="$(find "$DEV_STATE/manifests" -maxdepth 1 -name 'dev-*.json' -print | sort | tail -n 1)"
./infra/scripts/dev-harness.sh promote --manifest "$MANIFEST" --live
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh smoke --json --live
```

Smoke PASS обязан содержать `backend_health`, `frontend_reachability`,
`auth_session_bootstrap`, `representative_api`, `database_readiness`,
`storage_readiness`, `migration_readiness`, `temporal_readiness`,
`processing_worker_readiness`, `media_worker_readiness`, `app_identity` и
`app_presentation`, `exact_source_sha`.

Открыть `http://127.0.0.1:8081/login` и убедиться, что server-rendered frontend
использует тот же backend origin. Единственный Dev app —
`/Applications/GRAF Dev.app` с bundle ID `pro.2brain.graf.dev`; окно и меню
называются `GRAF Dev`, а на иконке есть Dev badge. Production app не изменяется.
Promotion сам штатно завершает старый процесс, заменяет bundle, обновляет
LaunchServices и запускает новую версию. Прямой `install-dev-app.sh` при
работающей Dev app обязан завершиться до файловой замены.

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
восстановимы. Если прежняя app была запущена, compensation возвращает её в
запущенное состояние; если была закрыта — не открывает. Rollback разрешён
только после checkout exact target SHA и ownership-проверки; чужой PID не
сигнализируется. В `runtime.json` и `docker inspect` image IDs обязаны совпасть
с выбранным manifest; совпадения одного source-SHA label недостаточно.

## 7. Contract and repository validation

```sh
uv run --directory apps/server --extra dev pytest -q \
  ../../tests/governance/test_dev_runtime.py \
  ../../tests/governance/test_dev_migration_preflight.py \
  ../../tests/governance/test_dev_rollback.py \
  ../../tests/governance/test_graf_local_adapter.py
GRAF_DEV_SOURCE_SHA="$(git rev-parse HEAD)" \
TWOBRAIN_PUBLIC_BASE_URL=http://127.0.0.1:8081 \
GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE=/tmp/graf-dev-config-key \
  docker compose -f infra/docker-compose.dev.yml config --quiet
python3 -m compileall -q scripts infra/scripts
```

После focused checks обновить PR и дождаться GitHub Actions
`governance-fast` на exact implementation SHA. Локальный fast/full CI для этого
среза не запускается. Full CI запускается позже один раз для frozen release
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
