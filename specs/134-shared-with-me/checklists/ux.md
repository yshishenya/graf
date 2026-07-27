# UX Requirements Checklist: «Поделились со мной»

**Purpose**: Assess whether menu, list and accessible-state requirements are
complete and reviewable before implementation.

**Created**: 2026-07-27

**Feature**: [spec.md](../spec.md)

## Navigation and Content

- [x] CHK001 Is the position and label of the separate navigation item clear
  for both cabinet variants? [Clarity, Spec §FR-001, §FR-010]
- [x] CHK002 Are card fields defined consistently with the promised minimum
  recipient metadata and level-of-access explanation? [Consistency, Spec §FR-003]
- [x] CHK003 Is the in-progress meeting state described sufficiently to avoid
  implying that unavailable materials are ready? [Clarity, Edge Cases]
- [x] CHK004 Is the empty state required to avoid implying that an invitation
  or a workspace exists when no current right is available? [Coverage, User
  Story 1]

## Accessible States

- [x] CHK005 Are Russian labels and assistive text requirements specified for
  menu, cards, empty state and unavailable state? [Completeness, Spec §FR-009]
- [x] CHK006 Is keyboard focus behavior defined for the navigation item and
  card destination? [Gap, Spec §FR-009]
- [x] CHK007 Are loading and retry requirements specific enough to distinguish
  an empty list from a failed list load? [Clarity, Spec §FR-009, Edge Cases]
- [x] CHK008 Are browser and embedded layout requirements consistent so that
  the same data does not receive different access meaning? [Consistency,
  Spec §FR-010]

## Acceptance Quality

- [x] CHK009 Can the two-action discovery criterion be objectively assessed
  from the documented entry point and destination? [Measurability, Spec §SC-001]
- [x] CHK010 Are no-results, loading and unavailable scenarios all intentionally
  included or excluded with a clear reason? [Coverage, Spec §FR-009]
