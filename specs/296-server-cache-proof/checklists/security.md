# Security Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [ ] CHK001 New proof fields contain no object keys, signed URLs, local paths, titles or transcripts; existing revision `manifest_sha256`/`track_sha256_by_role` fields are explicitly allowed.
- [x] CHK002 Storage status uses the request tenant context and respects billing-table RLS.
- [ ] CHK003 Role matrix is exact: personal owner manage, corporate admin read-only with visible amounts, member/unknown read-only with null amounts and no management action.
- [x] CHK004 Playback proof fails closed when storage is missing, times out, errors, or returns a size mismatch.
- [x] CHK005 `archive_audio=false` and unknown archive custody never authorize local deletion.
- [x] CHK006 Retention `unsafe`, `blocked`, `expired`, missing or too-close deadlines never authorize local deletion.
- [x] CHK007 Open deletion, pending purge, account/workspace mismatch and sync conflict block cleanup and eviction.
- [ ] CHK008 Cleanup/eviction paths are inside the recordings root, regular files, non-symlinks; no path traversal.
- [ ] CHK009 Receipts/reports are atomic, 0600, outside the recordings root, and contain no private content.
- [ ] CHK010 Dry-run/cleanup/eviction perform no destructive server mutation, object deletion or local queue write; the idempotent sync-state expiry reconciliation is explicitly allowed and tested.
- [ ] CHK011 Effective kill switch = persisted setting && no operator env disable; disabling takes effect on the next scheduler run without restart and never restores/deletes anything else.
- [x] CHK012 Logs use sanitized codes/fingerprints and do not leak credentials, paths or meeting content.

## Reviewer Notes

- Review date: 2026-11-16. Totals: 6/12 checked, 6 unchecked. See `review-2026-11-16.md` for evidence and corrections.
- CHK002 and CHK012 are checked at the contract/design level; the route and logging implementation are still pending and must be rechecked after implementation.
