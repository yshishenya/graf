# Contract: Diagnostics And Evidence Safety

## Purpose

Keep Apple processing spike diagnostics useful without leaking private audio or
meeting content.

## Allowed Diagnostic Fields

- Feature id and candidate id.
- Route class and bounded input/output display class.
- Candidate kind and enabled/unavailable/failed state.
- Frame, duration, route-change, Stop/quit, and failure counters.
- Residual leakage threshold summaries.
- Speech preservation status.
- Timing/alignment status.
- Format/channel/sample-rate summary.
- CPU/latency/no-hang status.
- Safe reason codes and next-step recommendation.

## Forbidden Diagnostic Fields

- Raw audio samples, clips, debug WAVs, spectrograms derived from private
  meetings, or packet dumps.
- Transcript text, speaker labels, inferred content, participant names, or
  meeting titles.
- Credentials, bearer tokens, passwords, signed URLs, provider job ids, object
  storage keys, secret paths, or private local paths.
- Unbounded logs from Apple/CoreAudio APIs that may contain device-owner or
  system-private content.

## Redaction Rules

- Diagnostics must remain useful after redaction; if a field is needed for
  debugging but unsafe to export, replace it with a bounded code or class.
- Committed evidence under `specs/038-apple-voice-processing-spike/evidence/`
  must be metadata-only.
- Runtime-only private captures, if used manually, must not be committed and
  must be excluded from issue comments, PR descriptions, and release notes.
