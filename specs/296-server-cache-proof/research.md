# Research: F296 — proof, cleanup, eviction

**Date**: 2026-11-16 | **Feature**: `296-server-cache-proof`

## R1. What proves server playback?

**Decision**: a dedicated `playback` proof in sync-state with `state`, `can_play`, `reason_code`, `media_revision_id`, `object_verified`, `verified_at`, `automatic_recovery`.

**Rationale**: `review.available` is true for every non-canceled processing status and is transcript/diarization state, not audio readiness. `can_play` can be true without an object stat because `review_playback_state()` treats `storage=None` as available and the actual size check happens only in the streaming route.

**Alternatives rejected**: using `uploaded`, `reviewAvailable`, `processingStatus=processed`, or cached `serverTruth`; all can be true before playback is actually available.

## R2. Which revision must playback prove?

**Decision**: the actual playback revision (`_latest_accepted_media_revision`), not the meeting revision. The client compares it to `localMediaRevisionId`.

**Rationale**: playback can be pinned to an older accepted outcome revision. The meeting revision may be newer. Deleting local revision R when playback serves R′ loses the only copy of R.

**Alternatives rejected**: comparing to `meeting.media_revision_id`; it would either permanently reject valid pinned playback or authorize the wrong revision.

## R3. What does `object_verified` mean?

**Decision**: the canonical playback artifact resolved for the actual playback revision; storage `stat` succeeded; `stat.size == artifact.byte_length`. `verified_at` is the server UTC time of this response check. A bounded read probe may be added later; full hashing every poll is not required.

**Rationale**: `_canonical_object_exists()` checks existence only; the playback route rejects a size mismatch later. The proof must fail closed before local deletion.

**Alternatives rejected**: trusting `TrackArtifact.validated_at` or `source_playback_verified_at`; those are different custody gates and are not a per-response object check.

## R4. How are `archive_audio` and `finalized_at` resolved?

**Decision**: from the latest `FINALIZED` upload session for the exact meeting media revision. Both are nullable; `archive_audio=null` or `false` means keep local. `finalized_at` from the server, not the client clock.

**Rationale**: sync-state currently loads only the active session, which excludes finalized sessions. `finalizedAt` in the client fingerprint is set with `Date()` after finalize and drives upload follow-up/custody; it must not be repurposed. `archive_audio=false` can still produce a canonical artifact, so playback proof must also require archive custody.

**Alternatives rejected**: exposing the active session only; defaulting `archive_audio=true`; using the client `finalizedAt`.

## R5. How is retention made safe?

**Decision**: expose effective `delete_after` and `policy_state`. Safe = `policy_state=active`, `delete_after` non-null, and remaining > 30 days. `unsafe`, `blocked`, `expired`, `not_configured`, or near expiry = keep local.

**Rationale**: default meeting retention is 365 days from `started_at`; `retention_delete_after` may be null. `null` must never mean “forever”. `CustodyReadModel.retention_deadline` is currently hardcoded to null, so a real projection is needed.

**Alternatives rejected**: treating null as safe; using only the meeting row column.

## R6. Storage status contract and roles

**Decision**: `GET /api/v1/desktop/storage/status`, tenant-scoped, `no-store`. Owner/admin with management rights gets amounts/threshold/action; member gets read-only with null amounts. Thresholds `normal/80%/95%/full/unknown`; action `none/open_billing_storage/contact_owner`.

**Rationale**: `/auth/me` hides member amounts and lacks a desktop-specific no-store/device contract. Billing tables are forced-RLS; a bare session returns no rows. Corporate owners map to `admin`, not `owner`; management requires personal owner + payer match.

**Alternatives rejected**: extending `/auth/me`; embedding workspace-wide sums into per-item sync-state.

## R7. How does the dry run read the queue without mutating it?

**Decision**: raw `upload-queue.json` data + a private lossy decoder. Do not call `loadItems()`/`loadDocumentOnQueue()`.

**Rationale**: `loadDocumentOnQueue` can migrate schema, normalize retired items, recover incidents, and quarantine a malformed queue by deleting the file. A dry run must change nothing.

**Alternatives rejected**: adding a “dryRun” flag to the existing loader; it still risks migration paths and is harder to prove.

## R8. Local artifact verification

**Decision**: a read-only probe checks manifest, review M4A, and WAV presence, regular-file status, path containment, size, and known SHA. It does not use `localPlaybackURL` or the player as proof.

**Rationale**: `retentionDecision.localArtifactsRetained` is policy state, not disk truth. `canProjectLocalPlayback` checks size/root only; `canOpenLocalPlayback` checks more but is a UI helper.

