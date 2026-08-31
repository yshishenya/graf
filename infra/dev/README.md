# GRAF Dev manifest harness

`dev-harness.sh` is the portable, metadata-only boundary for the one local Dev
environment. It does not contact production, delete application data, build a
container, or install an app by itself. A project adapter may connect a valid
manifest to those actions only after the manifest and Dev boundary checks pass.

The state directory is `GRAF_DEV_STATE_DIR` or the shared machine-local
`~/Library/Application Support/GRAF Dev/<repo>/harness` path on macOS
(`~/.cache/GRAF Dev/<repo>/harness` on other systems). It contains only
metadata, a lock and an atomic `active-manifest.json` pointer. A state path that
looks like production is rejected. Origins must be loopback (`localhost`,
`127.0.0.1` or `[::1]`). Set `GRAF_DEV_STATE_DIR` explicitly when a disposable
fixture needs a worktree-local state directory.

## Operations

```sh
./infra/scripts/dev-harness.sh build --sha <40-hex-sha> --feature-id 216
./infra/scripts/dev-harness.sh build --sha <40-hex-sha> --feature-id 216 --dry-run
dev_state="$(./infra/scripts/dev-harness.sh status --json | jq -r '.state_dir')"
./infra/scripts/dev-harness.sh promote --manifest "$dev_state/manifests/dev-<sha12>.json"
./infra/scripts/dev-harness.sh promote --manifest <path> --dry-run
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh smoke --json --fixture
./infra/scripts/dev-harness.sh rollback --dry-run
./infra/scripts/dev-harness.sh reset-data --confirm-dev-reset --dry-run
```

## Реальный локальный adapter

По умолчанию команды metadata-only и не запускают Docker, backend или macOS
app. На macOS разработчик может явно включить adapter:

```sh
./infra/scripts/dev-harness.sh build --sha "$(git rev-parse HEAD)" --feature-id 216 --live
dev_state="$(./infra/scripts/dev-harness.sh status --json | jq -r '.state_dir')"
./infra/scripts/dev-harness.sh promote --manifest "$dev_state/manifests/dev-<sha12>.json" --live
./infra/scripts/dev-harness.sh smoke --json --live
```

`build --live` проверяет Compose, импорт backend и подписывает ровно один
`GRAF Dev.app`. `promote --live` использует `start-local.sh`, поднимает только
локальные Postgres/MinIO, запускает backend и атомарно устанавливает один
`/Applications/GRAF Dev.app`. `smoke --live` проверяет live/ready API,
server-rendered `/login`, public auth providers и соответствие установленного
app exact SHA/origin/bundle ID. Live adapter отказывает, если SHA не совпадает
с текущим `HEAD`, origin не loopback или отсутствует Developer signing
identity. Он не предназначен для production/staging и не запускается в CI.

`--live --dry-run` не выполняет реальные build/promote side effects.

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
data. `smoke --fixture` proves the deterministic contract without network
access; real health probes and Compose/macOS actions are opt-in through the
GRAF adapter above.

The live adapter records both the backend launch command and the macOS `ps`
start-time token in `runtime.json`. Stop and rollback signal a process only when
both identities still match; a legacy runtime record without `start_token` is
treated as unowned and fails closed, so remove/repair it manually after
confirming that no Dev backend is running.

The full field contract is [manifest.schema.json](manifest.schema.json).
