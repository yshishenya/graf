# Security And Lifecycle Checklist: Local Upload Custody

**Purpose**: Validate requirement quality for privacy, forbidden content,
retention, deletion, local purge, metadata-only incidents, and lifecycle
accounting.
**Created**: 2026-06-26
**Feature**: `specs/057-local-upload-custody/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [x] CHK001 Are forbidden-content requirements defined for UI, diagnostics,
  logs, reports, specs, screenshots, and validation evidence? [Completeness,
  Spec FR-024, FR-043, Contracts Forbidden Content]
- [x] CHK002 Are metadata-only incident requirements complete for reason
  category, responsible role, timestamps, lifecycle state, safe identity, and
  terminal outcome? [Completeness, Spec US5, FR-004, FR-023-FR-024]
- [x] CHK003 Are local purge requirements defined for success, failed,
  unverified, already missing, undeleted, and cannot-verify cases?
  [Completeness, Spec Edge Cases, FR-042, Data Model Local Purge Verification]
- [x] CHK004 Are retention warning and terminal undelivered requirements
  complete enough to prevent silent irreversible loss? [Completeness, Spec US1,
  FR-002-FR-004, SC-009-SC-010]

## Requirement Clarity

- [x] CHK005 Is purge acknowledgement clearly conditioned on verified deletion,
  tombstone, or cryptographic unrecoverability? [Clarity, Spec FR-042,
  Clarifications]
- [x] CHK006 Is "metadata-only" defined with concrete forbidden examples for
  raw audio, transcript text, local paths, credentials, tokens, cookies, signed
  URLs, and secret values? [Clarity, Spec FR-024, FR-043]
- [x] CHK007 Are terminal states clear about not promising recovery after
  policy purge, user deletion, or unrecoverable cannot-send outcomes? [Clarity,
  Spec User-Facing State Model, Data Model State Transitions]

## Requirement Consistency

- [x] CHK008 Do deletion and retention requirements align with constitution
  wording that deletion only covers what 2brain Rec controls? [Consistency,
  Constitution IV, Spec FR-029, User-Facing State Model]
- [x] CHK009 Do privacy requirements preserve the desktop/server boundary by
  preventing direct desktop egress to MediaScribe or object storage?
  [Consistency, Spec FR-033, Plan Constraints]
- [x] CHK010 Do safe report requirements align across normal user UI,
  admin/support role, and server incident/read-model contracts? [Consistency,
  Spec US5, FR-052, Handoff Contract]

## Acceptance Criteria Quality

- [x] CHK011 Are forbidden-content scans and metadata-only evidence criteria
  measurable enough for implementation closeout? [Measurability, Spec SC-012]
- [x] CHK012 Are purge validation criteria measurable enough to distinguish
  verified success from failed or unverified local purge? [Measurability, Spec
  SC-015]

## Dependencies & Assumptions

- [x] CHK013 Are dependencies on existing retention/deletion lifecycle and
  local purge truth explicitly documented? [Dependency, Spec Dependencies,
  Plan Technical Context]
- [x] CHK014 Are assumptions about retaining local copies while policy allows
  stated clearly enough for future retention-policy changes? [Assumption, Spec
  Assumptions, Data Model Custody Item]
