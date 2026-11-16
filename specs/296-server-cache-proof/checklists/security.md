# Security Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 New proof fields contain no object keys, signed URLs, local paths, titles or transcripts; existing revision `manifest_sha256`/`track_sha256_by_role` fields are explicitly allowed.
- [x] CHK002 Storage status uses the request tenant context and respects billing-table RLS.
- [x] CHK003 Role matrix is exact: personal owner manage, corporate admin read-only with visible amounts, member/unknown read-only with null amounts and no management action.
- [x] CHK004 Playback proof fails closed when storage is missing, times out, errors, or returns a size mismatch.
- [x] CHK005 `archive_audio=false` and unknown archive custody never authorize local deletion.
- [x] CHK006 Retention `unsafe`, `blocked`, `expired`, missing or too-close deadlines never authorize local deletion.
- [x] CHK007 Open deletion, pending purge, account/workspace mismatch and sync conflict block cleanup and eviction.
- [x] CHK008 Cleanup/eviction paths are inside the recordings root, regular files, non-symlinks; no path traversal.
- [x] CHK009 Receipts/reports are atomic, 0600, outside the recordings root, and contain no private content.
- [x] CHK010 Dry-run/cleanup/eviction perform no destructive server mutation, object deletion or local queue write; the idempotent sync-state expiry reconciliation is explicitly allowed and tested.
- [x] CHK011 Effective kill switch = persisted setting && no operator env disable; disabling takes effect on the next scheduler run without restart and never restores/deletes anything else.
- [x] CHK012 Logs use sanitized codes/fingerprints and do not leak credentials, paths or meeting content.

## Reviewer Notes

- **Implementation re-review 2026-11-16**: 12/12 checked. Evidence: `LocalCacheCleanupService` path/fingerprint/fence checks; `LocalCacheCleanupTests` symlink/preexisting-symlink/atomic-receipt/0600/concurrent tests; `test_sync_state_expires_old_session_and_allows_same_revision_retry`; `LocalCacheEvictionSchedulerTests` user/operator kill-switch tests. Full Swift suite has one stale static assertion, tracked in the review report; it is not a security behavior failure.
