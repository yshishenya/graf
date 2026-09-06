# UX Checklist: MediaScribe v0.5.3 integration fidelity

**Purpose**: Validate the user path through processing, partial results and recovery.
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

- [x] UX-001 Transcript is hidden until matching diarization is ready, with a concrete next state.
- [x] UX-002 Summary loading/failure is visually and semantically independent from transcript availability, including stored output with `not_requested` provider status.
- [x] UX-003 Provider block boundaries are not silently changed by GRAF display logic.
- [x] UX-004 Countdown uses server-derived next check, has a manual check action and resets safely after manual action.
- [x] UX-005 Busy/disabled, refresh, background-tab, keyboard, screen-reader, reduced-motion and forced-colors states are covered by existing cabinet contracts.
- [x] UX-006 Terminal failure, no-recognizable-speech, unknown-role and degraded diarization states do not leave the user at a dead end.
