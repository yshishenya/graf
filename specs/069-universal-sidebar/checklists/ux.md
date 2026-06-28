# UX Checklist: Universal Cabinet Sidebar

**Purpose**: Validate sidebar UX, accessibility, embedded behavior, and fragment-boundary requirements before implementation planning
**Created**: 2026-06-28
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are covered user cabinet surfaces explicitly named and bounded? [Completeness, Spec §Assumptions]
- [x] CHK002 Are admin and auth surfaces explicitly excluded from the shared sidebar scope? [Completeness, Spec §FR-012, Spec §Assumptions]
- [x] CHK003 Are browser and desktop embedded navigation requirements both defined? [Completeness, Spec §FR-002, Spec §FR-003]
- [x] CHK004 Are disabled/future destination requirements defined for visual state and keyboard behavior? [Completeness, Spec §FR-008]
- [x] CHK005 Are dynamic update and fragment boundaries specified separately from full-page shell behavior? [Completeness, Spec §FR-006, Spec §FR-015]

## Requirement Clarity

- [x] CHK006 Is the active destination requirement specific enough to distinguish one current destination from ordinary links and unavailable destinations? [Clarity, Spec §FR-007, Spec §FR-016]
- [x] CHK007 Is the keyboard focus requirement distinct from the selected destination requirement? [Clarity, Spec §FR-014]
- [x] CHK008 Is compact embedded behavior described without implying a second native product navigation system? [Clarity, Spec §US2, Spec §FR-004]
- [x] CHK009 Is the shared sidebar contract described in terms of brand area, items, state, counters, footer, and accessibility labels? [Clarity, Spec §FR-001]

## Requirement Consistency

- [x] CHK010 Do the browser and desktop embedded requirements use one destination identity model with route adaptation only where needed? [Consistency, Spec §FR-003, Spec §Key Entities]
- [x] CHK011 Do native desktop boundary requirements align with visible consent and one-action stop constraints? [Consistency, Spec §US2, Spec §Assumptions]
- [x] CHK012 Do fragment requirements align with the success criteria that only one shell/sidebar exists after dynamic updates? [Consistency, Spec §FR-006, Spec §SC-003]

## Acceptance Criteria Quality

- [x] CHK013 Are success criteria measurable for all covered full pages, active states, fragment updates, keyboard behavior, and desktop embedded ownership? [Measurability, Spec §Success Criteria]
- [x] CHK014 Are acceptance scenarios independently testable for consistent navigation, desktop embedded navigation, and content-only updates? [Acceptance Criteria, Spec §User Scenarios]
- [x] CHK015 Is brand-distance preservation stated as a requirement rather than left as subjective visual preference? [Measurability, Spec §FR-009]

## Scenario And Edge Case Coverage

- [x] CHK016 Are narrow viewport and compact embedded scenarios covered? [Coverage, Spec §US2, Spec §Edge Cases]
- [x] CHK017 Are secondary navigation landmark risks covered for future pages? [Coverage, Spec §Edge Cases]
- [x] CHK018 Are full-page responses used in dynamic updates constrained so they cannot duplicate shell markup? [Coverage, Spec §Edge Cases]
- [x] CHK019 Are unavailable MVP navigation destinations covered without promising unfinished behavior? [Coverage, Spec §Edge Cases]

## Dependencies And Assumptions

- [x] CHK020 Are dependencies on existing cabinet visual language, route ownership, and fragment behavior documented? [Assumption, Spec §Assumptions]
- [x] CHK021 Is the native desktop product navigation exclusion documented as a boundary, not an implementation accident? [Assumption, Spec §FR-004]
