# Diagnostic Redaction Family Coverage (US3)

## Purpose

Verify every diagnostic-family sample is generated with redaction status and without forbidden content.

## Scenarios

1. Install failure sample:
   - Build one diagnostic from install-preflight/repair/precondition failures.
   - Verify forbidden fields are absent.
2. Route failure sample:
   - Build diagnostic with missing route and recovery family metadata.
3. Permission failure sample:
   - Ensure credential fields are absent and permission status is explicit.
4. Permission/device failure sample:
   - Mix route and permission failure markers and ensure `blocked_sensitive_content` is set only on detection.
5. Network/server outage sample:
   - Keep raw audio/transcript fields out of diagnostic manifest.

## Expected Outcome

- `redactionState` is always present.
- No `rawAudio`, `audioSnippet`, `transcriptText`, credentials, tokens, or signed URLs in generated sample.
