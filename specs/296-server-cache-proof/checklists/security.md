# Security Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 New proof fields contain no object keys, signed URLs, local paths, titles or transcripts; existing revision `manifest_sha256`/`track_sha256_by_role` fields are explicitly allowed.
- [x] CHK002 Storage status uses the request tenant context and respects billing-table RLS.
- [x] CHK003 Role matrix is exact: personal owner manage, corporate admin read-only with visible amounts, member/unknown read-only with null amounts and no management action.
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

- **Re-review 2026-11-16**: 8/12 checked, 4 unchecked. Design blockers: 0. CHK008–CHK011 are implementation-evidence items: the contracts/plans specify the behavior, but code and tests are still pending (T015, T019, T020).
- CHK003 is checked against `contracts/desktop-storage-status.md:28-37` and `data-model.md:60-65`. `data-model.md:48` wording should be aligned during implementation; it does not change the role matrix.
