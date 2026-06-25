# Infra And Evidence Requirements Checklist: MVP Live Owner Journey And UI Proof

**Purpose**: Validate production evidence, timing, and release requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are release tag, deployed SHA, production health, and installed app version all included in the proof model? [Completeness, Owner Journey Contract §Required P1 Gates]
- [x] CHK002 Are owner journey gates specified with pass/fail/blocked/unproven/out-of-scope states? [Completeness, Owner Journey Contract §Required P1 Gates]
- [x] CHK003 Are stored outcome category states and counts included as a P1 production proof gate? [Completeness, Spec §FR-004]
- [x] CHK004 Is representative timing evidence specified with audio duration, queue/wait, workflow, provider, finalize-to-review, and result? [Completeness, Timing Contract §Required Fields]

## Requirement Clarity

- [x] CHK005 Is the 180-second-per-hour target stated without allowing extrapolation from short recordings? [Clarity, Spec §FR-005, Timing Contract §Target Rule]
- [x] CHK006 Are `pilot_blocked`, `internal_pilot_candidate`, `user_rollout_ready`, and `production_ready` claim boundaries explicit? [Clarity, Spec §SC-007, Owner Journey Contract §Claim Rules]

## Scenario Coverage

- [x] CHK007 Are no-current-candidate and no-long-timing-candidate cases covered as valid blocked/unproven outcomes? [Coverage, Spec §User Story 2]
- [x] CHK008 Are production health green but owner review unavailable cases covered? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are local fixture/synthetic evidence boundaries separated from production proof? [Consistency, Spec §FR-003]

## Acceptance Criteria Quality

- [x] CHK010 Can local CI, deploy dry-run, execute deploy, and production health checks be objectively tied to release readiness? [Acceptance Criteria, Quickstart §8-10]
