# Current Product Status

Date: 2026-06-15

This document is the short status source after accepting the local recording
artifact-format slice and drafting the next architecture/product decisions. The
PRD remains the product baseline; feature specs remain the detailed
implementation record.

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
- The meeting-app mute issue discovered during validation is preserved as
  `022-meeting-mute-truth`, a backlog privacy slice that supersedes the old
  `009-respect-meeting-mute` draft branch. It is not part of the current
  mainline sequence and authorizes no implementation until clarification and
  planning resolve canonical mute truth, unsupported-target behavior, muted
  interval artifact truth, user-facing limitation copy, and the QA target
  matrix.
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
- Feature `021-production-deployment-plan` is implemented as a remote-first
  infrastructure readiness slice for `2brain.dev` and `/opt/projects/2brain-rec`.
  It adds production Compose hardening, env/secret templates, remote backup,
  migration, restore rehearsal, rollback/halt helpers, internal smoke identity,
  first-smoke evidence templates, cleanup accounting, and forbidden-content
  scans. The highest allowed successful status is `infra_smoke_ready`; this is
  not production readiness, user rollout readiness, or internal pilot readiness.
- Feature `031-rls-hardening` is implemented locally as a backend tenant
  isolation hardening slice. It adds PostgreSQL RLS policies for accepted
  tenant-owned identity, auth/session/device, ingest, meeting, processing,
  transcript, audit, and dependency tables; explicit request, worker,
  auth-bootstrap, session-lookup, callback-lookup, and allowlisted maintenance
  DB contexts; rollout/rollback validation helpers; and ADR `003` for future
  tenant-owned tables. It does not add dashboard, share/download, retention,
  deletion execution, billing, admin UI, desktop capture/upload, or new
  MediaScribe behavior. Live production enforcement is not enabled by this
  slice and still requires a separate explicit operator decision after gates
  pass.
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
- Feature `022-meeting-mute-truth` must resolve meeting-app mute truth before
  local recording can be accepted as privacy-correct when a user mutes inside
  Zoom/browser targets.
- Built-in speakerphone clean dual-track acceptance remains constrained by
  `020` evidence: packages can be captured, but transcription readiness must
  stay blocked when persisted package evidence is contaminated, unproven, or
  unavailable. Live Apple/WebRTC/AEC cleanup remains a future gated slice.
- Driver live virtual-device publication is not accepted for MVP recording and
  must not be revived without a separate future advanced-routing spec,
  implementation, and safety evidence.
- Dashboard notes/review, share/download surfaces, server retention, and
  deletion workflows are not accepted yet.
- The `012` backend foundation exists as a repository implementation with
  `021` remote-first infrastructure smoke readiness scaffolding; real user
  rollout and desktop uploader slices are still not accepted.
- Live production enforcement of `031-rls-hardening` RLS policies is not
  accepted automatically. The code, migration, validation helper, and runbook
  are present, but production enforcement remains blocked until a separate
  operator decision records fresh metadata-only evidence.
- Feature `011-assisted-auto-recording` remains requirements-only. Detect-only,
  detect-and-ask, automatic naming, and future auto-record behavior have not
  been implemented or accepted.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.

## Next Product Slice

Recommended next feature: `016-meeting-dashboard-review`.
`015` now provides backend processing state and imported transcript/diarization
data, but intentionally exposes no dashboard meeting detail, transcript review,
notes, playback, share, download, or deletion execution surface. `016` should
turn the accepted processing state into a simple authorized review experience
without weakening local recording visibility, one-action stop, metadata-only
diagnostics, explicit egress policy, storage truth, or deletion accounting.

A remote `021` infrastructure smoke on `2brain.dev` can continue only within
the `infra_smoke_ready` boundary until dashboard, access, retention, deletion,
and user rollout slices are separately accepted.

Keep separate unless the next spec explicitly changes scope:

- `014-desktop-upload-queue`: macOS app sends local recordings to the server,
  shows upload status, retries failures, and preserves local artifacts until
  upload truth is known.
- `016-meeting-dashboard-review`: web dashboard meeting list/detail,
  processing state, transcript, notes, playback, and review surfaces.
- `017-access-sharing-downloads`: role-based meeting access, team visibility,
  download/export permissions, login-required share links, optional public-link
  policy, and share-page lifecycle/audit.
- `018-retention-deletion-execution`: server-side retention jobs, deletion
  workflows, deletion verification reports, local desktop purge coordination,
  backup expiry accounting, and external dependency deletion truth.
- Assisted auto-start and generalized meeting detection.
- Feature `022-meeting-mute-truth` meeting-app mute truth.
- Live speakerphone cleanup/AEC: Apple voice processing, WebRTC AEC3, custom
  AEC, and mixed-audio fallback remain decision records or future spike gates
  after `020`. They are not runtime behavior in the finalization-only slice.

## Deferred Work Register

Use this register as the anti-drift memory for work intentionally left out of
the current accepted implementation or `012` ingest slice.

- `022-meeting-mute-truth`: resolve meeting-app mute truth before broader
  local recording acceptance. This supersedes the old
  `009-respect-meeting-mute` draft branch as the canonical backlog record.
- `011-assisted-auto-recording`: plan and implement detect-and-ask, automatic
  naming, and any future auto-start behavior from the accepted requirements.
- `014-desktop-upload-queue`: make the macOS app send local artifacts to the
  server, show upload status, retry safely, and preserve local artifacts until
  upload truth is known.
- `016-meeting-dashboard-review`: show meetings, processing state, transcript,
  notes, playback, and review surfaces.
- `017-access-sharing-downloads`: add RBAC/team visibility, audio/transcript/
  summary downloads, share links/pages, lifecycle, and audit.
- `018-retention-deletion-execution`: implement retention/deletion workflows,
  deletion reports, local purge coordination, backup expiry, and external
  dependency deletion truth.
- `021-production-deployment-plan`: use the remote-first runbook to reach
  `infra_smoke_ready` for the Rec stack, while keeping user rollout and pilot
  claims blocked until later product slices are accepted.
- `020-hardware-route-matrix`: complete physical-device route matrix rows that
  require unavailable hardware before claiming broad hardware speakerphone
  acceptance. Current automated acceptance covers persisted-package
  finalization behavior, not every physical device route.
- `031-rls-hardening`: future tenant-owned tables and product surfaces must
  follow ADR `003-tenant-isolation-rls`; live production enforcement remains a
  separate operator decision after local, PostgreSQL, and production-like gates.
- `direct-object-upload`: future upload optimization only after a separate
  security and lifecycle review; `012` remains `server_mediated`.
- Browser/packaging evidence still pending: Yandex Browser smoke, long-duration
  30/60 minute integrity, and signed/notarized installer evidence.
