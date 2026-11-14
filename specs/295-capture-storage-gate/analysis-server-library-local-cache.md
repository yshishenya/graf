> **Superseded 2026-11-14**: This document records the analysis and audit findings. The authoritative F295 scope is `spec.md`/`plan.md`; F295 deletes no files. F296 is not implementation-ready until the server playback/storage contract and tombstones exist.

# Analysis: серверная библиотека и локальный кэш

**Feature**: `295-capture-storage-gate`
**Date**: 2026-11-13
**Status**: draft for independent review

## 1. Цель

Перейти от текущей схемы «локальная библиотека + жёсткий лимит 2 ГБ» к схеме:

- сервер GRAF — источник правды и долгосрочная библиотека встреч;
- macOS-приложение — буфер записи, очередь отправки и ограниченный локальный кэш;
- локальные файлы удаляются после подтверждения серверной копии и готовности серверного прослушивания;
- активная запись никогда не обрывается из-за заполнения хранилища;
- серверная квота управляет долгосрочным хранением.

## 2. Текущее состояние

### 2.1. Локальный жизненный цикл

1. `LocalRecordingWriter` пишет `manifest.json`, `meeting-review.m4a`, `meeting-transcription.wav`.
2. `DesktopUploadQueueService` добавляет `DesktopUploadQueueItem` в `upload-queue.json`.
3. После загрузки item переходит в `state = .uploaded`.
4. `retentionDecision.localArtifactsRetained = true` — локальные файлы остаются.
5. `LocalRecordingPlayer` открывает `meeting-review.m4a` локально.
6. Веб-кабинет получает локальные строки через `GRAFLocalRecordings` и показывает кнопку «Слушать запись с этого Mac» на странице встречи.
7. `DesktopMeetingShellView` показывает раздел «Записи на этом Mac», включая `uploaded`.
8. `ContentView.meetingDetectionStorageRisk()` суммирует `artifactProfile.totalUploadBytes` по всей очереди, включая `uploaded` и `terminal_deleted`.
9. `RecordingPrerequisiteGate` блокирует любой `storageRisk != .healthy`.
10. `LocalBufferService.defaultPolicy` — 2 ГБ, warning 75%, critical 90%, резерв 20 МБ.

### 2.2. Серверная сторона

- `billing/catalog.py`: Free 250 МБ, Trial 500 МБ, Personal 5 ГБ, пакеты +5 ГБ до 99 пакетов (500 ГБ).
- `classify_storage_threshold`: normal / 80% / 95% / full.
- `billing_usage_content.html`: предупреждения и действия «увеличить хранилище», «удалить старые записи», «обработать без сохранения аудио».
- `billing/storage.py`: `StorageAdmissionError("storage capacity exceeded")`, резервирование и учёт canonical playback.
- Серверное прослушивание: `cabinet/egress.py`, range-запросы, авторизация.
- Серверное удаление: deletion/purge tasks, `local_buffer_expiry_days`.
- `ServerTruthFingerprint`: `meetingId`, `mediaRevisionId`, `reviewAvailable`, `reviewStatus`, `finalizedAt`, `processingStatus`, `deletionState`, `accessState`.

## 3. Целевая модель

### 3.1. Состояния локального item

Предлагаемые состояния/флаги:

- `pending` — запись сохранена локально, ещё не отправлена;
- `uploading` — идёт отправка;
- `cached` — сервер подтвердил, локальная копия ещё хранится;
- `evicted` — локальные файлы удалены, серверная встреча доступна;
- `failed/blocked` — требует действия пользователя;
- `localOnly` — сервера нет, удалять нельзя.

### 3.2. Политика кэша

- Бюджет: 10 ГБ или 5% диска, максимум 50 ГБ (значение требует подтверждения).
- Warning: 80% бюджета.
- Critical: 95% бюджета.
- Eviction: LRU среди `cached`, начиная с самых старых/давно не открывавшихся.
- Никогда не evict: `pending`, `uploading`, `failed/blocked`, pinned, deletion-pending.
- Grace period после подтверждения сервера: 7 дней (значение требует подтверждения).
- Перед eviction: проверить `meetingId`, `reviewAvailable`/playback-ready, `deletionState`, `accessState`.
- При ошибке проверки — fail closed, файлы оставить.

### 3.3. Серверная квота

- 80% — предупреждение в приложении и кабинете.
- 95% — сильное предупреждение.
- full — новые записи не сохраняются; активная запись завершается.
- Ошибка загрузки `storage_capacity_exceeded` должна показываться понятным действием: открыть `/billing/storage` или удалить старые встречи.

