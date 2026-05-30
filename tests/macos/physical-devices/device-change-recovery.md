# Device Change Recovery Scenarios (US3)

## Purpose

Validate recovery from physical device disconnect, Bluetooth profile changes, and replacement devices.

## Scenarios

1. Start with a selected physical microphone and start route verification.
   - Capture readiness state is `ready`.
2. Disconnect selected microphone mid-run.
   - Verify Audio Health switches to degraded/error quickly.
   - Verify capture does not continue silently.
3. Reconnect original microphone or select an alternative supported device.
   - Verify the app can re-run route verification and return to readiness state.

4. Simulate Bluetooth profile change (A2DP/Handsfree where supported).
   - Verify output path becomes muted/noisy/degraded with explicit recovery copy.
   - Verify remote call can continue via host fallback or stop with user-facing warning.

5. Switch selected output while capture is active.
   - Verify route graph and passthrough state reflect actual selection.
   - Verify active-capture stop remains available.

## Expected Outcome

- All changes map to distinct recovery families: device disconnect, profile switch, unsupported profile.
- No automatic silent retry without explicit user action.
