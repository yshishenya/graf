# Contract: Passthrough Diagnostics

## Allowed Fields

- Current live passthrough status.
- Microphone path status and failure category.
- Speaker path status and failure category.
- Selected physical device names and stable identifiers.
- Virtual device publication status.
- App heartbeat status.
- Latency measurement.
- Leakage measurement.
- Browser target evidence status.
- Route invalidation and recovery action.
- Installer/runtime probe result.

## Forbidden Fields

- Raw audio.
- Audio snippets or waveform payloads.
- Transcript text.
- Meeting content.
- Credentials.
- Tokens.
- Signed URLs.
- Live credential paths.
- MediaScribe request payloads.
- Langfuse content-bearing traces.

## Export Rule

Diagnostic export must run through the shared redactor and fail closed when a
forbidden field is detected.

## Evidence Rule

Synthetic fixtures may name forbidden fields to test the redactor, but generated
diagnostics must omit those fields and must not contain real secrets or meeting
content.
