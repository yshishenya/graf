# Data Model: Гигиена дискового пространства Dev-стенда и ускорение CI

**Feature**: 269-dev-storage-hygiene | **Date**: 2026-09-16

Сущности не вводят новых внешних хранилищ: модель описывает локальное состояние
стенда (`GRAF_DEV_STATE_DIR`), контракты CLI и артефакты CI. Схема манифеста,
формат архива образов и журнал перехода схемы сохраняются без изменений (R9).

## Сущности

### Manifest (существующая, без изменений схемы)

- `manifest_id`: `dev-<sha12>`; первичный ключ локального состояния.
- `source_sha`: 40-hex; привязка к исходному состоянию.
- `parent_manifest_id`: предыдущий активный манифест; определяет целевой откат.
- `components[].digest`: идентификаторы образов (Docker image ID) и digest приложения.
- `status`, `health`, `created_at`, `promoted_at`, `dev_boundary`.
- Правила: `manifest_id` уникален; повторная сборка того же SHA не перезаписывает существующий манифест с другой метаинформацией (существующее поведение).

### ArtifactSet (локальные артефакты манифеста)

- `manifest_id`: владелец набора.
- `archive`: путь `artifacts/<manifest_id>/runtime-images.tar`; существует только у целевого отката.
- `app_bundle`: путь `artifacts/<manifest_id>/GRAF Dev.app`; существует у активного и целевого манифестов.
- `build_dir`: путь `artifacts/<manifest_id>/build`; переходное состояние, удаляется после успешной сборки.
- `bytes`: суммарный размер набора (для отчёта).
- Правила: не более одного архива на стенд; архив принадлежит только `parent_manifest_id` активного манифеста.
- Свежесобранный кандидат сохраняет приложение до promote; каталог сборки удаляется сразу после успешной сборки. Политика хранения не может удалить кандидата, ожидающего продвижения.

### RetentionSet (вычисляемая политика)

- `active_manifest_id`: из `active-manifest.json`.
- `rollback_target_id`: `parent_manifest_id` активного манифеста (может отсутствовать).
- `keep`: соответствие `manifest_id → {archive?, app_bundle?}`:
  - активный: `app_bundle`;
  - целевой: `archive`, `app_bundle`.
- `remove`: все остальные `artifacts/<manifest_id>` и теги `graf-dev-immutable:<manifest_id>-*`.
- Правила: если `rollback_target_id` отсутствует, архив не хранится; `keep` никогда не пуст при наличии активного манифеста; свежесобранный кандидат передаётся как дополнительный `keep_extra` до promote.
- Если у целевого манифеста артефакты уже отсутствуют (удалены предыдущей уборкой), план не падает и сохраняет активный набор; `status` сообщает `archive_present=false`, а откат за пределы удержанного поколения требует пересборки.

### PruneReceipt (результат операции `prune`)

- `schema_version`: `dev-prune-receipt.v1`.
- `dry_run`: bool.
- `removed[]`: `{path, bytes, kind}` где kind ∈ `artifact_set | archive | app_bundle | build_dir | schema_snapshot | app_backup | image_tag`.
- `kept[]`: `{manifest_id, paths[]}`.
- `bytes_freed`: целое.
- `status`: `ok | partial`.
- `partial_reasons[]`: строки (например, `docker_unavailable`).
- `started_at`, `finished_at`.
- Правила: dry-run не изменяет состояние и сообщает те же пути; `status=partial` не отменяет уже выполненные удаления файлов; квитанция дописывается в `prune-history.jsonl` в state root (FR-010), dry-run в журнал не пишется.

### SchemaTransitionSnapshot (существующая, меняется жизненный цикл)

- `operation_id`: `upgrade-<ns>`; каталог `schema-transactions/<operation_id>`.
- `phase`: `prepared … verified | complete | recovered` (журнал `schema-transition.json`).
- `snapshots`: `graf-dev-postgres-data.tar`, `graf-dev-minio-data.tar`.
- Правила: удаляется при переходе в `complete | recovered`; сохраняется при любых незавершённых фазах.

### AppBackup (существующая)

- Путь `transactions/previous-<pid>-<ns>.app`.
- Правила: удаляется после успешной операции (существующее поведение) либо операцией `prune` под общим lock.

### EvidenceArtifact (артефакт доказательств CI)

- `name`: `source-revision`, `changelog`, `macos-product-<product>`, `server-result`, `macos-result`.
- `path`: относительный путь в репозитории.
- `digest`: `sha256:<64 hex>`.
- Правила: каждая запись привязана к точному `observed_sha_end`; для macOS перечисляются продукты сборки, а не весь каталог `.build`.

### SwiftBuildCache (кэш CI)

- `key`: `swift-<os>-<arch>-spm6.0.3-<hash(Package.resolved)>-v1`.
- `paths`: `apps/macos/.build`, `~/.cache/org.swift.swiftpm`, `~/Library/Caches/org.swift.swiftpm`.
- `restore_keys`: префикс ключа без хэша `Package.resolved`.
- Правила: попадание кэша не отменяет ни одну проверку; промах приводит к полной сборке; ключ меняется при изменении `Package.resolved` или версии инструмента.

## Переходы состояний

```text
build (candidate)        -> artifacts/<candidate>/{build?, app}   # archive не создаётся
promote (success)        -> active=<candidate>, target=<prev_active>
                            создаётся archive для target, app остаётся у обоих,
                            всё остальное удаляется, build/ удаляется
rollback (success)       -> active=<target>, target=<target.parent>
                            archive для нового target (может потребоваться rehydrate),
                            прежний active становится артефактом вне политики
schema promote/resume    -> phase in {complete, recovered} => удаление snapshots
prune                    -> применение RetentionSet + удаление снапшотов завершённых
                            переходов и остаточных AppBackup
unfinished transition    -> prune и автоматическая уборка запрещены (FR-004)
rollback_required        -> prune запрещён до восстановления
```

## Валидационные правила

- Удаление разрешено только внутри `GRAF_DEV_STATE_DIR`; пути проверяются на принадлежность state root (защита от выхода за пределы).
- Активный и целевой манифесты неприкосновенны; их образы остаются проверяемыми через `docker image inspect`.
- Архив целевого манифеста не удаляется, пока манифест остаётся целевым.
- Ошибка Docker переводит квитанцию в `partial`, но не прерывает файловые удаления и не изменяет active pointer.
