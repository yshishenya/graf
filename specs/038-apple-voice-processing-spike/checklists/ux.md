# UX And Control Requirements Checklist: Apple Voice Processing Spike

**Purpose**: Validate visible-control, user guidance, and product-copy requirements before tasks and implementation
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are visible active-capture and one-action Stop requirements defined for every Apple processing path? [Completeness, Spec §FR-013]
- [x] CHK002 Are user-facing clean-recording claims blocked unless all evidence gates pass? [Completeness, Spec §SC-006]
- [x] CHK003 Are guidance-only outcomes defined separately from accepted recording behavior? [Completeness, Spec §FR-002, Research §Decision: Treat Mic Modes As Guidance]
- [x] CHK004 Are next-step recommendations required for blocked or unproven outcomes? [Completeness, Spec §SC-005]

## Requirement Clarity

- [x] CHK005 Is the product boundary clear that Apple processing availability does not equal clean speakerphone support? [Clarity, Spec §Program Context]
- [x] CHK006 Are Mic Mode/Voice Isolation requirements clear about user/system control and no hidden setting changes? [Clarity, Spec §FR-014]
- [x] CHK007 Are route-change and user setting changes required to state whether the conclusion is invalidated, narrowed, or preserved? [Clarity, Spec §US3]

## Acceptance Criteria Quality

- [x] CHK008 Are user-facing/release-facing wording requirements objectively measurable as zero false clean claims? [Acceptance Criteria, Spec §SC-006]
- [x] CHK009 Can outcome selection be objectively reviewed as exactly one primary state? [Measurability, Spec §US4, Data Model §AppleProcessingOutcome]
- [x] CHK010 Are accepted, blocked, guidance-only, and deferred outcomes traceable enough for PR/release notes? [Traceability, Contract §Apple Processing Spike Result]

## Scenario Coverage

- [x] CHK011 Are Stop/quit scenarios included so candidate processing cannot continue invisibly? [Coverage, Quickstart §Manual Runtime Matrix]
- [x] CHK012 Are browser meeting scenarios included so user-facing claims are not based only on synthetic playback? [Coverage, Spec §FR-007]
- [x] CHK013 Are fallback paths to `039` and `040` represented for non-accepted Apple outcomes? [Coverage, Spec §US4]

## Notes

- Checklist is complete after reviewing `spec.md`, `research.md`, `data-model.md`,
  and `quickstart.md`.
