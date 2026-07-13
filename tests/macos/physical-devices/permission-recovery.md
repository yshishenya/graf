# Current Capture Permission Recovery

## Purpose

Validate fail-closed recovery for the two permissions required by the supported
recording graph.

## Scenarios

1. Request recording with microphone permission denied.
   - Start is blocked with microphone-specific guidance.
2. Request recording with Screen & System Audio permission denied.
   - Start is blocked with system-audio-specific guidance.
3. Grant the missing permission in System Settings and return to GRAF.
   - Permission truth refreshes without starting recording automatically.
4. Start recording manually after both permissions are granted.
   - Active capture is visible and one-action Stop is available.
5. Revoke a required permission before a later recording.
   - The later start fails closed and does not claim a complete package.

## Expected Outcome

- Permission failures are not conflated with storage, device, or source-scope
  failures.
- Permission recovery never auto-starts recording.
- Evidence remains metadata-only and contains no private meeting content.
