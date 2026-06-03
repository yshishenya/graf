# Driver And Audio Checklist: Recording Artifact Format

**Purpose**: Validate recording/audio requirements before implementation changes touch local capture artifacts
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are required track roles defined as separate local microphone and incoming/remote audio artifacts? [Completeness, Spec §FR-001]
- [x] CHK002 Is the required WAV format fully specified: PCM signed 16-bit little-endian, mono, 16000 Hz? [Completeness, Spec §FR-002]
- [x] CHK003 Are timeline requirements defined for shared `t=0`, silence preservation, and no VAD trimming? [Completeness, Spec §FR-004]
- [x] CHK004 Are late-start, dropout, and format finalization edge cases represented? [Coverage, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK005 Is the MediaScribe role mapping clear enough to avoid file-name guessing in future backend ingest? [Clarity, Spec §FR-003, Spec §FR-005]
- [x] CHK006 Are degraded/failed conditions defined for missing, empty, misaligned, or incorrectly formatted tracks? [Clarity, Spec §FR-006]
- [x] CHK007 Are existing pre-010 artifacts clearly classified as legacy/not transcription-ready? [Clarity, Spec §FR-012]

## Consistency And Safety

- [x] CHK008 Do requirements preserve the driver-first separate-track product promise? [Consistency, Constitution §I]
- [x] CHK009 Do requirements avoid putting conversion or file work into HAL/Core Audio callbacks? [Consistency, Plan §Constraints]
- [x] CHK010 Are existing `007` visible indicator and `008` saved/degraded truth gates preserved? [Consistency, Spec §FR-009, Spec §SC-006]
