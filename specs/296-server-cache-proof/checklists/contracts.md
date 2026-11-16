# Contracts Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [ ] CHK001 All new sync-state fields are additive with fail-closed defaults.
- [ ] CHK002 Old server payloads decode in the new client and never imply safety.
- [ ] CHK003 Old clients can read new payloads and old queue documents without errors.
- [ ] CHK004 `playback.media_revision_id` is the actual playback revision, not the meeting revision by fallback.
- [ ] CHK005 `object_verified=true` requires a real stat/size match for the canonical artifact.
- [ ] CHK006 `archive_audio`/`finalized_at` are revision-scoped and null when no finalized session exists.
- [ ] CHK007 Retention exposes an effective deadline and never treats null as forever.
- [ ] CHK008 Storage status role/threshold/action vocabulary is exact and documented.
- [ ] CHK009 Error mapping distinguishes no audio, preparing, terminal, archive false, object missing, deleting, access denied and dependency failure.
- [ ] CHK010 OpenAPI drift is updated and the exact-equality test passes.
- [ ] CHK011 No new database migration, enum case or queue schema version is required.
- [ ] CHK012 Contract tests cover old/new compatibility and the fail-closed matrix.