**Alternatives rejected**: trusting the queue’s `artifactProfile` or `retentionDecision`.

## R9. Cleanup and eviction scope

**Decision**: only `meeting-transcription.wav`. Keep `meeting-review.m4a`, `manifest.json`, the directory, and the queue row.

**Rationale**: review audio keeps local playback and F284 fallback alive; the manifest is package identity and must not be rewritten; the row is needed for purge/deletion reporting and re-scan protection.

**Alternatives rejected**: deleting all local artifacts; deleting review audio; pruning queue rows.

## R10. Cache policy

**Decision**: PRD baseline — 5 GB per device, warning 80%, critical 95%, free-disk reserve `min(10 GB, 10% of disk)`, 7-day retention/grace. Configurable.

**Rationale**: F295’s 2 GB/75/90/20 MB was an interim stopgap. The PRD is the product baseline and explicitly defines these values. The reserve must be dynamic, not a fixed 20 MB.

**Alternatives rejected**: 10 GB/5%/50 GB (unapproved); keeping 2 GB (contradicts PRD).

## R11. Automatic eviction trigger and order

**Decision**: single-flight, bounded, off-main; trigger on launch, after upload finalization, after recording stop, and after footprint refresh. Evict oldest verified WAVs first until under warning. Kill switch disables all future evictions; no restoration.

**Rationale**: a background timer in the render path or unbounded scans would hurt UX. Oldest-first is deterministic and matches LRU-like intent without tracking per-file access.

**Alternatives rejected**: per-render eviction; deleting newest first; random order.

## R12. Receipt and idempotency

**Decision**: durable receipt per cleanup/eviction in `<queue dir>/LocalCacheEviction/receipts/`, atomic 0600, keyed by local recording + revision + action. Repeated action on an already-missing WAV is a no-op.

**Rationale**: deletion reporting, support, and audit need evidence; queue rows are not pruned. The receipt must not contain paths/titles/transcripts.

**Alternatives rejected**: storing receipts in the queue JSON (schema change); no receipt.

## R13. Compatibility and downgrade

**Decision**: additive JSON; new Swift fields optional; unknown strings stay strings; no new `UploadItemState` cases; queue schema stays v3; proofs are not persisted in the queue in this feature.

**Rationale**: old clients ignore unknown keys; old queue documents decode; new clients must not infer safety from missing fields. Bumping the queue schema would make older builds reject the file.

**Alternatives rejected**: schema v4; `cached`/`evicted` enum cases.

## R14. Encryption and backup

**Decision**: keep FileVault/File Protection and existing `LocalCustodyFileProtection`; app-level AES-GCM and Time Machine exclusion are out of scope for this slice. Outbox remains backed up; evictable cache is documented.

**Rationale**: changing encryption/backup is a separate privacy decision with migration and recovery impact. The PRD’s “encrypted buffer” is currently satisfied by platform file protection in this codebase.

**Alternatives rejected**: introducing AES-GCM now; changing Time Machine behavior without product approval.

## R15. Side effects of sync-state reads

**Decision**: accept the existing idempotent upload-session expiry reconciliation in sync-state; it does not touch local files or the queue. The dry-run guarantee is local: no local file/queue mutation.

**Rationale**: expiry restoration is existing server behavior needed for correct revision projection; removing it would change upload semantics. If a strict read-only mode is needed later, add a separate flag, not a behavior change in F296.

**Alternatives rejected**: a new read-only endpoint duplicating sync-state; skipping expiry (wrong revision projection).

## R16. OpenAPI and contract drift

**Decision**: update `specs/012-server-ingest-foundation/contracts/openapi.yaml` together with runtime schemas; keep the exact-equality drift test.

**Rationale**: the repo enforces exact OpenAPI equality. Additive runtime changes without the committed YAML fail CI.

**Alternatives rejected**: exempting the new route from drift; generating at test time only.

## R17. Release sequencing

**Decision**: Phase A/B/C code may ship in one train, but manual cleanup and auto WAV eviction stay disabled until Phase A is deployed and a production dry run shows zero eligible false positives. Then enable Phase B, verify, and enable Phase C only if the full fail-closed matrix and production evidence are clean; otherwise keep Phase C off behind the kill switch and follow up.

**Rationale**: the user wants full closure, but automatic deletion without production proof is the highest-risk step. The kill switch and phase gates preserve safety without another product cycle.

**Alternatives rejected**: enabling auto-eviction before the contract is live; deferring manual cleanup for a separate release when the contract is already proven.
