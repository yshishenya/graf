# Текущий статус продукта

Date: 2026-06-26

Этот документ коротко фиксирует состояние продукта во время MVP live UI
proof-slice `052-mvp-live-ui-proof`. PRD остается базовой продуктовой
линией; feature specs и metadata-only evidence остаются подробной историей
реализации.

## Accepted Now

- macOS is the selected MVP platform.
- The Core Audio HAL component publishes `2brain Rec Microphone` and
  `2brain Rec Speaker`.
- The installed local package can be upgraded, `coreaudiod` can be restarted,
  and both virtual devices return visible/alive in default-safe idle state.
- Low-resource routing is the current local default: public virtual devices
  stay lightweight while physical input/output routes are opened only when a
  virtual-device client needs audio or the user runs an explicit check.
- Non-recording passthrough smoke is accepted for Telemost, Chrome, Opera, and
  Zoom in the local environment.
- `Run Check` is now a recheck/repair action, not the normal activation path
  for ordinary browser/meeting audio.
- The current route truth model separates publication, virtual client I/O, app
  bridge, physical-device routing, and future recording triggers.
- Diagnostics and validation artifacts remain metadata-only and must not include
  raw audio, transcript text, credentials, tokens, signed URLs, passwords, or
  meeting content.
- Manual user-facing `Record`/`Stop` exists in the local macOS app with visible
  recording state and one-action stop from feature `007`.
- Local recording persistence from feature `008` is accepted for local artifact
  creation after manual `Record`/`Stop`: local mic track, remote speaker track,
  metadata-only manifest, saved/degraded/failed truth, and metadata-only
  diagnostics.
- One-minute manual recording smoke is accepted for Yandex Telemost, Chrome,
  Opera, and Zoom for features `007` and `008`: visible manual recording,
  one-action stop, and saved local recording artifacts.
- Feature `022-meeting-mute-truth` is implemented as the product-owned mute
  truth layer for local macOS recording. The desktop app exposes `Pause` and
  `Resume` beside always-available `Stop`; product Pause suppresses local
  microphone capture and records metadata-only privacy segments in
  `manifest.json`; unsupported/deferred meeting targets fail closed as
  `meeting_mute_unproven`, `unsupported`, `degraded`, or `failed`, never as a
  meeting-app-mute-respecting claim. Target-specific QA fixtures, validation
  script coverage, diagnostics redaction, and upload-queue regressions are
  included. This slice does not implement third-party Zoom/Telemost mute
  adapters or claim that meeting-app mute itself is respected.
- MediaScribe dual-track API contract is recorded in
  `docs/integrations/mediascribe-dual-track-api.md` for future backend
  transcription work. The real API key is intentionally not committed.
- Feature `010-recording-artifact-format` is accepted for local artifact
  format. Automated gates and a fresh manual `Record`/`Stop` smoke on
  2026-06-04 MSK confirmed a local package with `manifest.json`, `mic.wav`,
  `incoming.wav`, dual-track MediaScribe role mapping, readiness metadata,
  diagnostics redaction, and `007`/`008` regression validation.
- Feature `011-assisted-auto-recording` is specified but not planned or
  implemented. It records the future detect-and-ask rollout, automatic naming
  policy, and local-trust-shell/server-dashboard UI authority model.
- Feature `012-server-ingest-foundation` is implemented as the first backend
  foundation slice in this repository: FastAPI ingest service scaffold,
  local/prod Docker Compose stacks, Postgres/Alembic schema models, MinIO
  server-mediated object boundary, provider-neutral tenant/device request
  checks, upload/session APIs, resumable/idempotent part acceptance, safe
  audit/logging helpers, status contracts, and inert processing placeholders.
  Final review remediation on 2026-06-04 added persistence/storage, forged-auth,
  missing-range, readiness, and lint coverage; local validation passed `36`
  server tests, Ruff, compileall, and compose config rendering. It does not
  deploy production, implement the desktop uploader, start Temporal workflows,
  call MediaScribe, or expose dashboard/share/delete surfaces.
- A second five-round review hackathon on 2026-06-04 found that 012 was not
  PR-ready until Phase 11 remediation completed. Phase 11 tasks T119-T180 and
  GitHub issues #112-#124 have now been remediated locally with traceability in
  `specs/012-server-ingest-foundation/tasks.md` and validation evidence in
  `specs/012-server-ingest-foundation/quickstart.md`. The remaining gate before
  PR/deployment-plan handoff is a final full repository sanity run, review of
  the dirty worktree, and an explicit commit/PR decision.
- Feature `013-federated-auth-foundation` is implemented on the backend and
  provides provider-based auth, workspace membership, session, account linking,
  and registered-device identity scaffolding for later desktop upload.
