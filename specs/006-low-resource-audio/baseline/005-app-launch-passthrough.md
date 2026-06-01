# Baseline Evidence: 005 App-Launch Passthrough

**Feature**: `006-low-resource-audio`
**Baseline**: `005-macos-passthrough-release-hardening`
**Captured**: 2026-06-01

## Accepted Baseline

The accepted pre-006 route lifecycle is the non-recording app-launch
passthrough stabilized in `005-macos-passthrough-release-hardening`.

Baseline expectations for this feature:

- 2brain Rec uses the macOS HAL virtual audio driver; no no-driver fallback is
  accepted.
- The public virtual devices are `2brain Rec Microphone` and
  `2brain Rec Speaker`.
- When the accepted app-launch route is active, browser and meeting apps can
  hear and be heard without pressing `Run Check`.
- Recording, transcription, upload, MediaScribe, Langfuse, analytics, and
  external network egress are not started by the route lifecycle.
- Driver/app handoff must fail closed rather than block Core Audio or imply
  recording.
- Diagnostic and validation evidence is metadata-only.

## Current Known Gaps Before 006

The 006 implementation exists to close these known gaps without losing the
accepted baseline:

- App-side physical Core Audio setup can still be reachable from synchronous
  startup paths.
- Physical AudioUnit setup and Core Audio enumeration are not yet proven bounded
  to 3000 ms across no-hang surfaces.
- Older app-health/public-device policy accepted hide-on-heartbeat behavior;
  006 changes the default requirement to visible fail-closed devices.
- Route truth must be represented as separate evidence planes rather than a
  single visible-device or ready flag.
- Low-resource default promotion requires local P1 gates and fallback to the
  accepted 005 lifecycle without reinstalling the HAL driver.

## Baseline Validation References

- `specs/005-macos-passthrough-release-hardening/spec.md`
- `specs/005-macos-passthrough-release-hardening/quickstart.md`
- `apps/macos/Scripts/validate-passthrough-release-hardening.sh`
- `qa/macos/release-candidate-checklist.md`
- `apps/macos/AudioDriver/RuntimeProofReport.md`

## Promotion Guard

Low-resource behavior must not replace this baseline unless all local P1 gates
from `specs/006-low-resource-audio/quickstart.md` pass. Any P1 failure keeps or
restores the accepted 005 app-launch route lifecycle.
