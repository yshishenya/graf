# Tasks: Deep Architecture Audit

**Input**: Design documents from `/specs/072-deep-architecture-audit/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: 072 is a significant architecture / high-risk read-only audit. Tests
are artifact validation and consistency checks in this stage. Runtime tests are
listed as gates for later refactor batches, not executed as 072 deploy proof.

**Organization**: Tasks are grouped by user story and keep product/runtime code
read-only in stage one.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different audit docs.
- **[Story]**: Which user story this task supports.
- Every task includes exact repository paths.

## Phase 1: Setup And Guardrails

**Purpose**: Anchor the slice and prevent accidental implementation work.

- [X] T001 Record the selected lane as significant architecture / high-risk read-only audit in `specs/072-deep-architecture-audit/plan.md`.
- [X] T002 Confirm 072 is anchored from a clean worktree based on fresh `origin/master` and record the decision in `specs/072-deep-architecture-audit/research.md`.
- [X] T003 Update the Spec Kit context pointer in `AGENTS.md` to `specs/072-deep-architecture-audit/plan.md`.
- [X] T004 [P] Keep all 072 audit deliverables under `specs/072-deep-architecture-audit/` except the managed `AGENTS.md` plan pointer.
- [X] T005 [P] Ensure `specs/072-deep-architecture-audit/quickstart.md` states no production deploy and no product/runtime code changes for stage one.

## Phase 2: Foundational Audit Contracts

**Purpose**: Define evidence contracts before interpreting architecture risks.

- [X] T006 [P] Define architecture finding fields in `specs/072-deep-architecture-audit/contracts/architecture-finding-contract.md`.
- [X] T007 [P] Define dependency graph evidence fields in `specs/072-deep-architecture-audit/contracts/dependency-graph-contract.md`.
- [X] T008 [P] Define runtime flow evidence fields in `specs/072-deep-architecture-audit/contracts/runtime-flow-contract.md`.
- [X] T009 [P] Define future refactor batch fields in `specs/072-deep-architecture-audit/contracts/refactor-batch-contract.md`.
- [X] T010 Model audit entities and relationships in `specs/072-deep-architecture-audit/data-model.md`.

**Checkpoint**: Evidence shape is stable before writing findings or roadmap.

## Phase 3: User Story 1 - Map Real Architecture (Priority: P1)

**Goal**: Build a repository-backed map of architecture, dependencies, and
runtime flows before any refactor.

**Independent Test**: A reviewer can follow `quickstart.md`, inspect audit docs,
and verify that all required product surfaces are represented without changing
runtime code.

- [X] T011 [P] Capture server surfaces and hotspots in `specs/072-deep-architecture-audit/audit/architecture-map.md` from `apps/server/src/twobrain_rec_server/`.
- [X] T012 [P] Capture macOS targets and hotspots in `specs/072-deep-architecture-audit/audit/architecture-map.md` from `apps/macos/Package.swift`, `apps/macos/RecApp/`, `apps/macos/Shared/`, and `apps/macos/AudioDriver/`.
- [X] T013 [P] Capture infra/script/runtime surfaces in `specs/072-deep-architecture-audit/audit/architecture-map.md` from `infra/` and `apps/macos/Scripts/`.
- [X] T014 [P] Capture docs/spec baseline surfaces in `specs/072-deep-architecture-audit/audit/architecture-map.md` from `docs/` and `specs/`.
- [X] T015 [P] Document Python server dependency graph in `specs/072-deep-architecture-audit/audit/dependency-graphs.md`.
- [X] T016 [P] Document Swift package target graph in `specs/072-deep-architecture-audit/audit/dependency-graphs.md`.
- [X] T017 [P] Document shell/infra entrypoint graph in `specs/072-deep-architecture-audit/audit/dependency-graphs.md`.
- [X] T018 [P] Document Docker/runtime dependency graph in `specs/072-deep-architecture-audit/audit/dependency-graphs.md`.
- [X] T019 [P] Document capture-to-local-package flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T020 [P] Document local-package-to-upload/ingest flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T021 [P] Document ingest-to-processing/MediaScribe flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T022 [P] Document cabinet/review/WebView flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T023 [P] Document deletion/export/local-purge flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T024 [P] Document support/diagnostics flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md`.
- [X] T025 [P] Document release/deploy flow in `specs/072-deep-architecture-audit/audit/runtime-flows.md` without executing deploy.

**Checkpoint**: Architecture and flow map can be reviewed independently.

## Phase 4: User Story 2 - Classify Architecture Risks (Priority: P1)

**Goal**: Classify each architecture risk as `delete now`, `split soon`,
`keep intentionally`, or `risky / needs spec`.

**Independent Test**: Every finding in `findings-register.md` has exact paths,
evidence, risk, next step, and pre-refactor checks.

