# Current Product Status

Date: 2026-06-16

This document is the short status source after the `034-mvp-loop-readiness`
readiness pass and the `022-meeting-mute-truth` closeout. The PRD remains the
product baseline; feature specs and metadata-only evidence artifacts remain the
detailed implementation record.

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
  misaligned, not-measured, or unproven packages fail closed for transcription
  readiness. The implementation is integrated on top of the accepted `025`
  system-audio capture path and does not replace scope approvals, permissions,
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
  `020` evidence: packages can be captured, but transcription readiness must
  stay blocked when persisted package evidence is contaminated, unproven, or
  unavailable. Live Apple/WebRTC/AEC cleanup remains a future gated slice.
- Driver live virtual-device publication is not accepted for MVP recording and
  must not be revived without a separate future advanced-routing spec,
  implementation, and safety evidence.
- Public meeting links, external-recipient invitations, partial deletion,
  legal-hold management, admin retention editing UI, billing, and desktop-owned
  deletion policy remain later slices.
- The `012` backend foundation exists as a repository implementation with
  `021` remote-first infrastructure smoke readiness scaffolding; real user
  rollout and desktop uploader slices are still not accepted.
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

Recommended next feature: `036-owner-review-live-polish`.
Feature `035-mvp-loop-live-evidence` closes the stale installed-desktop proof
gap: the permissioned `/Applications/2brain Rec.app` can run the visible local
recording loop and produce a validated metadata-only local artifact. The
remaining launch blockers are now more specific:

- production owner review on `rec.2brain.pro` is not yet proven because the
  protected `/meetings` route returned `401 missing_auth_context` without a
  commit-safe authenticated owner session;
- list/detail/governance UI is fixture-backed, not live-owner proven;
- notes/action output is still a truthful placeholder, not a launchable
  generated-output capability;
- production evidence remains `infra_smoke_ready`, not a user rollout journey;
- the installed desktop surface is operational and safe, but still needs the
  accepted clean-room V8 product polish before a broad launch claim.

Before any pilot claim, implement or validate the owner auth/session path for
`rec.2brain.pro`, capture metadata-safe live owner review evidence, decide
whether notes/actions are implemented or explicitly deferred for MVP, and carry
the desktop/web product surface toward the accepted V8 baseline.

A remote `021` infrastructure smoke on `2brain.dev` can continue only within
the `infra_smoke_ready` boundary until user rollout slices and live journey
evidence are separately accepted.

Keep separate unless the next spec explicitly changes scope:

- Public-link and external-recipient sharing policy: optional public links,
  expiration, abuse controls, external invitations, and legal/admin copy.
- Notes/action output: decide whether the MVP requires generated notes/action
  items next or whether a truthful planned placeholder remains acceptable for an
  internal pilot.
- Assisted auto-start and generalized meeting detection.
- Live speakerphone cleanup/AEC: Apple voice processing, WebRTC AEC3, custom
  AEC, and mixed-audio fallback remain decision records or future spike gates
  after `020`. They are not runtime behavior in the finalization-only slice.
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
- `031-rls-hardening` / `032-rls-live-enforcement`: future tenant-owned tables
  and product surfaces must follow ADR `003-tenant-isolation-rls`; destructive
  RLS probes stay on disposable/test databases, and production truth must be
  proven with read-only catalog metadata.
- Post-MVP editing/media backlog: features `044`-`047` are reserved for local
  media trim revisions, online transcript edit sync, video capture package
  foundation, and explicit media replace/reprocess flows. They are not part of
  `042` MVP, but `042` must avoid data/identity choices that would force
  duplicate meetings later.
- `direct-object-upload`: future upload optimization only after a separate
  security and lifecycle review; `012` remains `server_mediated`.
- Browser/packaging evidence still pending: Yandex Browser smoke, long-duration
  30/60 minute integrity, and signed/notarized installer evidence.
