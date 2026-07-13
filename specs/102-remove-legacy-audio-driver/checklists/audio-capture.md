# Audio Capture Requirements Checklist: Remove Legacy Separate Audio Driver

**Purpose**: Validate that requirements fully protect the accepted current recording graph and user-control guarantees
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are both supported inputs—ScreenCaptureKit incoming audio and app-owned microphone samples—explicitly defined as retained? [Completeness, Spec §FR-009, Contract §current-recording-path]
- [x] CHK002 Are dual original tracks, manifest truth, permission state, visible capture, and one-action Stop all named as non-regression requirements? [Completeness, Spec §FR-010]
- [x] CHK003 Are current meter ownership and source semantics specified so deleting the legacy signal type cannot remove live recording feedback? [Completeness, Contract §current-recording-path]
- [x] CHK004 Are manual, meeting-detection-assisted, permission-blocked, source-failure, and stop/finalization flows all inside the preserved boundary? [Coverage, Spec §User Story 2]

## Requirement Clarity and Consistency

- [x] CHK005 Is “behaviorally unchanged” decomposed into objectively observable graph, artifact, control, and diagnostic contracts? [Clarity, Spec §SC-004–SC-006]
- [x] CHK006 Is the requirement to remove route eligibility consistent with the requirement to retain generic physical route/leakage metadata? [Consistency, Research §Decisions 4 and 6]
- [x] CHK007 Is current permission truth defined without conflating microphone permission with system-audio permission? [Clarity, Spec §FR-010, Contract §current-recording-path]

## Acceptance Criteria Quality

- [x] CHK008 Is the before/after regression baseline quantified by named suites and expected zero-failure evidence? [Measurability, Plan §Validation Plan]
- [x] CHK009 Are artifact acceptance criteria specific about roles, source independence, format/schema stability, and failure truth? [Measurability, Contract §current-recording-path]
- [x] CHK010 Are resource and performance requirements sufficient to prevent driver deletion from masking a current capture leak or callback regression? [Non-Functional, Plan §Performance Goals]

## Exception and Recovery Coverage

- [x] CHK011 Are requirements defined for denied permissions, missing/unproven microphone input, ScreenCaptureKit start failure, storage risk, and indicator loss? [Coverage, Spec §User Story 2]
- [x] CHK012 Is recovery copy required to use current capture actions and explicitly forbidden from recommending driver repair? [Clarity, Spec §US2 Acceptance 3]
- [x] CHK013 Is the current AVAudioRecorder fallback distinguished from the removed HAL driver so compatibility cleanup cannot delete it accidentally? [Assumption, Data Model §Compatibility decisions]

## Notes

- Capture requirements are sufficiently specific for implementation and regression review.
