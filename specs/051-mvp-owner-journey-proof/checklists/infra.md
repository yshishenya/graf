# Infra And Evidence Requirements Checklist: MVP Owner Journey Proof

**Purpose**: Validate production evidence and deployment requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are production health, deployed SHA, release tag, and installed app version all included in the evidence model? [Completeness, Data Model §MVP Owner Journey Evidence Pack]
- [x] CHK002 Are owner journey gates specified with pass/fail/blocked/unproven states? [Completeness, Spec §FR-002, Contract §Required P1 Gates]
- [x] CHK003 Are stored outcome category states and counts included as a P1 production proof gate? [Completeness, Spec §FR-006, Data Model §Stored Outcome Proof]
- [x] CHK004 Is representative timing evidence specified with audio duration, queue/wait, processing, finalize-to-review, and target result? [Completeness, Timing Contract]

## Requirement Clarity

- [x] CHK005 Is the three-minute-per-hour timing target stated without allowing extrapolation from short recordings? [Clarity, Spec §FR-008, Timing Contract]
- [x] CHK006 Are `pilot_blocked`, `internal_pilot_candidate`, `production_ready`, and `user_rollout_ready` claim boundaries explicit? [Clarity, Spec §FR-017, §FR-018, §SC-008]

## Scenario Coverage

- [x] CHK007 Are delayed, duplicated, unavailable, or stuck processing cases covered? [Coverage, Edge Cases]
- [x] CHK008 Are unproven timing and missing-outcomes cases allowed to remain visible blockers? [Coverage, Spec §US2, §US3]

## Acceptance Criteria Quality

- [x] CHK009 Can local CI and production deploy/smoke gates be objectively checked before claiming release/deploy completion? [Acceptance Criteria, Spec §SC-009, Quickstart §8-9]
