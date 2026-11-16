# UX Checklist: F296

**Review Ownership**: reviewer-owned. Mark `[x]` only with concrete evidence.

- [x] CHK001 Cleanup action uses the exact copy in `contracts/ux-copy.md` and explains that only the local transcription WAV is removed.
- [x] CHK002 Copy states that review audio, manifest and local playback remain.
- [x] CHK003 Copy states that the server meeting is not deleted.
- [x] CHK004 Confirmation is explicit and cannot be confused with server deletion.
- [x] CHK005 The amount of space to be freed is shown before confirmation.
- [x] CHK006 Ineligible items explain the reason without raw errors or internal codes.
- [x] CHK007 Automatic eviction is explained in plain language and can be disabled.
- [x] CHK008 Kill switch state is visible and takes effect without a restart.
- [x] CHK009 VoiceOver labels cover cleanup, confirmation, reasons, cache status and the toggle, using `contracts/ux-copy.md`.
- [x] CHK010 Warning vs critical cache states are informational, not false errors.
- [x] CHK011 F284 local playback and local-only labels remain unchanged.
- [x] CHK012 No new library or duplicate local-recordings surface is introduced.

## Reviewer Notes

- **Re-review 2026-11-16**: 12/12 checked at the copy/design level. Design blockers: 0. UI implementation and copy/AX tests are still pending (T016, T020).
- CHK010 is checked against `contracts/ux-copy.md:45,59` and `plan.md:191`; F296 warning/eviction is informational. The critical capture state remains an F295 capture gate, not an F296 false error.
