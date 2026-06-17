# Launch Readiness Requirements Checklist: MVP Loop Live Evidence

**Purpose**: Validate that requirements define launch-readiness claims,
blockers, and next actions without overclaiming.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are all P1 journey classes represented: installed desktop capture, owner web review, readiness claim, and clean-room reference alignment? [Completeness, Spec §User Scenarios]
- [x] CHK002 Are remaining launch gaps required to include severity, affected journey, current evidence, missing evidence, owner area, and next action? [Completeness, Spec §FR-007]
- [x] CHK003 Are accepted claims and excluded claims explicitly modeled? [Completeness, Data Model §ReadinessClaim]
- [x] CHK004 Are status docs and changelog updates required when the strongest claim or next slice changes? [Completeness, Spec §FR-008]

## Requirement Clarity

- [x] CHK005 Is the condition for claiming `mvp_loop_ready` unambiguous? [Clarity, Spec §US3, Contract §Claim Rules]
- [x] CHK006 Is the condition for staying `pilot_blocked` unambiguous when P0/P1 gaps remain? [Clarity, Contract §Claim Rules]
- [x] CHK007 Is the stale recommendation rule explicit enough to prevent recommending already accepted features as next slices? [Clarity, Contract §Stale Recommendation Rule]

## Scenario Coverage

- [x] CHK008 Are both successful live-loop proof and blocked-live-loop outcomes covered by acceptance scenarios? [Coverage, Spec §US3]
- [x] CHK009 Are notes/action output and production user-journey proof treated as possible blockers rather than hidden assumptions? [Coverage, Spec §US2, §US3]

## Acceptance Criteria Quality

- [x] CHK010 Can every P0/P1 blocker be traced to a launch-gap row and evidence path? [Traceability, Spec §SC-006]
- [x] CHK011 Are follow-up slices required when missing behavior is outside 035 scope? [Acceptance Criteria, Spec §FR-012]