- Feature `015-mediascribe-processing-pipeline` is implemented as the first
  server-side processing slice after accepted ingest. It adds durable
  processing workflow/job/result/segment/audit/dependency tables, idempotent
  `processing/<meeting_id>` workflow identity, internal pickup, server-side
  dual-track MediaScribe submission from owner-controlled artifacts,
  poll/import services, content-safe processing status, failure/retry
  classification, restart-safe job reuse, and metadata-only dependency truth.
  On 2026-06-11, `master` at `4cda38c` was deployed to
  `2brain.dev:/opt/projects/2brain-rec` with the production processing worker
  and Temporal services running. A real local app recording passed production
  e2e through public upload/finalize, internal pickup, Temporal worker
  processing, live MediaScribe submit/poll, result import, content-safe status,
  and cleanup: workflow `processed`, MediaScribe job `ready`, result
  `imported`, transcript and diarization available, dependency state
  `mediascribe:imported`, and no cleanup residue.
  Desktop clients still do not call MediaScribe, hold MediaScribe credentials,
  receive signed dependency URLs, or receive transcript/audio/download surfaces
  in this slice.
- Feature `016-meeting-dashboard-review` is implemented as the server-owned web
  cabinet for meeting review. It adds authorized meeting list/detail APIs and
  HTML routes, ready/partial/processing/failed states, safe transcript and
  speaker timeline rendering, truthful unavailable states, non-mutating
  governance placeholders, desktop-embedded route variants, responsive
  screenshots, and no-secret/no-private-content validation. It intentionally
  does not execute share/export/download/delete/retention policies or replace
  native desktop capture controls.
- Feature `017-access-sharing-downloads` is implemented as the browser/server
  owned access, sharing, download, and export layer for accepted meeting review
  data. It adds effective owner/team/shared/denied access decisions for list,
  detail, share, download, export, and desktop-embedded routes; login-required
  share grants and revocation; server-mediated artifact downloads;
  policy-filtered export packages; metadata-only access/egress activity; truthful
  post-egress deletion copy; RLS coverage for the new access/egress tables; and
  synthetic screenshot evidence for desktop and compact layouts. It does not
  enable public links, external-recipient invitations, retention execution,
  deletion execution, admin policy editing, billing, or desktop-owned egress
  policy. On 2026-06-16, `master` at
  `39b8c5fbfae74159e5e50f5c2471f19ff64f1e36` was deployed to
  `2brain.dev:/opt/projects/2brain-rec`; production read-only verification
  showed `rec-api` healthy, Alembic `0006_access_sharing_downloads`, and
  `/api/v1/health/live` plus `/api/v1/health/ready` returning ok/ready. This is
  `infra_smoke_ready` evidence, not user rollout readiness.
- Feature `018-retention-deletion-execution` is implemented and production-smoke
  validated as the server-owned retention and deletion execution layer after
  access/share/download/export. It adds whole-meeting deletion requests,
  immediate access blocking for deleting/deleted meetings, metadata-only
  deletion verification reports, retention policy snapshots and scans,
  device-scoped local desktop purge tasks and acknowledgements, truthful backup
  expiry state, MediaScribe/Langfuse/workflow/temp/diagnostics dependency
  limits, post-egress copy limits from existing egress audit, lifecycle activity
  rows, safe retry guidance, and RLS coverage for deletion lifecycle tables.
  Desktop clients can list and acknowledge local purge tasks without uploading
  private proof payloads. On 2026-06-16, `master` at
  `ab875e7ba50f15ff57323581ba0edfa7abd5ad5c` was deployed to production and
  verified within the `infra_smoke_ready` boundary. This slice does not add
  public links, external-recipient invitations, partial deletion, legal-hold
  management, admin retention editing UI, billing, or desktop-owned deletion
  policy.
- Feature `034-mvp-loop-readiness` is implemented as the launch-readiness gate
  over the owner MVP value loop. It produces metadata-only JSON/Markdown
  readiness evidence, a launch gap register, clean-room reference comparison,
  desktop/web/policy lifecycle local-runtime regression evidence, and bounded
  claim rules. Its current outcome is `pilot_blocked`: the strongest production
  claim remains `infra_smoke_ready`, while `mvp_loop_ready`,
  `internal_pilot_candidate`, `user_rollout_ready`, and `production_ready` stay
  excluded until P1 launch blockers are closed.
- Feature `035-mvp-loop-live-evidence` is implemented as the current
  validation-only evidence pack after `022`. It proves the installed
  `/Applications/2brain Rec.app` desktop loop with Record, Pause, Resume, Stop,
  metadata-safe screenshots, and latest local artifact validation. It also
  checks the production web owner route on `rec.2brain.pro`: `/meetings` exists
  but live owner review remains blocked by `401 missing_auth_context`, while
  list/detail/governance behavior is covered by safe fixture-backed evidence.
  The strongest truthful claim remains `pilot_blocked` with bounded
  `infra_smoke_ready`; `mvp_loop_ready`, `internal_pilot_candidate`,
  `user_rollout_ready`, and `production_ready` remain excluded.
