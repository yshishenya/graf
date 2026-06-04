# Current Product Status

Date: 2026-06-04

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
- The meeting-app mute issue discovered during validation is parked on
  `009-respect-meeting-mute` for a future slice and is not part of the current
  mainline sequence.
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
- Feature `021-production-deployment-plan` is implemented as a remote-first
  infrastructure readiness slice for `2brain.dev` and `/opt/projects/2brain-rec`.
  It adds production Compose hardening, env/secret templates, remote backup,
  migration, restore rehearsal, rollback/halt helpers, internal smoke identity,
  first-smoke evidence templates, cleanup accounting, and forbidden-content
  scans. The highest allowed successful status is `infra_smoke_ready`; this is
  not production readiness, user rollout readiness, or internal pilot readiness.
- ADR `001-local-trust-shell-and-server-dashboard` is accepted. Capture-critical
  desktop trust surfaces stay local/native; server/web surfaces own
  post-meeting, transcript, notes, admin, retention, deletion, audit, and fleet
  workflows.

## Not Accepted Yet

- Yandex Browser is intentionally skipped/not accepted in the current
  browser/meeting smoke cycle.
- Meeting-app mute truth must be resolved in a future slice before local
  recording can be accepted as privacy-correct when a user mutes inside
  Zoom/browser targets.
- Long-duration 30/60 minute integrity acceptance is not complete.
- Desktop upload queue wiring, MediaScribe transcription, dashboard notes,
  Temporal workflow starts, server retention, and deletion workflows are not
  accepted yet.
- The `012` backend foundation exists as a repository implementation with
  `021` remote-first infrastructure smoke readiness scaffolding; real user
  rollout and desktop uploader slices are still not accepted.
- Feature `011-assisted-auto-recording` remains requirements-only. Detect-only,
  detect-and-ask, automatic naming, and future auto-record behavior have not
  been implemented or accepted.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.

## Next Product Slice

Recommended next feature: `013-federated-auth-foundation` or
`014-desktop-upload-queue`, depending on whether identity/session work or
desktop upload UX should be unblocked first. The `021` deployment slice can be
used as the infrastructure runbook baseline while those product slices remain
separate.

Goal: connect the accepted local artifact and implemented server ingest
foundation to real user/device identity and the macOS upload queue without
weakening local recording visibility, stop control, metadata-only diagnostics,
explicit egress policy, storage truth, or deletion accounting.

Recommended scope:

- Provider-neutral user/workspace/session/device identity sufficient for a
  trusted desktop uploader.
- macOS upload queue that picks up local `010` artifacts, calls the `012`
  ingest API, shows pending/uploading/retrying/uploaded/degraded/failed truth,
  and preserves local files until server status is known.
- A remote `021` infrastructure smoke on `2brain.dev` only after DNS/TLS,
  secrets, backup, migration, restore rehearsal, and cleanup evidence pass.

Keep separate unless the next spec explicitly changes scope:

- `013-federated-auth-foundation`: provider-neutral user authentication and
  account/device identity, with priority login providers for the Russian market
  such as Yandex ID, VK ID, and Telegram Login, plus later Sber ID and T-ID
  where partner setup allows.
- `014-desktop-upload-queue`: macOS app sends local recordings to the server,
  shows upload status, retries failures, and preserves local artifacts until
  upload truth is known.
- `015-mediascribe-processing-pipeline`: server-side MediaScribe
  submit/poll/result import from finalized ingested artifacts. This slice owns
  starting the durable processing workflow after ingest finalization, using
  internal meeting/upload/artifact identifiers and idempotent workflow IDs.
- `016-meeting-dashboard-review`: web dashboard meeting list/detail,
  processing state, transcript, notes, playback, and review surfaces.
- `017-access-sharing-downloads`: role-based meeting access, team visibility,
  download/export permissions, login-required share links, optional public-link
  policy, and share-page lifecycle/audit.
- `018-retention-deletion-execution`: server-side retention jobs, deletion
  workflows, deletion verification reports, local desktop purge coordination,
  backup expiry accounting, and external dependency deletion truth.
- Assisted auto-start and generalized meeting detection.
- Feature `009` meeting-app mute truth.

## Deferred Work Register

Use this register as the anti-drift memory for work intentionally left out of
the current accepted implementation or `012` ingest slice.

- `009-respect-meeting-mute`: resolve meeting-app mute truth before broader
  local recording acceptance.
- `011-assisted-auto-recording`: plan and implement detect-and-ask, automatic
  naming, and any future auto-start behavior from the accepted requirements.
- `013-federated-auth-foundation`: implement provider-neutral auth, account
  linking, sessions, workspace membership, and registered device identity.
- `014-desktop-upload-queue`: make the macOS app send local artifacts to the
  server, show upload status, retry safely, and preserve local artifacts until
  upload truth is known.
- `015-mediascribe-processing-pipeline`: start the durable processing workflow
  after ingest, submit/poll/import MediaScribe results, and keep credentials
  server-side.
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
- `RLS-hardening`: if PostgreSQL Row-Level Security is deferred by `012` plan,
  create a traceable task or GitHub issue candidate with compensating
  application-level authorization checks.
- `direct-object-upload`: future upload optimization only after a separate
  security and lifecycle review; `012` remains `server_mediated`.
- Browser/packaging evidence still pending: Yandex Browser smoke, long-duration
  30/60 minute integrity, and signed/notarized installer evidence.
