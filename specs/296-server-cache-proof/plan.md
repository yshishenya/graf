# Implementation Plan: F296 — Доказуемая серверная копия и безопасная очистка локального кэша

**Branch**: `296-server-cache-proof` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Status**: Planned

## Summary

F296 закрывает накопление локального кэша без риска потерять запись. Работа делится на три жёстко упорядоченные фазы:

- **Phase A (F296a)**: аддитивный серверный контракт playback/archive/retention/storage, клиентский декодер, чистый предикат пригодности и сухой отчёт. Ни одного удаления.
- **Phase B (F296b)**: пользовательская очистка только `meeting-transcription.wav` для доказанных серверных копий, с повторной проверкой, квитанцией, идемпотентностью и сохранением review-аудио/manifest/local playback.
- **Phase C (F296c)**: автоматический eviction только WAV по политике PRD (5 ГБ / 80% / 95% / 10 ГБ-или-10% / 7 дней), с kill switch, детерминированным порядком, квитанциями и fail-closed.

Phase B и Phase C могут разрабатываться в этом же поезде, но включаются только после выкладки Phase A и чистого сухого прогона на production: до этого ручная очистка и автоматический eviction выключены, а при любой ошибке доказательства файлы остаются.

## Technical Context

**Language/Version**: Swift 6.0.3 (macOS 14+), Python 3.13, FastAPI, SQLAlchemy async, PostgreSQL, MinIO/S3.

**Primary Dependencies**: существующие `DesktopUploadClient`, `DesktopUploadQueueService`, `LocalRecordingStorageUsage`, `LocalRecordingPlayer`, серверные `ingest/desktop_sync.py`, `cabinet/egress.py`, `normalization/*`, `deletion/*`, `billing/*`.

**Storage**: PostgreSQL (существующие таблицы `upload_sessions`, `track_artifacts`, `meetings`, billing), объектное хранилище MinIO; локальные файлы в `DesktopUploadQueueService.recordingsRootURL`; JSON-очередь `desktop-upload-queue.v3`.

**Testing**: XCTest (`apps/macos/Scripts/run-swift-tests.sh`), ContractValidation, pytest (`apps/server/.venv`), OpenAPI drift, GitHub `governance-fast`/`macos-pr`/`pr-metadata`, `release-full`, нотаризация/Sparkle.

**Risk / Validation Lane**: `high-risk-product` — backend-контракт, storage, retention, deletion-adjacent, локальные файлы, автоматическое удаление. Обязательны clarify, reviewer-owned checklists, analyze, issue sync, полный релизный контур.

**Release Gate**: `cd-remote.sh --dry-run`, production deploy, health/runtime SHA; Developer ID, notarization, staple, Gatekeeper, Sparkle/live appcast.

**Target Platform**: self-hosted Linux server + macOS app.

**Project Type**: web-service + desktop-app.

**Performance Goals**: сухой прогон до 200 записей, не более 2 параллельных lifecycle-запросов, timeout 5 с на запрос и 120 с на прогон; измерение размера вне MainActor; никакого перечисления файлов в SwiftUI render path.

**Constraints**: никаких миграций; аддитивный JSON; старые клиенты игнорируют новые поля; старые серверные ответы дают `unknown` и keep-local; очередь остаётся schema v3; локальный плеер/bridge/local-only не меняются.

**Scale/Scope**: текущая очередь 74 items (35 uploaded, 37 terminal_deleted, 2 blocked, 10 deletion operations); целевой объём — тысячи записей, поэтому dry-run/eviction обязаны быть bounded и не сканировать файлы в render path.

## Constitution Check

