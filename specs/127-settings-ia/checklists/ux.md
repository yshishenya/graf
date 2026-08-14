# UX Requirements Quality Checklist: единая архитектура настроек

**Purpose**: Validate that the settings UX requirements are complete, clear and
testable before implementation.
**Created**: 2026-07-25
**Feature**: [spec.md](../spec.md)
**Audience**: Product/design reviewer and implementation reviewer.

## Information architecture

- [x] CHK001 — Is the global entry point and the maximum navigation depth explicitly defined? [Completeness, Spec §FR-001–FR-002]
- [x] CHK002 — Are all existing settings surfaces mapped to a canonical category or an explicit legacy path? [Traceability, Spec §FR-005, SC-002]
- [x] CHK003 — Are unsupported future categories explicitly excluded instead of represented by empty navigation items? [Scope, Spec §US3, Assumptions]
- [x] CHK004 — Are browser and embedded desktop navigation semantics required to remain equivalent? [Consistency, Spec §US1, FR-015]

## Scope and interaction clarity

- [x] CHK005 — Is the scope vocabulary finite and tied to a user-visible ownership context? [Clarity, Spec §FR-004]
- [x] CHK006 — Are owner-only, native-only and unavailable states required to explain both the reason and the next step? [Coverage, Spec §US2, FR-003–FR-004]
- [x] CHK007 — Are pristine, dirty, saving, saved and error states defined for grouped forms? [Completeness, Spec §FR-012–FR-013]
- [x] CHK008 — Does the specification distinguish navigation links from state-changing actions? [Consistency, Spec §FR-014]

## Accessibility and responsive states

- [x] CHK009 — Are semantic heading, path, status, empty, loading and unavailable requirements defined for every applicable category? [Coverage, Spec §FR-003, FR-014]
- [x] CHK010 — Are dialog accessible name, keyboard close, opener focus restoration and first useful focus target all specified? [Accessibility, Spec §FR-014, Edge Cases]
- [x] CHK011 — Are keyboard-only and visible-focus acceptance signals measurable rather than described only as “convenient”? [Measurability, Spec §SC-004]
- [x] CHK012 — Are empty, expired, stale, denied and partial-failure states represented without implying success? [Exception coverage, Spec §Edge Cases, FR-007]

## Content and terminology

- [x] CHK013 — Are Russian labels and role translations required consistently across global navigation, category pages and controls? [Consistency, Spec §FR-016]
- [x] CHK014 — Does the summary-format requirement explicitly distinguish built-in workspace defaults from personal formats? [Clarity, Spec §FR-006]
- [x] CHK015 — Does the calendar requirement state the intended information order without prescribing a fake conflict action? [Clarity, Spec §FR-007, research Decision 5]
- [x] CHK016 — Does the recording requirement explain native handoff without introducing a web capture policy? [Safety boundary, Spec §FR-011, SC-008]
- [x] CHK017 — Is every supported settings category, including notifications,
  discoverable from the shared navigation in browser and embedded modes?
  [Discoverability, Spec §FR-002, FR-018]
