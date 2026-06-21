# Manual Runtime Matrix: Microphone Sample Graph Foundation

Use this matrix for metadata-only manual evidence. Do not paste raw audio,
transcripts, private meeting content, live local paths, credentials, tokens, or
screenshots with private data.

| Scenario | Expected Result | Evidence To Record | Status | Notes |
|----------|-----------------|--------------------|--------|-------|
| No explicit recording microphone selected | Recording uses current macOS default input and stores default fallback truth. | Redacted package id, manifest selection mode, frame/stop truth. | Pending | |
| Native recording microphone selected | Recording uses selected input and stores selected input truth. | Redacted package id, selected input display metadata, frame/stop truth. | Pending | |
| Selected microphone unavailable before Record | Start is blocked or fails closed with `device_unavailable`. | Reason code, recovery action, no clean success claim. | Pending | |
| 2brain virtual microphone selected | Selection is rejected before capture. | Rejection reason, recovery action, no recording started. | Pending | |
| Microphone permission denied | Start is blocked with permission recovery copy. | Permission state, blocker reason, no partial accepted package. | Pending | |
| Microphone frames stop or stay silent | Package records `no_frames`, `silent_input`, degraded, failed, or unproven truth. | Stream health status and manifest failure reason. | Pending | |
| Speakerphone leakage present | Leakage finalization remains authoritative and does not mark clean without evidence. | Leakage status and transcription gate. | Pending | |
| Stop while recording | Mic stream stops, package finalizes, indicator clears, no invisible capture remains. | Stop time, active state cleared, CPU/resource note. | Pending | |
| App quit while recording | Capture resources release and final truth is bounded, not clean by default. | Quit/failure reason, active state cleared, package/failure status. | Pending | |

## Reviewer Notes

- Mark `Status` as `Pass`, `Fail`, or `Blocked`.
- Keep all notes content-safe and redacted.
- Link to GitHub issues only by issue number or URL.
