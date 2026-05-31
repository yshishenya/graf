# coreaudiod Passthrough Recovery

## Scope

Validate that live passthrough degrades safely when `coreaudiod` restarts and
recovers only after both virtual devices and app-side bridge paths are rechecked.

## Preconditions

- `2brain Rec Microphone` and `2brain Rec Speaker` are visible in macOS.
- A physical input and physical output are selected in 2brain Rec.
- Live passthrough is active and recording remains off.
- The visible local state distinguishes passthrough from recording.

## Steps

- [ ] Start live passthrough with built-in or wired devices.
- [ ] Confirm local speech and remote audio are usable before restart.
- [ ] Restart `coreaudiod`.
- [ ] Confirm 2brain Rec marks passthrough stale/degraded, not ready.
- [ ] Confirm the driver remains fail-closed until the bridge reconnects.
- [ ] Run the runtime device probe after restart.
- [ ] Re-run mic, speaker, latency, leakage, and no-loopback checks.
- [ ] Confirm ready/active state returns only after all required checks pass.
- [ ] Confirm diagnostics record metadata-only recovery events.

## Pass Criteria

- No silent ready state is shown during or immediately after restart.
- No recording, upload, transcript generation, or MediaScribe call starts.
- The app records `coreaudiod_restarted` or equivalent recovery metadata.
- Recovery requires fresh live passthrough evidence, not old cached evidence.

## Evidence

```text
Status: pending physical recovery validation
Synthetic companion: live-passthrough-fail-closed-check
```
