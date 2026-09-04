# Tasks: Полноценная изолированная Dev-среда GRAF

**Input**: Design documents from `specs/229-dev-runtime-full-stack/`

**Prerequisites**: `spec.md`, `clarifications.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/dev-runtime.v1.md`, `quickstart.md` and reviewer-
owned checklists.

**Tests**: Required by the `high-risk-feature` lane. Contract and negative tests
must be written before implementation tasks in each story where practical.

**Source boundary**: immutable-image hardening is based on current
`origin/master` SHA `b0c06935bc1af90be6f92981357a61af3d80bb19`; the original
F229 slice began from F227 SHA `836cbba8f1c53695dd9e06a21f58bf74365286ef`.
Root `CHANGELOG.md`, production Compose, production data and unrelated feature
contexts are not owned.

## Phase 1: Setup

**Purpose**: freeze the feature contract and create isolated test fixtures.

- [X] T001 Record Feature 229, issue #6276, base SHA and `high-risk-feature` lane in `specs/229-dev-runtime-full-stack/plan.md` and `.specify/feature.json` (Issue #6277).
- [X] T002 [P] Add the owned metadata-only changelog fragment in `changes/unreleased/F229.yaml` (Issue #6278).
- [X] T003 [P] Add clean, empty, mismatch and production-boundary fixtures in `tests/governance/fixtures/feature_229/` (Issue #6279).
- [X] T004 [P] Add the v1 runtime contract fixtures and malformed examples in `tests/governance/fixtures/feature_229/runtime/` (Issue #6280).

## Phase 2: Foundational contracts

**Purpose**: establish boundaries that every user story depends on.

**Checkpoint**: no story implementation begins until these contracts and the
reviewer-owned infra/security checklist are accepted.

- [X] T005 Add the GRAF-specific service, namespace, readiness and transaction contract to `specs/229-dev-runtime-full-stack/contracts/dev-runtime.v1.md` and `infra/dev/manifest.schema.json` (Issue #6281).
- [X] T006 [P] Write contract tests for manifest/component SHA equality, Dev app identity, loopback origins and metadata-only evidence in `tests/governance/test_dev_runtime.py` (Issue #6282).
- [X] T007 [P] Write migration preflight unit/fixture tests for empty, matching, unknown, multiple-head and divergent states in `tests/governance/test_dev_migration_preflight.py` (Issue #6283).
- [X] T008 [P] Write production-boundary and namespace collision tests in `tests/governance/test_dev_runtime_isolation.py` (Issue #6284).
- [X] T009 Define reviewer-owned requirement, infra and security checklists in `specs/229-dev-runtime-full-stack/checklists/requirements.md`, `checklists/infra.md` and `checklists/security.md`; leave all reviewer markers unchecked (Issue #6285).

## Phase 3: User Story 1 — Полный стек на одном SHA (Priority: P1) 🎯 MVP

**Goal**: one exact-SHA `build → promote → smoke` run starts and proves the
server-rendered frontend, API, Temporal, processing worker, media worker,
Postgres and MinIO without manual service orchestration.

**Independent Test**: on a clean disposable Dev state, run the commands from
`quickstart.md`; every required readiness check passes and every component
reports the requested SHA.

### Tests for User Story 1

- [X] T010 [P] [US1] Add Compose service-graph, loopback-port and healthcheck contract tests in `tests/governance/test_dev_compose_contract.py` (Issue #6286).
- [X] T011 [P] [US1] Add exact-SHA image/app/runtime identity tests in `tests/governance/test_dev_runtime_identity.py` (Issue #6287).
- [X] T012 [P] [US1] Add live-smoke check coverage tests for API, `/login`, Temporal, processing worker and media worker in `tests/governance/test_dev_live_smoke.py` (Issue #6288).

### Implementation for User Story 1

- [X] T013 [US1] Make the full service graph and explicit Dev namespace/loopback bindings reproducible in `infra/docker-compose.dev.yml` (Issue #6289).
- [X] T014 [US1] Add the bounded full-stack startup path with migration-before-readiness ordering in `infra/scripts/start-dev-runtime.sh` (Issue #6290).
- [X] T015 [US1] Add migration graph/database-state preflight with fail-closed diagnostic output in `infra/scripts/dev-migration-preflight.py` (Issue #6291).
- [X] T016 [US1] Extend the GRAF adapter to build the Dev Compose images, pass source-SHA metadata and verify every running service in `scripts/dev-harness.py` (Issue #6292).
- [X] T017 [US1] Extend live smoke to require named Temporal, processing-worker, media-worker and exact-SHA checks in `scripts/dev-harness.py` (Issue #6293).
- [X] T018 [US1] Add only the minimal server/container source-SHA metadata needed for runtime verification in `infra/server/Dockerfile` and existing health modules (Issue #6294).

**Checkpoint**: US1 is independently demonstrable with a clean-state live
smoke; provider calls remain disabled unless separately configured.

## Phase 4: User Story 2 — Изоляция состояния и безопасные миграции (Priority: P1)

**Goal**: Dev cannot touch production or old local state, and an incompatible
migration is blocked before API/workers readiness without destructive repair.

**Independent Test**: mismatch and boundary fixtures fail closed while old state
and production app/data fingerprints remain unchanged.

### Tests for User Story 2

- [X] T019 [P] [US2] Add tests proving old local volumes, production paths, public origins and credentials are rejected in `tests/governance/test_dev_runtime_isolation.py` (Issue #6295).
- [X] T020 [P] [US2] Add integration tests proving migration mismatch blocks API/worker readiness and emits an actionable metadata-only result in `tests/governance/test_dev_migration_preflight.py` (Issue #6296).
- [X] T021 [P] [US2] Add negative tests forbidding `alembic stamp`, direct `alembic_version` edits and `docker compose down -v` in `tests/governance/test_dev_safety_guards.py` (Issue #6297).

### Implementation for User Story 2

- [X] T022 [US2] Add explicit Compose project, volume, network, port and state-root derivation with production-looking path rejection in `scripts/dev-harness.py` and `infra/docker-compose.dev.yml` (Issue #6298).
- [X] T023 [US2] Route all Dev migration/startup operations through the preflight and preserve the historical local path as non-active in `infra/scripts/start-dev-runtime.sh` and `infra/dev/README.md` (Issue #6299).
- [X] T024 [US2] Ensure provider credentials/endpoints cannot bleed into the local adapter or app environment in `scripts/dev-harness.py` and `apps/macos/Scripts/build-dev-app.sh` (Issue #6300).
- [X] T025 [US2] Record metadata-only migration outcome and safe-new-state instructions under the Dev state contract in `infra/dev/manifest.schema.json` and `infra/dev/README.md` (Issue #6301).

**Checkpoint**: isolation and mismatch behavior are independently testable with
no production mutation and no manual revision repair.

## Phase 5: User Story 3 — Атомарная promotion и rollback (Priority: P1)

**Goal**: one machine-local Dev app/runtime can be promoted or rolled back as a
single transaction, with previous state recoverable after any injected failure.

**Independent Test**: two valid candidates plus failures at staging, install,
runtime-start and smoke leave the previous candidate active; valid rollback
returns to smoke PASS.

### Tests for User Story 3

- [X] T026 [P] [US3] Add promotion lock, stale-parent and pointer-commit tests in `tests/governance/test_dev_promotion_transaction.py` (Issue #6302).
- [X] T027 [P] [US3] Add failure-injection compensation tests for app/runtime snapshots and unowned PID refusal in `tests/governance/test_dev_promotion_transaction.py` (Issue #6303).
- [X] T028 [P] [US3] Add exact-target rollback and post-rollback smoke tests in `tests/governance/test_dev_rollback.py` (Issue #6304).

### Implementation for User Story 3

- [X] T029 [US3] Integrate Compose project stop/start, runtime ownership and service identity into the existing lock-protected promotion path in `scripts/dev-harness.py` (Issue #6305).
- [X] T030 [US3] Preserve one `/Applications/GRAF Dev.app`, stable `pro.2brain.graf.dev` identity and atomic staged replacement in `apps/macos/Scripts/install-dev-app.sh` (Issue #6306).
- [X] T031 [US3] Commit the active pointer only after full smoke and implement compensation/rollback for every failed promotion stage in `scripts/dev-harness.py` (Issue #6307).
- [X] T032 [US3] Require exact checkout SHA and the same smoke contract for rollback in `scripts/dev-harness.py` and `infra/dev/README.md` (Issue #6308).

**Checkpoint**: one active manifest/app/runtime is restored or the operation is
truthfully marked `rollback_required`; no unowned process is signalled.

## Phase 6: Polish, documentation and validation

**Purpose**: make the process usable by agents and operators without context
growth or release confusion.

- [X] T033 [P] Update the concise Dev operator instructions and blocked-state table in `infra/dev/README.md` and `docs/agent-guidance/local-development.md` (Issue #6309).
- [X] T034 [P] Add metadata-only evidence examples and production-before/after fingerprint procedure to `specs/229-dev-runtime-full-stack/quickstart.md` (Issue #6310).
- [X] T035 [P] Add governance validation for Feature 229 ownership, no root `CHANGELOG.md` edits and no secret/private-content evidence in `scripts/validate-dev-runtime.py` and `tests/governance/test_dev_runtime.py` (Issue #6311).
- [X] T036 Re-run `$speckit-analyze` after immutable-image hardening and resolve all critical/high findings, recording the append-only result in `specs/229-dev-runtime-full-stack/analysis.md` without changing reviewer-owned checklist markers (Issue #6493).
- [X] T037 Re-run `$speckit-taskstoissues`, verify a canonical owner for T041 and no duplicate task issues for T001–T041; record the link in `specs/229-dev-runtime-full-stack/issue-links.md` (Issue #6494).
- [X] T038 Re-run the quickstart contract/negative tests, Compose/shell/Python checks and the required GitHub `governance-fast` gate on the exact hardened implementation SHA; record metadata-only evidence (Issue #6495).
- [X] T039 Fix the live presentation regression, then execute one clean-state macOS live smoke and injected-failure rollback rehearsal on the final exact implementation SHA; prove the running app is `GRAF Dev` with channel `dev` and the Dev-badged icon, and verify `/Applications/GRAF.app` and production data are unchanged before declaring the feature ready (Issue #6496).
- [X] T040 Re-run `$speckit-converge` append-only after T041–T039; leave any missing remote/operator gate open with a Russian status comment on issue #6276 (Issue #6497).
- [X] T041 [US3] Pin candidate, compensation and rollback Compose services to immutable image IDs recorded by the selected manifest, require those IDs in the direct runtime entrypoint, block before stopping the active runtime when an image is missing/mismatched, verify actual container image IDs after startup, and add regression coverage in `scripts/dev-harness.py`, `infra/docker-compose.dev.yml`, `infra/scripts/start-dev-runtime.sh`, `infra/dev/manifest.schema.json`, `tests/governance/test_dev_rollback.py`, `tests/governance/test_dev_runtime.py`, `tests/governance/test_dev_compose_contract.py` and `tests/governance/test_graf_local_adapter.py` (Issue #6411).

## Dependencies & Execution Order

```text
T001–T004 → T005–T009 → T010–T018 → T019–T025 → T026–T032
T032 → T033–T035 → T037(issue sync for T041) → T041 → T036 → T038 → T039 → T040
```

- Setup and foundational contracts must complete before any story.
- US1 is the MVP and must prove full-stack readiness before isolation/rollback
  claims are accepted.
- US2 depends on the runtime namespace/preflight contracts in US1.
- US3 depends on a known-good full-stack smoke but its failure tests can be
  prepared in parallel with US2.
- Documentation tasks T033–T035 can run in parallel after contracts stabilize.
- The immutable-image follow-up is tracked before implementation; its analyze,
  exact-SHA GitHub validation, live rehearsal and convergence gates remain
  sequential and cannot reuse pre-hardening evidence.

## Parallel execution examples

After Phase 1, T006, T007 and T008 may run in parallel because they own separate
test files. In US1, T010, T011 and T012 may run in parallel. In US2, T019–T021
may run in parallel. In US3, T026–T028 may run in parallel. No two agents may
edit the same feature file, root `AGENTS.md` or root `CHANGELOG.md`.

## Implementation Strategy

1. **MVP**: complete foundational contracts and US1; prove full stack on one
   exact SHA with clean-state smoke.
2. **Safety**: complete US2; prove isolation and migration fail-closed behavior.
3. **Recovery**: complete US3; prove atomic promotion and rollback.
4. **Operator handoff**: documentation, analyze, task-to-issue sync, focused
   fast CI and live evidence.
5. Full CI and production release remain owned by the later release-train gate,
   not by this feature.

## Legacy Impact

Classification: `retain-with-exception`

The old processing-disabled `start-local.sh`-only live adapter is retained only
as a non-active, bounded exception until T038–T039 pass and operator cutover.
Feature 228 owns its later removal. No new caller, compatibility fallback,
duplicate app, per-worktree live runtime or shared old volume may be added.

owner: `dev-runtime`

expiry: 2026-10-31

removal trigger: full-stack adapter reaches clean-state smoke PASS and rollback
evidence; then Feature 228 retirement review

retirement task: Feature 228 issue #6238, task T000; this feature only changes the active adapter

risk: an incomplete adapter can produce a misleading green result while worker
or Temporal paths are disabled

validation: exact-SHA identity, isolation, migration mismatch, smoke and
failure-injection rollback tests

reason: keep the incomplete path available only for controlled rollback and
diagnosis while the full-stack adapter is validated; do not add new use of it.
