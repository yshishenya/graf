# Security And Privacy Requirements Checklist: Manual Media Upload UI

**Purpose**: Validate data-boundary, auth, CSRF, and privacy requirement quality
before implementation
**Created**: 2026-07-07
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and plans, not implementation
behavior.

## Auth And CSRF Boundaries

- [x] CHK001 Are browser and embedded unsafe upload actions required to use the
  same CSRF protection class as other cookie-authenticated cabinet mutations?
  [Completeness, Spec FR-010, Plan Summary, Contract Cabinet Upload Request]
- [x] CHK002 Is public `087` API compatibility protected so cabinet CSRF does
  not silently break Bearer/device upload clients? [Consistency, Research CSRF
  Decision, Contract Public API Compatibility]
- [x] CHK003 Is the embedded desktop session/cookie requirement explicit enough
  to avoid relying on legacy injected headers for POST/subresource upload
  requests? [Clarity, Spec Clarifications, Research Embedded Desktop Decision]
- [x] CHK004 Are missing, stale, and invalid CSRF/session cases covered as
  user-visible recovery states? [Coverage, Spec US3, Spec Edge Cases, Contract
  Error Copy Contract]

## Secret, Egress, And Content Boundaries

- [x] CHK005 Are MediaScribe credentials, dependency URLs, dependency job ids,
  signed URLs, object keys, raw media, raw transcript text, and private paths
  explicitly forbidden from UI, errors, logs, tests, and evidence? [Completeness,
  Spec FR-011, Plan Constraints, Data Model Upload Failure State]
- [x] CHK006 Is client-side direct MediaScribe or object-storage upload excluded
  clearly enough to prevent implementation drift? [Clarity, Spec Assumptions,
  Out Of Scope, Plan Constraints]
- [x] CHK007 Does the plan preserve server-mediated upload custody through the
  `087` backend path instead of creating a new storage path? [Consistency, Plan
  Storage, Research Backend Custody Decision]
- [x] CHK008 Are committed evidence and screenshot/privacy boundaries stated
  for this feature's docs and tests? [Coverage, Quickstart Forbidden Content
  Scan, Product Gates]

## Lifecycle And Deletion Truth

- [x] CHK009 Are cancellation-before-acceptance and deletion-after-acceptance
  requirements distinguished without promising unsafe undo or universal
  erasure? [Clarity, Spec FR-009, Spec Clarifications, Plan Constitution Check]
- [x] CHK010 Are accepted uploads required to reuse existing lifecycle/deletion
  accounting from `087` rather than creating untracked media artifacts?
  [Completeness, Spec Clarifications, Plan Storage]
- [x] CHK011 Are processing failures represented as accepted-media plus
  processing status, rather than hidden deletion or false transcript readiness?
  [Consistency, Spec US3, Spec FR-007, Data Model State Rules]

## Access And Tenant Scope

- [x] CHK012 Are owner, workspace, device/session, and meeting access boundaries
  documented for upload creation and post-acceptance review? [Completeness,
  Spec US1-US4, Data Model Manual Upload Submission]
- [x] CHK013 Are signed-out, expired-session, mismatched workspace/device, and
  access-denied cases covered without leaking meeting content? [Coverage, Spec
  Edge Cases, Contract Error Copy Contract]
- [x] CHK014 Are duplicate/retry/idempotency requirements clear enough to avoid
  accidental duplicate meetings for one draft while still allowing a future
  deliberate re-upload design? [Clarity, Spec FR-018, Data Model Upload Sheet]

## Validation Traceability

- [x] CHK015 Do success criteria require focused auth/CSRF, safe-failure, and
  no-secret validation before closeout? [Acceptance Criteria, Spec SC-003,
  SC-005, SC-006, Quickstart]
- [x] CHK016 Is the high-risk validation lane documented consistently across
  spec, plan, and quickstart? [Consistency, Spec Clarifications, Plan Risk /
  Validation Lane, Quickstart Closeout Gate]

## Notes

- Review result: 2026-07-07. Requirement quality is sufficient for tasks after
  security/privacy review; no blocking gaps found.
