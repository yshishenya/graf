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

Перед ручными проверками установленного приложения прочитайте
[обязательные правила GRAF Dev](../../docs/agent-guidance/local-development.md).

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
./infra/scripts/dev-harness.sh prune --dry-run
./infra/scripts/dev-harness.sh prune
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

`build --live` под общим Dev lock проверяет `docker-compose.dev.yml`, импорт
backend, собирает полный набор образов с label exact SHA и подписывает ровно
один `GRAF Dev.app`.

Для двух датированных образов MinIO используется
`docker compose pull --policy missing`: уже загруженные версии используются
повторно, отсутствующие требуют успешной загрузки. Postgres/Temporal продолжают
загружаться как раньше. Image ID всех компонентов измеряются; архив образов
создаётся позже — при `promote`, только для целевого отката (см.
[Политика хранения](#политика-хранения-локальных-артефактов)).

`promote --live` использует только `start-dev-runtime.sh`: Compose namespace
`graf-dev` поднимает Postgres, MinIO, Temporal, migration, API и оба worker.
Migration preflight и seed выполняются внутри выбранного immutable server image
до migration command и application readiness; checkout-side server source не
участвует в startup или compensation.
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
`promote`. `build` and `promote` take the same exclusive lock; `promote` replaces the active pointer
only after validation; a stale candidate or malformed component is refused.
The first failed/partial operation therefore leaves the previous active
manifest untouched. Re-promoting the active manifest is idempotent. If
compensation fails, metadata-only `rollback-required.json` makes terminal
`rollback_required` visible through `status`, including a first promotion with
no previous active manifest.

`status` also reports the installed application as `app.path` and
`app.installed`. If `/Applications/GRAF Dev.app` is absent while a manifest is
active, `status` adds a `warnings` entry naming that path. Do not trust a running
process instead of this field: the lifecycle helper identifies the app by bundle
path, so an app whose bundle was removed keeps running and still answers
`running`. Restore it with `promote` of the unchanged active manifest from its
exact-SHA checkout; the verified bundle of the active manifest stays in
`artifacts/<manifest-id>/GRAF Dev.app`. Never repair the installation by copying
a bundle by hand.

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

Each live `promote` stores exactly one machine-local `runtime-images.tar` — for
the rollback target (the previous active manifest) — beside that manifest's app
bundle. `build` no longer creates an archive and removes its intermediate
`build/` directory after a successful build. `rehydrate` reloads the retained
archive under the shared lock and verifies every manifest image ID and source
label; it never rebuilds or substitutes a missing rollback image. A manifest
outside the retention policy cannot be rehydrated: rebuild a new candidate.

## Политика хранения локальных артефактов

На диске постоянно хранятся только:

- приложение активного манифеста (будущий целевой откат);
- архив образов и приложение целевого манифеста отката (`parent_manifest_id`).

Всё остальное удаляется автоматически после успешных `build`, `promote` и
`rollback`: наборы артефактов старых кандидатов, их immutable-теги
`graf-dev-immutable:*`, каталоги сборки, снапшоты завершённых переходов схемы и
остаточные копии приложения `transactions/previous-*.app`. Глобальные
`docker system prune` / `image prune -a` не используются.

Ручная уборка без сборки:

```sh
./infra/scripts/dev-harness.sh prune --dry-run    # отчёт без изменений
./infra/scripts/dev-harness.sh prune              # применить политику
```

`prune` берёт общий state lock, печатает машиночитаемую квитанцию и дописывает
её в `prune-history.jsonl` в состоянии стенда. Операция запрещена при
незавершённом переходе схемы или состоянии `rollback_required`; удаления
ограничены каталогом состояния Dev.

Порядок восстановления сохранённого отката:

Восстановление выполняется из рабочей копии того SHA, на который делается откат.
Проверка точного соответствия сравнивает манифест цели с текущей рабочей копией,
поэтому из копии активного манифеста восстановление всегда отвергается — это
ожидаемое поведение защиты, а не сбой.

```sh
state="$(./infra/scripts/dev-harness.sh status --json | jq -r '.state_dir')"
manifest="$state/manifests/dev-<sha12>.json"
sha="$(jq -r '.source_sha' "$manifest")"
git switch --detach "$sha"   # рабочая копия цели отката, дерево должно быть чистым
./infra/scripts/dev-harness.sh rehydrate --manifest "$manifest"
./infra/scripts/dev-harness.sh rollback --dry-run
```

Откат за пределы удержанного поколения возможен только пересборкой из исходников
точного SHA: старые образы и архивы политикой не хранятся.

The full field contract is [manifest.schema.json](manifest.schema.json).
