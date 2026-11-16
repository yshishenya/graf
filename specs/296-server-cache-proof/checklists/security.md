# Security Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [ ] CHK001 Sync-state and storage-status responses contain no object keys, signed URLs, hashes, local paths, titles or transcripts.
- [ ] CHK002 Storage status uses the request tenant context and respects billing-table RLS.
- [ ] CHK003 Member/corporate-admin roles cannot see amounts or management actions they are not entitled to.
- [ ] CHK004 Playback proof fails closed when storage is missing, times out, errors, or returns a size mismatch.
- [ ] CHK005 `archive_audio=false` and unknown archive custody never authorize local deletion.
- [ ] CHK006 Retention `unsafe`, `blocked`, `expired`, missing or too-close deadlines never authorize local deletion.
- [ ] CHK007 Open deletion, pending purge, account/workspace mismatch and sync conflict block cleanup and eviction.
- [ ] CHK008 Cleanup/eviction paths are inside the recordings root, regular files, non-symlinks; no path traversal.
- [ ] CHK009 Receipts/reports are atomic, 0600, outside the recordings root, and contain no private content.
- [ ] CHK010 Dry-run/cleanup/eviction do not call server mutation, object deletion, or local queue write APIs.
- [ ] CHK011 Kill switch disables automatic eviction without restoring or deleting anything else.
- [ ] CHK012 Logs use sanitized codes/fingerprints and do not leak credentials, paths or meeting content.
