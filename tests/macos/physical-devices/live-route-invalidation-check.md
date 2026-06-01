# Live Route Invalidation Check

## Purpose

Validate that accepted live route readiness becomes stale when the physical,
browser, Bluetooth, app I/O, or Core Audio environment changes.

## Required Scenarios

- [ ] Pass readiness with selected physical microphone and physical output.
- [ ] Change the selected physical microphone and confirm readiness becomes
  stale within 5 seconds.
- [ ] Change the selected physical output and confirm readiness becomes stale
  within 5 seconds.
- [ ] Change browser microphone or speaker target and confirm readiness becomes
  stale within 5 seconds.
- [ ] Switch Bluetooth/AirPods profile and confirm the route becomes stale or
  degraded, not release-ready.
- [ ] Kill the desktop app audio engine and confirm public devices hide or
  become unavailable within 5 seconds.
- [ ] Restart `coreaudiod` and confirm readiness remains stale until a new
  user-triggered readiness check passes.

## Acceptance

Every invalidation event must include source, previous readiness state, new
readiness state, detection time, and recovery action. Evidence must remain
metadata-only.
