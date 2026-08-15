# UX Requirements Checklist: Remove Workspace Legacy

**Purpose**: Validate workspace naming, visibility, recovery and accessibility requirements
**Created**: 2026-08-15
**Feature**: [spec.md](../spec.md)

## Information Architecture

- [x] CHK001 Is the canonical personal name specified independently from its type/role subtitle? [Clarity, Spec §FR-008–FR-009]
- [x] CHK002 Is corporate naming tied to the real workspace name instead of a generic `Команда` label? [Consistency, Spec §FR-008–FR-009]
- [x] CHK003 Is selector content limited to active customer workspaces? [Completeness, Spec §FR-003, FR-008]
- [x] CHK004 Is pending invitation represented as a separate action rather than an active workspace? [Coverage, Spec §US2]

## User Journey And Recovery

- [x] CHK005 Is the one-workspace first-login outcome measurable across signup and repeat login? [Measurability, Spec §SC-001]
- [x] CHK006 Is revoked corporate recovery defined without exposing or activating the internal anchor? [Coverage, Spec §FR-007]
- [x] CHK007 Is missing-personal repair behavior specified, including fail-closed ambiguity? [Edge Case, Spec §FR-007]
- [x] CHK008 Is immediate billing after signup covered by an explicit edge case and personal-only rule? [Coverage, Spec §Edge Cases, FR-010]

## Public Boundary And Accessibility

- [x] CHK009 Is non-disclosure of internal identifier/name required for public HTML, JSON and auth responses? [Privacy, Spec §FR-015]
- [x] CHK010 Are visible Russian labels unambiguous for both personal and corporate roles? [Localization, Spec §FR-008–FR-009]
- [x] CHK011 Are existing selector status semantics retained for screen readers and keyboard users by scope? [Assumption, Contract §Listing and activation]
- [x] CHK012 Can UX acceptance be verified without relying on raw database names? [Measurability, Spec §SC-001–SC-002]

## Notes

- All UX requirement-quality items pass; implementation must preserve existing focus, CSRF and live-status contracts.
