# Contract: Diagnostics And Evidence Safety

## Purpose

Keep WebRTC AEC3 diagnostics useful without leaking private audio, meeting
content, credentials, or local paths.

## Allowed Diagnostic Fields

- Feature id, candidate id, corpus id, row id.
- Route class and promotion scope.
- Scenario family and validation kind.
- Dependency readiness, license readiness, packaging readiness, signing status.
- Reference status, timing confidence, route-change count, Stop/quit status.
- Residual leakage status and bounded threshold summaries.
- Speech preservation status.
- Candidate status, lineage status, rollback status, and app status state.
- Acceptance-threshold profile id and bounded pass/block threshold summaries.
- Frame, duration, slice, full-file, long-form, room/device/volume counters.
- Safe reason codes and next-step recommendation.

## Forbidden Diagnostic Fields

- Raw audio samples, clips, debug WAVs, spectrograms derived from private
  meetings, or packet dumps.
- Transcript text, speaker labels, inferred meeting content, participant names,
  or meeting titles.
- Credentials, bearer tokens, passwords, signed URLs, provider job ids, object
  storage keys, secret paths, or private local paths.
- Unbounded logs from WebRTC, CoreAudio, AVFoundation, or system APIs that may
  contain device-owner or system-private content.

## Redaction Rules

- Diagnostics must remain useful after redaction; unsafe detail becomes a
  bounded code or class.
- Committed evidence under `specs/039-webrtc-aec3-speakerphone-spike/evidence/`
  must be metadata-only.
- Runtime-only private captures, if used manually, must not be committed and
  must be excluded from issue comments, PR descriptions, release notes, and
  diagnostic bundles.
- A diagnostics row that cannot be made metadata-only is blocked.
