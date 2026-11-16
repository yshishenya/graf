# Contracts Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 All new sync-state fields are additive with fail-closed defaults.
- [x] CHK002 Old server payloads decode in the new client and never imply safety.
- [x] CHK003 Old clients can read new payloads and old queue documents without errors.
- [x] CHK004 `playback.media_revision_id` is the server UUID and `playback.local_media_revision_id` the local ID of the actual playback revision; `finalized_upload` matches both; active `upload_session` is separate.
- [x] CHK005 `object_verified=true` requires a real stat/size match and a bounded read probe for the canonical artifact.
- [x] CHK006 `finalized_upload.archive_audio`/`finalized_at` are revision-scoped, null when no finalized session exists, and never mixed with the active `upload_session`.
- [x] CHK007 Retention exposes an effective deadline and never treats null as forever.
- [x] CHK008 Storage status role/threshold/action matrix is exact, including corporate admin and unknown role; missing DB is 503, projection failure is 200 unknown.
- [x] CHK009 Error mapping distinguishes no audio, preparing, terminal, archive false, object missing, deleting, access denied and dependency failure.
- [x] CHK010 OpenAPI drift is updated and the exact-equality test passes.
- [x] CHK011 No new database migration, enum case or queue schema version is required.
- [x] CHK012 Contract tests cover old/new compatibility and the fail-closed matrix.

## Reviewer Notes

- **Implementation re-review 2026-11-16**: 12/12 checked. Evidence: `DesktopServerProof.swift` optional decode; `DesktopUploadClientTests` old-payload/fractional/unknown/404 tests; server playback/custody/OpenAPI tests; `LocalCacheEligibilityTests` fail-closed matrix. The committed `openapi.yaml` contains the new route and schemas; the focused server lane is reported green.
- CHK004/CHK006 are covered by `DesktopServerProof.swift` separate `uploadSession`/`finalizedUpload`, `LocalCacheEligibility` server-UUID/local-ID matching, and `test_sync_state_keeps_active_revision_two_and_finalized_revision_one_separate`.