- Feature `042-recording-sync-transcription-loop` is implemented and
  local-gate validated in the current feature branch. It adds an offline-safe
  desktop upload queue v2, deterministic local media revision identity, server
  `MediaRevision`, resumable sync-state reconciliation, one logical meeting
  with one accepted initial revision, revision-keyed processing workflow
  identity, MediaScribe provenance, web and embedded desktop transcript review
  parity, visible conflict/recovery states, metadata-only diagnostics, deletion
  lifecycle accounting, and RLS coverage for the new media revision table.
  Focused validation passed macOS queue/review/diagnostic tests, server
  ingest/sync/processing/cabinet/RLS tests, and the final
  `infra/scripts/ci-local.sh` gate. This is local implementation readiness
  only: the branch is not merged, not PR-reviewed, not deployed, and has no
  production upload-to-transcript e2e evidence yet.
- Feature `045-transcription-results-pipeline` is implemented, merged,
  released as `v2026.06.24.1`, and deployed to production. Structurally valid
  local packages remain upload/transcription eligible even when local leakage,
  echo, silence, timing, or transcription-readiness checks are degraded,
  failed, inconclusive, or unavailable. Consent, permission, missing/unreadable
  files, package role/size/checksum/fingerprint integrity, lifecycle, and
  privacy boundaries remain hard gates. Accepted server finalization starts or
  reuses one processing workflow when processing is enabled, unavailable
  dependencies become visible processing blockers without rolling back upload
  success, and web plus embedded desktop review expose matching transcript and
  diarization availability for the accepted media revision. Quality warnings
  are retained as metadata-only artifact profile context, not as queue-blocking
  failure reasons. Production evidence on 2026-06-24 proved a real installed
  app recording could upload, finalize, process through MediaScribe, and reach
  a review state with transcript, diarization, playback, workflow presence, and
  both source roles visible. Speakerphone quality remains a product limitation:
  the pipeline accepts degraded-but-structurally-valid recordings, but this is
  not proof of clean echo/noise suppression.
- Feature `046-meeting-playback-timestamp-seek` is implemented, merged through
  PR `#1564`, released as `v2026.06.24.2`, and deployed to production. A ready
  meeting can expose a server-owned playback route, the review page can render
  an audio player, transcript timestamps can seek the player, and web plus
  desktop embedded review use the same playback state. For recordings with
  microphone and incoming/system audio, review playback must represent both
  retained sources in one review stream; if one source is missing, purged, still
  processing, failed, deleted, not allowed, or unsafe to combine, playback fails
  closed with a simple unavailable state. Latest closeout evidence on
  2026-06-24: focused 046 server quickstart `39 passed`, browser runtime
  `failures=[]` across web/embedded desktop/mobile and blocked states, macOS
  SwiftPM suite `575 tests, 0 failures`, GitHub Release published in Russian,
  open 046 GitHub issues `[]`, and production deploy `deploy_result=pass` with
  `readiness_verdict=infra_smoke_ready` on deployed commit `cd168c0`. The
  installed local app bundle is version `2026.06.24.2` and launches from
  `/Applications`. This still does not implement real echo cancellation,
  noise suppression, transcript editing, waveform generation, signed/notarized
  external distribution, or final user-rollout readiness.
- Feature `047-cabinet-runtime-truth` is implemented, merged through PR
  `#1635`, released as `v2026.06.25.2`, and deployed to production on top of
  the `048` playback baseline as the macOS cabinet trust correction. The desktop
  shell no longer treats a configured cabinet URL as proof that the server,
  session, or review surface is healthy. It starts configured cabinets in a
  neutral checking state, shows server-unavailable truth for offline/timeout
  navigation failures, treats successful login/sign-up page loads as
  auth-required instead of ready, and shows green cabinet status only after an
  allowed authenticated meeting list/detail route finishes. The runtime state
  is shared from the embedded WebKit cabinet into the native shell, while
  native Record/Stop/upload truth remains visible for every cabinet state.
  Local evidence on 2026-06-25: focused macOS cabinet tests passed
  `20 + 15 + 9` tests, full macOS SwiftPM passed `579 tests, 0 failures`,
  focused server cabinet tests passed `43 passed`, fixture and real-server
  Playwright/Chrome runtime checks passed with `failures=[]`, production health
  returned live `ok` and ready `ready`, full local CI passed
  `570 passed, 4 skipped, 8 warnings`, deploy dry-run returned
  `deploy_result=dry_run`, and production health returned live `ok` and ready
  `ready` after release closeout.
