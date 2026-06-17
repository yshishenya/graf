# Contract: Readiness Claim

Feature: `035-mvp-loop-live-evidence`

## Claim Rules

- `production_ready` is out of scope for 035.
- `user_rollout_ready` is forbidden unless a separate accepted rollout gate
  proves it.
- `internal_pilot_candidate` is forbidden while any P0/P1 launch gap remains.
- `mvp_loop_ready` is forbidden while any P0/P1 launch gap remains.
- `pilot_blocked` is required when at least one P0/P1 launch gap remains.
- `infra_smoke_ready` remains the strongest infrastructure-only claim when live
  user journey evidence is incomplete.

## Required Traceability

Every claim must cite:

- readiness report path;
- launch gap register path;
- validation log path;
- command/manual evidence proving or blocking the claim.

## Stale Recommendation Rule

The report and status docs must not recommend a feature already accepted as the
next required slice. If a feature closes a gap, the matrix must remove or
downgrade that gap before recommending the next slice.