### 3.4. UX

- «Встречи» — серверная библиотека, основной список.
- «Очередь отправки» — только незавершённые/ошибочные локальные записи.
- «Локальный кэш» — размер, очистка, закрепление (если нужно).
- Убрать «Записи на этом Mac» как библиотеку.
- Убрать кнопку «Слушать запись с этого Mac» для серверных встреч.
- Оставить аварийное прослушивание неотправленной/сбойной записи (рекомендация; требует подтверждения).

## 4. Что удалить

| Компонент | Действие |
|---|---|
| `LocalRecordingPlayer` | удалить или оставить только recovery preview |
| `ContentView.handleLocalRecordingAction(.open)` | убрать локальное открытие `uploaded` |
| `DesktopUploadQueueService.localPlaybackURL` | запретить для `uploaded` |
| `canOpenLocalPlayback` / `canProjectLocalPlayback` | ограничить неотправленными |
| `EmbeddedCabinetLocalRecordingRow.canOpen` | `false` для серверных записей |
| `EmbeddedCabinetLocalRecordingBridge.openAction` | убрать/перенаправить на серверную встречу |
| `cabinet.js` detail local playback | убрать кнопку |
| `DesktopMeetingShellView.localQueueRows` | только очередь, без `uploaded` |
| `DesktopMeetingShellLocalQueuePolicy` | убрать библиотеку |
| `LocalRecordingPlayer` в sync/delete/reset | удалить вместе с плеером |
| `localCaptureFailureCopy` | только для локальных сбоев |
| `meetingDetectionStorageRisk` | фактический размер кэша |
| `LocalBufferService.defaultPolicy` 2 ГБ | заменить на cache policy |
| история `uploaded`/`terminal_deleted` | архивировать/удалять после sync |
| тесты локального плеера | удалить/переписать |

## 5. Что добавить

- `LocalCachePolicy` — бюджет, warning/critical, резерв диска.
- `LocalRecordingCacheManager` — фактический размер, LRU, eviction, pin.
- `LocalCacheState` — `pending`, `uploading`, `cached`, `evicted`, `localOnly`.
- `ServerStorageStatus` — квота, использовано, threshold, ссылка.
- `StorageCapacityError` — обработка `storage_capacity_exceeded`.
- Storage page/banner в приложении.
- Миграция существующих `uploaded` и `terminal_deleted` записей.
- Очистка/сжатие очереди после eviction.
- Тесты: eviction, warning, server full, offline, account switch, migration.

## 6. Пользовательские сценарии

### Обычная запись

record → local → upload → server confirmed → cached (grace) → evicted → server playback.

### Нет сети

record → local queue → retry → upload when online. Ничего не evict до подтверждения.

### Сервер заполнен

active recording finishes; upload fails; local item remains; user sees storage action. New recordings blocked until space/upgrade.

### Сервер недоступен, но запись уже на сервере

cached item can be played locally until eviction; after eviction server playback requires server. Offline playback is a product decision.

### Нет аккаунта

local-only mode; no eviction; separate local storage policy.

### Смена аккаунта

cache scoped to account/workspace; previous account cache hidden/purged; pending items not uploaded to new account.

### Удаление

server deletion purges local cache; local cache deletion does not delete server meeting; deletion-pending blocks eviction.

## 7. Риски и слабые места

1. **Data loss**: eviction before server copy/playback is verified. Mitigation: require `meetingId` + `reviewAvailable` + reconciliation + fail closed.
2. **Offline playback loss**: after eviction no local playback. Decision needed.
3. **Queue growth**: if `uploaded` items are not removed, JSON grows for years. Mitigation: prune/compact; maybe SQLite.
4. **No account**: cannot use server library; local-only must not be evicted.
5. **Server full**: upload failures must not lose local file; active recording must finish.
6. **Account switch**: cache leakage across accounts.
7. **Deletion/purge races**: don't evict while deletion or upload in progress.
8. **Support incidents**: local files may be needed for diagnostics; use server copy/metadata if evicted.
9. **UI confusion**: recordings disappear from local list; show clear server link and cache status.
10. **Performance**: measuring cache size and rendering thousands of items; cache/index.
11. **Existing local files**: 35 uploaded items (1.1 GB) need migration; 37 terminal_deleted rows need cleanup.
12. **Server quota mismatch**: local cache must not use the server 5 GB quota as its own budget; separate values.
13. **Active upload**: eviction must not delete files being uploaded.
14. **Pinned/offline**: if supported, eviction must respect pin.
15. **Playback availability**: server `reviewAvailable` may be false during normalization; keep local until ready.
16. **Local file protection**: current files are file-protected, not app-encrypted; eviction reduces local exposure.
17. **Tests**: browser tests for local playback/rows will fail; need rewrite.
18. **Rollback**: if eviction is enabled and then disabled, evicted files cannot be restored; server copy is the recovery.

