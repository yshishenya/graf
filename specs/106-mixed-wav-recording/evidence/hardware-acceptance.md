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

## 2026-07-18 — exact baseline rollback attempt

- The exact baseline package for `v2026.07.17.6` was built from peeled commit
  `4be444e82ec449a3bb5312920fb0cd6008072c56`; its package hash and strict
  designated-requirement signature check passed. The staged app was never
  copied over `/Applications`.
- The baseline was launched through the visible desktop shell with manual
  Start in a temporary `CFFIXED_USER_HOME` and with upload/cabinet traffic
  constrained to loopback. No baseline WAV, M4A or manifest was created. A
  second user-context launch reached the same manual Start surface and failed
  closed with `system_audio.runtime_start_failed` (`timeoutMs=30000`). The
  isolated launch timed out at the baseline runtime bound (`timeoutMs=120000`).
- Candidate v5 integrity was unchanged across the attempt: manifest SHA-256
  `c76acc2267d1b4db4ac3acaa9d46d6ef6d7f4489c1b72d327d67cca0505da4d2`, WAV
  SHA-256 `381450f9fb26bca6a298f19c83ab89b1eec0f783857f20a961fea7e80015a3fd`,
  and M4A SHA-256
  `67193de638b497de1e62a0c86f1365d5cbb88535088b1eaf41013d0dbc791a41` both
  before and after. No candidate resubmit or rewrite occurred.
- This is a rollback **fail/open**, not a pass: the exact baseline could not
  produce a subsequent recording because the OS capture runtime timed out.
  T063 and T064 remain open; no installer, updater, TCC or deployment rollback
  claim is made.