- Feature `048-real-playback-availability` is implemented, merged through PR
  `#1610`, released as `v2026.06.25.1`, and deployed to production as the
  product-visible playback correction after `046`. A normal ready owner review
  no longer needs `audio_download=allowed` to show playback: review listening
  is separated from file download/export policy, while the "Files" audio
  download action can remain policy-blocked. The web review and macOS embedded
  review render the same transcript-first surface with a persistent bottom
  player, timestamp seek controls, speed/skip/time controls, and diarization
  speaker lanes. The playback route is server-mediated, relative, range-aware
  (`206`/`Accept-Ranges`/`Content-Range`), and does not expose signed URLs,
  storage object keys, raw audio diagnostics, or private paths. Closeout
  evidence: RED reproduced the 046 real-product gap (`15 failed, 14 passed`),
  extended focused validation passed `48 passed, 1 warning`, the real local
  FastAPI/Playwright verifier on 2026-06-25 passed across ordinary web,
  mobile-width web, and desktop embedded review with range playback and no
  visible audio download link, full local CI passed
  `570 passed, 4 skipped, 90 warnings`, and production deploy returned
  `deploy_result=pass` with deployed SHA
  `94e6cbfa2c15d9e3e94ee8d533c13d91b0f5c4d9`; the later
  `v2026.06.25.2` production release still contains the 048 playback merge.
  This still does not implement materialized compressed share audio, public
  links, real echo cancellation, noise suppression, waveform generation,
  transcript editing, native Swift playback controls, signed/notarized
  distribution, or final user-rollout readiness.
- Feature `049-meeting-outcomes-mvp` is implemented, merged through PR `#1706`,
  released as `v2026.06.25.4`, and deployed to production as the stored meeting
  outcomes slice for MVP readiness. The notes/action output blocker is closed
  by stored, launch-safe outcome rows:
  summary, key points, decisions, action items, follow-ups, risks, questions,
  and evidence states are materialized only from transcript-backed source
  segments, with category-level not-found/not-inferable truth instead of
  fabrication. Web review and macOS embedded review share the same server-owned
  response, responsive layout, source evidence rows, processing/blocked/partial
  states, and playback coexistence. Privacy boundaries stay in force: outcome
  text is hidden from list egress and denied/deleted/deleting states, outcome
  artifacts are included in deletion accounting, RLS inventory covers outcome
  tables, and committed evidence remains metadata-only. The notes/action output
  blocker is closed for the MVP surface; follow-up work is quality, editing,
  richer controls, and rollout hardening, not basic outcome availability. This
  does not claim production rollout readiness by itself.
- Feature `050-mvp-launch-proof` is implemented, merged through PR `#1753`,
  released as `v2026.06.25.5`, and deployed to production as the MVP
  launch-proof closeout slice. It verifies the installed macOS app, production
  server, web cabinet, embedded review, playback, transcript, diarization,
  speaker timeline, stored outcomes evidence, product status, release notes,
  and deploy truth against a bounded MVP claim. The final 050 claim remains
  `pilot_blocked`: playback, timestamp seek, bottom speaker timeline,
  web/embedded parity, truthful macOS cabinet state, docs, release, and deploy
  gates passed; `mvp_loop_ready`, `internal_pilot_candidate`,
  `user_rollout_ready`, and `production_ready` stay excluded until a fresh live
  owner journey, stored outcomes on a production candidate, and representative
  one-hour timing proof pass with metadata-only evidence.
- Feature `058-web-cabinet-htmx-shell` is implemented in the current feature
  branch as a local architecture refactor for the server-owned cabinet shell.
  It fixes the frontend foundation as Jinja templates, reusable cabinet
  component macros, one static CSS/token layer, centralized Lucide-style inline
  SVG icons, and locally vendored HTMX `2.0.10`; Tailwind, ready UI kits, SPA
  frameworks, CDN UI assets, frontend build pipelines, component preview apps,
  and separate design-system packages remain out of scope. Browser and desktop
  embedded cabinet list/detail routes share one online shell, HTMX updates are
  bounded fragments with full-page fallback, unsafe cookie-authenticated
  cabinet actions require CSRF proof, and desktop route policy uses exact
  approved route kinds including deletion reports. Native Record/Stop, active
  capture, upload truth, permission recovery, diagnostics, and offline recovery
  remain outside WebView ownership. Local evidence on 2026-06-26: targeted
  server checks passed `93 passed, 5 warnings`; runtime checker passed
  `result=pass` across `8` synthetic surfaces and `12` checks; desktop cabinet
  checks passed `63 tests, 0 failures`; static source guard passed; full local
  CI passed `685 passed, 4 skipped, 94 warnings` with `ci_local_result=pass`.
  This branch has no database migration or machine-readable JSON contract
  change and is not merged, released, deployed, or production-smoked yet.
