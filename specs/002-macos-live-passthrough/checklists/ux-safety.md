# Checklist: UX And Safety Requirement Quality

**Purpose**: Validate that user-facing readiness and recovery behavior remains
truthful, visible, and safe.

- [x] CHK001 Does the spec prohibit hidden recording during readiness checks?
- [x] CHK002 Is the ready state blocked unless both real paths pass?
- [x] CHK003 Are degraded states distinct from installed/visible states?
- [x] CHK004 Are recovery actions required for microphone, speaker, self-routing, loopback, and device-change failures?
- [x] CHK005 Is one-action stop preserved for active capture?
- [x] CHK006 Are UI states required to use non-color-only cues and accessible labels?
- [x] CHK007 Does the spec avoid promising backend transcription or upload in this feature?
- [x] CHK008 Are proof devices prevented from being treated as safe normal system defaults before passthrough acceptance?

## Notes

Requirements are safe to move into task generation. UI implementation must keep
the current truthful `not ready for calls yet` state until route evidence exists.
