# UX Requirements Checklist: Safe Browser Login Returns and Callback Diagnostics

**Purpose**: Validate that the cabinet recovery experience is complete, neutral, accessible, and consistent across browser surfaces.
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [browser auth return contract](../contracts/browser-auth-return.md)

## Recovery Experience Completeness

- [x] CHK001 Are regular browser and embedded cabinet return outcomes specified as matching-but-surface-specific destinations? [Completeness, Spec §FR-002, §FR-004]
- [x] CHK002 Is the distinction between an authorized preserved deep link and an unavailable fallback list explicit and free of meeting-existence clues? [Clarity, Spec §FR-003, §FR-004, §FR-008]
- [x] CHK003 Are direct unavailable detail journeys specified separately from post-sign-in recovery, so bookmarked and revoked links have a normal product path? [Coverage, Spec §User Story 2, §FR-007]
- [x] CHK004 Do requirements cover missing, denied, deleted, malformed, and access-changed detail states under one neutral experience? [Scenario Coverage, Spec §User Stories, Edge Cases, §FR-013]

## Content And Accessibility Clarity

- [x] CHK005 Does the unavailable-page requirement constrain the page to neutral recovery wording rather than diagnostic terminology or an explanation of the access decision? [Clarity, Spec §User Story 2, §FR-008]
- [x] CHK006 Are shell continuity, semantic heading, and keyboard-accessible matching-list action specified for the unavailable state? [Accessibility, Spec §FR-014]
- [x] CHK007 Is the matching list action defined for both surfaces without requiring a new client route, modal, toast, or brand treatment? [Consistency, Spec §FR-007, Assumptions, Plan §Structure Decision]
- [x] CHK008 Is the scope boundary for asynchronous fragments stated so the full-page recovery experience does not conflict with existing machine-readable terminal states? [Consistency, Contract §Direct unavailable detail behavior]

## Acceptance Criteria Quality

- [x] CHK009 Can the required human-facing result be objectively distinguished from a raw problem document using status, media type, shell, heading, action, and exclusion criteria? [Measurability, Spec §SC-003, Contract §Direct unavailable detail behavior]
- [x] CHK010 Are successful and denied post-sign-in scenarios independently measurable for both cabinet surfaces? [Measurability, Spec §SC-001, §SC-002]
- [x] CHK011 Do the scenarios explicitly prohibit private content and internal identifiers in the recovery output rather than only requiring a link away? [Privacy, Completeness, Spec §FR-008, §SC-001]

## Notes

- Review pass 1: 11/11 requirement-quality questions pass. FR-014 was added during this pass to make the existing shell, semantic heading, and keyboard action explicit instead of relying on an implicit UI convention.
