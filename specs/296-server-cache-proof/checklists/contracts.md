# Contracts Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 All new sync-state fields are additive with fail-closed defaults.
- [ ] CHK002 Old server payloads decode in the new client and never imply safety.
- [x] CHK003 Old clients can read new payloads and old queue documents without errors.
- [ ] CHK004 `playback.media_revision_id` is the actual playback revision; `upload_session.media_revision_id` equals it; custody is read for that same revision.
- [ ] CHK005 `object_verified=true` requires a real stat/size match and a bounded read probe for the canonical artifact.
- [ ] CHK006 `archive_audio`/`finalized_at` are revision-scoped and null when no finalized session exists.
- [x] CHK007 Retention exposes an effective deadline and never treats null as forever.
- [ ] CHK008 Storage status role/threshold/action matrix is exact, including corporate admin and unknown role; missing DB is 503, projection failure is 200 unknown.
- [ ] CHK009 Error mapping distinguishes no audio, preparing, terminal, archive false, object missing, deleting, access denied and dependency failure.
- [ ] CHK010 OpenAPI drift is updated and the exact-equality test passes.
- [x] CHK011 No new database migration, enum case or queue schema version is required.
- [ ] CHK012 Contract tests cover old/new compatibility and the fail-closed matrix.

## Reviewer Notes

- Review date: 2026-11-16. Totals: 4/12 checked, 8 unchecked. See `review-2026-11-16.md` for evidence and corrections.
- CHK003 and CHK011 are checked for the additive JSON/queue-schema and persistence surface. They do not replace the compatibility and drift tests required by CHK002/CHK012.
