# Security Requirements Checklist: Real Playback Availability

**Purpose**: Validate that playback requirements protect audio access, storage boundaries, deletion truth, and metadata-only evidence.
**Created**: 2026-06-24
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are protected playback resources defined separately from audio download/export resources? [Completeness, Spec §FR-001, §FR-003]
- [X] CHK002 Are unauthorized, deleted, deleting, purged, transcript-only, processing, failed, missing-source, and storage-unavailable states covered? [Coverage, Spec §FR-007]
- [X] CHK003 Are server-mediated playback boundaries specified without direct storage URLs or signed URLs? [Completeness, Spec §FR-004]
- [X] CHK004 Are range-playback requirements specified without weakening access or audit requirements? [Completeness, Spec §FR-005, §FR-013]

## Requirement Clarity

- [X] CHK005 Is review playback clearly distinguished from artifact download/export policy? [Clarity, Spec §FR-002, §FR-003]
- [X] CHK006 Is the dual-source playback requirement clear enough to prevent misleading single-track playback? [Clarity, Spec §FR-006]
- [X] CHK007 Are safe unavailable reasons required for blocked playback states? [Clarity, Spec §FR-007]
- [X] CHK008 Are forbidden evidence contents explicitly listed? [Clarity, Spec §FR-013]

## Requirement Consistency

- [X] CHK009 Do playback requirements align with existing access, deletion, storage, and audit boundaries? [Consistency, Plan §Constitution Check]
- [X] CHK010 Are web and embedded desktop security requirements consistent for the same meeting and viewer? [Consistency, Spec §FR-011]
- [X] CHK011 Is clean-room Krisp reference usage constrained away from proprietary code, copy, icons, and assets? [Consistency, Spec §Assumptions]

## Acceptance Criteria Quality

- [X] CHK012 Can real default owner playback, disabled download policy, route range behavior, and denied states be objectively measured? [Measurability, Spec §SC-001 through §SC-005]
- [X] CHK013 Are metadata-only validation outcomes measurable without private content? [Measurability, Spec §SC-004, §SC-007]

## Edge Case Coverage

- [X] CHK014 Are malformed or out-of-bounds range requests included as edge cases? [Coverage, Spec §Edge Cases]
- [X] CHK015 Are missing-source and unsafe-review-audio edge cases covered? [Coverage, Spec §Edge Cases]
