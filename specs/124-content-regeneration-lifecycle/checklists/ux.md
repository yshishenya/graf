# Requirements Quality Checklist: Regeneration UX and Accessibility

**Purpose**: Validate that owner/shared interaction, recovery copy and accessibility requirements are complete and unambiguous.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are initial, manual, retryable, terminal, stale, expired and blocked candidate states defined? [Completeness, Spec §FR-029]
- [X] CHK002 Is owner-only preview explicitly required before accept? [Completeness, Spec §FR-011]
- [X] CHK003 Are accepted current, candidate and shared-viewer surfaces separated? [Completeness, Spec §User Story 2/6]
- [X] CHK004 Are keyboard, VoiceOver, focus and live-region requirements defined for every candidate action? [Coverage, Spec §FR-031, NFR-006]

## Requirement Clarity and Consistency

- [X] CHK005 Does ready copy name the selected format rather than an ambiguous generic variant? [Clarity, Spec §FR-029]
- [X] CHK006 Is explicit refresh intent distinguished from selecting the already-current format? [Clarity, Spec §FR-014, User Story 2]
- [X] CHK007 Are stale conflicts required to provide a visible recovery action rather than an error-only state? [Clarity, Spec §FR-030]
- [X] CHK008 Are “current remains visible” and “candidate never publishes itself” consistent across all state transitions? [Consistency, Spec §FR-005/013/017]

## Scenario and Edge Coverage

- [X] CHK009 Are refresh, closed tab, hidden tab, worker restart and expired candidate journeys covered? [Coverage, Spec §User Story 7]
- [X] CHK010 Are quota, provider failure, no transcript and deleted meeting states represented with one next step? [Coverage, Spec §User Story 1/7]
- [X] CHK011 Are narrow-window, reduced-motion and shared-viewer controls bounded without focus theft? [Edge Case, Spec §FR-031, NFR-006]

## Acceptance Quality

- [X] CHK012 Are polling bounds measurable by deadline/attempt budget and hidden-document pause? [Measurability, Spec §FR-025, SC-008]
- [X] CHK013 Can an owner complete preview, accept, reject, conflict refresh and retry with keyboard-only controls? [Acceptance, Spec §SC-007]