- **I. Capture-First MVP Integrity**: PASS. Запись не блокируется серверной квотой; меняется только политика локального буфера по PRD, с сохранением visible indicator и Stop.
- **II. Visible Consent And User Control**: PASS. Ручная очистка требует подтверждения; автоматический eviction объясняется и имеет kill switch; запись остаётся управляемой.
- **III. Plaintext Observability**: PASS. Новые поля не добавляют raw audio, transcript, paths или credentials; квитанции и отчёты используют отпечатки и коды причин.
- **IV. Deletion Truth And Lifecycle Accounting**: PASS. Серверная встреча не удаляется; локальная очистка учитывается квитанцией; полный purge продолжает работать; tombstone/row pruning не выполняются.
- **V. Public macOS Distribution And Update Integrity**: PASS. Developer ID/notarization/Sparkle gates не меняются.
- **VI. Spec-Driven Delivery With Testable Gates**: PASS. Полный Spec Kit, reviewer-owned checklists, analyze, issues, release evidence.
- **VII. Reference-Fidelity Product Design**: PASS. Новая copy следует существующему языку локальных записей; accessibility labels обязательны.
- **VIII. Local Cache / Server Library**: PASS. F296 реализует именно этот слой; F284 fallback сохраняется.

## Design

### Phase A — server proof, client predicate, dry run

#### A1. Server schema additions (additive, no migration)

`apps/server/src/twobrain_rec_server/api/schemas.py`:

- `DesktopPlaybackProof`:
  - `state: PlaybackPreparationStateValue = "unavailable"`
  - `can_play: bool = False`
  - `reason_code: PlaybackPreparationReasonCode = "no_audio"`
  - `media_revision_id: UUID | None = None` — серверный UUID фактической ревизии playback
  - `local_media_revision_id: str | None = None` — локальный ID той же ревизии
  - `object_verified: bool = False`
  - `verified_at: datetime | None = None` — серверное UTC-время этой проверки
  - `automatic_recovery: bool = False`
- `DesktopSyncRetentionState`: `delete_after`, `policy_state`.
- `DesktopSyncFinalizedUploadState`: `session_id`, `media_revision_id`, `local_media_revision_id`, `archive_audio`, `finalized_at`, `status`.
- `DesktopStorageStatusResponse`: `billing_role`, `access_mode`, `plan_code`, `used_bytes`, `reserved_bytes`, `capacity_bytes`, `available_bytes`, `threshold`, `action`, `action_path`, `meeting_retention_days`, `source_audio_retention_days`, `retention_policy_state`, `observed_at`.
- Add `playback` and `finalized_upload` to `DesktopRecordingSyncStateResponse`; add `retention` to `DesktopSyncMeetingState`. `DesktopSyncUploadSessionState` remains active-session-only. `finalized_upload` must describe the same server and local revision as `playback`.

Все новые поля имеют fail-closed defaults: `can_play=false`, `object_verified=false`, `verified_at=null`, `archive_audio=null`, `finalized_at=null`, `policy_state=not_configured`.

#### A2. Finalized custody lookup

`apps/server/src/twobrain_rec_server/ingest/store.py`:

- `FinalizedUploadCustody(session_id, media_revision_id, local_media_revision_id, archive_audio, finalized_at)`.
- `finalized_upload_custody_for_revision(db, workspace_id, meeting_id, media_revision_id)` — последняя `FINALIZED` сессия **ревизии playback**, с ordering `created_at desc, id desc`; sync-state передаёт `playback.media_revision_id`, а не meeting revision.
- `archive_audio_for_revision` делегирует в новый helper, сохраняя текущий legacy default `True` при отсутствии строки.

#### A3. Playback proof

`apps/server/src/twobrain_rec_server/cabinet/egress.py`:

- `desktop_playback_proof(db, *, meeting, access, revision, storage, timeout)`:
  1. `_latest_accepted_media_revision` — фактическая ревизия playback; она передаётся во все последующие чтения.
  2. `review_playback_state(..., storage=None)` — получить state/can_play/reason/automatic_recovery без небезопасной ветки «storage is None => available».
  3. Если `archive_audio_for_revision` не true → `audio_not_archived`, `can_play=false`, `object_verified=false`.
  4. Найти `_stored_review_m4a_artifact(..., revision=<та же ревизия>)`; проверить `stat_object` и bounded read probe (первые 12–64 КиБ) с timeout; `object_verified=true` только при `stat.size == artifact.byte_length` и успешном чтении.
  5. Ошибка/таймаут/несовпадение размера → `preparing`, `can_play=false`, `object_verified=false`, `automatic_recovery` по состоянию job.
  6. `verified_at=datetime.now(UTC)` только при успешной stat+read проверке.
