# GRAF Dev full-stack runtime

`dev-harness.sh` is the portable boundary for the one local Dev
environment. It does not contact production, delete application data, build a
container, or install an app by itself. A project adapter may connect a valid
manifest to those actions only after the manifest and Dev boundary checks pass.

The state directory is `GRAF_DEV_STATE_DIR` or the shared machine-local
`~/Library/Application Support/GRAF Dev/<repo>/harness` path on macOS
(`~/.cache/GRAF Dev/<repo>/harness` on other systems). It contains metadata,
machine-local build/rollback artifacts, a lock and an atomic
`active-manifest.json` pointer. A state path that
looks like production is rejected. Origins must be loopback (`localhost`,
`127.0.0.1` or `[::1]`). Set `GRAF_DEV_STATE_DIR` explicitly when a disposable
fixture needs a worktree-local state directory.

## Operations

```sh
./infra/scripts/dev-harness.sh build --sha <40-hex-sha> --feature-id 229 --live
./infra/scripts/dev-harness.sh build --sha <40-hex-sha> --feature-id 216 --dry-run
dev_state="$(./infra/scripts/dev-harness.sh status --json | jq -r '.state_dir')"
./infra/scripts/dev-harness.sh promote --manifest "$dev_state/manifests/dev-<sha12>.json" --live
./infra/scripts/dev-harness.sh promote --manifest <path> --dry-run
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh smoke --json --live
./infra/scripts/dev-harness.sh rollback --dry-run
./infra/scripts/dev-harness.sh rehydrate --manifest <path>
./infra/scripts/dev-harness.sh reset-data --confirm-dev-reset --dry-run
```

## Реальный локальный adapter

По умолчанию команды metadata-only и не запускают Docker, backend или macOS
app. На macOS разработчик может явно включить adapter:

```sh
./infra/scripts/dev-harness.sh build --sha "$(git rev-parse HEAD)" --feature-id 229 --live
dev_state="$(./infra/scripts/dev-harness.sh status --json | jq -r '.state_dir')"
./infra/scripts/dev-harness.sh promote --manifest "$dev_state/manifests/dev-<sha12>.json" --live
./infra/scripts/dev-harness.sh smoke --json --live
```

`build --live` проверяет `docker-compose.dev.yml`, импорт backend, собирает
полный набор образов с label exact SHA и подписывает ровно один `GRAF Dev.app`.
`promote --live` использует только `start-dev-runtime.sh`: Compose namespace
`graf-dev` поднимает Postgres, MinIO, Temporal, migration, API и оба worker.
Migration preflight выполняется до migration command и application readiness.
`smoke --live` проверяет API, server-rendered `/login`, auth bootstrap,
Postgres/MinIO/migration, Temporal, processing/media worker, app identity и
presentation (`GRAF Dev`, channel `dev`, отдельная Dev-иконка) и exact SHA.
Перед заменой bundle adapter штатно завершает процесс, запущенный из
`/Applications/GRAF Dev.app`, после установки обновляет LaunchServices и
запускает новый bundle. Компенсация восстанавливает прежнее запущенное или
остановленное состояние. Прямой `install-dev-app.sh` fail-closed, пока Dev app
работает. Live adapter также отказывает, если SHA не совпадает с `HEAD`, origin
не loopback, у Compose нет ожидаемого label или отсутствует signing identity.
Он не предназначен для production/staging и не запускается в CI.

`--live --dry-run` не выполняет реальные build/promote side effects.

В базовом Dev-профиле MediaScribe намеренно не настроен: processing worker
остаётся запущенным и poller readiness проходит, но любая activity, требующая
внешнего provider, получает безопасный `blocked_config` без сетевого egress.
Это доказывает wiring Temporal/worker и не имитирует успешную транскрибацию.
Production не использует этот startup fallback и требует штатные server-side
MediaScribe credentials.

`build` creates one manifest for backend, frontend, worker and the single
`pro.2brain.graf.dev` app. Every component must report the same exact source
SHA. In a real GRAF checkout, `build` resolves the Alembic graph head with
`uv run alembic heads`; `GRAF_DEV_MIGRATION_HEAD` or `--migration-head` may
provide an explicitly verified override. Fixture manifests may use an explicit
synthetic head, but the default `unknown` value is deliberately rejected by
`promote`. `promote` takes an exclusive lock and replaces the active pointer
only after validation; a stale candidate or malformed component is refused.
The first failed/partial operation therefore leaves the previous active
manifest untouched. Re-promoting the active manifest is idempotent.

`rollback` selects the manifest's parent unless an explicit manifest ID is
provided. `reset-data` is intentionally limited to metadata-only Dev state and
requires `--confirm-dev-reset`; it never removes production or application
data. `smoke --fixture` is non-authoritative and only validates receipt shape;
real health probes and Compose/macOS actions are required for promotion.

The live adapter records both the backend launch command and the macOS `ps`
start-time token in `runtime.json`. Stop and rollback signal a process only when
both identities still match; a legacy runtime record without `start_token` is
treated as unowned and fails closed, so remove/repair it manually after
confirming that no Dev backend is running.

Each live build stores a machine-local `runtime-images.tar` beside its app
artifact. `rehydrate` reloads that archive under the shared lock and verifies
every manifest image ID and source label; it never rebuilds or substitutes a
missing rollback image.

The full field contract is [manifest.schema.json](manifest.schema.json).
