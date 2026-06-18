# GitHub Issue Sync: Recording Sync And Transcription Loop

Feature: `042-recording-sync-transcription-loop`
Repository: `yshishenya/crisp`

Generated from `specs/042-recording-sync-transcription-loop/tasks.md` using the project GitHub issue canon.

| Task | Issue | State | Priority | Area | Type | Title Scope |
|------|-------|-------|----------|------|------|-------------|
| `T001` | [#1191](https://github.com/yshishenya/crisp/issues/1191) | OPEN | P2 | docs | test-gap | Create implementation evidence log |
| `T002` | [#1192](https://github.com/yshishenya/crisp/issues/1192) | OPEN | P2 | docs | test-gap | Create synthetic fixture README for offline/upload/review evidence |
| `T003` | [#1193](https://github.com/yshishenya/crisp/issues/1193) | OPEN | P2 | tests | test-gap | Add server fixture helpers for revision-aware recordings |
| `T004` | [#1194](https://github.com/yshishenya/crisp/issues/1194) | OPEN | P2 | macos | test-gap | Add macOS fixture helpers for queue v2 items |
| `T005` | [#1195](https://github.com/yshishenya/crisp/issues/1195) | OPEN | P2 | docs | docs | Record checklist closure notes for 042 |
| `T006` | [#1196](https://github.com/yshishenya/crisp/issues/1196) | OPEN | P1 | db | test-gap | Add failing migration/model tests for media revisions |
| `T007` | [#1197](https://github.com/yshishenya/crisp/issues/1197) | OPEN | P1 | security | test-gap | Add failing RLS tests for media revision tenant isolation |
| `T008` | [#1198](https://github.com/yshishenya/crisp/issues/1198) | OPEN | P1 | contract | test-gap | Add failing OpenAPI contract tests for revision-aware ingest/sync fields |
| `T009` | [#1199](https://github.com/yshishenya/crisp/issues/1199) | OPEN | P1 | macos | test-gap | Add failing desktop queue schema migration tests |
| `T010` | [#1200](https://github.com/yshishenya/crisp/issues/1200) | OPEN | P1 | ingest | feature | Add media revision statuses/source kinds to apps/server/src/twobrain_rec_server/domain/statuses.py |
| `T011` | [#1201](https://github.com/yshishenya/crisp/issues/1201) | OPEN | P1 | db | feature | Add MediaRevision model and revision links |
| `T012` | [#1202](https://github.com/yshishenya/crisp/issues/1202) | OPEN | P1 | db | docs | Update model exports for media revision entities |
| `T013` | [#1203](https://github.com/yshishenya/crisp/issues/1203) | OPEN | P1 | db | feature | Add Alembic migration 0008_recording_sync_transcription_loop.py |
| `T014` | [#1204](https://github.com/yshishenya/crisp/issues/1204) | OPEN | P1 | contract | feature | Add revision-aware Pydantic schemas |
| `T015` | [#1205](https://github.com/yshishenya/crisp/issues/1205) | OPEN | P1 | ingest | feature | Add revision service helpers |
| `T016` | [#1206](https://github.com/yshishenya/crisp/issues/1206) | OPEN | P1 | macos | hardening | Add desktop queue v2 fields and conflict enum |
| `T017` | [#1207](https://github.com/yshishenya/crisp/issues/1207) | OPEN | P1 | macos | feature | Add queue v1-to-v2 migration behavior |
| `T018` | [#1208](https://github.com/yshishenya/crisp/issues/1208) | OPEN | P1 | macos | hardening | Add diagnostic redaction coverage for revision/sync fields |
| `T019` | [#1209](https://github.com/yshishenya/crisp/issues/1209) | OPEN | P1 | contract | docs | Update committed API contract reference for revision-aware ingest |
| `T020` | [#1210](https://github.com/yshishenya/crisp/issues/1210) | OPEN | P1 | macos | test-gap | Add offline enqueue/restart tests |
| `T021` | [#1211](https://github.com/yshishenya/crisp/issues/1211) | OPEN | P1 | macos | test-gap | Add local package eligibility tests for blocked/degraded recordings |
| `T022` | [#1212](https://github.com/yshishenya/crisp/issues/1212) | OPEN | P1 | macos | test-gap | Add desktop capture/upload copy tests for local-only states |
| `T023` | [#1213](https://github.com/yshishenya/crisp/issues/1213) | OPEN | P1 | macos | feature | Generate deterministic localMediaRevisionId during queue item creation |
| `T024` | [#1214](https://github.com/yshishenya/crisp/issues/1214) | OPEN | P1 | macos | feature | Preserve non-terminal local artifacts and queue state across service reload |
| `T025` | [#1215](https://github.com/yshishenya/crisp/issues/1215) | OPEN | P1 | macos | hardening | Add local-only and blocked upload labels |
| `T026` | [#1216](https://github.com/yshishenya/crisp/issues/1216) | OPEN | P1 | macos | feature | Surface local queue rows without server success claims |
| `T027` | [#1217](https://github.com/yshishenya/crisp/issues/1217) | OPEN | P1 | docs | test-gap | Record US1 validation evidence |
| `T028` | [#1218](https://github.com/yshishenya/crisp/issues/1218) | OPEN | P1 | tests | test-gap | Add server tests for idempotent meeting and media revision creation |
| `T029` | [#1219](https://github.com/yshishenya/crisp/issues/1219) | OPEN | P1 | tests | test-gap | Add server tests for immutable accepted revision fingerprints |
| `T030` | [#1220](https://github.com/yshishenya/crisp/issues/1220) | OPEN | P1 | macos | test-gap | Add desktop tests preserving meeting/revision ids across re-enqueue |
| `T031` | [#1221](https://github.com/yshishenya/crisp/issues/1221) | OPEN | P1 | ingest | feature | Create or reuse initial media revision during meeting creation |
| `T032` | [#1222](https://github.com/yshishenya/crisp/issues/1222) | OPEN | P1 | ingest | feature | Implement media revision creation/reuse rules |
| `T033` | [#1223](https://github.com/yshishenya/crisp/issues/1223) | OPEN | P1 | ingest | feature | Include media revision identity |
| `T034` | [#1224](https://github.com/yshishenya/crisp/issues/1224) | OPEN | P1 | ingest | feature | Bind upload sessions to media revisions |
| `T035` | [#1225](https://github.com/yshishenya/crisp/issues/1225) | OPEN | P1 | ingest | feature | Bind track artifacts and manifest snapshots to media revisions |
| `T036` | [#1226](https://github.com/yshishenya/crisp/issues/1226) | OPEN | P1 | macos | feature | Persist server mediaRevisionId into desktop queue truth |
| `T037` | [#1227](https://github.com/yshishenya/crisp/issues/1227) | OPEN | P1 | docs | test-gap | Record US2 validation evidence |
| `T038` | [#1228](https://github.com/yshishenya/crisp/issues/1228) | OPEN | P1 | ingest | test-gap | Add server sync-state contract tests |
| `T039` | [#1229](https://github.com/yshishenya/crisp/issues/1229) | OPEN | P1 | tests | test-gap | Add upload resume and expired-session integration tests |
| `T040` | [#1230](https://github.com/yshishenya/crisp/issues/1230) | OPEN | P1 | macos | test-gap | Add desktop client reconciliation tests |
| `T041` | [#1231](https://github.com/yshishenya/crisp/issues/1231) | OPEN | P1 | tests | test-gap | Add checksum mismatch tests |
| `T042` | [#1232](https://github.com/yshishenya/crisp/issues/1232) | OPEN | P1 | ingest | feature | Add desktop sync-state service |
| `T043` | [#1233](https://github.com/yshishenya/crisp/issues/1233) | OPEN | P1 | ingest | feature | Expose GET /api/v1/desktop/recordings/{local_recording_id}/sync-state |
| `T044` | [#1234](https://github.com/yshishenya/crisp/issues/1234) | OPEN | P1 | ingest | hardening | Return revision-aware accepted bytes and conflict states |
| `T045` | [#1235](https://github.com/yshishenya/crisp/issues/1235) | OPEN | P1 | macos | feature | Reconcile before upload attempts |
| `T046` | [#1236](https://github.com/yshishenya/crisp/issues/1236) | OPEN | P1 | macos | hardening | Persist reconciliation truth and conflict states |
| `T047` | [#1237](https://github.com/yshishenya/crisp/issues/1237) | OPEN | P1 | macos | hardening | Handle expired sessions and missing ranges without duplicate meetings |
| `T048` | [#1238](https://github.com/yshishenya/crisp/issues/1238) | OPEN | P1 | docs | test-gap | Record US3 validation evidence |
| `T049` | [#1239](https://github.com/yshishenya/crisp/issues/1239) | OPEN | P1 | tests | test-gap | Add revision-keyed processing workflow tests |
| `T050` | [#1240](https://github.com/yshishenya/crisp/issues/1240) | OPEN | P1 | tests | test-gap | Add processing pickup integration tests for media revisions |
| `T051` | [#1241](https://github.com/yshishenya/crisp/issues/1241) | OPEN | P1 | web | test-gap | Add cabinet API contract tests for media revision provenance |
| `T052` | [#1242](https://github.com/yshishenya/crisp/issues/1242) | OPEN | P1 | macos | test-gap | Add desktop embedded review link tests for revision-aware queue items |
| `T053` | [#1243](https://github.com/yshishenya/crisp/issues/1243) | OPEN | P1 | ux | test-gap | Add review accessibility, localization, and compact-width contract tests |
| `T054` | [#1244](https://github.com/yshishenya/crisp/issues/1244) | OPEN | P1 | macos | test-gap | Add embedded desktop review accessibility and status-link tests |
| `T055` | [#1245](https://github.com/yshishenya/crisp/issues/1245) | OPEN | P1 | temporal | feature | Key processing workflow identity by media_revision_id |
| `T056` | [#1246](https://github.com/yshishenya/crisp/issues/1246) | OPEN | P1 | ingest | feature | Bind processing workflows and jobs to media revisions |
| `T057` | [#1247](https://github.com/yshishenya/crisp/issues/1247) | OPEN | P1 | mediascribe | feature | Bind MediaScribe job submit/import records to media revisions |
| `T058` | [#1248](https://github.com/yshishenya/crisp/issues/1248) | OPEN | P1 | processing | docs | Include media revision provenance |
| `T059` | [#1249](https://github.com/yshishenya/crisp/issues/1249) | OPEN | P1 | web | feature | Include media revision provenance |
| `T060` | [#1250](https://github.com/yshishenya/crisp/issues/1250) | OPEN | P1 | web | docs | Render revision-aware status |
| `T061` | [#1251](https://github.com/yshishenya/crisp/issues/1251) | OPEN | P1 | macos | test-gap | Open revision-aware uploaded queue items |
| `T062` | [#1252](https://github.com/yshishenya/crisp/issues/1252) | OPEN | P1 | ux | test-gap | Apply localization-safe accessible status labels and compact-width review behavior |
| `T063` | [#1253](https://github.com/yshishenya/crisp/issues/1253) | OPEN | P1 | macos | test-gap | Apply embedded desktop review accessibility and status-link behavior |
| `T064` | [#1254](https://github.com/yshishenya/crisp/issues/1254) | OPEN | P1 | docs | test-gap | Record US4 validation evidence |
| `T065` | [#1255](https://github.com/yshishenya/crisp/issues/1255) | OPEN | P1 | macos | test-gap | Add desktop conflict-state tests |
| `T066` | [#1256](https://github.com/yshishenya/crisp/issues/1256) | OPEN | P1 | tests | test-gap | Add server sync conflict integration tests |
| `T067` | [#1257](https://github.com/yshishenya/crisp/issues/1257) | OPEN | P1 | web | test-gap | Add cabinet blocked/failed state tests |
| `T068` | [#1258](https://github.com/yshishenya/crisp/issues/1258) | OPEN | P1 | macos | test-gap | Add desktop UX copy tests for conflict states |
| `T069` | [#1259](https://github.com/yshishenya/crisp/issues/1259) | OPEN | P1 | infra | test-gap | Add infrastructure dependency failure tests for object-store writes, DB transactions, workflow start, MediaScribe, cabinet timeout, and expired upload sessions |
| `T070` | [#1260](https://github.com/yshishenya/crisp/issues/1260) | OPEN | P1 | infra | test-gap | Add local disk-full and temporary upload cleanup tests |
| `T071` | [#1261](https://github.com/yshishenya/crisp/issues/1261) | OPEN | P1 | macos | hardening | Map server sync conflicts to safe desktop states |
| `T072` | [#1262](https://github.com/yshishenya/crisp/issues/1262) | OPEN | P1 | macos | docs | Apply conflict transitions |
| `T073` | [#1263](https://github.com/yshishenya/crisp/issues/1263) | OPEN | P1 | lifecycle | hardening | Return auth/access/deletion/session conflict states |
| `T074` | [#1264](https://github.com/yshishenya/crisp/issues/1264) | OPEN | P1 | macos | hardening | Show conflict-safe queue copy and next actions |
| `T075` | [#1265](https://github.com/yshishenya/crisp/issues/1265) | OPEN | P1 | web | test-gap | Show blocked/failed review status without fake transcript |
| `T076` | [#1266](https://github.com/yshishenya/crisp/issues/1266) | OPEN | P1 | infra | hardening | Map dependency-unavailable infrastructure failures to safe sync-state responses |
| `T077` | [#1267](https://github.com/yshishenya/crisp/issues/1267) | OPEN | P1 | infra | hardening | Show disk-full, temporary cleanup, and dependency-failure next actions without private paths |
| `T078` | [#1268](https://github.com/yshishenya/crisp/issues/1268) | OPEN | P1 | docs | test-gap | Record US5 validation evidence |
| `T079` | [#1269](https://github.com/yshishenya/crisp/issues/1269) | OPEN | P1 | security | test-gap | Add no-secret/no-content contract tests for recording sync |
| `T080` | [#1270](https://github.com/yshishenya/crisp/issues/1270) | OPEN | P1 | macos | test-gap | Add diagnostic redaction tests for queue/revision fields |
| `T081` | [#1271](https://github.com/yshishenya/crisp/issues/1271) | OPEN | P1 | lifecycle | test-gap | Add lifecycle/deletion accounting tests for media revisions |
| `T082` | [#1272](https://github.com/yshishenya/crisp/issues/1272) | OPEN | P1 | security | test-gap | Add RLS enforcement tests for media revisions |
| `T083` | [#1273](https://github.com/yshishenya/crisp/issues/1273) | OPEN | P1 | lifecycle | hardening | Add media revision lifecycle state updates |
| `T084` | [#1274](https://github.com/yshishenya/crisp/issues/1274) | OPEN | P1 | lifecycle | hardening | Include media revision artifacts |
| `T085` | [#1275](https://github.com/yshishenya/crisp/issues/1275) | OPEN | P1 | macos | hardening | Redact queue/revision diagnostics on desktop |
| `T086` | [#1276](https://github.com/yshishenya/crisp/issues/1276) | OPEN | P1 | security | hardening | Add RLS policy declarations for media revision tables |
| `T087` | [#1277](https://github.com/yshishenya/crisp/issues/1277) | OPEN | P1 | docs | test-gap | Add metadata-only evidence scan notes |
| `T088` | [#1278](https://github.com/yshishenya/crisp/issues/1278) | OPEN | P2 | docs | docs | Update release notes for 042 |
| `T089` | [#1279](https://github.com/yshishenya/crisp/issues/1279) | OPEN | P1 | validation | test-gap | Run focused macOS validation |
| `T090` | [#1280](https://github.com/yshishenya/crisp/issues/1280) | OPEN | P1 | validation | test-gap | Run focused server validation |
| `T091` | [#1281](https://github.com/yshishenya/crisp/issues/1281) | OPEN | P1 | validation | test-gap | Run infra/scripts/ci-local.sh and record result |
| `T092` | [#1282](https://github.com/yshishenya/crisp/issues/1282) | OPEN | P1 | validation | test-gap | Review specs/042-recording-sync-transcription-loop/contracts/desktop-sync-contract.md |
| `T093` | [#1283](https://github.com/yshishenya/crisp/issues/1283) | OPEN | P1 | validation | test-gap | Review specs/042-recording-sync-transcription-loop/contracts/media-revision-contract.md |
| `T094` | [#1284](https://github.com/yshishenya/crisp/issues/1284) | OPEN | P1 | validation | test-gap | Review specs/042-recording-sync-transcription-loop/contracts/review-surface-contract.md |
| `T095` | [#1285](https://github.com/yshishenya/crisp/issues/1285) | OPEN | P2 | docs | docs | Update docs/current-product-status.md with accepted 042 implementation status and remaining gaps |
| `T096` | [#1286](https://github.com/yshishenya/crisp/issues/1286) | OPEN | P1 | validation | test-gap | Scan specs/042-recording-sync-transcription-loop/validation for forbidden private content before commit |

All issues use labels `feature:042`, `priority:*`, `area:*`, `gate:*`, and `type:*`.