- Не менять cabinet `PlaybackPreparationState` и его контракт.

#### A4. Sync-state builder and route

`apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`:

- `get_desktop_recording_sync_state(..., settings=None, storage=None)`.
- После expiry-restore и загрузки meeting/deletion/access:
  - `playback = await desktop_playback_proof(...)`.
  - `finalized_upload` из revision-scoped finalized custody; `upload_session` остаётся активной сессией.
  - `meeting.retention` из `retention_projection(meeting, settings)`.
- Ошибка custody/proof не должна маскировать deletion/access/conflict: конфликты строятся как сегодня, proof только дополняет.
- `api/ingest.py`: передать `settings` и `StorageDependency`; `Cache-Control: no-store`.

#### A5. Retention projection

`apps/server/src/twobrain_rec_server/deletion/retention.py`:

- `retention_projection(meeting, settings) -> (delete_after, policy_state)`.
- Explicit `retention_delete_after` приоритетен; иначе `started_at + retention_meeting_delete_after_days`.
- `unsafe`/`blocked`/`expired` сохраняются; отсутствие deadline → `not_configured`; ничего не persist на GET.

#### A6. Storage status route

`apps/server/src/twobrain_rec_server/billing/storage_status.py` + `GET /api/v1/desktop/storage/status`:

- Tenant-scoped DB (`get_request_db_session`), `Cache-Control: no-store`.
- `access_mode=manage` только personal owner + workspace owner + payer match; иначе `read_only`.
- Member: `used/reserved/capacity/available=null`, `threshold=unknown`, `action=none`. Corporate owner/admin: `read_only`, суммы видимы, `action=contact_owner`. Unknown role: safe member profile. Read-only does not imply null amounts for admin; only member has null amounts.
- Threshold `normal/80%/95%/full/unknown`; action `none/open_billing_storage/contact_owner`.
- Ошибка projection → `threshold=unknown`, без 5xx.

#### A7. Client decode

`apps/macos/Shared/Sources/Models/DesktopServerProof.swift`:

- `ServerTimestamp` — tolerant ISO8601 decoder (fractional and non-fractional).
- `DesktopServerProof` optional fields; missing → `nil`, never safe defaults.
- `DesktopUploadReconciliation` gets `proof: DesktopServerProof?` and `fetchedAt: Date`.
- `DesktopUploadClient`:
  - decode new blocks;
  - `.reloadIgnoringLocalCacheData` for sync-state;
  - 404 → nil;
  - unknown strings remain strings.
- Не менять `ServerTruthFingerprint.finalizedAt` (клиентские часы) и не persist proof в очередь.

#### A8. Pure eligibility predicate

`apps/macos/Shared/Sources/Models/LocalCacheEligibility.swift`:

- Inputs: item, document, scope, proof, local facts, policy, now.
- Gates: uploaded/finalized, owner scope, no deletion/purge, no conflict, fresh proof (`maximumProofAge = 120 s`), meeting/revision match, playback local revision == local revision and finalized_upload server/local revision == playback, `state=available`, `can_play=true`, `reason_code=canonical_ready`, `object_verified=true`, `verified_at` fresh, `archive_audio=true`, `finalized_at` non-null + grace (`7 days`), `deletion_state=none`, `access_state=owner`, retention safe (`> 30 days`), local files verified (manifest + review + WAV; size/hash).
- Any missing/unknown/error → `keep`, primary reason + all reasons.
- No IO in the predicate; no `localPlaybackURL`/player.

#### A9. Dry-run report

