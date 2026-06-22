# Manual Runtime Matrix: Apple Voice Processing Spike

Use this matrix for metadata-only manual evidence. Do not paste raw audio,
transcripts, private meeting content, live local paths, credentials, tokens,
signed URLs, participant identifiers, or screenshots with private data.

| Scenario | Required Result | Evidence To Record | Status | Issue | Notes |
|----------|-----------------|--------------------|--------|-------|-------|
| Built-in mic plus built-in speakers, far-end only | Baseline and candidate leakage summaries are recorded; no clean claim unless leakage gate passes. | Route class, baseline/candidate leakage status, residual leakage summary, redacted package id. | Pending | #1388 | |
| Built-in mic plus built-in speakers, near-end only | Local speech remains present; candidate is blocked if speech is over-suppressed. | Local speech preservation status, candidate state, failure reason if blocked. | Pending | #1388 | |
| Built-in mic plus built-in speakers, double-talk | Local speech preservation and residual far-end leakage are both classified. | Double-talk classification, candidate quality status, no clean claim unless all gates pass. | Pending | #1388 | |
| Loud speaker or clipping | Candidate fails closed if clipping invalidates evidence. | Clipping state, blocked/degraded reason, no accepted route without valid evidence. | Pending | #1388 | |
| Route change before recording | Candidate records stable, blocked, degraded, or unproven route truth before start. | Before-route class, after-route class, candidate state, reason code. | Pending | #1388 | |
| Route change during recording | Stop/finalize remains bounded and candidate truth is not silently accepted. | Route-change time bucket, capture state, final candidate state, package truth. | Pending | #1388 | |
| Built-in mic plus wired headphones | Headset/clean route remains separate from speakerphone acceptance. | Route class, leakage status, candidate dependency state. | Pending | #1388 | |
| USB headset | Headset-class behavior is classified without false Apple dependency. | Route class, candidate availability, package lineage status. | Pending | #1388 | |
| Browser meeting target | Evidence is not synthetic-only and maps to a real meeting target class. | Browser/app class, baseline/candidate rows, no content-bearing meeting data. | Pending | #1388 | |
| Stop while candidate processing is active | Active indicator clears; capture stops; no hidden processing remains. | Stop result, active state cleared, resource release status. | Pending | #1388 | |
| App quit while candidate processing is active | Capture resources release and final truth is bounded, not clean by default. | Quit/failure reason, active state cleared, package/failure status. | Pending | #1388 | |
| Diagnostics export | Diagnostics include only redacted metadata and no raw content or secrets. | Redaction result, forbidden-field scan result, diagnostic bundle state. | Pending | #1388 | |

## Reviewer Notes

- Mark `Status` as `Pass`, `Fail`, or `Blocked`.
- Keep all notes content-safe and redacted.
- Link to GitHub issues only by issue number or URL.
- Bluetooth or AirPods-class evidence can be added when hardware is available,
  but it is not required for the first built-in speakerphone decision.