- Feature `036-owner-review-live-polish` is implemented as the current owner
  review visual/auth baseline. It adds browser email login/signup flows, Postal
  delivery configuration, session-protected web cabinet routes, installed
  desktop login recovery, denser clean-room meeting list/detail surfaces, and
  native/embedded shell polish. The 036 readiness pack now records the bounded
  `pilot_blocked` outcome: visual/product polish and notes/action truth states
  are accepted, and the installed-app idle/active/paused/resumed/stopped
  walkthrough is covered by cropped native-inspector evidence. Live owner
  list/detail/governance proof is now committed as metadata-safe Chrome owner
  session evidence. Launchable generated notes/actions or an explicit pilot
  deferral, plus production user rollout evidence, remain separate blockers.
  Evidence remains metadata-safe and keeps the production
  claim bounded unless a separate rollout gate proves stronger live owner-review
  behavior.
- Feature `043-app-zoom-shortcuts` is implemented on top of the `036` owner
  review shell baseline as a local macOS readability feature. Standard macOS
  shortcuts adjust only the embedded meeting workspace zoom, persist the local
  supported zoom value, recover invalid saved values to 100%, and leave native
  Record/Stop/upload truth/local readiness outside the scaled WebKit surface.
  This slice does not change capture, upload, backend meeting data, retention,
  deletion, auth, or production rollout state.
- Feature `038-apple-voice-processing-spike` is implemented as a bounded
  metadata-only Apple candidate evidence slice. Its current primary outcome is
  `defer_to_webrtc_aec3`: Apple processing is not accepted for built-in
  speakerphone recording, original `mic.wav`/`incoming.wav`/`manifest.json`
  package truth remains authoritative, existing `020` leakage finalization
  remains the clean/leakage/unproven authority, and user-facing/release-facing
  copy must not claim clean speakerphone behavior from Apple evidence. The next
  technical slice is `039-webrtc-aec3-speakerphone-spike`.
- Feature `033-desktop-cabinet-embedding` is implemented as the macOS shell
  bridge for the accepted `016` cabinet route classes. The desktop app now
  opens a `Встречи` workspace after native capture controls, hosts embedded
  meeting list/detail surfaces through WebKit, preserves native Record/Stop and
  upload truth outside the embedded surface, shows bounded unavailable/auth
  states, and opens review only for uploaded queue items with server meeting
  identity. Screenshot evidence uses synthetic local fixtures and contains no
  Krisp private captures, real account identifiers, transcript text, raw audio,
  signed URLs, or live local paths.
- Feature `021-production-deployment-plan` is implemented as a remote-first
  infrastructure readiness slice for `2brain.dev` and `/opt/projects/2brain-rec`.
  It adds production Compose hardening, env/secret templates, remote backup,
  migration, restore rehearsal, rollback/halt helpers, internal smoke identity,
  first-smoke evidence templates, cleanup accounting, and forbidden-content
  scans. The highest allowed successful status is `infra_smoke_ready`; this is
  not production readiness, user rollout readiness, or internal pilot readiness.
- Feature `031-rls-hardening` is implemented and deployed as a backend tenant
  isolation hardening slice. It adds PostgreSQL RLS policies for accepted
  tenant-owned identity, auth/session/device, ingest, meeting, processing,
  transcript, audit, and dependency tables; explicit request, worker,
  auth-bootstrap, session-lookup, callback-lookup, and allowlisted maintenance
  DB contexts; rollout/rollback validation helpers; and ADR `003` for future
  tenant-owned tables. Production inspection on 2026-06-15 showed
  `/opt/projects/2brain-rec` at commit `3fd2162`, Alembic
  `0005_rls_hardening`, and every covered production table reporting
  `relrowsecurity=true` plus `relforcerowsecurity=true`. It does not add
  dashboard, share/download, retention, deletion execution, billing, admin UI,
  desktop capture/upload, or new MediaScribe behavior.
- Feature `032-rls-live-enforcement` corrects the stale `031` rollout truth:
  production RLS enforcement is verified enabled and forced through read-only
  PostgreSQL catalog metadata, while destructive same/cross-tenant probes
  remain limited to disposable or explicit test databases.
- Feature `025-system-audio-capture-pivot` is accepted as the macOS MVP
  recording path. It records local microphone plus incoming/system audio without
  requiring virtual device selection, preserves dual-track local artifacts, and
  closes the final evidence gates for permission matrix, controlled artifact,
  CPU/resource behavior, 30-minute development validation, 75-minute release
  validation, forbidden-content scan, and final scope review.
