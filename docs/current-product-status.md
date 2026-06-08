# Current Product Status

Date: 2026-06-04

This document is the short status source after accepting the local recording
artifact-format slice and drafting the next architecture/product decisions. The
PRD remains the product baseline; feature specs remain the detailed
implementation record.

## Accepted Now

- macOS is the selected MVP platform.
- The MVP architecture has pivoted to system-audio-first capture after
  `019-live-route-stability` revalidation showed the driver-first path can
  trigger CoreAudio CPU runaway and probe hangs.
- ADR `002-system-audio-first-mvp-pivot` is accepted.
- Constitution v2.0.0 allows MVP recording without a virtual audio driver.
- The HAL virtual-driver path is parked as future advanced-routing work and is
  not part of MVP acceptance.
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

- System-audio-first recording implementation is not yet complete. Feature
  `025-system-audio-capture-pivot` defines the new MVP path but still needs
  clarify/plan/tasks/implementation/validation.
- Existing driver-based live route evidence from `019` is superseded and must
  not be counted as MVP acceptance.
- Yandex Browser is intentionally skipped/not accepted in the previous
  browser/meeting smoke cycle.
- Bluetooth and AirPods-class live route stability is product backlog for a
  dedicated future slice. It must cover long-duration route stability,
  autorepair, profile switching, reconnect behavior, latency, route
  preservation, recording timeline integrity, and metadata-only evidence before
  wireless headset routes can be treated as release-ready.
- Meeting-app mute truth must be resolved in a future slice before local
  recording can be accepted as privacy-correct when a user mutes inside
  Zoom/browser targets.
- Long-duration 30/75 minute integrity acceptance is not complete. It must be
  rerun against the system-audio-first capture path after `025` implementation.
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

Recommended next feature: `025-system-audio-capture-pivot`.

Goal: replace the MVP recording path with direct system-audio plus microphone
capture, preserving local recording visibility, one-action stop,
metadata-only diagnostics, dual-track artifacts, and low CPU/system stability.

Recommended scope:

- macOS permission truth for microphone and screen/system audio.
- System-audio capture service for incoming audio.
- Microphone capture service for local audio.
- Dual-track local writer with manifest truth for saved/degraded/blocked
  tracks.
- UI states for permissions, active recording, levels, stop, and degraded
  capture.
- CPU/memory/no-hang validation with the HAL driver absent or ignored.

Keep separate unless the next spec explicitly changes scope:

- Driver/virtual-device routing.
- MediaScribe submit/poll/result import.
- Full web dashboard meeting detail/transcript/notes UI.
- Server retention/deletion execution.
- Assisted auto-start and generalized meeting detection.
- Feature `009` meeting-app mute truth.
