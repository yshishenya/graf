# Tasks: Production Deployment Plan

**Input**: Design documents from `specs/021-production-deployment-plan/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `.specify/memory/constitution.md`

**Tests**: Included because this feature contains production deployment gates, secret handling, rollback, smoke evidence, and safety boundaries that must be executable and repeatable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: User story label for story phases only.
- Every task includes an exact repository path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the deployment file layout, safe evidence location, and script conventions used by all stories.

- [X] T001 Create deployment documentation directory and README shell in `docs/deployments/2brain-rec/README.md`
- [X] T002 Create production environment template directory in `infra/env/README.md`
- [X] T003 [P] Create deployment helper script directory and conventions in `infra/scripts/README.md`
- [X] T004 [P] Create smoke helper conventions in `apps/server/scripts/README.md`
- [X] T005 [P] Create deployment test fixture package marker in `apps/server/tests/fixtures/deployment.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared production safety primitives that MUST be complete before any user story implementation.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 [P] Add readiness verdict constants and forbidden verdict list in `apps/server/src/twobrain_rec_server/config.py`
- [X] T007 [P] Add deployment evidence forbidden-content patterns in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [X] T008 Add smoke identity configuration fields with production validation in `apps/server/src/twobrain_rec_server/config.py`
- [X] T009 [P] Add deployment evidence fixture builders in `apps/server/tests/fixtures/deployment.py`
- [X] T010 Add production deployment validation module skeleton in `apps/server/src/twobrain_rec_server/deployment.py`
- [X] T011 Add deployment helper unit test skeleton in `apps/server/tests/unit/test_deployment_helpers.py`
- [X] T012 Add deployment readiness contract test skeleton in `apps/server/tests/contract/test_deployment_readiness_contract.py`

**Checkpoint**: Shared constants, validation hooks, and test fixtures are ready for story work.

---

## Phase 3: User Story 1 - Operator Can Prepare The Production Stack (Priority: P1) MVP

**Goal**: The operator can prepare the production stack with a clear Compose layout, secret/env policy, volume boundary, and public/private exposure model for `https://rec.2brain.pro`.

**Independent Test**: Render the production Compose config with dummy non-secret values and review `docs/deployments/2brain-rec/README.md`, `infra/env/rec.production.env.example`, and `infra/docker-compose.yml` to confirm services, ports, volumes, secrets, and dependencies are complete without live values.

### Tests for User Story 1

- [X] T013 [P] [US1] Add contract tests for required secret/env template fields in `apps/server/tests/contract/test_secrets_env_contract.py`
- [X] T014 [P] [US1] Add integration tests for Docker secret declarations and public/private port exposure in `apps/server/tests/integration/test_compose_hardening.py`
- [X] T015 [P] [US1] Add unit tests for production fail-closed secret validation cases in `apps/server/tests/unit/test_config_validation.py`
- [X] T016 [P] [US1] Add documentation exposure tests for deployment docs avoiding live secrets in `apps/server/tests/integration/test_production_docs_exposure.py`

### Implementation for User Story 1

- [X] T017 [US1] Create production env template with placeholders, owners, rotation notes, and required/optional markers in `infra/env/rec.production.env.example`
- [X] T018 [US1] Convert production Compose services from env-only secrets to Docker secrets plus env template references in `infra/docker-compose.yml`
- [X] T019 [US1] Document Rec API public binding, reverse-proxy expectation, and internal-only service exposure in `docs/deployments/2brain-rec/README.md`
- [X] T020 [US1] Document Rec-owned Postgres and MinIO volume ownership, backup inclusion, encryption expectation, restore expectation, and disk-full halt behavior in `docs/deployments/2brain-rec/README.md`
- [X] T021 [US1] Extend production settings validation for Docker secret file presence, unreadable secret files, and dev default rejection in `apps/server/src/twobrain_rec_server/config.py`
- [X] T022 [US1] Implement production config validation CLI for fail-closed preflight checks in `infra/scripts/validate-production-config.sh`
- [X] T023 [US1] Add degraded-awareness config fields for MediaScribe and Langfuse without making them readiness blockers in `apps/server/src/twobrain_rec_server/config.py`
- [X] T024 [US1] Update internal readiness detail to report MediaScribe and Langfuse as degraded-awareness only in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T025 [US1] Record out-of-scope rollout wording and allowed `infra_smoke_ready` verdict language in `docs/deployments/2brain-rec/README.md`

