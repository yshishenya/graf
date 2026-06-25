# UX Requirements Checklist: MVP Launch Proof

**Purpose**: Validate review/app interface requirements before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are requirements defined for web cabinet, embedded macOS review, native macOS shell, and mobile-width web surfaces? [Completeness, Spec §User Stories]
- [x] CHK002 Are active tab, transcript-first review, persistent playback, and speaker timeline requirements explicitly covered? [Completeness, Spec §FR-004, §FR-007]
- [x] CHK003 Are server-unavailable and auth-required cabinet states specified for the installed app? [Completeness, Spec §FR-006]
- [x] CHK004 Are Krisp clean-room boundaries specified without allowing copied assets or private screenshots? [Completeness, Spec §FR-008]

## Requirement Clarity

- [x] CHK005 Is "consistent web and embedded review truth" defined with concrete visible states? [Clarity, Spec §US1, §US2]
- [x] CHK006 Is "no overlap or clipping" measurable through horizontal overflow and rendered layout evidence? [Clarity, Spec §SC-003]
- [x] CHK007 Are native capture controls distinguished from server-owned WebKit review content? [Clarity, Spec §US2]

## Scenario Coverage

- [x] CHK008 Are ready, unavailable, missing-session, server-down, mobile, and embedded review scenarios addressed? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are more speakers than the timeline color set and missing review artifacts covered as edge cases? [Coverage, Spec §Edge Cases]

## Acceptance Criteria Quality

- [x] CHK010 Can the UX requirements be validated without reading or committing private meeting content? [Measurability, Spec §FR-009, §SC-002]
