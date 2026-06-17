# Contract: Readiness Claim Update

Feature: `036-owner-review-live-polish`

## Purpose

Keep readiness, current product status, changelog, evidence, tasks, and issues
aligned after 036.

## Required Outputs

- `docs/evidence/036-owner-review-live-polish/README.md`
- `docs/evidence/036-owner-review-live-polish/validation-log.md`
- `docs/evidence/036-owner-review-live-polish/readiness-report.json`
- `docs/evidence/036-owner-review-live-polish/readiness-report.md`
- `docs/evidence/036-owner-review-live-polish/launch-gap-register.md`
- `docs/evidence/036-owner-review-live-polish/clean-room-reference.md`
- Updated `docs/current-product-status.md`
- Updated `CHANGELOG.md`

## Claim Rules

1. `mvp_loop_ready` remains excluded if owner review, notes/actions, or an
   equivalent P1 value-loop gap remains open.
2. `internal_pilot_candidate` remains excluded unless accepted live owner
   journey evidence or explicit narrower pilot guardrails exist.
3. `user_rollout_ready` and `production_ready` remain excluded unless separate
   rollout evidence exists.
4. Closed 036 gaps must not remain listed as future work.
5. New blockers discovered during live proof must be listed with severity,
   journey, missing evidence, and next action.

## Validation

The final closeout must run focused readiness tests, canonical local CI, macOS
build/tests when desktop code changes, forbidden-content scans, `git diff
--check`, and GitHub issue/task reconciliation.