- Feature `020-speaker-to-mic-leakage` is accepted as the post-stop
  finalization truth gate for local dual-track packages. After `Stop`, saved
  `mic.wav` and `incoming.wav` evidence is measured against
  `leakage-threshold.v1`; `manifest.json` uses
  `local-recording-manifest.v3`; contaminated, ambiguous, malformed,
  misaligned, not-measured, or unproven packages still record local
  transcription-readiness failure/degradation truth. Feature `045` changes how
  that truth is used for product upload/transcription eligibility: for
  structurally valid packages it is diagnostic metadata, not an upload blocker.
  The implementation is integrated on top of the accepted `025` system-audio
  capture path and does not replace scope approvals, permissions,
  capture-health evidence, dual-track role mapping, or system-audio recording
  truth.
- `020` diagnostics remain metadata-only: leakage status, transcription gate,
  route metadata, threshold metadata, and measurement summaries may be included,
  but raw audio, transcript text, credentials, tokens, signed URLs, passwords,
  meeting content, and live filesystem paths remain forbidden.
- `020` is finalization-only. It does not introduce external egress, a
  MediaScribe call, live echo cancellation, recording-time route remediation,
  driver fallback, or a customer-visible auto-start policy.
- The driver-based live virtual-device publication blocker from `019` / issue
  #234 is superseded for MVP recording by `025` and parked as future
  advanced-routing work. Its unsafe HAL publication attempts remain preserved
  as negative evidence and must not be counted as accepted driver evidence.
- ADR `001-local-trust-shell-and-server-dashboard` is accepted. Capture-critical
  desktop trust surfaces stay local/native; server/web surfaces own
  post-meeting, transcript, notes, admin, retention, deletion, audit, and fleet
  workflows.

## Not Accepted Yet

- Yandex Browser is intentionally skipped/not accepted in the current
  browser/meeting smoke cycle.
- Third-party meeting-app mute adapters are not accepted yet. Local privacy
  truth is product-owned through 2brain `Pause`/`Resume`/`Stop`; Zoom/browser
  mute state remains unverified unless a future adapter provides fresh
  target-specific evidence.
- Built-in speakerphone clean dual-track acceptance remains constrained by
  `020`/`038` evidence: packages can be captured and, after `045`, structurally
  valid imperfect packages can still proceed to server transcription, but the
  product must not label polluted microphone audio as clean local speech.
  Feature `038` did not accept Apple processing for built-in speakerphone
  recording; `044` remains the real echo/noise suppression runtime candidate.
- Driver live virtual-device publication is not accepted for MVP recording and
  must not be revived without a separate future advanced-routing spec,
  implementation, and safety evidence.
- Public meeting links, external-recipient invitations, partial deletion,
  legal-hold management, admin retention editing UI, billing, and desktop-owned
  deletion policy remain later slices.
- Feature `042` production behavior is not accepted yet. The local
  implementation passed `ci-local`, but merge, PR review, deployment,
  production smoke, and production upload-to-transcript evidence still need a
  separate approval and closeout.
- Production RLS coverage is accepted only for the `031` covered table
  inventory. Future tenant-owned tables and product surfaces still need their
  own ADR `003` classification, tests, and metadata-only evidence before merge.
- Feature `011-assisted-auto-recording` remains requirements-only. Detect-only,
  detect-and-ask, automatic naming, and future auto-record behavior have not
  been implemented or accepted.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.
- Feature `030-mvp-experience-design-system` now provides the MVP product
  experience/design handoff: full clean-room Krisp/2brain audit, native vs web
  route boundaries, status/provenance matrices, screen specs, server-owned
  embedded product UI contract, and the active Figma v8 clean Russian review
  candidate. V8 supersedes the v5-v7.4 prototype lineage after stakeholder and
  five-critic reviews found flow, density, settings, technical-copy, and
  visual-quality blockers in earlier drafts. Current V8 evidence covers 17
  top-level MVP frames, 98 valid click reactions, dark/light theme proof,
  shared upload/search overlays, desktop/web owner-value-loop coverage, and a
  stakeholder visual approval pack.
  V8 is the implementation baseline for the first real desktop/web UI slice;
  final stakeholder visual acceptance remains the polish gate for declaring the
  interface handoff final. This is design-readiness evidence only; it does not
  implement production desktop or web UI.

## Next Product Slice

Feature `050-mvp-launch-proof` is closed as the MVP launch-proof slice. Its job
was to decide, with evidence rather than optimism, whether the current product
can be called an internal pilot candidate.

Feature `051-mvp-owner-journey-proof` is implemented, merged through PR `#1799`,
released as `v2026.06.25.7`, deployed to production at
`67cb9a15752143881cb0123e1ef5fa9c9c60a632`, and followed by post-deploy
closeout release `v2026.06.25.8`. It did not add a new user feature. It checked
the installed app, production health, short production processing metadata,
stored outcomes, playback/timeline runtime, macOS cabinet truth, and readiness
docs before any MVP claim could be raised.

The 051 result keeps the product at `pilot_blocked`: installed app identity,
current production health, local web/embedded playback/timeline/outcome runtime,
and native false-green guards pass, but the three P1 proof gates below remain
open.

