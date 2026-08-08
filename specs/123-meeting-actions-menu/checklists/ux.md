# UX And Accessibility Requirements Checklist: Понятное меню действий со встречей

**Purpose**: Validate information architecture, capability, destructive-action, accessibility and clean-room requirement quality before implementation
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are the visible primary action and complete ordered secondary-action set explicitly defined? [Completeness, Spec §FR-001–FR-007]
- [x] CHK002 Are the exact labels and differentiating helper texts documented for export and audio? [Completeness, Spec §FR-004–FR-005]
- [x] CHK003 Are the items excluded from the quick menu and their destination explicitly defined? [Completeness, Spec §FR-008–FR-010]
- [x] CHK004 Are browser and embedded desktop expectations both specified? [Completeness, Spec §FR-021]

## Requirement Clarity

- [x] CHK005 Is “compact” bounded by action count, content limits, target size and prohibited surfaces rather than left subjective? [Clarity, Spec §FR-002–FR-003, FR-008, FR-019]
- [x] CHK006 Is action availability assigned unambiguously to existing server capability and policy truth? [Clarity, Spec §FR-014–FR-015]
- [x] CHK007 Is destructive separation defined through order, divider, text/icon and non-color cues? [Clarity, Spec §FR-007]
- [x] CHK008 Are focus destinations explicit for menu open, dismissal, details close, export close and delete cancel? [Clarity, Spec §FR-010, FR-017–FR-018]

## Requirement Consistency

- [x] CHK009 Do menu labels, order and helper copy agree across user stories, functional requirements, success criteria and the UI contract? [Consistency, Spec §US1, FR-003–FR-007, SC-002]
- [x] CHK010 Do hidden-action requirements remain consistent with unchanged final server authorization and egress rechecks? [Consistency, Spec §US1, FR-014–FR-015, SC-004]
- [x] CHK011 Do details and deletion requirements preserve rather than weaken existing lifecycle truth? [Consistency, Spec §US2–US3, FR-009, FR-013]
- [x] CHK012 Does clean-room reuse align with the explicit prohibition on competitor-specific expression? [Consistency, Spec §FR-022]

## Scenario Coverage

- [x] CHK013 Are primary export, audio, details and delete flows independently testable? [Coverage, Spec §US1–US3]
- [x] CHK014 Are partial capability sets, no-action state, processing and deletion-in-progress covered? [Coverage, Spec §Edge Cases, FR-024]
- [x] CHK015 Are click, keyboard, outside-click, Escape and destination-transition flows all specified? [Coverage, Spec §US4, FR-017–FR-018]
- [x] CHK016 Are direct-request denial and render-to-action race requirements retained so UI hiding cannot become authorization? [Coverage, Spec §Edge Cases, FR-014]

## Non-Functional Requirements

- [x] CHK017 Are keyboard keys, focus behavior, accessible names, non-color cues and minimum targets fully specified? [Accessibility, Spec §FR-016–FR-020]
- [x] CHK018 Are zoom, narrow viewport, theme, contrast, forced colors and reduced motion included with measurable outcomes? [Accessibility, Spec §FR-020, SC-003, SC-005]
- [x] CHK019 Is visual fidelity measured against the selected GRAF concept with P0/P1/P2 blocking criteria? [Measurability, Spec §SC-009]
- [x] CHK020 Are new dependency, storage, endpoint, egress and lifecycle additions explicitly excluded? [Scope, Spec §FR-023, Out of Scope]

## Notes

- 20/20 requirement-quality checks pass.
- Depth: formal pre-implementation/release gate.
- Audience: author and PR reviewer.
- Focus: simple IA, policy-derived availability, deletion safety, accessibility,
  browser/embedded parity and clean-room visual distance.
