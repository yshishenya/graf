# UX Requirements Checklist: browser invitation error responses

**Purpose**: Validate that the browser recovery requirements are clear and
usable for unavailable invitation states.

**Created**: 2026-07-26

**Feature**: [spec.md](../spec.md)

## Human-readable outcome

- [X] Is the difference between a valid first entry and an unavailable/replayed
  link stated in user-facing terms? [Clarity, User Story 1]
- [X] Does the specification prohibit a technical JSON-file presentation in
  every browser error case? [Completeness, Spec FR-002]
- [X] Is the safe next action defined without promising renewed access?
  [Clarity, Spec FR-003]
- [X] Are no-content and no-secret states explicit for unavailable pages?
  [Coverage, Spec FR-007]

## Browser and email edge cases

- [X] Are duplicate-tab and link-preview cases included? [Edge Case Coverage]
- [X] Are missing and generic `Accept` headers covered for email and embedded
  browser navigation? [Completeness, Spec FR-002]
- [X] Is the unauthenticated transition to the normal GRAF login flow defined?
  [Clarity, Spec FR-004]

## Accessibility and consistency

- [X] Is the unavailable result required to remain within the existing GRAF
  cabinet shell? [Consistency, contract browser-invitation-errors.md]
- [X] Is the result understandable without relying on a raw status code or
  technical response format? [Usability, User Story 1]
- [X] Is the valid first-entry presentation explicitly preserved while the
  unavailable state changes? [Consistency, Spec FR-001]