**Checkpoint**: US1 is independently testable through Compose rendering, secret validation, docs review, and readiness contract tests.

---

## Phase 4: User Story 2 - Operator Can Run Migration And Backup Safely (Priority: P1)

**Goal**: The operator can run backup-before-migration, migration verification, and restore/rollback rehearsal with explicit evidence before claiming readiness.

**Independent Test**: Dry-run the runbook scripts in a production-like environment and verify backup evidence exists before migration, restore/rollback rehearsal is recorded, and failed verification blocks `infra_smoke_ready`.

### Tests for User Story 2

- [X] T026 [P] [US2] Add backup-before-migration evidence tests in `apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py`
- [X] T027 [P] [US2] Add migration runbook command tests for blocked and pass outcomes in `apps/server/tests/unit/test_deployment_runbook.py`
- [X] T028 [P] [US2] Add restore/rollback rehearsal verdict contract tests in `apps/server/tests/contract/test_deployment_readiness_contract.py`

### Implementation for User Story 2

- [X] T029 [US2] Implement metadata-only backup evidence template in `docs/deployments/2brain-rec/backup-evidence-template.md`
- [X] T030 [US2] Implement backup helper for Rec Postgres and MinIO metadata references in `infra/scripts/backup-rec-stack.sh`
- [X] T031 [US2] Implement migration verification helper around Alembic state and readiness checks in `infra/scripts/verify-rec-migration.sh`
- [X] T032 [US2] Implement production-like restore rehearsal helper with explicit pass/blocked output in `infra/scripts/rehearse-rec-restore.sh`
- [X] T033 [US2] Implement rollback decision helper for halt, restore, rollback, and blocked outcomes in `infra/scripts/rollback-rec-stack.sh`
- [X] T034 [US2] Document migration preflight, backup-before-change, migration execution, verification, and rollback decision points in `docs/deployments/2brain-rec/migration-runbook.md`
- [X] T035 [US2] Add migration and rollback evidence fields to deployment helper models in `apps/server/src/twobrain_rec_server/deployment.py`

**Checkpoint**: US2 is independently testable through dry-run backup, migration verification, restore rehearsal, and rollback decision evidence.

---

## Phase 5: User Story 3 - Operator Can Perform First Production Smoke (Priority: P1)

**Goal**: The operator can run the first production smoke for the accepted `012` ingest boundary with a dedicated internal smoke identity/device, safe upload, no forbidden side effects, cleanup, and metadata-only evidence.

**Independent Test**: Run the smoke helper against a local production-like endpoint or `https://rec.2brain.pro` using a non-sensitive artifact and confirm health, migration state, Postgres persistence, MinIO persistence, upload finalization, no side effects, log redaction, cleanup, and evidence fields.

### Tests for User Story 3

- [X] T036 [P] [US3] Add smoke evidence schema contract tests in `apps/server/tests/contract/test_smoke_evidence_contract.py`
- [X] T037 [P] [US3] Add smoke identity/device boundary unit tests in `apps/server/tests/unit/test_smoke_identity_seed.py`
- [X] T038 [P] [US3] Add first-smoke ingest boundary integration tests in `apps/server/tests/integration/test_production_smoke_boundary.py`
- [X] T039 [P] [US3] Add smoke cleanup unit tests for database and object residue outcomes in `apps/server/tests/unit/test_smoke_cleanup.py`
- [X] T040 [P] [US3] Add forbidden-content scan tests for evidence and logs in `apps/server/tests/unit/test_deployment_evidence_scan.py`

### Implementation for User Story 3

