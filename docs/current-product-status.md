# Current Product Status

Date: 2026-06-01

This document is the short status source after merging
`006-low-resource-audio` into `master`. The PRD remains the product baseline;
feature specs remain the detailed implementation record.

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

## Not Accepted Yet

- Manual user-facing recording session start/stop is not production accepted.
- Persistent capture indicator and one-action stop for active recording still
  need the next Spec Kit feature slice.
- Separate recorded local/remote track artifacts and long-duration 30/60 minute
  integrity acceptance are not complete.
- Upload, resumable ingest, MediaScribe transcription, dashboard notes, server
  retention, and deletion workflows are not implemented in the macOS client
  slice.
- Yandex Browser is intentionally skipped/not accepted in the current browser
  smoke cycle.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.

## Next Product Slice

Recommended next feature: `007-capture-session-indicator`.

Goal: turn the accepted non-recording audio route into a safe product recording
surface with manual start/stop, persistent visible local indication,
one-action stop, recording state transitions, and basic audit evidence. This
must preserve the constitutional rule that active capture can never be silent or
invisible.