Feature `052-mvp-live-ui-proof` is implemented, merged through PR `#1844`, and
followed by production fix PRs after deploy and cleanup gates exposed real
blockers. It rechecks the real installed app, production cabinet, KRISP-style
playback/timeline reference, stored outcomes, and timing before any stronger
MVP claim. The current deployed release is `v2026.06.26.3` at
`6c1b2f2ffa2545ee3a2f5bc5af734b0f19bcbd1e`: public health returns live `ok`
and ready `ready`, production smoke passes, and synthetic timing artifacts were
cleaned up without residue. Earlier 052 production fix PR `#1845` shipped
`v2026.06.25.10` at `db1eca18f08d26f6816b2bd88067709d0e57e590`: production
smoke reported `processing=enabled`, `temporal=configured`, and
`mediascribe=dispatcher_only`; `rec-api` dispatches Temporal work, does not mount the MediaScribe key,
and the key stays on `rec-processing-worker`.

The allowed current claim remains `pilot_blocked`. The bounded shipped claim is
`infra_smoke_ready`; `mvp_loop_ready`, `internal_pilot_candidate`,
`user_rollout_ready`, and `production_ready` remain excluded until the
fresh owner journey, production stored outcomes on that journey, and live
owner-review UI gaps are closed. 052 fixture-backed web/mobile/embedded checks
pass playback, timestamp seek, speaker lanes, and stored outcome rows; the
installed macOS shell also avoids a false-green cabinet state. A production-safe
synthetic one-hour candidate processed in 37 seconds created-to-imported, under
the 180-seconds-per-hour target, with transcript, diarization, playback, speaker
timeline, and stored outcome counts available. Live production owner review
remains degraded. The latest fresh installed-app candidate proves record,
upload, finalization, and processing, but imported `0` transcript segments and
`0` diarization segments; its stored outcome set is blocked with
`outcomes_transcript_unavailable`. That candidate cannot close review,
speaker-timeline, or stored-outcome proof, so these local and production checks
still do not prove MVP rollout readiness.

Feature `057-local-upload-custody` is implemented, merged through PR `#2052`,
and released as `v2026.06.26.12` as the product-owned custody layer for local
desktop recordings.
It keeps the server WebView meeting list authoritative, removes normal-user
transport retry controls, preserves local recordings with automatic custody
processing, exposes compact native aggregate status, emits metadata-safe
admin/support incident truth, separates upload/processing/deletion/local purge
states, and fails closed on local purge acknowledgement unless deletion,
tombstone, or unrecoverability is verified. Focused local evidence passed the
057 Swift custody/purge/projection suites and focused server custody/purge
read-model suites on 2026-06-26. This is merged/released local implementation
readiness, not production-smoked evidence, and feature `058` still owns server
cabinet presentation refactor work.

Current evidence already accepted before 050:

- `045` lets structurally valid recordings proceed to upload/transcription even
  when local audio quality diagnostics are degraded, while keeping permission,
  consent, integrity, lifecycle, and privacy gates hard.
- `046` and `048` provide real review playback, server-mediated range playback,
  and transcript timestamp seek in web and embedded review.
- `047` keeps the macOS cabinet status honest: green state requires a real
  authenticated allowed route, not just a configured URL.
- `049` closes the notes/action output blocker with stored meeting outcomes,
  transcript-backed evidence, category truth, privacy/deletion/RLS coverage, and
  web/embedded review parity.

Remaining launch boundary after 052:

- `fresh-owner-journey-evidence` stays open until a current live owner journey
  proves record/stop/upload/finalize/process/review from the installed app.
  The latest fresh candidate reaches processing, but not usable review content.
- `production-stored-outcomes-evidence` stays open until a current production
  installed-app candidate shows stored outcome states and counts without private
  generated text. Synthetic production-safe outcome counts exist, and the
  latest fresh candidate has a blocked outcome set, but neither replaces a
  fresh candidate with reviewable transcript content.
- Live owner-review UI proof stays degraded until authenticated production
  detail and embedded review can be opened and checked end to end; the
  historical production blocker remains recorded as `missing auth context`
  where the live route cannot prove owner context.
- Signed/notarized installer evidence, Yandex Browser support, real
  speakerphone echo/noise suppression, compressed share audio, public links,
  waveform polish, transcript editing, and native Swift playback controls remain
  outside the MVP launch-proof claim unless a later spec changes scope.

A remote `021` infrastructure smoke on `2brain.dev` can continue only within
the `infra_smoke_ready` boundary until user rollout slices and live journey
evidence are separately accepted.

Keep separate unless the next spec explicitly changes scope:

- Public-link and external-recipient sharing policy: optional public links,
  expiration, abuse controls, external invitations, and legal/admin copy.