- [X] T041 [US3] Implement internal smoke identity/device seed helper that never reuses dev seed identity in `apps/server/scripts/seed_smoke_identity.py`
- [X] T042 [US3] Implement production smoke runner for health, readiness, migration state, upload, persistence, side effects, degraded-awareness, and verdict capture in `infra/scripts/run-production-smoke.sh`
- [X] T043 [US3] Implement safe smoke upload wrapper using the existing artifact helper flow in `apps/server/scripts/upload_test_artifact.py`
- [X] T044 [US3] Implement smoke artifact cleanup helper for database records and MinIO objects in `apps/server/scripts/cleanup_smoke_artifacts.py`
- [X] T045 [US3] Implement metadata-only evidence writer and forbidden verdict validation in `apps/server/src/twobrain_rec_server/deployment.py`
- [X] T046 [US3] Implement forbidden-content scan helper for evidence summaries and captured logs in `infra/scripts/scan-deployment-evidence.sh`
- [X] T047 [US3] Create smoke evidence template with all required contract fields in `docs/deployments/2brain-rec/infra-smoke-template.md`
- [X] T048 [US3] Document first production smoke steps, cleanup expectations, and no-side-effect assertions in `docs/deployments/2brain-rec/first-production-smoke.md`

**Checkpoint**: US3 is independently testable through the first-smoke runner and smoke evidence contract.

---

## Phase 6: User Story 4 - Operator Can Roll Back Or Halt Rollout (Priority: P2)

**Goal**: The operator can halt or roll back when health, migration, backup, storage, smoke upload, forbidden-content, unsafe exposure, or cleanup checks fail.

**Independent Test**: Run rollback/halt scenarios in dry-run mode and verify each documented failure class produces `blocked`, `halt`, `restore`, or `rollback` evidence instead of `infra_smoke_ready`.

### Tests for User Story 4

- [X] T049 [P] [US4] Add rollback failure-class coverage tests in `apps/server/tests/unit/test_deployment_rollback_decisions.py`
- [X] T050 [P] [US4] Add integration tests that blocked backup, restore, cleanup, or forbidden log checks prevent `infra_smoke_ready` in `apps/server/tests/integration/test_deployment_readiness_gates.py`
- [X] T051 [P] [US4] Add deployment evidence wording tests that reject `production_ready`, `user_rollout_ready`, and `internal_user_pilot_ready` in `apps/server/tests/contract/test_deployment_readiness_contract.py`

### Implementation for User Story 4

- [X] T052 [US4] Implement rollback/halt trigger mapping for DNS/TLS, secrets, health, migration, backup, storage, disk-full, unsafe exposure, smoke upload, and forbidden-content failures in `apps/server/src/twobrain_rec_server/deployment.py`
- [X] T053 [US4] Extend rollback helper to emit cleanup obligations and residue owner fields in `infra/scripts/rollback-rec-stack.sh`
- [X] T054 [US4] Document rollback/halt scenarios, prior-state references, and truthful status wording in `docs/deployments/2brain-rec/rollback-runbook.md`
- [X] T055 [US4] Add cleanup residue and follow-up wording to deployment evidence README in `docs/deployments/2brain-rec/README.md`

**Checkpoint**: US4 is independently testable through rollback/halt dry-runs and readiness gate tests.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation alignment, and Spec Kit traceability after desired user stories are complete.

- [X] T056 [P] Update current product status with 021 `infra_smoke_ready` boundary and remaining non-ready slices in `docs/current-product-status.md`
- [X] T057 [P] Update PRD trace notes for deployment readiness without expanding user rollout claims in `docs/prd-voice-layer-final.md`
- [X] T058 Run full server validation from quickstart in `apps/server/tests/`
- [X] T059 Run production Compose config validation from quickstart against `infra/docker-compose.yml`
- [X] T060 Run forbidden-content scan across deployment docs and evidence templates in `docs/deployments/2brain-rec/`
- [X] T061 Verify all Spec Kit analysis findings are resolved before implementation closure using `specs/021-production-deployment-plan/tasks.md`

## Phase 8: Review Follow-up Hardening

