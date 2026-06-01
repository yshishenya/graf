# Aggregate And Multi-Output Route Check

## Purpose

Record metadata-only evidence for aggregate, multi-output, and Bluetooth route
handling in the pre-recording hardening slice.

## Required Scenarios

- [ ] Physical microphone change.
- [ ] Physical output change.
- [ ] Aggregate input or output route.
- [ ] Multi-output route.
- [ ] Bluetooth route as managed pilot, blocked, or not accepted.

## Acceptance

- Built-in and wired direct routes are release-quality targets.
- Aggregate, multi-output, and Bluetooth routes must be recorded as `passed`,
  `blocked`, or `not_accepted` with a reason.
- If the app cannot prove a route with the same criteria as direct built-in or
  wired routes, the route must not be accepted as release-ready.
