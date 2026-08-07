# UX Requirements Checklist: Launch Landing Redesign

**Purpose**: Validate that the launch landing, product-proof, accessibility, brand-distance and public-truth requirements are complete and implementation-ready.
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are the hero goal, primary action, secondary action and platform-neutral boundary all specified? [Completeness, Spec §User Story 1, FR-002–FR-003]
- [x] CHK002 Are the required proof chapters and their relationship to visible product evidence defined? [Completeness, Spec §User Story 2, FR-004–FR-010]
- [x] CHK003 Are landing and download responsibilities separated clearly enough to prevent macOS-first positioning in the hero? [Completeness, Spec §User Story 3, FR-003, FR-015–FR-017]
- [x] CHK004 Are future AI, billing and platform promises explicitly bounded rather than silently omitted? [Completeness, Spec §Assumptions, FR-011–FR-014, FR-021–FR-022]

## Requirement Clarity

- [x] CHK005 Is “real product screenshot” defined clearly enough to exclude ImageGen panels, illustrations and obsolete UI? [Clarity, FR-008, Contract §Product proof]
- [x] CHK006 Is the difference between manual system-audio recording and approved-target auto-recording unambiguous? [Clarity, FR-005–FR-006, Contract §Copy boundary]
- [x] CHK007 Is the rule for current versus future AI/egress wording explicit and objectively gated? [Clarity, FR-011–FR-012, Spec §User Story 2]
- [x] CHK008 Is price authority distinguished from payment execution so YooKassa cannot become the source of a landing price? [Clarity, FR-013–FR-014, Spec §User Story 4]

## Requirement Consistency

- [x] CHK009 Do hero, chapter and final CTA requirements use one consistent download destination and one existing login destination? [Consistency, FR-015, Contract §Route contract]
- [x] CHK010 Do the selected visual direction and public-truth requirements resolve conflicts in favor of truthful copy without discarding the chosen hierarchy? [Consistency, Spec §Assumptions, Plan §Design and Implementation]
- [x] CHK011 Do screenshot requirements align with privacy, synthetic-data and no-secret repository rules? [Consistency, FR-008–FR-010, Constitution §III]
- [x] CHK012 Do platform availability requirements consistently avoid disabled controls, dates and unsupported release claims? [Consistency, FR-016–FR-017, Contract §Platform availability]

## Acceptance Criteria Quality

- [x] CHK013 Can hero comprehension and download findability be measured with explicit participants and time limits? [Measurability, SC-001–SC-002]
- [x] CHK014 Can responsive and accessibility outcomes be objectively assessed across named viewport widths and interaction modes? [Measurability, SC-004–SC-005]
- [x] CHK015 Can absence of personal data, fake prices and unsupported claims be verified from public output? [Measurability, SC-006–SC-007]

## Scenario And Edge-Case Coverage

- [x] CHK016 Are no-JavaScript, image failure, reduced-motion, 200% zoom and 320 px reflow scenarios specified? [Coverage, Spec §Edge Cases]
- [x] CHK017 Is the fail-closed path defined when a verified public macOS release is unavailable? [Coverage, User Story 3, FR-017, Contract §Platform availability]
- [x] CHK018 Is the no-approved-catalog state defined so no amount or false checkout action appears? [Coverage, User Story 4, FR-013–FR-014]
- [x] CHK019 Is the unsupported-service case defined so logos and tested-compatibility claims cannot exceed evidence? [Coverage, Spec §Edge Cases, FR-005, FR-021]

## Dependencies And Release Gates

- [x] CHK020 Are screenshot, signed-installer, AI/egress and billing dependencies named as release gates rather than hidden implementation assumptions? [Dependency, FR-022, Spec §Assumptions, Plan §Release Gate]
- [x] CHK021 Is production deployment explicitly outside this implementation pass and subject to separate approval? [Scope, Spec §Assumptions, Plan §Release Gate]

## Notes

- Requirements quality gate passed. Implementation must retain the truth-safe copy boundary even when visual fidelity would favor the original mock wording.
