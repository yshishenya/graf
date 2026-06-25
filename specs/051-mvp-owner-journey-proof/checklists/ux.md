# UX Requirements Checklist: MVP Owner Journey Proof

**Purpose**: Validate UI/UX requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are web desktop, web mobile-width, embedded desktop, embedded mobile-width, and native macOS surfaces all specified? [Completeness, Spec §User Story 4]
- [x] CHK002 Are requirements defined for transcript, playback, timestamp seek, speaker timeline, and stored outcomes in the same review flow? [Completeness, Spec §FR-005, §FR-010]
- [x] CHK003 Are degraded states specified for missing transcript, diarization, playback, timeline, outcomes, auth, and server availability? [Coverage, Spec §FR-007, Edge Cases]

## Requirement Clarity

- [x] CHK004 Is "interface quality" expressed with measurable checks such as overlap, clipping, overflow, console/runtime errors, stale tabs, and missing primary controls? [Clarity, Spec §FR-010, §SC-005]
- [x] CHK005 Is the Krisp reference boundary clear enough to prevent copying brand, assets, screenshots, copy, icons, or private content? [Clarity, Spec §FR-013]
- [x] CHK006 Are native macOS capture-control visibility requirements separated from embedded WebKit review requirements? [Clarity, Spec §FR-011, §FR-012]

## Scenario Coverage

- [x] CHK007 Are server-down, auth-expired, cached-ready, and login-page cases covered? [Coverage, Edge Cases]
- [x] CHK008 Are speaker timeline edge cases covered, including more speakers than the visible color set? [Coverage, Edge Cases]
- [x] CHK009 Are web/embedded state divergence cases covered? [Coverage, Edge Cases]

## Acceptance Criteria Quality

- [x] CHK010 Can the UI requirements be objectively validated without relying on subjective "looks good" language? [Acceptance Criteria, Spec §SC-005, §SC-006]
