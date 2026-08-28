# UX and Security Requirements Checklist: Safe Desktop Offer Route

**Purpose**: Validate requirement quality for the legal-document UX and desktop route security boundary
**Created**: 2026-08-28
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are requirements defined for opening the offer, preserving checkout, and avoiding billing mutations? [Completeness, Spec §FR-001–FR-005]
- [x] CHK002 Are the external destination fields that may and may not cross the desktop boundary explicitly documented? [Completeness, Spec §FR-004]
- [x] CHK003 Are requirements defined for unknown, third-party, and insecure sibling routes? [Coverage, Spec §Edge Cases, FR-003]

## Requirement Clarity

- [x] CHK004 Is the allowed legal route identified by an exact canonical path rather than an open-ended legal-route category? [Clarity, Spec §Assumptions]
- [x] CHK005 Is the expected ownership of the legal document—browser rather than embedded cabinet—unambiguous? [Clarity, Spec §FR-001, Assumptions]

## Requirement Consistency

- [x] CHK006 Are external opening requirements consistent with fail-closed handling of all routes outside the exact allowlist? [Consistency, Spec §FR-001, FR-003]
- [x] CHK007 Are no-mutation requirements consistent across user scenarios, functional requirements, and success criteria? [Consistency, Spec §User Story 1, FR-002, SC-002]

## Acceptance Criteria Quality

- [x] CHK008 Can the absence of the blocked desktop state and the continued availability of checkout be objectively assessed? [Measurability, Spec §SC-001, SC-004]
- [x] CHK009 Can the absence of payment, subscription, and consent mutations be objectively assessed? [Measurability, Spec §SC-002]

## Dependencies and Assumptions

- [x] CHK010 Is the dependency on the existing public HTTPS `/offer` document and a separate signed macOS release explicitly stated? [Dependency, Spec §Assumptions]

## Notes

- Standard depth for PR reviewers; focus is the exact-route trust boundary and non-mutating legal UX.
