# Sync/API Checklist: Local Upload Custody

**Purpose**: Validate requirement quality for durable local custody,
automatic retry, server reconciliation, stable problem codes, and the 057/058
API/read-model boundary.
**Created**: 2026-06-26
**Feature**: `specs/057-local-upload-custody/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [x] CHK001 Are durable custody ledger requirements defined for identity,
  fingerprints, server ids, accepted ranges, retry records, retention deadline,
  and custody state? [Completeness, Spec FR-034-FR-038, Data Model Custody
  Item]
- [x] CHK002 Are automatic retry trigger requirements defined for launch,
  activation, auth/session change, network recovery, wake, scheduled retry, and
  local recording finalization? [Completeness, Spec FR-039-FR-040, Contract
  `desktop-custody-contract.md`]
- [x] CHK003 Are server reconciliation requirements defined before upload,
  finalize, review-open, terminal decision, and purge acknowledgement?
  [Completeness, Spec FR-026, FR-038]
- [x] CHK004 Are malformed queue document requirements defined as quarantine
  and blocked custody truth instead of silent reset? [Completeness, Spec FR-036,
  Data Model Queue Document Quarantine]

## Requirement Clarity

- [x] CHK005 Is 404 `recording_not_found` defined unambiguously as
  server-unknown local custody, not terminal loss or fake server-row permission?
  [Clarity, Spec FR-049, Clarifications]
- [x] CHK006 Are owner/action/retry-class fields specified as
  machine-readable contracts rather than copy parsed from human text? [Clarity,
  Spec FR-050, Handoff Contract]
- [x] CHK007 Are problem-code classes defined for auth, quota, policy,
  deletion, stale device, conflict, dependency, payload, and unknown transient
  failures? [Clarity, Spec FR-051, Handoff Contract Problem Codes]
- [x] CHK008 Are server-known upload, processing, review, deletion, and local
  custody states separated clearly enough to avoid a generic failed/success
  status? [Clarity, Spec US6, FR-018-FR-019]

## Requirement Consistency

- [x] CHK009 Do 057 write-scope requirements consistently exclude
  `cabinet/web.py`, templates, CSS/static, and meeting-list/detail markup?
  [Consistency, Spec FR-046-FR-048a, Plan Structure Decision]
- [x] CHK010 Do server API/read-model field requirements align with feature
  `058` consuming those fields without importing native custody logic?
  [Consistency, Spec FR-054, Handoff Contract]
- [x] CHK011 Are retry requirements consistent with immutable local recording
  identity and no duplicate server meeting/session/job creation? [Consistency,
  Spec FR-025, FR-044, SC-013]

## Acceptance Criteria Quality

- [x] CHK012 Are success criteria measurable for 401, 403, 409, 410, 413, 429,
  and 503 mappings by owner, retry policy, action, and copy? [Measurability,
  Spec SC-016]
- [x] CHK013 Are cross-feature 057/058 validation criteria measurable enough to
  prove one server-known row plus native aggregate custody only? [Measurability,
  Spec SC-019-SC-020]

## Edge Case Coverage

- [x] CHK014 Are partial upload, upload session expiry, accepted-range
  reconciliation, finalize-response loss, and relaunch cases all represented?
  [Coverage, Spec Edge Cases, SC-013]
- [x] CHK015 Are auth expiry, wrong workspace, stale device, server deletion,
  quota/policy block, and dependency unavailable separated as distinct
  requirement states? [Coverage, Spec Edge Cases, Failure Ownership Matrix]