- [X] T062 [P] [US1] Remove live production secret values from container environment and read runtime credentials from Docker secret files in `apps/server/src/twobrain_rec_server/config.py` and `infra/docker-compose.yml`
- [X] T063 [P] [US2] Replace live volume archive backup with Postgres logical dump and MinIO API mirror backup in `infra/scripts/backup-rec-stack.sh`
- [X] T064 [US2] Implement non-destructive restore rehearsal by restoring the Postgres dump into a temporary database and MinIO objects into a temporary bucket in `infra/scripts/rehearse-rec-restore.sh`
- [X] T065 [P] [US4] Preserve rollback helper remote arguments for trigger, prior-state reference, residue owner, and follow-up fields in `infra/scripts/rollback-rec-stack.sh`
- [X] T066 [US4] Clarify rollback helper as decision/evidence-only unless a separate destructive restore procedure is explicitly chosen in `docs/deployments/2brain-rec/rollback-runbook.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Stories (Phases 3-6)**: Depend on Foundational completion.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational. MVP deployment preparation slice.
- **US2 (P1)**: Can start after Foundational, but final readiness evidence uses US1 secret/config boundaries.
- **US3 (P1)**: Can start after Foundational, but full smoke execution depends on US1 config and US2 backup/restore readiness.
- **US4 (P2)**: Can start after Foundational and can be developed alongside US2/US3, but final validation depends on US2/US3 failure scenarios.

### Within Each User Story

- Tests should be written first and initially fail before implementation.
- Contract and unit tests can usually run before integration tests.
- Scripts and docs should use the same field names as `specs/021-production-deployment-plan/contracts/`.
- Each story reaches a checkpoint before the next readiness claim is made.

---

## Parallel Opportunities

- Setup tasks T003-T005 can run in parallel after T001-T002 are understood.
- Foundational tasks T006-T009 can run in parallel; T010-T012 depend on their file conventions.
- US1 tests T013-T016 can run in parallel; implementation T017-T020 can run in parallel before validation wiring T021-T025.
- US2 tests T026-T028 can run in parallel; scripts T030-T033 can be split by helper file after T029 defines the evidence template.
- US3 tests T036-T040 can run in parallel; helpers T041-T048 can be split by script/module file.
- US4 tests T049-T051 can run in parallel; T052-T055 can be split by code, script, and docs.
- Polish docs T056-T057 can run in parallel before validation tasks T058-T061.

## Parallel Example: User Story 1

```bash
# Contract/integration/unit/doc exposure tests can be created together:
Task: "T013 [P] [US1] Add contract tests for required secret/env template fields in apps/server/tests/contract/test_secrets_env_contract.py"
Task: "T014 [P] [US1] Add integration tests for Docker secret declarations and public/private port exposure in apps/server/tests/integration/test_compose_hardening.py"
Task: "T015 [P] [US1] Add unit tests for production fail-closed secret validation cases in apps/server/tests/unit/test_config_validation.py"
Task: "T016 [P] [US1] Add documentation exposure tests for deployment docs avoiding live secrets in apps/server/tests/integration/test_production_docs_exposure.py"
```

## Parallel Example: User Story 3

```bash
# Smoke runner, cleanup, evidence scan, and evidence template touch separate files:
Task: "T042 [US3] Implement production smoke runner for health, readiness, migration state, upload, persistence, side effects, degraded-awareness, and verdict capture in infra/scripts/run-production-smoke.sh"
Task: "T044 [US3] Implement smoke artifact cleanup helper for database records and MinIO objects in apps/server/scripts/cleanup_smoke_artifacts.py"
Task: "T046 [US3] Implement forbidden-content scan helper for evidence summaries and captured logs in infra/scripts/scan-deployment-evidence.sh"
Task: "T047 [US3] Create smoke evidence template with all required contract fields in docs/deployments/2brain-rec/infra-smoke-template.md"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1.
3. Validate production Compose rendering, secret/env template, private service exposure, and `infra_smoke_ready` wording boundaries.
4. Stop before production smoke until US2 and US3 are complete.

### Deployment-Ready Increment

1. Add US2 backup/migration/restore rehearsal.
2. Add US3 first production smoke and cleanup.
3. Add US4 rollback/halt failure coverage.
4. Run Phase 7 validation and `$speckit-analyze` before implementation is considered ready.

### Safety Boundary

Successful 021 implementation can only produce `infra_smoke_ready`. It must not claim `production_ready`, `user_rollout_ready`, or `internal_user_pilot_ready`.