`apps/macos/RecApp/Sources/Upload/LocalCacheEvictionDryRunService.swift`:

- Raw read-only queue decode (no `loadItems`/`loadDocumentOnQueue`; no migration, normalization, quarantine).
- Lossy per-item decode; malformed item → `queue_item_undecodable`.
- Bounded proof fetch: max 200, concurrency 2, 5 s per request, 120 s total, generation/scope fence.
- Off-main footprint measurement using `LocalRecordingFootprintMeasurer` with timeout.
- Report to `<queue dir>/LocalCacheEviction/dry-run-<timestamp>.json` + `latest.json`, 0600, atomic; injectable directory; never inside recordings root.
- Schema `local-cache-eviction-dry-run.v1`: totals, byReason, items with fingerprints, verdict, primary/all reasons, bytes, proof summary; no paths/titles/transcripts.
- Sanitized `AppLog` event.
- Entry point: diagnostics/env `GRAF_RUN_CACHE_EVICTION_DRY_RUN=1`, no UI.

### Phase B — manual WAV cleanup

`LocalCacheCleanupService`:

- Revalidate the full predicate immediately before unlink using a fresh sync-state read.
- Delete only `item.transcriptionAudioPath` (`meeting-transcription.wav`), after verifying:
  - path is inside `recordingsRootURL`, regular file, not symlink;
  - `reviewAudioPath` and `manifestPath` exist and are readable;
  - `canProjectLocalPlayback`/`canOpenLocalPlayback` still true;
  - file size/hash match the profile.
- Capture `activeDeletionScope` + `deletionScopeGeneration` before network; re-check before unlink.
- Durable receipt: `pending` intent before unlink, `completed` after; meeting/media/playback revision, verified_at, bytes, owner scope, app version, timestamp; no paths/titles. On retry, a pending intent + missing WAV becomes `completed`/`noop`, never a second deletion.
- Idempotent: already missing WAV → success/no-op; receipt appended once.
- Queue row, `retentionDecision`, `serverTruth`, `finalizedAt` unchanged; no `UploadItemState` change.
- UI: existing local recordings surface gets «Освободить место» with confirmation:
  - copy explains WAV only, review/manifest stay, server meeting not deleted, local playback remains;
  - accessibility label/identifier;
  - no new library.
- Tests: only WAV removed; review/manifest/queue unchanged; local playback works; purge after cleanup; account switch fence; idempotency; symlink/outside-root rejection.

### Phase C — automatic WAV eviction

`LocalCacheEvictionScheduler` + `LocalCachePolicy`:

- Policy from PRD: 5 GB per device, warning 80%, critical 95%, reserve `min(10 GB, 10% of disk)`, retention/grace 7 days.
- Trigger: app launch, after upload finalization, after recording stop, after footprint refresh; debounced and single-flight; no timer in render path.
- Only WAV; only `eligible` items; oldest `verified_at`/`finalized_at` first; stop at warning.
- Never evict if kill switch off, proof missing/stale, archive false, retention unsafe, deletion/purge open, account mismatch, review/manifest missing.
- Kill switch: effective = persisted app setting (default true) AND not `GRAF_DISABLE_LOCAL_CACHE_AUTO_EVICTION`; read on every scheduler run, so disabling takes effect without restart. The first release starts with the operator env switch on until the production dry run is clean, then the operator removes it.
- Receipts same as manual; idempotent; no queue schema/row changes.
- UI: cache status + explanation + toggle; accessible; no scary/error styling for normal eviction.
- Tests: thresholds, reserve, order, kill switch, fail-closed matrix, account switch, deletion race, performance (off-main, no render path), no double delete.
- Rollback: kill switch; no file restoration (server copy is recovery); document.

### Policy change

`LocalBufferService.defaultPolicy` moves from the interim 2 GB/75/90/20 MB to PRD 5 GB/80/95/`min(10 GB, 10%)`/7 days. `LocalBufferPolicy` gets a resolved reserve helper; capture gate and cache manager share the footprint measurement. This is a deliberate product-baseline change and must be covered by tests and release notes.

