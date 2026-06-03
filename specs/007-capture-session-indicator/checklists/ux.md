# UX And Visible Control Checklist: Manual Capture Session And Visible Indicator

**Purpose**: Validate visible-state, accessibility, and control requirement quality before implementation
**Created**: 2026-06-01
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is a persistent local visible indicator required for every active recording? [Completeness, Spec §FR-003]
- [x] CHK002 Is one-action stop required for active recording? [Completeness, Spec §FR-002]
- [x] CHK003 Is fail-closed behavior required if all visible indicators disappear? [Completeness, Spec §FR-004]
- [x] CHK004 Are window-close/background scenarios covered? [Coverage, Spec §US2]
- [x] CHK005 Are blocked start and recovery messages required for policy, permission, route, storage, and indicator failures? [Completeness, Spec §FR-014]

## Requirement Clarity

- [x] CHK006 Is active recording copy required to be distinguishable from non-recording passthrough copy? [Clarity, Spec §FR-005]
- [x] CHK007 Is the stop control requirement phrased as one interaction, not vague ease-of-use language? [Clarity, Spec §FR-002]
- [x] CHK008 Are active recording states enumerated clearly enough for UI implementation? [Clarity, Spec §FR-008]
- [x] CHK009 Is color-alone status communication prohibited? [Clarity, Spec §FR-009]

## Accessibility And Localization

- [x] CHK010 Are keyboard navigation and assistive technology requirements present for stop? [Coverage, Spec §FR-009]
- [x] CHK011 Are critical active/blocked/failure states required to have text, not only icons or color? [Coverage, Spec §US2]
- [x] CHK012 Is localization-sensitive copy bounded to concrete blocker categories and actions? [Measurability, Spec §FR-014]

## Consistency

- [x] CHK013 Do visible indicator requirements align with the constitution's no invisible recording rule? [Consistency, Constitution §II]
- [x] CHK014 Do UI requirements avoid implying upload, transcription, summary, or dashboard publication? [Consistency, Contract visible-indicator]
