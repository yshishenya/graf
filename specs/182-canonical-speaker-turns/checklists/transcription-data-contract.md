# Transcription Data Contract Checklist: Canonical Provider Speaker Turns

**Purpose**: Validate that speaker truth, degradation, identity, and consumer parity requirements are complete before implementation.

**Created**: 2026-08-21

## Canonical source and conservation

- [x] CHK001 Is the canonical temporal source explicit for both accepted and degraded provider results? [Completeness, Spec FR-002, FR-009]
- [x] CHK002 Is raw ASR evidence explicitly separated from attributed provider turns? [Clarity, Spec FR-003]
- [x] CHK003 Are all speaker-guessing and silent-repair approaches prohibited? [Consistency, Spec FR-004, FR-009]
- [x] CHK004 Is text conservation defined with deterministic representation-only normalization? [Measurability, Research Decision 3]
- [x] CHK005 Are duplicate text, non-positive duration, chronology, tiny unknown, and conservation defects bounded and testable? [Coverage, Spec FR-008]
- [x] CHK006 Does degradation preserve content once without treating unsafe provider rows as truth? [Failure state, Spec FR-010]

## Identity and time

- [x] CHK007 Are provider key, stable GRAF key, canonical label, and editable display name distinct? [Clarity, Spec FR-005]
- [x] CHK008 Is legacy saved-name behavior safe under ambiguity and renumbering? [Compatibility, Spec FR-020]
- [x] CHK009 Are unknown, mixed, and uncertain identities excluded from confirmed participants and rename? [Coverage, Spec FR-007, FR-016]
- [x] CHK010 Is the talk-time denominator and user-facing label unambiguous? [Clarity, Spec FR-015]
- [x] CHK011 Are exact canonical time values separated from presentation rounding? [Consistency, Spec FR-014]

## Surface parity

- [x] CHK012 Are normal recording and manual upload required to converge after import? [Coverage, Spec FR-013]
- [x] CHK013 Are API, UI, timeline, every requested export, and outcomes named explicitly? [Completeness, Spec FR-001, FR-012]
- [x] CHK014 Is degraded state included in the parity tuple rather than treated as surface-only copy? [Traceability, Canonical contract]
- [x] CHK015 Are the two supplied production defect classes reproducible without private fixtures? [Measurability, SC-011]

## Notes

- All requirements are complete; no clarification blocker remains.