## Validation Plan

- Focused server pytest: sync-state contract, playback proof, custody, retention, storage status, OpenAPI drift.
- Focused Swift tests: decode/compatibility, predicate truth table, dry-run no-mutation, cleanup/eviction, F284/local-only/deletion regression, performance contracts.
- Full `apps/macos/Scripts/run-swift-tests.sh`, ContractValidation, changelog validation.
- GitHub `governance-fast`, `macos-pr`, `pr-metadata` on exact PR SHA.
- `release-full` on frozen candidate; Developer ID/notarization/staple/Gatekeeper/Sparkle/live appcast.
- `cd-remote.sh --dry-run`; production deploy; health/runtime SHA; `validation.md` evidence.
- Real-queue dry run before Phase B/C enablement: zero file mutation, zero queue mutation, exact report SHA.

## Project Structure

### Documentation

```text
specs/296-server-cache-proof/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-sync-proof.md
│   ├── desktop-storage-status.md
│   ├── eligibility-reasons.md
│   ├── dry-run-report.schema.json
│   └── cleanup-receipt.schema.json
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── contracts.md
│   └── ux.md
└── tasks.md
```

### Source code

```text
apps/server/src/twobrain_rec_server/
├── api/schemas.py
├── api/ingest.py
├── api/auth.py
├── ingest/desktop_sync.py
├── ingest/store.py
├── cabinet/egress.py
├── deletion/retention.py
├── billing/storage_status.py
└── normalization/* (read-only reuse)

apps/server/tests/
├── contract/test_desktop_playback_proof_contract.py
├── contract/test_desktop_retention_projection_contract.py
├── contract/test_desktop_storage_status_contract.py
├── contract/test_recording_sync_contract.py
├── contract/test_desktop_status_contract.py
├── contract/test_recording_sync_no_secret_egress.py
├── contract/test_openapi_contract_drift.py
└── integration/test_desktop_sync_custody_fields.py

apps/macos/
├── Shared/Sources/Models/DesktopServerProof.swift
├── Shared/Sources/Models/LocalCacheEligibility.swift
├── Shared/Sources/Models/LocalCacheEvictionReport.swift
├── RecApp/Sources/Upload/DesktopUploadClient.swift
├── RecApp/Sources/Upload/LocalCacheEvictionDryRunService.swift
├── RecApp/Sources/Upload/LocalCacheCleanupService.swift
├── RecApp/Sources/Upload/LocalCacheEvictionScheduler.swift
├── RecApp/Sources/Buffering/LocalBufferService.swift
├── RecApp/Sources/Buffering/LocalRecordingStorageUsage.swift
├── RecApp/Sources/AppShell/ContentView.swift
└── Shared/Tests/*.swift
```

**Structure Decision**: изменения аддитивны и локализованы в существующих server ingest/cabinet/billing модулях и macOS upload/buffering слоях. Новых приложений, пакетов или схем БД нет.

## Complexity Tracking

| Change | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Separate playback proof from `review.available` | Review availability is not playback; `can_play` can be true without an object stat | Reusing review fields would delete before playback exists |
| Revision-scoped finalized custody | Active session excludes finalized; newer revision must not bleed into older local item | Meeting-level lookup can pick the wrong revision |
| Object stat verification | `can_play` can be true without verifying the object | Existence-only or no check risks deleting the only copy |
| Read-only queue snapshot | Existing `loadItems` migrates/normalizes/quarantines | A dry run must not mutate the queue |
| WAV-only cleanup/eviction | Preserves review playback and F284 fallback | Deleting all artifacts would break local playback |
| PRD policy change | 2 GB/75/90/20 MB is an interim F295 stopgap; PRD requires 5 GB/80/95/10 GB-or-10% | Keeping interim values contradicts the product baseline |
| Kill switch | Automatic deletion is irreversible locally | A code rollback cannot restore evicted files |
