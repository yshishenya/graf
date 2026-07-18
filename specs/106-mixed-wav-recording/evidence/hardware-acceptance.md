# Installed-App Hardware Acceptance

**Status**: open — no result is invented.

## Preconditions still required

- The exact `v2026.07.17.6` baseline tag and commit SHA are verified as
  `4be444e82ec449a3bb5312920fb0cd6008072c56`.
- The local install and controlled hardware procedure require separate approval.
- The user-confirmed, still-in-progress parallel `v2026.07.16.7` work must
  not be used as the baseline or merged into this feature.

## Candidate build provenance

- A local-only `2026.07.17.10` candidate was built from
  `d9d4d6f7970bb21f20cc2d2a66bde1f850d2e9da` with the stable owner signing
  identity. Its strict owner-only update validator passed against the
  separately installed `2026.07.17.9` app with designated-requirement
  continuity and the same configured public update contract.
- The local package intentionally has no Developer ID package signature and is
  not notarized. It was used only from an isolated staging path; the parallel
  installed app was left untouched and no release action was performed.

## Required future metadata-only verdicts

- 60-minute v5 timeline, route and incoming-level check;
- exact package member/format/hash-count/duration checks;
- user-visible intermediate progress, one-job processing, playback and
  transcript status;
- deletion and rollback of one subsequent controlled recording.

Do not add audio, decoded media, marker text, transcript text, device name,
private path, credential, signed URL or provider payload to this file.

## 2026-07-18 — installed candidate capture receipt

- Candidate build: `2026.07.18.1`, source `7d9bae03`; local installer package
  SHA-256 was recorded as `03d8d89157340a4a75a666dc32d39051117304152b88a68213e99394872a2fac`.
  The candidate was staged outside `/Applications`; no installed production
  app was replaced.
- A real candidate desktop process recorded for 60:16.979 and was finalized
  through the app termination-cleanup path after the screen locked. The saved
  v5 manifest reports `status=saved`, `failureReason=none`, exactly two
  artifacts, and no unexplained duration difference.
- The package members and metadata-only format check passed: one
  `meeting-transcription.wav` (`pcm_s16le`, mono, 16 kHz, 3,616.979875 s) and
  one `meeting-review.m4a` (AAC-LC, mono, 48 kHz, 3,617.024000 s). The manifest
  reports both tracks `timelineAligned=true`, `timelineStartMs=0`, and equal
  logical duration `3,616,979 ms`; the AAC presentation-frame delta is zero.
  The source track is the only ASR field and the playback track is separate.
- The stable output-volume observation remained `56` with `muted=false` before
  and throughout the run. The microphone health gate passed with frames
  observed and `silenceStatus=audible`; permission state was granted for both
  microphone and system audio at start.
- The independent ScreenCaptureKit probe delivered callbacks but measured
  zero RMS for the synthetic speaker marker in this locked/headless audio
  environment, and the incoming meter stayed quiet. Therefore this receipt
  proves duration, package shape, timeline, volume stability and mic capture,
  but does **not** claim audible incoming/system-signal acceptance. T063 stays
  open until the same run is repeated with an observable non-zero incoming
  signal after the Mac is unlocked.
