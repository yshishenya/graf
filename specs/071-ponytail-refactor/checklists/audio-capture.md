# Audio Capture Checklist: Ponytail Refactor Audit

**Purpose**: Requirement-quality gate for macOS capture-adjacent cleanup boundaries.
**Created**: 2026-06-30
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are capture visibility, one-action stop, track truth, permissions, and local recording safety explicitly preserved? [Plan §Constitution Check]
- [x] CHK002 Are macOS capture and audio-driver cleanup candidates required to use focused Swift/capture validation before completion? [Spec §SC-004]
- [x] CHK003 Are driver/audio proof files treated as high-risk rather than ordinary dead code? [Spec §Edge Cases]

## Requirement Clarity

- [x] CHK004 Is the scope of macOS audit clear enough to separate read-only audit, safe test cleanup, and behavior-changing capture cleanup? [Spec §User Story 3]
- [x] CHK005 Are future driver behavior changes excluded unless a dedicated task and validation note exist? [Spec §SC-005]

## Scenario Coverage

- [x] CHK006 Are hardware/runtime edge cases acknowledged by requiring validation rather than static deletion? [Spec §FR-013]
- [x] CHK007 Are existing safety tests protected from deletion without replacement evidence? [Spec §Edge Cases]

## Notes

- This checklist does not approve capture behavior changes; it ensures the cleanup requirements forbid accidental capture regressions.