## 8. План реализации

### F295 (срочно)

- фактический размер локальной папки;
- warning не блокирует;
- блокировка только critical/full/резерв;
- скрыть красный индикатор в `.failed`;
- показать причину в меню;
- тесты и релиз.

### F296 (серверная библиотека)

1. Добавить cache policy/manager и состояния.
2. Ограничить локальное прослушивание неотправленными записями.
3. Убрать локальные строки `uploaded` из библиотеки.
4. Добавить eviction после server confirmed + grace.
5. Добавить server storage status/error mapping.
6. Добавить storage UI.
7. Свернуть/сжать очередь.
8. Миграция существующих записей.
9. Тесты, release-full, deploy.

### F297 (опционально)

- offline/pin;
- настройки кэша;
- SQLite/индекс;
- retention-политики;
- админские лимиты.

## 9. Вопросы для независимой проверки

1. Все ли места локального прослушивания/локальных строк найдены?
2. Не удаляем ли мы нужную функциональность для неотправленных/сбойных записей?
3. Достаточно ли признаков `meetingId` + `reviewAvailable`/`reviewStatus` для безопасного eviction?
4. Как отличить серверную готовность playback от просто `uploaded`?
5. Что делать при сервере без аккаунта/недоступном сервере?
6. Не сломает ли удаление `LocalRecordingPlayer` сценарии deletion/sync/reset?
7. Как мигрировать 35 существующих uploaded записей без потери данных?
8. Как сохранить support incident и deletion evidence после eviction?
9. Нужен ли SQLite вместо JSON уже сейчас?
10. Какие тесты и browser-сценарии обязательны?
11. Где серверная квота и локальный кэш могут противоречить друг другу?
12. Какие UX-состояния нужно показать пользователю?

---

# Independent review findings (2026-11-13)

The adversarial architecture review found the plan **not ready for F296 implementation**. F295 remains safe as a small bugfix. The earlier relief idea is deferred to F296b.

## P0 corrections

1. **`reviewAvailable` is not playback readiness.**
   - Server `_review_available` is true for every non-canceled processing status.
   - `reviewStatus` is about transcript/diarization, not audio.
   - `DesktopSyncReviewState` has no playback field.
   - Correction: add `playback { state, reason_code, can_play, playback_ready_at }` to sync-state and require `can_play == true`, `state == available`, `reason_code == canonical_ready`, matching meeting/media revision, `processingStatus == processed`, `deletionState == none`, valid access, conflict none.

2. **Eviction must use fresh server truth.**
   - Cached `serverTruth` can be stale; reconciliation errors are swallowed.
   - Correction: require a synchronous authenticated sync-state request at eviction time, a max age, `syncGeneration` fence, and fail closed on offline/auth/5xx/timeout/unknown. Persist an eviction receipt.

3. **Do not gate capture on server billing quota.**
   - Product gate: manual Record/Stop remains available when workspace policy permits.
   - `StorageAdmissionError("storage capacity exceeded")` occurs during normalization reservation, after upload, not at upload admission.
   - `UploadFailureCategory.storageQuota` is currently automatically retryable; make it manual-only.
   - Correction: allow local recording, keep local copy, show “server did not save audio; local copy kept”, offer upgrade/delete/`archive_audio=false`. Block capture only on real local disk reserve, not server quota.

4. **Do not prune deletion identity rows.**
   - Local purge tasks match items by `meetingId`; missing rows produce `.unverified` and a failed deletion report.
   - Current queue has 10 accepted deletion operations.
   - Correction: keep compact tombstones (`meetingId`, `directoryId`, `ownerScope`, `localArtifactsRetained=false`, `evictedAt`, evidence hash). Prune only heavy payload. Never remove while a deletion operation is open.

## P1 corrections

