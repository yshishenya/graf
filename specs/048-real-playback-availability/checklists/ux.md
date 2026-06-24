# UX Requirements Checklist: Real Playback Availability

**Purpose**: Validate that playback UX requirements are clear, usable, accessible, responsive, and clean-room.
**Created**: 2026-06-24
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are bottom player controls specified for play/pause, skip backward, skip forward, current time, duration, speed, and source-state copy? [Completeness, Spec §FR-008]
- [X] CHK002 Are transcript timestamp seek controls specified only for valid playback timestamps? [Completeness, Spec §FR-009]
- [X] CHK003 Are speaker timeline lanes specified when diarization is available? [Completeness, Spec §FR-010]
- [X] CHK004 Are unavailable playback states required to preserve transcript readability? [Completeness, Spec §FR-012]

## Requirement Clarity

- [X] CHK005 Is "persistent bottom review player" defined clearly enough for web and embedded desktop? [Clarity, Spec §US2, §FR-008]
- [X] CHK006 Is the Krisp reference constrained to interaction pattern rather than copied visual design? [Clarity, Spec §Assumptions]
- [X] CHK007 Are mobile and embedded layout constraints stated without ambiguous "looks good" wording? [Clarity, Spec §SC-006]

## Requirement Consistency

- [X] CHK008 Do web cabinet and macOS embedded review requirements use the same playback state and unavailable reasons? [Consistency, Spec §FR-011]
- [X] CHK009 Are timestamp seek requirements consistent with the streaming/range playback requirement? [Consistency, Spec §FR-005, §FR-009]

## Acceptance Criteria Quality

- [X] CHK010 Can timestamp seek be objectively measured within one second? [Measurability, Spec §SC-003]
- [X] CHK011 Can responsive layout and overflow be objectively measured for desktop, mobile, and embedded views? [Measurability, Spec §SC-006]

## Edge Case Coverage

- [X] CHK012 Are invalid timestamps, missing diarization, unavailable audio, and metadata-loading states addressed? [Coverage, Spec §Edge Cases]
- [X] CHK013 Are keyboard activation requirements covered through player controls and timestamp controls? [Coverage, Contract §Web And Embedded Review UI]
