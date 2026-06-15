# Security Checklist: RLS Production Enforcement Truth

**Purpose**: Validate security, privacy, tenant-boundary, and evidence-safety requirements quality for 032
**Created**: 2026-06-15
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates whether requirements are complete, clear,
measurable, and consistent. It does not verify implementation behavior.

## Tenant Boundary Requirements

- [x] CHK001 Are production RLS truth requirements tied to the same covered tenant-owned table set as feature 031? [Traceability, Spec FR-013, Plan Phase 1]
- [x] CHK002 Are requirements clear that production proof requires both enabled and forced RLS state, not only an Alembic revision? [Clarity, Spec US2, Spec FR-013]
- [x] CHK003 Are future dashboard, access, sharing, retention, and deletion dependencies explicitly tied to truthful production RLS status? [Coverage, Spec US4, Spec FR-015]

## Production Safety Requirements

- [x] CHK004 Are destructive same/cross-tenant probe requirements clearly limited to disposable or explicit test databases? [Clarity, Spec US1, Spec FR-004]
- [x] CHK005 Are live production checks specified as read-only catalog metadata inspection rather than customer-row reads or mutations? [Completeness, Spec US2, Spec FR-013]
- [x] CHK006 Are blocked states defined when production inspection cannot prove every covered table is enabled and forced? [Coverage, Spec US2, Spec SC-007]

## Evidence And Secret Discipline

- [x] CHK007 Are forbidden evidence contents enumerated for docs, scripts, tests, logs, and comments? [Completeness, Spec FR-018]
- [x] CHK008 Are metadata-only evidence requirements clear enough to record production commit, Alembic revision, and table counts without exposing secrets? [Clarity, Data Model RLSProductionTruthVerdict]
- [x] CHK009 Are stale `not_changed` claims required to be corrected without erasing historical pre-production context? [Consistency, Spec US3, Contract rollout-truth-remediation]

## Failure And Rollback Requirements

- [x] CHK010 Are halt and rollback states defined for failed production verification or remediation? [Coverage, Spec FR-009, Spec FR-010]
- [x] CHK011 Are requirements measurable enough to block production-enabled claims when test evidence is stale, failed, inconclusive, or forbidden-content bearing? [Measurability, Spec SC-001, Spec SC-002]
- [x] CHK012 Are production verification failure outputs required to name missing or failed tables without leaking customer data? [Clarity, Contract production-rls-state]
