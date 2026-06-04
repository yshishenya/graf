# Security Checklist: Server Ingest Foundation

**Purpose**: Validate security, privacy, tenant isolation, secret handling, and deletion-truth requirements quality for 012.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests whether the requirements are complete, clear, measurable, and consistent. It is not an implementation test plan.

## Requirement Completeness

- [x] CHK001 Are authentication requirements defined for every ingest operation class: create, read, upload-part, missing-range, finalize, abort, retry, and status? [Completeness, Spec §FR-042]
- [x] CHK002 Are registered device identity requirements complete enough to distinguish active, revoked, wrong-user, and wrong-workspace devices? [Completeness, Spec §FR-001/FR-042]
- [x] CHK003 Are tenant boundary requirements defined for organization, workspace, owner user, device, meeting, upload session, object key, and audit event records? [Coverage, Spec §FR-032/FR-044]
- [x] CHK004 Are requirements defined for safe handling of temporary upload objects after aborted, expired, degraded, and failed sessions? [Completeness, Spec §FR-023/SC-011]
- [x] CHK005 Are deletion-truth requirements complete enough to cover server metadata, object storage, temporary objects, local desktop buffers, MediaScribe, workflow state, diagnostics, and backups in later slices? [Completeness, Spec §FR-024]

## Requirement Clarity

- [x] CHK006 Is "short-lived, scoped upload authorization" quantified or constrained with clear scope dimensions such as session, device, track, range, workspace, and expiry? [Clarity, Spec §FR-004]
- [x] CHK007 Is the requirement to not trust client-supplied organization/workspace/user/device identifiers unambiguous about server-derived scope precedence? [Clarity, Spec §FR-043]
- [x] CHK008 Are secret and content exclusion requirements specific about prohibited data classes in logs, diagnostics, tokens, API responses, browser bundles, and committed files? [Clarity, Spec §FR-019/FR-021]
- [x] CHK009 Is the distinction between server-mediated upload authorization and direct object-storage credentials clear enough to prevent accidental signed MinIO URL exposure? [Clarity, Spec §FR-037/FR-038]

## Requirement Consistency

- [x] CHK010 Are application-level tenant checks consistently required in spec, plan, data model, contracts, and quickstart without relying on deferred RLS for 012 correctness? [Consistency, Spec §FR-042/FR-045]
- [x] CHK011 Is PostgreSQL RLS consistently framed as a traceable hardening follow-up rather than an implicit blocker or silent omission? [Consistency, Spec §FR-045, Plan §Research]
- [x] CHK012 Are MediaScribe and Temporal non-egress boundaries consistent across functional requirements, success criteria, plan, quickstart, and API responses? [Consistency, Spec §FR-018/SC-018]

## Acceptance Criteria Quality

- [x] CHK013 Are cross-user, cross-device, cross-workspace, and cross-organization denial outcomes measurable without exposing foreign resource existence? [Measurability, Spec §SC-019]
- [x] CHK014 Are secret/content scan criteria measurable enough to define pass/fail for logs, diagnostics, API responses, configuration, and desktop-facing outputs? [Measurability, Spec §SC-008]
- [x] CHK015 Are checksum conflict and idempotency requirements measurable for matching and mismatching retries without requiring implementation-specific algorithms? [Measurability, Spec §FR-013/FR-014/SC-004/SC-005]

## Edge Case Coverage

- [x] CHK016 Are requirements defined for authorization changes during an active upload, including device revocation before finalization? [Coverage, Spec §Edge Cases]
- [x] CHK017 Are requirements defined for metadata-store failure after object write succeeds, including cleanup/accounting truth? [Coverage, Spec §Edge Cases/FR-023]
- [x] CHK018 Are replayed, expired, wrong-device, wrong-user, wrong-workspace, and wrong-meeting upload token scenarios addressed as requirements rather than left to implementation discretion? [Coverage, Spec §Edge Cases/FR-042]

## Notes

- Items should be checked only when the written requirements are sufficiently clear and complete for task generation.
