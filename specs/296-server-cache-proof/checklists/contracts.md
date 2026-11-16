# Contracts Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 All new sync-state fields are additive with fail-closed defaults.
- [ ] CHK002 Old server payloads decode in the new client and never imply safety.
- [x] CHK003 Old clients can read new payloads and old queue documents without errors.
- [x] CHK004 `playback.media_revision_id` is the server UUID and `playback.local_media_revision_id` the local ID of the actual playback revision; `finalized_upload` matches both; active `upload_session` is separate.
- [x] CHK005 `object_verified=true` requires a real stat/size match and a bounded read probe for the canonical artifact.
- [x] CHK006 `finalized_upload.archive_audio`/`finalized_at` are revision-scoped, null when no finalized session exists, and never mixed with the active `upload_session`.
- [x] CHK007 Retention exposes an effective deadline and never treats null as forever.
- [x] CHK008 Storage status role/threshold/action matrix is exact, including corporate admin and unknown role; missing DB is 503, projection failure is 200 unknown.
- [x] CHK009 Error mapping distinguishes no audio, preparing, terminal, archive false, object missing, deleting, access denied and dependency failure.
- [ ] CHK010 OpenAPI drift is updated and the exact-equality test passes.
- [x] CHK011 No new database migration, enum case or queue schema version is required.
- [ ] CHK012 Contract tests cover old/new compatibility and the fail-closed matrix.

## Reviewer Notes

- **Re-review 2026-11-16**: 9/12 checked, 3 unchecked. Design blockers: 0. CHK002/CHK010/CHK012 are implementation evidence: client decode, OpenAPI drift and compatibility/fail-closed tests are still pending (T007, T009, T010, T012).
- CHK004/CHK006 are checked against `spec.md:125`, `plan.md:74-92`, `research.md:13-35`, `data-model.md:67-76` and `contracts/desktop-sync-proof.md:37-54`. During implementation, the playback proof must pass the resolved `revision` explicitly, expose both server and local revision IDs, and use the finalized-custody helper; these are covered by T002/T003/T005/T009–T011.
