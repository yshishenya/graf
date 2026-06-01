# Coreaudiod Release-Hardening Recovery

## Purpose

Record metadata-only evidence that 2brain Rec does not leave stale ready UI or a
stale active route after `coreaudiod` restarts.

## Preconditions

- Local package is installed.
- `2brain Rec` is open.
- Virtual devices are visible and default-safe.
- No recording, transcription, upload, MediaScribe, Langfuse, or server workflow
  is active.

## Steps

- [ ] Record initial route state and runtime probe output.
- [ ] Restart `coreaudiod`.
- [ ] Record whether virtual devices disappear, reappear, or stay visible.
- [ ] Record whether app route state becomes stale/degraded/blocked within 5
  seconds or becomes ready only after fresh evidence.
- [ ] Run `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe`.
- [ ] Record result as `passed`, `blocked`, or `not_accepted`.

## Evidence Rules

- Do not attach raw audio, transcript text, credentials, tokens, signed URLs, or
  meeting content.
- If a browser keeps stale selected device IDs after restart, record it as
  blocked/not accepted until the user reselects devices or the app detects a
  safe recovery path.