- Keep a first-class local cache/outbox surface and local playback for cached/unsent/failed items. Remove local playback from the **server meeting detail** and from the **main library**, not from the cache surface.
- Define offline/no-account mode explicitly. If no server, local-only is the library; no eviction.
- Reconcile cache budget with PRD: 5GB/80/95 and 10GB-or-10% reserve. Do not use 10GB/5%/50GB without a capacity table and product approval.
- Migration must delete no files on first launch; inventory, backup, dry run, user-initiated cleanup, resumable/idempotent.
- Define cache key by macOS user + server origin + workspace + actor. Hide, don’t purge, pending/failed items on account switch. Purge only verified server copies.
- Privacy: decide AES-GCM vs FileVault/File Protection risk acceptance; exclude evictable cache from Time Machine; keep outbox backed up.
- Split F296 into phases: playback contract/dry run; user-initiated cleanup/migration; automatic eviction with kill switch.
- Queue write amplification: batch progress writes, cap retry records, compact JSON; define SQLite threshold.
- Reuse existing `UploadItemState`/`RetentionDecision`; add minimal cache fields, not a duplicate state machine.
- Deletion tests must use a non-UI “local artifact present” API, not `localPlaybackURL`.

## Revised F295 scope (final)

1. Actual local footprint, measured off-main and cached.
2. Warning does not block manual or automatic start; critical/must-degrade/reserve blocks.
3. `.failed` hides the red recording light; safe failure reason in tray.
4. No file deletion, no queue schema change, no local playback removal.
5. Tests, release-full, notarization, deploy, health.

F295 relief/file cleanup is **out of scope** and belongs to F296b.

## Revised F296 phases

- **F296a**: server playback contract; eligibility predicate; dry run; no deletion.
- **F296b**: user-initiated cleanup + migration + tombstones; keep local review playback.
- **F296c**: automatic LRU eviction, budget formula, grace, pin, encryption/backup decision, performance index, kill switch.
- **F297**: optional offline pin, SQLite, admin limits, retention policies.

## Decisions required

1. Playback contract owner and exact fields.
2. Freshness requirement for eviction evidence.
3. Offline playback: cache surface vs server-only.
4. No-account/local-only support.
5. Server-full behavior: capture remains available; what is blocked (archive audio only?).
6. Cache budget: PRD 5GB/80/95/10GB reserve vs another formula.
7. Privacy: AES-GCM vs documented FileVault/File Protection.
8. Cache key and account/workspace scoping.
9. Deletion tombstone format and server acknowledgement.
10. Migration: WAV-only first step vs all local files later.
11. Performance targets and SQLite threshold.
12. Release-blocking tests and reviewer checklist.

---

# Server audit corrections (2026-11-13)

The server audit confirmed the plan's eviction predicate is unsafe. Key corrections:

## Playback proof

- `uploaded` only means `finalize` accepted the package.
- `reviewAvailable` is transcript/review availability, true during pending processing; it is not playback.
- `can_play` can be true without an object stat because `playback_artifact()` calls `review_playback_state()` without storage; later stat can fail.
- Playback may use a pinned older media revision; sync-state exposes the meeting revision, not necessarily the playback revision.
- Required contract: `playback { state, can_play, reason_code, media_revision_id, object_verified, verified_at, automatic_recovery }`. Require `available`, `can_play=true`, `object_verified=true`, `reason_code=canonical_ready`, same media revision as the local item, `archive_audio=true`, `deletion_state=none`, `access_state=owner`, retention safe.
- If any field is missing/unknown or reconciliation fails: keep local files.

## Server storage reality

- 5 GB + packages is a **canonical playback quota**, not total server storage.
- Uploads are not quota-admitted; only normalization reserves storage.
- Raw source audio is kept by default (`retention_source_audio_days=None`) and is not counted in the quota.
- `storage_capacity_exceeded` makes the normalization job terminal; increasing quota does not repair an already-uploaded meeting. Need operator repair, new revision/re-upload, or explicit retry path.
- `archive_audio=false` means no server playback (`audio_not_archived`); never evict local audio for such meetings.
- Free 250 MB, Trial 500 MB (no add-ons), Personal 5 GB + packages. Plan expiry/downgrade reduces capacity without deleting data.
- Default meeting retention is 365 days; the app has no retention field and cannot assume "forever".

## Required server/app contract additions

1. `playback` object in sync-state with actual playback revision and object verification.
2. `storage` status contract (used, capacity, threshold, plan, action, retention) for owners and a read-only/member state.
3. `upload_session.archive_audio` and server `finalized_at`.
4. `retention { delete_after, policy_state }`.
5. Separate source admission and playback admission; do not gate manual capture on billing quota.
6. Explicit error mapping: playback ready, preparing, capacity terminal, no archive, object missing, deleting, quota blocked, object-store outage.
7. `storage_capacity_exceeded` recovery/retry path; upgrade alone is insufficient.

## Migration corrections

