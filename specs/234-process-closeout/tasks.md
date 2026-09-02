# Tasks: Process Closeout And Issue Truth

## Phase 1: Identity and allocator

- [X] T001 [P] Update `scripts/claim-feature.py` to use bounded exact GitHub candidate searches and exclude the requested branch from collision detection. (Issue #6374)
- [X] T002 Add regression tests in `tests/governance/test_validator_safety.py` for bounded candidate lookup, branch self-collision and fail-closed timeout behavior. (Issue #6375)

## Phase 2: Truthful issue closeout

- [X] T003 [US2] Add an executable closeout check/runbook under `scripts/` and `docs/agent-guidance/` that rejects unchecked tasks, stale evidence or missing Russian closure comments. (Issue #6376)
- [X] T004 [US2] Reconcile Feature 233 tasks and issue #6363 with exact PR checks and a detailed closure comment. (Issue #6377)

## Phase 3: Agent and PR surfaces

- [X] T005 [US3] Align `.github/pull_request_template.md` and `harness/templates/pull-request.md` with GitHub `governance-fast` authoritative-gate wording and local-CI fallback wording. (Issue #6378)
- [X] T006 [US3] Run Spec Kit/governance validation, update the F234 changelog fragment, and attach exact-SHA evidence to the PR (governance-fast run #33638341407, SHA `99be8f83309ed03de6283a744c880b01682d34cf`). (Issue #6379)

## Dependencies

T001 -> T002 -> T003,T004,T005 -> T006

## Legacy Impact

`untouched`: local CI remains available as explicit fallback. No old alias,
fallback, flag, dependency or fixture is introduced. Legacy deletion remains a
separate follow-up slice after the process is stable.
