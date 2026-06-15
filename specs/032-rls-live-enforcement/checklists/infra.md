# Infra Checklist: RLS Production Enforcement Truth

**Purpose**: Validate operational, deployment, production-state, and documentation-truth requirements quality for 032
**Created**: 2026-06-15
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates whether requirements are ready for planning
and task generation. It does not execute deployment or production checks.

## Production Target Requirements

- [x] CHK001 Is the production target identified clearly enough for future tasks to avoid checking the wrong environment? [Clarity, Spec Clarifications, Plan Technical Context]
- [x] CHK002 Are deployed commit and Alembic revision required in production truth evidence? [Completeness, Spec FR-005, Spec FR-006]
- [x] CHK003 Are requirements clear that Alembic current alone is insufficient without table-state inspection? [Clarity, Spec US2, Research production catalog inspection]

## Validation Workflow Requirements

- [x] CHK004 Are local, disposable/test, production-like, and production read-only validation classes distinguished clearly? [Consistency, Contract rls-validation-output]
- [x] CHK005 Are blocked states defined for unreachable production, stale evidence, missing table coverage, and forbidden content? [Coverage, Spec Edge Cases, Contract production-rls-state]
- [x] CHK006 Are quickstart commands scoped enough to avoid accidental destructive production probes? [Safety, Quickstart Sections 3-4]

## Documentation Truth Requirements

- [x] CHK007 Are all required stale-wording surfaces listed so tasks can update status docs, runbooks, ADR, quickstart, code output, and tests? [Completeness, Contract rollout-truth-remediation]
- [x] CHK008 Are current-state docs required to distinguish production-verified-enabled from historical pre-production wording? [Clarity, Spec FR-020]
- [x] CHK009 Are changelog requirements included for the operational/security truth correction? [Traceability, Spec FR-016]

## Operational Closeout Requirements

- [x] CHK010 Are final evidence fields defined for local/test gate result, deployed commit, Alembic revision, table counts, stale wording scan, and forbidden-content scan? [Completeness, Quickstart Section 7]
- [x] CHK011 Are rollback/residue requirements defined if production verification fails after prior rollout claims? [Coverage, Spec US4, Data Model RolloutTruthRemediation]
- [x] CHK012 Are future table inventory drift risks addressed through a traceable migration/policy inventory requirement? [Consistency, Research covered table inventory]
