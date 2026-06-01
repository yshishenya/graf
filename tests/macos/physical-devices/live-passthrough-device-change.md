# Live Passthrough Device Change

## Scope

Validate that changing a physical microphone or speaker during live passthrough
invalidates the active route and requires a fresh readiness check.

## Preconditions

- Live passthrough is active with built-in or wired devices.
- `2brain Rec Microphone` and `2brain Rec Speaker` are selected in a browser call
  or local route probe.
- Recording, upload, transcript generation, and assisted auto-start are off.

## Steps

- [ ] Start live passthrough with a known-good physical input and output.
- [ ] Disconnect or switch the physical microphone.
- [ ] Confirm microphone passthrough becomes stale/degraded.
- [ ] Confirm the virtual microphone does not self-route or leak speaker audio.
- [ ] Restore or select a valid physical microphone.
- [ ] Re-run microphone readiness and no-loopback checks.
- [ ] Disconnect or switch the physical output.
- [ ] Confirm speaker passthrough becomes stale/degraded.
- [ ] Restore or select a valid physical output.
- [ ] Re-run speaker readiness, latency, and leakage checks.

## Pass Criteria

- Any route change invalidates the current live passthrough evidence.
- Ready/active state returns only after fresh evidence for both paths.
- Diagnostics include metadata-only route change and recovery events.
- Browser targets are not marked passed until tested after the final route state.

## Evidence

```text
Status: pending physical device-change validation
Synthetic companion: live-passthrough-fail-closed-check
```
