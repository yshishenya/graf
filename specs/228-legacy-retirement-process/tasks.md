---
description: "Dependency-ordered tasks for Feature 228 managed legacy retirement"
---

# Tasks: Управляемое поэтапное retirement legacy

**Input**: `spec.md`, `clarifications.md`, `plan.md`
**Risk lane**: Significant feature.
**Precondition for implementation**: reviewer-owned checklists are reviewed,
`speckit-analyze` has no unresolved Critical/High finding, and task-to-issues
has completed. None of these tasks authorizes runtime deletion or production
mutation.

## Phase 1: Reconcile and establish the planning baseline

- [ ] T001 Record Feature 228 ownership, exact base SHA and planning-only scope in `specs/228-legacy-retirement-process/spec.md` and `.specify/feature.json`.
- [ ] T002 [P] Compare `specs/220-legacy-retirement/` on `codex/220-legacy-retirement` with current `HEAD`; record adopted, superseded and unverified requirements in `specs/228-legacy-retirement-process/plan.md`.
- [ ] T003 [P] Record the read-only comparison of `codex/206-legacy-cleanup`, `specs/206-mediascribe-polling-recovery/` and current processing compatibility in `specs/228-legacy-retirement-process/plan.md`.
- [ ] T004 Create the canonical Feature 228 issue/task mapping through `.specify/extensions/github-issue-canon/` and `specs/228-legacy-retirement-process/tasks.md`.

## Phase 2: Foundational safety contracts

- [ ] T005 [P] Write failing metadata-only, contained-path and forbidden-field tests in `tests/governance/test_legacy_inventory.py`.
- [ ] T006 [P] Write failing registry/exception lifecycle tests in `tests/governance/test_legacy_registry.py`.
- [ ] T007 [P] Write failing scope-fence, protected-domain and rollback-requirement tests in `tests/governance/test_retirement_slice.py`.
- [ ] T008 Define the versioned registry and metadata-only inventory schemas in `governance/legacy/registry.schema.json` and `governance/legacy/registry.v1.yaml`.
- [ ] T009 Extend `scripts/validate-legacy-impact.py` only where tests show it cannot enforce finite exception fields or exact classification.
- [ ] T010 Wire schema and changed-path validation fail-closed into `scripts/check-development-process.py` without broad file-system/user-data scanning.

## Phase 3: User Story 1 — Deterministic inventory (P1) 🎯 MVP

**Goal**: Produce a safe candidate registry before any removal decision.

**Independent test**: two runs on one SHA match exactly; source or registry
digest change reports stale; content-bearing field fixtures fail.

- [ ] T011 [P] [US1] Add deterministic ordering, exact-SHA and stale-evidence fixtures in `tests/governance/test_legacy_inventory.py`.
- [ ] T012 [US1] Implement a stdlib-only metadata discovery adapter with stable contour IDs in `scripts/legacy-inventory.py`.
- [ ] T013 [US1] Implement source digest, registry digest, sorted output and stale detection in `scripts/legacy-inventory.py`.
- [ ] T014 [US1] Seed only observed candidates as `candidate` or `blocked` with source evidence in `governance/legacy/registry.v1.yaml`; do not label them removable.
- [ ] T015 [US1] Add a metadata-only inventory runbook and candidate/approved distinction in `docs/agent-guidance/legacy-retirement.md`.

## Phase 4: User Story 2 — Prevent new unowned legacy (P1)

**Goal**: Make a compatibility exception finite, visible and task-backed.

**Independent test**: unowned legacy-sensitive changes and expired exceptions
fail; an explicit bounded exception passes without false positives on archival
evidence.

- [ ] T016 [P] [US2] Add synthetic alias, fallback, flag, dependency, fixture and documentation changed-path fixtures in `tests/governance/test_validator_safety.py`.
- [ ] T017 [US2] Implement `retain-with-exception` validation against the registry owner, expiry, trigger, validation and linked task/issue in `scripts/validate-legacy-registry.py`.
- [ ] T018 [US2] Add a narrow active-path taxonomy and documented archival/evidence exclusions to `scripts/legacy-inventory.py` and `docs/agent-guidance/legacy-retirement.md`.
- [ ] T019 [US2] Update `.github/pull_request_template.md` and `docs/agent-guidance/development-process.md` with the bounded Legacy Impact declaration without adding active context to root `AGENTS.md`.

## Phase 5: User Story 3 — Prepare one safe retirement slice (P1)

**Goal**: Ensure future removal is small, reversible and independently reviewable.

**Independent test**: a synthetic slice fails without every applicable
protected-domain evidence item and passes only with a bounded scope fence.

