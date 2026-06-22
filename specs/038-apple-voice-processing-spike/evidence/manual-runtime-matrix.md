# Manual Runtime Matrix: Apple Voice Processing Spike

Use this matrix for metadata-only manual evidence. Do not paste raw audio,
transcripts, private meeting content, live local paths, credentials, tokens,
signed URLs, participant identifiers, or screenshots with private data.

| Scenario | Required Result | Evidence To Record | Status | Issue | Notes |
|----------|-----------------|--------------------|--------|-------|-------|
| Built-in mic plus built-in speakers, far-end only | Baseline and candidate leakage summaries are recorded; no clean claim unless leakage gate passes. | Route class, baseline/candidate leakage status, residual leakage summary, redacted package id. | Blocked | #1388 | No accepted live Apple processing route was proven in 038; outcome is `defer_to_webrtc_aec3`. |
| Built-in mic plus built-in speakers, near-end only | Local speech remains present; candidate is blocked if speech is over-suppressed. | Local speech preservation status, candidate state, failure reason if blocked. | Blocked | #1388 | Speech preservation remains unproven for Apple processing. |
| Built-in mic plus built-in speakers, double-talk | Local speech preservation and residual far-end leakage are both classified. | Double-talk classification, candidate quality status, no clean claim unless all gates pass. | Blocked | #1388 | Double-talk acceptance remains unproven for Apple processing. |
| Loud speaker or clipping | Candidate fails closed if clipping invalidates evidence. | Clipping state, blocked/degraded reason, no accepted route without valid evidence. | Blocked | #1388 | No Apple candidate was promoted; clipping rows cannot be accepted. |
| Route change before recording | Candidate records stable, blocked, degraded, or unproven route truth before start. | Before-route class, after-route class, candidate state, reason code. | Blocked | #1388 | Fail-closed route-change reason codes are implemented; live Apple route is not accepted. |
| Route change during recording | Stop/finalize remains bounded and candidate truth is not silently accepted. | Route-change time bucket, capture state, final candidate state, package truth. | Blocked | #1388 | Candidate truth remains metadata-only and cannot override package truth. |
| Built-in mic plus wired headphones | Headset/clean route remains separate from speakerphone acceptance. | Route class, leakage status, candidate dependency state. | Blocked | #1388 | Headset route acceptance is not part of the 038 outcome. |
| USB headset | Headset-class behavior is classified without false Apple dependency. | Route class, candidate availability, package lineage status. | Blocked | #1388 | USB headset acceptance is not part of the 038 outcome. |
| Browser meeting target | Evidence is not synthetic-only and maps to a real meeting target class. | Browser/app class, baseline/candidate rows, no content-bearing meeting data. | Blocked | #1388 | No accepted browser meeting Apple runtime route was proven. |
| Stop while candidate processing is active | Active indicator clears; capture stops; no hidden processing remains. | Stop result, active state cleared, resource release status. | Pass | #1388 | Automated lifecycle and capture-safety tests prove release on Stop without hidden capture. |
| App quit while candidate processing is active | Capture resources release and final truth is bounded, not clean by default. | Quit/failure reason, active state cleared, package/failure status. | Pass | #1388 | Automated lifecycle tests prove app-quit release state. |
| Diagnostics export | Diagnostics include only redacted metadata and no raw content or secrets. | Redaction result, forbidden-field scan result, diagnostic bundle state. | Pass | #1388 | 038 helper passed diagnostic bundle/redaction coverage. |

## Reviewer Notes

- Mark `Status` as `Pass`, `Fail`, or `Blocked`.
- Keep all notes content-safe and redacted.
- Link to GitHub issues only by issue number or URL.
- Bluetooth or AirPods-class evidence can be added when hardware is available,
  but it is not required for the first built-in speakerphone decision.
