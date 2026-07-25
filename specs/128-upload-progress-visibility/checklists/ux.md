# UX Requirements Checklist: Видимый прогресс загрузки записи

**Purpose**: Validate requirement quality for upload-progress visibility,
accessibility, localization and calm custody UX.

**Created**: 2026-07-25

**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are active upload, finalization, ready, queued, retrying, blocked and missing-measurement states explicitly covered? [Completeness, Spec FR-001–FR-006]
- [X] CHK002 Are single-row and multiple-row presentation boundaries defined without adding a second queue surface? [Completeness, Spec FR-010]
- [X] CHK003 Are visible text, linear indicator and percentage requirements all present rather than relying on color? [Completeness, Spec FR-003, FR-009]

## Requirement Clarity

- [X] CHK004 Is the difference between 100% accepted bytes and `uploaded` stated in observable language? [Clarity, Spec FR-004–FR-005]
- [X] CHK005 Is the rule for omitting the percentage when total bytes are unavailable unambiguous? [Clarity, Spec FR-002, Edge Cases]
- [X] CHK006 Is the scope limited to per-row progress, with ETA, speed, HUD and manual controls explicitly excluded? [Clarity, Spec Assumptions, Out of Scope]

## Requirement Consistency

- [X] CHK007 Are progress visibility rules consistent with the existing automatic-custody/no-manual-retry contract? [Consistency, Spec FR-006, FR-008]
- [X] CHK008 Are accessible labels required to communicate the same state and percentage as the visible row? [Consistency, Spec FR-003, FR-009]

## Acceptance Criteria Quality

- [X] CHK009 Can each measurable outcome be checked across 0%, partial, 100%-before-uploaded and uploaded states? [Measurability, Spec SC-001–SC-003]
- [X] CHK010 Does the success criteria distinguish user comprehension from transport or production acceptance? [Measurability, Spec SC-004, Out of Scope]

## Scenario And Edge Coverage

- [X] CHK011 Are zero progress, missing total, stale snapshot, rapid update and multiple-row cases addressed? [Coverage, Edge Cases]
- [X] CHK012 Are narrow layout, VoiceOver, localization and color-independent states included in the requirements? [Coverage, Spec FR-009, FR-012]
