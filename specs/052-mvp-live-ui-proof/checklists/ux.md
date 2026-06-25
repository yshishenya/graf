# UX Requirements Checklist: MVP Live Owner Journey And UI Proof

**Purpose**: Validate UI/UX requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are web desktop, web compact, macOS embedded, and native macOS shell surfaces all specified? [Completeness, Spec §User Story 3, FR-009]
- [x] CHK002 Are transcript, playback, timestamp seek, speaker timeline, diarization, and outcomes required in the same ready review flow? [Completeness, Spec §FR-007]
- [x] CHK003 Are unavailable states defined for auth, server health, missing transcript, missing playback, missing timeline, and missing outcomes? [Coverage, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK004 Is false-ready behavior explicitly forbidden rather than left to subjective UI judgement? [Clarity, Spec §FR-006, FR-013]
- [x] CHK005 Is speaker timeline visibility required in measurable terms, including bottom timeline lanes tied to the reviewed meeting? [Clarity, Spec §FR-010, SC-004]
- [x] CHK006 Is the KRISP reference boundary clear enough to prevent copying brand, screenshots, assets, private content, or trade dress? [Clarity, Spec §FR-011]
- [x] CHK007 Are native macOS recording/upload truth requirements separated from embedded web review requirements? [Consistency, Interface Contract §macOS Embedded Cabinet]

## Scenario Coverage

- [x] CHK008 Are web/embedded divergence and cached-ready cases addressed as requirements? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are compact layout risks covered without introducing subjective "looks good" language? [Measurability, Spec §SC-003]
- [x] CHK010 Are speaker assignment and multi-speaker expectations covered at the interaction-pattern level without requiring post-MVP editing? [Scope, Interface Contract §KRISP Clean-Room Reference]

## Acceptance Criteria Quality

- [x] CHK011 Can UI quality be objectively classified with pass/fail/blocker evidence instead of taste-based review? [Acceptance Criteria, Spec §SC-003, SC-004]
