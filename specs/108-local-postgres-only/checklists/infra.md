# Infrastructure Requirements Checklist: Local PostgreSQL Only

**Purpose**: Validate that the PostgreSQL-only infrastructure requirements are complete, clear and safe before implementation.  
**Created**: 2026-07-17  
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 - Are the supported local database service, its ownership boundary and its readiness prerequisite explicitly specified? [Completeness, Spec §FR-001]
- [X] CHK002 - Are ordinary tests, RLS tests and migration tests all required to use the same supported database family? [Completeness, Spec §FR-002, §FR-003]
- [X] CHK003 - Is the active surface from which SQLite support must be removed explicitly enumerated? [Completeness, Spec §FR-004]
- [X] CHK004 - Are production data, roles, secrets, addresses and schema changes explicitly excluded? [Completeness, Spec §FR-006, Out of Scope]

## Requirement Clarity

- [X] CHK005 - Is the generated test database naming rule precise enough to distinguish safe disposable targets from a developer database? [Clarity, Spec §FR-002, Key Entities]
- [X] CHK006 - Are the allowed database host boundary and unsupported target behavior defined before mutation can occur? [Clarity, Spec §FR-002, Edge Cases]
- [X] CHK007 - Is failure recovery for unavailable Docker or occupied local ports described without suggesting a remote fallback? [Clarity, Spec §FR-005, Edge Cases]

## Requirement Consistency

- [X] CHK008 - Do the PostgreSQL-only requirement and the production non-mutation requirement consistently permit existing production URLs while rejecting unsupported local drivers? [Consistency, Spec §FR-004, §FR-006]
- [X] CHK009 - Does the historical-evidence exception remain limited to archival material and avoid conflict with the active-path removal requirement? [Consistency, Spec §FR-004, §FR-008]

## Acceptance Criteria Quality

- [X] CHK010 - Are the success outcomes measurable for test coverage, active SQLite references and migration lifecycle? [Measurability, Spec §SC-002, §SC-003, §SC-004]
- [X] CHK011 - Is the phrase "one documented scenario" bounded by observable setup, readiness, migration and test outcomes? [Measurability, Spec §SC-001]

## Scenario And Edge-Case Coverage

- [X] CHK012 - Are initial setup, repeat execution, unavailable service and unsafe-address scenarios all specified? [Coverage, User Story 1]
- [X] CHK013 - Are upgrade, downgrade and clean-database migration requirements specified for the supported storage family? [Coverage, User Story 2]
- [X] CHK014 - Are cleanup requirements defined for normal, failure and interrupted test runs? [Coverage, Edge Cases, Spec §FR-002]

## Dependencies And Assumptions

- [X] CHK015 - Is the Docker Engine dependency stated with a clear recovery action and without a hidden production dependency? [Assumption, Spec §Assumptions]
- [X] CHK016 - Is the dependency on the existing local Compose service documented rather than silently introducing a new stack? [Dependency, Spec §FR-001, Assumptions]

## Notes

- No unresolved requirement-quality gaps remain. The checklist is for the
  specification and plan, not for implementation verification.