- Do not bulk-drop 37 `terminal_deleted` rows: some are local-only deletions with `localArtifactsRetained=true` and files may still exist.
- Run `finishLocalOnlyDeletions()`/purge processing first; remove rows only when files are absent and deletion is confirmed/local-only.
- Keep compact tombstones for deletion reporting.
- Do not assume `.uploaded` items have server playback; some may have no normalization job or terminal capacity failure.
- Do not add `cached`/`evicted` to `UploadItemState` without a downgrade-safe optional field; old builds fail on unknown enum values.
- Cache is global per app channel, not per account; enforce ownerScope/workspace explicitly.

## Revised F295 safety

- Actual footprint, warning non-blocking, critical block, failed light/reason.
- **No file deletion in F295.**
- The earlier “Освободить место”/WAV cleanup idea is deferred to F296b because the current contract cannot prove `archive_audio=true`, playback readiness, or a partial-eviction ledger.
- Current production queue evidence remains useful for F296 dry-run: 31 processed, 4 failed-terminal, 2 blocked, 10 accepted deletion operations.

## Revised F296 prerequisite

Eviction cannot ship until the playback contract, object verification, archive/retention fields, deletion tombstones, and capacity recovery path are implemented and tested. Until then, keep local files.

---

# Local audit corrections (2026-11-13)

The local code audit found the original removal table unsafe and partially based on a false premise.

## Key corrections

1. **Native “Записи на этом Mac” is local-only mode, not a server library.**
   - `DesktopMeetingShellView.localMeetingsWorkspace` is rendered only when `cabinetConfigured == false`.
   - In server mode, uploaded local rows are already hidden by `cabinet.js` except during handoff.
   - Do not filter/remove `.uploaded` rows from this list; it would break local-only mode and the rule “local queue truth stays until server meeting is confirmed”.

2. **The detail button “Слушать запись с этого Mac” is a required F284 fallback.**
   - `specs/284-recording-continuity-playback/spec.md` requires local playback when server playback is unavailable due to quota.
   - `local-recording-detail.test.cjs` exercises `storage_capacity_exceeded`.
   - Do not remove it without an explicit product decision to supersede F284 and a server playback-ready contract.

3. **`LocalRecordingPlayer` must remain as a gated recovery/fallback player.**
   - It serves failed/partial capture, local-only/historical packages, and server quota fallback.
   - Keep `reconcile`, `revoke`, `close`; extend `reconcile` to close when the file no longer exists after eviction.

4. **Keep `localPlaybackURL`, `canOpenLocalPlayback`, `canProjectLocalPlayback`, bridge `openAction`, `documentScript`, message handler, `visibleItemIDs`.**
   - They are the authorization/checksum boundary for recovery playback and are covered by deletion/access tests.
   - Restrict `open` only for verified server-backed items after eviction; do not weaken checks.

5. **Keep `DesktopMeetingShellLocalQueuePolicy` progress helpers.**
   - Used by native and web rows; only `allRowsForLocalMode` is a library concept. Split, do not delete the type.

6. **Do not prune uploaded/terminal_deleted rows without a tombstone ledger.**
   - `scanAndEnqueueCompletedRecordings` re-enqueues any remaining `manifest.json`.
   - Purge acknowledgement, support incidents, notifications, analytics, and custody summaries depend on queue rows.
   - `terminal_deleted` includes local-only deletions with files still present; run `finishLocalOnlyDeletions()` first.

7. **Add, do not remove:**
   - durable tombstone/ledger keyed by `directoryId` + `meetingId`;
   - queue-owned `LocalRecordingCacheManager` with single writer/serial queue;
   - account-scoped cache (`ownerScope`), local-only policy;
   - “delete local cache only” API that does not create a server meeting deletion;
   - post-upload list refresh bridge/handoff grace;
   - `evicted` copy in local-copy/support state;
   - off-main measured footprint shared by gate and cache manager;
   - queue schema v4 downgrade guard/migration.

## Corrected removal list

- Remove only the 2 GB history-based storage gate (F295).
- Remove local playback/detail access **only after verified eviction** of a server-backed copy, or after an explicit product decision to supersede F284.
- Do not remove the player, bridge open, local-only list, progress helpers, or `localPlaybackURL`.
- Do not remove queue identity rows until tombstones, purge ack, support, notifications, analytics, and re-scan protection are in place.

## Corrected addition list

- Server playback contract with actual revision + object verification + verified_at.
- Storage status/retention/archive contract.
- Tombstone ledger.
- Queue-integrated cache manager, account scoping, local-only mode.
- Delete-local-cache-only API/UI.
- Handoff refresh/grace.
- Eviction copy/reporting.
- Tests for recovery playback, eviction, re-scan, purge ack, account switch, local-only, support/analytics continuity.
