# UX Requirements Checklist: Recording Selection And Delete

**Purpose**: Validate selection/delete UX requirements before implementation
**Created**: 2026-06-26
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are selection states defined for zero, one, and many selected rows? [Completeness, Spec §FR-001-003]
- [x] CHK002 Are row-level and toolbar-level delete entry points both specified? [Completeness, Spec §FR-003, FR-005]
- [x] CHK003 Are cancellation, success, and failure states defined for deletion? [Coverage, Spec §FR-008-010]
- [x] CHK004 Are out-of-scope actions explicitly excluded, including unread, overflow menu, and bulk download? [Scope, Spec §FR-014]

## Requirement Clarity

- [x] CHK005 Is disabled download behavior unambiguous and measurable? [Clarity, Spec §FR-004]
- [x] CHK006 Is deletion copy bounded to 2brain Rec control rather than universal erasure? [Clarity, Spec §FR-007]
- [x] CHK007 Are Russian localization requirements explicit for all new visible UI copy? [Clarity, Spec §SC-004]

## Accessibility And Edge Cases

- [x] CHK008 Are keyboard and screen-reader requirements specified for selection and delete controls? [Coverage, Spec §FR-012]
- [x] CHK009 Are disappearing rows and partial batch failure addressed as edge cases? [Edge Case, Spec §Edge Cases]
- [x] CHK010 Are metadata-only evidence boundaries specified for runtime proof? [Security/Privacy, Spec §SC-007]
