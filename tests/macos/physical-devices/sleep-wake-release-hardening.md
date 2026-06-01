# Sleep/Wake Release-Hardening Check

## Purpose

Record metadata-only evidence for installed driver publication, app readiness,
and truthful stale/recheck behavior across macOS sleep/wake.

## Steps

- [ ] Record pre-sleep runtime probe output.
- [ ] Put the Mac to sleep.
- [ ] Wake the Mac.
- [ ] Record whether macOS Sound settings and selected browser/meeting settings
  open without hanging.
- [ ] Record whether the route is ready only after valid evidence, or otherwise
  stale/degraded/repair.
- [ ] Record result as `passed`, `blocked`, or `not_accepted`.

## Evidence Rules

- No meeting content, raw audio, transcripts, credentials, tokens, signed URLs,
  or screenshots with sensitive meeting content.
- If the test is skipped, record `not_accepted` and the reason.
