# UX Checklist: Recording Artifact Format

**Purpose**: Validate user-facing and QA-facing requirements for recording artifact readiness
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are user-facing saved/degraded/failed outcomes preserved after the format change? [Completeness, Spec §FR-009]
- [x] CHK002 Is artifact discovery still required after `Stop` even though file names change? [Completeness, Spec §US1]
- [x] CHK003 Are QA inspection expectations defined without requiring logs or developer-only tools? [Completeness, Spec §US1, Spec §US3]

## Requirement Clarity

- [x] CHK004 Are file names and identifiers required to be safe and content-free? [Clarity, Spec §FR-007]
- [x] CHK005 Is the out-of-scope boundary clear enough that users will not see upload/transcription promises in this slice? [Clarity, Spec §Assumptions]
- [x] CHK006 Are legacy/non-ready artifacts required to be labeled truthfully rather than accepted silently? [Clarity, Spec §FR-012]

## Acceptance Criteria Quality

- [x] CHK007 Are success criteria measurable for locating artifacts and validating format? [Measurability, Spec §SC-001, Spec §SC-002]
- [x] CHK008 Are failure and degraded UX states traceable to concrete reasons? [Coverage, Spec §US3]
- [x] CHK009 Are visible recording state and one-action stop preserved as explicit requirements? [Consistency, Spec §FR-009]