- [X] T026 [US2] Create the findings summary table in `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T027 [P] [US2] Record delete-now policy and current zero-delete result in `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T028 [P] [US2] Record split-soon findings for cabinet, readiness, macOS app/upload/diagnostics/scripts/models/admin surfaces in `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T029 [P] [US2] Record keep-intentionally findings for runtime dependencies, parked driver, release scripts, recording writer, specs/docs, Docker services, WebView policy, and redaction rules in `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T030 [P] [US2] Record risky/needs-spec findings for auth, deletion, MediaScribe, DB/RLS/migrations, capture, Langfuse, deploy, product-status reconciliation, and cabinet/native-shell authority in `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T031 [US2] Verify each finding follows `specs/072-deep-architecture-audit/contracts/architecture-finding-contract.md`.

**Checkpoint**: Risk register is usable without opening a refactor PR.

## Phase 5: User Story 3 - Produce Small-PR Roadmap (Priority: P1)

**Goal**: Convert architecture findings into safe future refactor batches.

**Independent Test**: Each roadmap batch has a goal, included/excluded scope,
expected diff shape, validation gates, and release policy.

- [X] T032 [P] [US3] Define cabinet web follow-up segmentation batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T033 [P] [US3] Define readiness matrix split batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T034 [P] [US3] Define desktop upload custody split batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T035 [P] [US3] Define desktop app composition split batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T036 [P] [US3] Define diagnostic evidence split batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T037 [P] [US3] Define capture script helper extraction batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T038 [P] [US3] Define shared Swift model segmentation batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T039 [P] [US3] Define admin surface split batch in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T040 [US3] List separate Spec Kit slices required before risky boundary changes in `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T041 [US3] Verify each batch follows `specs/072-deep-architecture-audit/contracts/refactor-batch-contract.md`.

**Checkpoint**: Roadmap can be executed as small future PRs.

## Phase 6: User Story 4 - Preserve Trust Boundaries (Priority: P1)

**Goal**: Keep capture, auth/session/device, privacy, deletion, MediaScribe,
Langfuse, MinIO/Postgres/Temporal, and desktop WebView/cabinet boundaries clear.

**Independent Test**: Required boundaries appear in `spec.md`, `plan.md`,
`runtime-flows.md`, `findings-register.md`, and `refactor-roadmap.md`.

- [X] T042 [P] [US4] Verify capture boundary coverage across `specs/072-deep-architecture-audit/spec.md`, `specs/072-deep-architecture-audit/audit/runtime-flows.md`, and `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T043 [P] [US4] Verify auth/session/device boundary coverage across `specs/072-deep-architecture-audit/spec.md`, `specs/072-deep-architecture-audit/audit/findings-register.md`, and `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.
- [X] T044 [P] [US4] Verify privacy and metadata-only evidence rules across `specs/072-deep-architecture-audit/spec.md`, `specs/072-deep-architecture-audit/plan.md`, and `specs/072-deep-architecture-audit/quickstart.md`.
- [X] T045 [P] [US4] Verify deletion/retention boundary coverage across `specs/072-deep-architecture-audit/audit/runtime-flows.md` and `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T046 [P] [US4] Verify MediaScribe and Langfuse boundary coverage across `specs/072-deep-architecture-audit/audit/runtime-flows.md` and `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T047 [P] [US4] Verify MinIO/Postgres/Temporal boundary coverage across `specs/072-deep-architecture-audit/audit/dependency-graphs.md`, `specs/072-deep-architecture-audit/audit/runtime-flows.md`, and `specs/072-deep-architecture-audit/audit/findings-register.md`.
- [X] T048 [P] [US4] Verify desktop WebView/cabinet boundary coverage across `specs/072-deep-architecture-audit/audit/runtime-flows.md`, `specs/072-deep-architecture-audit/audit/findings-register.md`, and `specs/072-deep-architecture-audit/audit/refactor-roadmap.md`.

**Checkpoint**: Future refactor batches cannot ignore safety boundaries.

## Phase 7: Validation And Analyze

**Purpose**: Validate 072 artifacts as a read-only audit package.

- [X] T049 Run the placeholder scan from `specs/072-deep-architecture-audit/quickstart.md` and resolve any 072 template leftovers.
- [X] T050 Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from the repository root.
- [X] T051 Run `$speckit-analyze` consistency review across `specs/072-deep-architecture-audit/spec.md`, `specs/072-deep-architecture-audit/plan.md`, `specs/072-deep-architecture-audit/tasks.md`, and supporting docs.
- [X] T052 Confirm final answer states the selected lane, no code/deploy/delete actions, and the five plain-language audit answers.

## Dependencies And Execution Order

- Phase 1 blocks all other work.
- Phase 2 blocks findings and roadmap tasks.
- Phase 3 can run in parallel by surface after Phase 2.
- Phase 4 depends on Phase 3 evidence.
- Phase 5 depends on Phase 4 findings.
- Phase 6 can run after Phase 3 and must be complete before final analyze.
- Phase 7 is last.

## Parallel Opportunities

- T006-T009 can run in parallel.
- T011-T018 can run in parallel by architecture surface.
- T019-T025 can run in parallel by runtime flow.
- T027-T030 can run in parallel by classification.
- T032-T039 can run in parallel by roadmap batch.
- T042-T048 can run in parallel by boundary.

## Implementation Strategy

1. Keep 072 stage one read-only for product/runtime code.
2. Complete the architecture evidence map before classifying findings.
3. Classify conservatively: absence of direct imports is not deletion proof.
4. Convert only `split soon` findings into ordinary future PR batches.
5. Move `risky / needs spec` findings into separate future Spec Kit slices.
6. Run analyze before calling the audit package complete.
