# Lifecycle And Operations Requirements Checklist: Review M4A Normalization

**Purpose**: Validate lifecycle, privacy, isolation, tenancy, rollout and rollback requirement quality before task generation
**Created**: 2026-07-14
**Feature**: [spec.md](../spec.md)

**Audience / depth**: PR, operations and release reviewers; formal high-risk gate.

## Requirement Completeness

- [x] CHK001 Are candidate, accepted source, attempt, canonical and temporary artifact ownership/lifecycle requirements all documented separately? [Completeness, Spec §FR-018/FR-030, Data Model §Data lifecycle]
- [x] CHK002 Are publication prerequisites defined for source fingerprint, full validation, immutable object registration, database visibility and one active canonical artifact? [Completeness, Spec §FR-006/FR-013/FR-035, Data Model §Publication]
- [x] CHK003 Are deletion and retention requirements defined for jobs, attempts, candidates, canonical objects, temp work files and operational reports? [Completeness, Spec §FR-018/FR-036, Lifecycle Contract §Deletion report/Retention]
- [x] CHK004 Are tenant isolation, forced RLS, worker tenant context and narrowly scoped global inventory/dispatch maintenance requirements documented? [Completeness, Spec §FR-026/FR-027, Lifecycle Contract §RLS and maintenance]
- [x] CHK005 Are deployment, migration, worker readiness, backfill gating, rollback and residue-free closeout requirements specified? [Completeness, Lifecycle Contract §Deployment gate/Rollback/Closeout evidence]

## Requirement Clarity

- [x] CHK006 Is the publication visibility boundary described without claiming a distributed MinIO/PostgreSQL transaction? [Clarity, Data Model §Transaction and race invariants]
- [x] CHK007 Is deletion-wins precedence explicit for every publish race and cleanup-pending state? [Clarity, Spec §FR-036/SC-017, Lifecycle Contract §Publication/deletion race]
- [x] CHK008 Are resource controls quantified for CPU, memory, concurrency, work storage, free-space reserve, output, timeouts and subprocess-output bounds? [Clarity, Spec §FR-021/FR-029, Lifecycle Contract §Resource controls]
- [x] CHK009 Are readiness and health states separated so a healthy worker cannot imply that media conversion or backfill succeeded? [Clarity, Lifecycle Contract §Readiness and metrics]
- [x] CHK010 Are rollback limits explicit for schema compatibility, previously published canonical objects and in-flight automatic jobs? [Clarity, Lifecycle Contract §Rollback]

## Privacy And Security Requirement Quality

- [x] CHK011 Is the safe metadata allowlist explicit and are raw filenames, paths, object keys/URLs, FFmpeg output, tags, content and credentials consistently forbidden? [Completeness, Spec §FR-020/FR-037/SC-010, Lifecycle Contract §Audit and logging]
- [x] CHK012 Are untrusted-media subprocess requirements specified for non-root execution, file-only protocols, process groups, private work files and image isolation? [Coverage, Plan §Constraints, Lifecycle Contract §Runtime topology]
- [x] CHK013 Are foreign-tenant and shared-viewer information-disclosure requirements defined for status and playback routes? [Coverage, Status Contract §Privacy/access rules]
- [x] CHK014 Are operational incidents metadata-only, deduplicated and clearly separated from any user repair action? [Consistency, Lifecycle Contract §Operational incidents]

## Scenario And Edge-Case Coverage

- [x] CHK015 Are object-upload-before-database-commit, database-commit-before-dispatch, worker crash, lease expiry and orphan cleanup scenarios addressed? [Coverage, Data Model §Transaction and race invariants, Backfill Contract §Restart recovery]
- [x] CHK016 Are concurrent deletion, retention purge, retry, backfill and publication scenarios assigned deterministic lock/precedence outcomes? [Coverage, Spec §FR-035/FR-036, Lifecycle Contract §Publication/deletion race]
- [x] CHK017 Are disk-full, no-temp-capacity, dependency outage, source mismatch and cleanup failure outcomes assigned safe durable states and recovery ownership? [Coverage, Spec §FR-031/FR-037, Lifecycle Contract §Resource controls/Operational incidents]
- [x] CHK018 Are migration upgrade/downgrade, legacy unvalidated artifacts and partial rollout with old API/processing workers covered? [Coverage, Data Model §Migration 0022, Lifecycle Contract §Rollback]

## Acceptance Criteria And Traceability

- [x] CHK019 Can lifecycle success be measured for 100% of overlapping deletion/retention events and reports? [Measurability, Spec §SC-008/SC-017]
- [x] CHK020 Can tenant isolation, no-secret egress, non-root worker/resource limits and zero-residue cleanup be evidenced independently? [Measurability, Spec §SC-010/SC-013, Quickstart §§7–8/15]
- [x] CHK021 Are release acceptance and rollback triggers tied to exact evidence rather than generic green health checks? [Acceptance Criteria, Plan §Release Gate, Lifecycle Contract §Deployment gate]
- [x] CHK022 Is deferred feature-097 security-scan work explicitly separated from ordinary 099 authorization/RLS/privacy acceptance gates? [Scope, Plan §Validation Plan, Quickstart §Purpose]

## Notes

- Final 2026-07-14 reconciliation: `22/22` items remain satisfied and map to
  migration/RLS, deletion-race, resource, cleanup and rollout evidence in
  `validation/traceability.md`.
- Items validate the written lifecycle and operations contract, not implementation behavior.
- Feature 097 remains deferred and untouched; this checklist does not claim completion of its standalone security scan.
