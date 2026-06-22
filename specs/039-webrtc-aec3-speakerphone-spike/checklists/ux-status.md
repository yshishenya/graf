# UX Status Requirements Checklist: WebRTC AEC3 Speakerphone Spike

**Purpose**: Validate requirements for calm in-app recording statuses, fallback visibility, rollback copy, and claim safety before task generation.
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the written requirements and plan artifacts, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are all required app status states enumerated for not evaluated, evaluating, original microphone truth, blocked, promoted, rolled back, fallback-relevant, and user-attention paths? [Completeness, Contract §Required Status States]
- [x] CHK002 Are candidate, problem, rollback, and fallback-relevant states explicitly required to appear in the app? [Completeness, Spec §FR-013a, Spec §SC-013]
- [x] CHK003 Is original microphone truth required to be visible when AEC3 is blocked, unproven, rolled back, or not promoted? [Completeness, Spec §FR-013a, Contract §Copy Rules]
- [x] CHK004 Are Stop visibility and one-action Stop preserved while AEC3 is evaluating, promoted, blocked, or rolled back? [Completeness, Spec §FR-013, Contract §Copy Rules]
- [x] CHK005 Are fallback-relevant states connected to the `040` decision path without implying that AEC3 has succeeded? [Completeness, Spec §User Story 4, Contract §Required Status States]
- [x] CHK006 Are attention states limited to cases where the user can take a clear immediate action? [Completeness, Spec §FR-013c, Contract §Copy Rules]

## Requirement Clarity

- [x] CHK007 Is "calm" status copy clarified through short, route-scoped, non-modal, non-noisy requirements? [Clarity, Spec §FR-013a, Spec §FR-013c, Contract §Copy Rules]
- [x] CHK008 Is status copy required to identify whether the app is using original microphone truth or an accepted promoted candidate when that matters? [Clarity, Spec §FR-013a, Contract §Copy Rules]
- [x] CHK009 Is the promoted status clearly limited to the built-in Mac microphone plus built-in Mac speakers route? [Clarity, Spec §FR-018, Contract §Required Status States]
- [x] CHK010 Are blocked and unproven statuses forbidden from using clean-recording claim words? [Clarity, Contract §Consistency Rules]
- [x] CHK011 Is stale, missing, or contradictory app status explicitly a blocker for immediate promotion? [Clarity, Contract §Consistency Rules, Spec §SC-013]
- [x] CHK012 Is status priority deterministic when active capture, rollback, promoted, blocked, fallback, evaluation, and original-truth states overlap? [Clarity, Contract §Consistency Rules]

## Requirement Consistency

- [x] CHK013 Do app status requirements align with package truth, manifest lineage, rollback events, and diagnostic state? [Consistency, Spec §FR-013a, Contract §Recording Package Lineage, Data Model §AppRecordingStatus]
- [x] CHK014 Do status requirements align with the constitution's visible capture and one-action Stop principles? [Consistency, Constitution §II, Plan §Constitution Check]
- [x] CHK015 Do app status requirements align with the no-private-content rules from diagnostics and evidence contracts? [Consistency, Spec §FR-013b, Contract §Diagnostics]
- [x] CHK016 Do rollback status requirements align with removal of the clean-recording claim after runtime evidence becomes unsafe? [Consistency, Spec §FR-006e, Spec §SC-012, Contract §App Recording Status]
- [x] CHK017 Do fallback-relevant status requirements avoid broadening the 039 route claim or prematurely solving 040? [Consistency, Spec §FR-017, Spec §FR-018]

## Acceptance Criteria Quality

- [x] CHK018 Is app-status success measured across 100% of candidate, problem, rollback, and fallback-relevant states rather than sampled ad hoc? [Measurability, Spec §SC-013]
- [x] CHK019 Are status privacy constraints measurable with zero forbidden private-content tolerance? [Measurability, Spec §FR-013b, Spec §SC-013]
- [x] CHK020 Are status/action requirements measurable enough to distinguish informational states from action-required states? [Measurability, Contract §Required Status States]
- [x] CHK021 Is status consistency with package truth measurable enough to block immediate promotion when status and manifest disagree? [Measurability, Contract §Consistency Rules]

## Edge Case Coverage

- [x] CHK022 Are stale, noisy, overly technical, inconsistent, fallback, rollback, Stop, and route-change status edge cases represented? [Coverage, Spec §Edge Cases]
- [x] CHK023 Are blocked-route, blocked-quality, blocked-stability, and dependency-blocked problems visible without exposing technical internals? [Coverage, Spec §FR-013a, Contract §Copy Rules]
- [x] CHK024 Are runtime recovery states covered after a candidate was promoted and then became unsafe? [Coverage, Recovery Flow, Spec §FR-006e, Spec §SC-012]
- [x] CHK025 Are supporting-route statuses prevented from implying clean speakerphone recording for non-built-in routes? [Coverage, Spec §FR-011, Spec §FR-018]
- [x] CHK026 Are Stop/quit paths covered so status visibility cannot hide active capture or block user control? [Coverage, Spec §FR-013, Quickstart §Controlled Real-Hardware App Recording Matrix]

## Dependencies & Assumptions

- [x] CHK027 Are app status requirements grounded in existing app surfaces rather than introducing a new noisy notification system? [Assumption, Plan §Primary Dependencies, Contract §Copy Rules]
- [x] CHK028 Are localization-sensitive claim words covered at least for English and Russian clean-recording variants? [Assumption, Contract §Consistency Rules]
- [x] CHK029 Are status requirements scoped to local app display and metadata evidence, not participant-facing notice policy? [Dependency, Constitution §II, Spec §FR-013a]

## Notes

- 2026-06-22: Passed after adding explicit no-noisy-alert requirements, deterministic priority, and rollback/fallback visibility rules.
