# Requirements Quality Checklist: Capture, custody and local-row UX

**Purpose**: Reviewer gate for high-risk capture, deletion and desktop UX requirements
**Created**: 2026-09-02
**Ownership**: `[x]` means reviewer approval of requirement quality, not implementation completion. `$speckit-implement` reads but does not modify these markers. Review is pending.

## Capture and privacy boundaries

- [ ] CHK001 Are finite overshoot, non-finite input, wrong frame size and genuine AEC failure specified as distinct cases? [Completeness, Spec §FR-010–FR-012]
- [ ] CHK002 Is the no-raw-microphone-fallback boundary explicit for every terminal capture path? [Coverage, Spec §FR-012]
- [ ] CHK003 Are cleaned-prefix retention and automatic-upload exclusion consistent? [Consistency, Spec §FR-006, FR-012]

## Custody and deletion

- [ ] CHK004 Is the allowed deletion target bounded to the recordings root and exact user-selected records? [Clarity, Spec §FR-013–FR-014]
- [ ] CHK005 Does the specification distinguish local package identity from server meeting identity throughout handoff? [Consistency, Spec §FR-009]
- [ ] CHK006 Are queue refresh and legacy misclassification requirements defined without requiring manual queue-file edits? [Coverage, Spec §FR-007–FR-008]

## UX, localization and accessibility

- [ ] CHK007 Are readable UTF-8, icon parity, duration truth and local primary action each independently specified? [Completeness, Spec §FR-001–FR-005]
- [ ] CHK008 Are pointer, keyboard and assistive-technology activation requirements present for the local primary action? [Coverage, Spec §US1/AC2, Edge Cases]
- [ ] CHK009 Is behavior defined when playback is absent and while server truth has not yet appeared in the refreshed list? [Edge Case, Spec §Edge Cases]

## Acceptance quality

- [ ] CHK010 Can the no-duplicate handoff result and AEC safety boundary be measured objectively? [Measurability, Spec §SC-003–SC-004]
- [ ] CHK011 Are cleanup success and preservation of the known-good meeting both explicit? [Completeness, Spec §SC-005]

## Notes

- Reviewer should evaluate wording before implementation; implementation evidence belongs in tasks/quickstart, not in this checklist.
- Review evidence belongs in the PR and quickstart; this file stays reviewer-owned.
