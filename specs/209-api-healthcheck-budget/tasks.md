# Tasks: API Healthcheck Budget

**Input**: Design documents from `specs/209-api-healthcheck-budget/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api-healthcheck.md`, `quickstart.md`

**Tests**: High-risk infrastructure lane requires a RED/GREEN contract check, rendered Compose validation, the fast PR gate, and the full exact-SHA production gate.

## Phase 1: User Story 1 — Не откатывать исправный API из-за слишком короткой проверки (Priority: P1) 🎯 MVP

**Goal**: Признать API healthy при успешном readiness-ответе в согласованном bounded budget, не ослабляя endpoint, failure semantics или rollback.

**Independent Test**: Existing Compose contract pins `/api/v1/health/ready`, request timeout `8`, runner timeout `10s`, unchanged interval/retries; guarded production rollout reaches healthy or rolls back only on real unready state.

### Tests for User Story 1

- [X] T001 [US1] Extend `test_production_compose_api_has_healthcheck_and_localhost_bind_policy` with RED assertions for the 8-second request budget and 10-second runner budget in `apps/server/tests/integration/test_compose_hardening.py`

### Implementation for User Story 1

- [X] T002 [US1] Set the existing API readiness request timeout to 8 seconds and Docker healthcheck timeout to 10 seconds without changing route, interval, retries, or rollback semantics in `infra/docker-compose.yml`
- [X] T003 [US1] Record the Feature 209 deployment healthcheck fix in the existing `2026.08.28.11` release section of `CHANGELOG.md`, then run the focused pytest contract, rendered Compose check, and `infra/scripts/ci-local.sh --fast`

**Checkpoint**: The repository contract and fast gate prove the minimal timeout correction before PR.

---

## Phase 2: Release And Production Proof

**Purpose**: Prove the merged exact SHA through the repository-owned release path.

- [ ] T004 Run full exact-SHA validation, `infra/scripts/cd-remote.sh --dry-run --branch master`, approved `--execute`, and metadata-only production checks for live, ready, container health, rollback status, and YooKassa test-shop configuration according to `specs/209-api-healthcheck-budget/quickstart.md`

---

## Dependencies & Execution Order

- T001 must fail against the old `3`/`5s` values before T002.
- T002 makes T001 green.
- T003 depends on T001 and T002 and is the PR gate.
- T004 depends on the reviewed PR being merged into a clean synchronized `master`; any new candidate SHA invalidates earlier full-CI evidence.

## Parallel Opportunities

None. The four tasks form one short dependency chain and intentionally touch shared release state serially.

## Implementation Strategy

1. Add the two assertions to the existing contract and capture RED.
2. Change only the two timeout values and capture GREEN.
3. Update the existing release changelog and pass focused, rendered Compose, and fast CI checks.
4. Merge through PR, then deploy only the exact synchronized master SHA through the guarded full-CI path.

## Notes

- Risk / validation lane: high-risk infrastructure and release/deploy blocker.
- No new helper, abstraction, dependency, endpoint, migration, billing change, or manual production edit is in scope.
- T004 remains open until production evidence exists; PR closeout must not claim deploy success early.