- [ ] T020 [P] [US3] Add migration and persistent-data contract fixtures to `tests/governance/test_retirement_slice.py`.
- [ ] T021 [P] [US3] Add Temporal replay/history compatibility contract fixtures to `tests/governance/test_retirement_slice.py`.
- [ ] T022 [P] [US3] Add macOS/Sparkle signing/appcast continuity contract fixtures to `tests/governance/test_retirement_slice.py`.
- [ ] T036 [P] [US3] Add historical MediaScribe dual-track/drain cutoff, canonical-source, unavailable-outcome and bounded-cleanup negative fixtures to `tests/governance/test_retirement_slice.py`.
- [ ] T023 [US3] Implement protected-domain and rollback/abort validation in `scripts/validate-retirement-slice.py`.
- [ ] T024 [US3] Add a retirement slice template and per-domain rehearsal references in `docs/agent-guidance/legacy-retirement.md`.
- [ ] T025 [US3] Create task-backed child issues only for owner/reviewer-approved `remove` records using `.specify/extensions/github-issue-canon/`; leave candidate and blocked records open.

## Phase 6: User Story 4 — Keep agent context bounded (P2)

**Goal**: Give an agent enough local instruction for one contour without a
shared mutable root file.

**Independent test**: context validation rejects active feature/registry state
in root instructions and accepts active scoped links and Feature pointer.

- [ ] T026 [P] [US4] Add root-router stability and scoped-guidance regression cases in `tests/governance/test_agent_context.py`.
- [ ] T027 [US4] Extend `scripts/validate-agent-context.py` for legacy-slice pointer and root-context size/content rules.
- [ ] T028 [US4] Document the minimum agent read set and "do not load full registry" rule in `docs/agent-guidance/legacy-retirement.md` and `docs/agent-guidance/README.md`.
- [ ] T029 [US4] Extract generic registry/schema/context templates to the `graf-development-harness` source repository only after GRAF tests establish their portability.

## Phase 7: User Story 5 — Release-train traceability (P2)

**Goal**: Bind an included retirement slice to its released candidate without
re-running Full CI for each feature commit.

**Independent test**: a candidate manifest without exact merged SHA, fragment
digest, slice/contour link or authoritative Full receipt is rejected.

- [ ] T030 [P] [US5] Add retirement-slice candidate/receipt negative fixtures in `tests/governance/test_release_candidate.py`.
- [ ] T031 [US5] Extend `infra/scripts/release-candidate.sh` and its schema only as needed to record included contour/slice references and fragment digest.
- [ ] T032 [US5] Update `docs/agent-guidance/release-and-validation.md` with the release-train inclusion rule and one-Full-CI boundary.

## Phase 8: Analysis, evidence and handoff

- [ ] T033 Run `$speckit-analyze`; resolve every Critical/High planning finding in `specs/228-legacy-retirement-process/` and regenerate affected reviewer checklist items without checking them.
- [ ] T034 Run Feature 228 metadata-only quickstart scenarios, `python3 scripts/check-development-process.py --self-test`, focused governance tests and `infra/scripts/ci-local.sh --fast` once on the PR-ready exact SHA; attach evidence to the Feature 228 PR.
- [ ] T035 Run `$speckit-converge`, confirm `legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0`, and record only the remaining blocked contours/limitations in `changes/unreleased/F228.yaml`.

## Dependencies and Parallel Opportunities

- T001–T004 establish provenance before implementation.
- T005–T010 are foundational and block all user stories.
- US1 (T011–T015) produces the candidate baseline before owner classification.
- US2 (T016–T019) and US3 fixtures (T020–T022) can proceed in parallel after
  schemas, because they own separate files.
- T023–T025 depend on US1/US2 and reviewer-approved records.
- US4 (T026–T029) can proceed after T015; it must not edit root `AGENTS.md`.
- US5 (T030–T032) depends on the Feature 227 release-train contract when it is
  available; otherwise it records an explicit dependency, not a duplicate flow.
- T033–T035 are final gates. No task may delete legacy or execute production CD.

## Requirement-to-task Traceability

| Requirement | Primary tasks | Evidence of completion |
|---|---|---|
| FR-001–FR-004 / SC-001–SC-002 | T005, T008, T011–T015 | Deterministic metadata-only registry/inventory tests on one exact SHA. |
| FR-005–FR-007 / SC-003 | T006, T009–T010, T016–T019 | Negative and valid exception/changed-path fixtures. |
| FR-008–FR-009 / SC-004 | T007, T023–T025 | Retirement-slice scope, abort, rollback and issue-link validator. |
| FR-010 / SC-005 | T020, T023–T024 | Migration/data protected-domain fixture and rehearsal contract. |
| FR-011 / SC-005 | T021, T023–T024 | Temporal replay/history protected-domain fixture and contract. |
| FR-012 / SC-005 | T022, T023–T024 | macOS/Sparkle trust/rollback protected-domain fixture and contract. |
| FR-013 / SC-004 | T014, T018, T023–T025 | Candidate classification plus reviewed, bounded removal-slice criteria. |
| FR-014 / SC-006 | T026–T029 | Root-router/context validator and scoped guidance review. |
| FR-015–FR-016 / SC-007 | T019, T030–T032 | PR/fragment/release-candidate schema and receipt tests. |
| FR-017 / SC-008 | T033–T035 | Unchanged reviewer checkboxes, review record and metadata-only closeout. |
| FR-018 / SC-008 | T001, T033–T035 | Planning-only scope and no destructive/production operation in evidence. |