- Notes/action output: `049` closes the MVP blocker with stored meeting
  outcomes. Follow-up work is quality/model improvement, editing, richer
  owner controls, or rollout hardening, not a replacement for the basic stored
  outcome surface.
- Interactive playback/timestamp seek: real visible owner review playback is
  implemented, merged, released, and production-smoked in `048`. Remaining
  playback-related work is post-MVP scope such as compressed share audio,
  public links, waveform polish, native Swift controls, or editing.
- Assisted auto-start and generalized meeting detection.
- Live speakerphone cleanup/AEC: Apple voice processing, WebRTC AEC3, custom
  AEC, and mixed-audio fallback remain decision records or future spike gates
  after `020`. They are not runtime behavior in the finalization-only slice.
  Detailed prepared backlog context is recorded in
  `docs/audio-capture-backlog.md`.
- Post-MVP editing and media revision work is tracked in
  `docs/post-mvp-editing-media-backlog.md`: local media trim/edit revisions,
  online transcript/speaker edit sync, video capture package foundation, and
  explicit replace/reprocess flows remain outside `042` MVP.

## Deferred Work Register

Use this register as the anti-drift memory for work intentionally left out of
the current accepted implementation or `012` ingest slice.

- Target-specific meeting-app mute adapters: future work only after separate
  privacy, platform, and QA evidence. Accepted feature `022` covers
  product-owned Pause/Resume truth and keeps unsupported meeting targets
  fail-closed; it does not claim third-party Zoom/Telemost mute interception.
- `011-assisted-auto-recording`: plan and implement detect-and-ask, automatic
  naming, and any future auto-start behavior from the accepted requirements.
- Public-link and external-recipient sharing policy: add optional public links,
  expiration, external invitations, abuse controls, and admin/legal copy after
  the login-required 017 flow is accepted.
- `021-production-deployment-plan`: use the remote-first runbook to reach
  `infra_smoke_ready` for the Rec stack, while keeping user rollout and pilot
  claims blocked until later product slices are accepted.
- `020-hardware-route-matrix`: complete physical-device route matrix rows that
  require unavailable hardware before claiming broad hardware speakerphone
  acceptance. Current automated acceptance covers persisted-package
  finalization behavior, not every physical device route.
- `037-microphone-sample-graph-foundation`: introduce an app-owned microphone
  sample graph before any live cleanup claim, while preserving the current
  `mic.wav`/`incoming.wav`/`manifest.json` package truth.
- `038-apple-voice-processing-spike`: evaluate Apple `AVAudioEngine` voice
  processing, `VoiceProcessingIO`, and Mic Mode/Voice Isolation as bounded
  spike candidates for reducing built-in speaker-to-mic leakage.
- `039-webrtc-aec3-speakerphone-spike`: evaluate WebRTC AEC3 with system audio
  as the render/far-end reference and microphone frames as capture input only
  after the app-owned microphone graph is available.
- `040-speakerphone-recording-fallback-decision`: decide headset-first,
  derived-cleaned, mixed-audio, pilot-only, or unsupported-route semantics if
  clean built-in speakerphone dual-track capture cannot be proven.
- `041-recording-permission-readiness-onboarding`: make microphone and
  Screen/System Audio readiness visible before the user starts recording.
- `031-rls-hardening` / `032-rls-live-enforcement`: future tenant-owned tables
  and product surfaces must follow ADR `003-tenant-isolation-rls`; destructive
  RLS probes stay on disposable/test databases, and production truth must be
  proven with read-only catalog metadata.
- `044-speakerphone-echo-noise-suppression`: clean-recording runtime slice for
  real echo cancellation/noise suppression. It must preserve package truth,
  metadata-only evidence, reversible fallback, and built-in speakerphone route
  limits before any clean speakerphone claim is allowed. It is separate from
  `045`, which lets imperfect-but-structurally-valid packages reach
  transcription/results without claiming the mic was cleaned.
- Post-MVP editing/media backlog still needs separate numbering after `048`:
  local media trim revisions, online transcript edit sync, video capture
  package foundation, and explicit media replace/reprocess flows are not part
  of `042`/`048` MVP, but current data/identity choices must avoid duplicate
  meetings later.
- `direct-object-upload`: future upload optimization only after a separate
  security and lifecycle review; `012` remains `server_mediated`.
- Browser/packaging evidence still pending: Yandex Browser smoke, long-duration
  30/60 minute integrity, and signed/notarized installer evidence.
- `mediascribe-large-audio-proxy-ceiling`: do not raise MediaScribe just
  because Rec accepts larger upload packages or future video files. MediaScribe
  receives only audio. Raise its separate OpenResty/nginx body limit only if
  real combined `mic_file` + `incoming_file` audio approaches the observed
  public proxy ceiling and starts failing with `413`.
