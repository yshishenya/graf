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
- ADR `001-local-trust-shell-and-server-dashboard` is accepted. Capture-critical
  desktop trust surfaces stay local/native; server/web surfaces own
  post-meeting, transcript, notes, admin, retention, deletion, audit, and fleet
  workflows.

## Not Accepted Yet

- Yandex Browser is intentionally skipped/not accepted in the current
  browser/meeting smoke cycle.
- Bluetooth and AirPods-class live route stability is product backlog for a
  dedicated future slice. It must cover long-duration route stability,
  autorepair, profile switching, reconnect behavior, latency, route
  preservation, recording timeline integrity, and metadata-only evidence before
  wireless headset routes can be treated as release-ready.
- Meeting-app mute truth must be resolved in a future slice before local
  recording can be accepted as privacy-correct when a user mutes inside
  Zoom/browser targets.
- Long-duration 30/75 minute integrity acceptance is not complete. Feature
  `019-live-route-stability` now implements the local metadata, policy,
  autorepair, route-release prevention, recording timeline, and validation
  evidence foundations for this gap. Manual 30-minute and 75-minute release
  evidence still must be collected before long-duration acceptance can be
  claimed.
- Upload, resumable ingest, MediaScribe transcription, dashboard notes, server
  retention, and deletion workflows are not implemented in the macOS client
  slice.
- No backend scaffold, Docker Compose deployment, Postgres schema, MinIO bucket
  wiring, Temporal workflow, upload API, or web dashboard implementation exists
  in this repository yet.
- Feature `011-assisted-auto-recording` remains requirements-only. Detect-only,
  detect-and-ask, automatic naming, and future auto-record behavior have not
  been implemented or accepted.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.

## Next Product Slice

Recommended next feature: `012-server-ingest-foundation`.

Goal: move from accepted local saved artifacts to an owner-controlled server
ingest foundation without weakening local recording visibility, stop control,
metadata-only diagnostics, explicit egress policy, storage truth, or deletion
accounting.

Recommended scope:

- Self-hosted backend skeleton for `rec.2brain.dev` and local development.
- Minimal auth/device registration sufficient for a trusted desktop uploader.
- Meeting and upload-session APIs for finalized local dual-track artifacts.
- Resumable/idempotent ingest with checksums, missing-range recovery, and
  truthful finalized/degraded/failed states.
- Postgres metadata and MinIO object storage foundations.
- Server-side MediaScribe credential boundary, but no required MediaScribe job
  submission in the first ingest foundation unless the new spec explicitly
  expands scope.
- Desktop-visible upload/session state contract for a later local upload queue
  UI slice.

Keep separate unless the next spec explicitly changes scope:

- MediaScribe submit/poll/result import.
- Full web dashboard meeting detail/transcript/notes UI.
- Server retention/deletion execution.
- Assisted auto-start and generalized meeting detection.
- Feature `009` meeting-app mute truth.
