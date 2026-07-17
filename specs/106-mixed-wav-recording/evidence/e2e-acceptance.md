# Synthetic End-to-End Acceptance Receipt

**Scope**: deterministic non-private test fixtures and fake provider only. No
real audio, transcript content, external provider action, installation or
production mutation occurred.

## 2026-07-17

- The native writer tests construct a v5 package with exactly one canonical WAV
  ASR source, one review M4A and a manifest from the same timestamped timeline.
- The desktop queue/client tests accept only the v5 role set and report
  byte-weighted intermediate progress across the whole package.
- The server v5 processing test finalizes that package, submits exactly one
  canonical WAV to a fake MediaScribe-compatible client, imports one ordered
  synthetic result with one synthetic speaker boundary, and verifies the
  cabinet exposes a ready transcript/speaker result while keeping playback out
  of ASR.
- The v5 deletion test purges the revision-bound `manifest`, `media` and
  `playback` artifacts and records their terminal lifecycle truth.
- The v3/v4 reader tests remain separate from v5 creation and v5 upload
  descriptors.

This proves the composed local pipeline. It is not a substitute for the
installed-app route/volume/60-minute, real upload and exact-baseline rollback
acceptance gate.
