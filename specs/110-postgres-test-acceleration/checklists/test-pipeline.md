# Test-pipeline Requirements Checklist: Быстрый и достоверный PostgreSQL test pipeline

**Purpose**: Проверить полноту, ясность и измеримость требований к ускорению
локального PostgreSQL gate до начала реализации.
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [runner contract](../contracts/local-postgres-test-pipeline.md)

## Requirement Completeness

- [X] CHK001 Are the PostgreSQL-only boundary and the explicit exclusion of SQLite stated for every supported test path? [Completeness, Spec §FR-001]
- [X] CHK002 Are safe locality, disposable ownership, and protection of developer/production data specified before any destructive operation? [Completeness, Spec §FR-002, Edge Cases]
- [X] CHK003 Are the fast baseline and the clean migration/RLS/empty-schema state distinguished rather than described as one ambiguous reset? [Completeness, Spec §FR-003–FR-004]
- [X] CHK004 Are direct worker-context requirements and the negative missing-context case both specified? [Completeness, Spec §FR-006]
- [X] CHK005 Are cleanup requirements defined for success, test failure, interruption and concurrent worktrees? [Completeness, Spec §FR-008, Edge Cases]

## Requirement Clarity And Consistency

- [X] CHK006 Is “максимально ускорить” quantified by a complete warm-gate target and a defined reference host? [Clarity, Spec §SC-001, Assumptions]
- [X] CHK007 Is “without reducing coverage” objectively constrained by collected and executed scenario counts plus no new conditional skip? [Clarity, Spec §FR-005, SC-002]
- [X] CHK008 Are focused checks clearly differentiated from canonical full-gate evidence? [Clarity, Spec §FR-010, Assumptions]
- [X] CHK009 Do the requirements consistently preserve RLS/tenant/migration guarantees while allowing a different reset method only for ordinary client scenarios? [Consistency, Spec §FR-003–FR-007]
- [X] CHK010 Is the stricter treatment of global PostgreSQL roles compatible with the parallelism requirement rather than in conflict with it? [Consistency, Plan §Constitution Check, Contract §Full-mode phases]

## Acceptance Criteria Quality

- [X] CHK011 Can the full-gate duration, collection/outcome equality, no-residue condition, and three-run stability be measured without private test data? [Measurability, Spec §SC-001–SC-005]
- [X] CHK012 Is the required timing evidence bounded to useful metadata and the top 20 slow scenarios? [Measurability, Spec §FR-009, SC-005]
- [X] CHK013 Is the criterion for choosing a default worker count defined as the fastest stable measured result instead of an unbounded CPU claim? [Clarity, Plan §Validation Plan]

## Scenario And Edge-Case Coverage

- [X] CHK014 Are normal API/contract, migration, RLS, empty-schema, worker-context, Docker-unavailable and focused-run scenarios all represented? [Coverage, Spec §User Stories 1–3]
- [X] CHK015 Are order-dependent commits, schema mutation, interrupted cleanup and cross-worktree collisions expressly covered? [Edge Case Coverage, Spec §Edge Cases]
- [X] CHK016 Is the recovery requirement explicit when the runner discovers an unsafe address, database name or role before writes begin? [Exception Flow, Spec §User Story 3]

## Dependencies And Ambiguities

- [X] CHK017 Are Docker readiness, PostgreSQL 17, the 10-CPU Docker reference host and the new development-only parallel test dependency documented as assumptions/dependencies? [Dependencies, Spec §Assumptions, Plan §Technical Context]
- [X] CHK018 Are production topology, credentials, data and release/deploy work explicitly outside the feature boundary? [Scope, Spec §Out of Scope]
- [X] CHK019 Is any template-database optimisation explicitly deferred until the simpler bounded-reset design has measurement evidence? [Ambiguity Resolution, Research §Decision 3]

## Notes

- All items are satisfied by the current specification and plan; no additional
  user clarification is material before task generation.
- This checklist assesses requirement quality only. It is not implementation or
  execution evidence.
