# UX Requirements Checklist: macOS Real Bidirectional Passthrough

**Purpose**: Validate visible state, recovery, accessibility, and brand-distance requirement quality
**Created**: 2026-05-31
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is active live passthrough required to be visible and distinct from recording? [Completeness, Spec §FR-007]
- [x] CHK002 Is a user-triggered recheck action required for stale, degraded, failed, and blocked states? [Completeness, Spec §FR-017]
- [x] CHK003 Are recovery actions required for microphone and speaker path failures? [Coverage, User Stories 1-2]
- [x] CHK004 Are non-color-only and localization-safe UI requirements included? [Completeness, Constitutional Requirements]

## Requirement Clarity

- [x] CHK005 Is the feature clear that live passthrough is non-recording? [Clarity, Spec §FR-006, §FR-007]
- [x] CHK006 Is "blocked/not accepted" browser copy constrained to avoid implying support? [Clarity, Contract browser-call]
- [x] CHK007 Are stale route states distinguishable from failed and degraded states? [Clarity, Data Model]

## Brand And Accessibility

- [x] CHK008 Is copied Krisp UI/copy explicitly prohibited? [Brand Distance, Spec §FR-018]
- [x] CHK009 Are accessible state labels and keyboard-reachable controls required if UI is changed? [Accessibility, Constitutional Requirements]
- [x] CHK010 Does the spec avoid using visible text to over-explain internal implementation? [Clarity]

## Scenario Coverage

- [x] CHK011 Are route change, app crash, `coreaudiod` restart, and browser stale-device recovery flows covered? [Coverage, User Story 4]
- [x] CHK012 Is the user protected from a silent broken call route through fail-closed and recovery states? [Coverage, Spec §FR-008, §FR-017]
