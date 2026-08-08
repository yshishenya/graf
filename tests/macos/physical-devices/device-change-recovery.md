# Current Microphone Device Change Recovery

## Purpose

Validate current app-owned microphone behavior when the selected physical input
changes or disappears without changing system-audio capture ownership.

## Scenarios

1. Select an available built-in, wired, USB, or Bluetooth microphone and start
   a manual recording.
2. Disconnect the selected microphone during capture.
   - The microphone track becomes degraded or failed truthfully.
   - Incoming ScreenCaptureKit audio and the visible Stop control remain owned
     by the active capture session.
3. Stop the recording once and verify the manifest records the microphone
   failure without claiming a complete accepted package.
4. Reconnect the input or choose another supported physical microphone.
5. Start a new manual recording and verify both current sources produce frames.
6. Present an aggregate, multi-output, virtual, unavailable, or unknown input
   and verify selection fails closed before recording.

## Expected Outcome

- No silent source substitution occurs.
- A microphone-source failure cannot hide active capture or remove one-action
  Stop.
- A later recording can recover after explicit supported-device selection.
- Evidence stays metadata-only.
