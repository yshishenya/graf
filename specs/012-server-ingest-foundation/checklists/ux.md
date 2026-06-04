# UX Checklist: Server Ingest Foundation

**Purpose**: Validate desktop-facing status, user-visible truth, support/operator messaging, and future UI contract requirements quality for 012.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md), [contracts/desktop-ingest-status.md](../contracts/desktop-ingest-status.md)

**Note**: 012 does not implement UI. This checklist validates whether requirements give future desktop/dashboard UI enough clear, truthful status semantics.

## Requirement Completeness

- [ ] CHK001 Are desktop-facing status requirements complete for pending, uploading, retrying, finalized/uploaded label, degraded, failed, aborted, and expired outcomes? [Completeness, Spec §FR-015, Contract §Status Values]
- [ ] CHK002 Are requirements complete enough for a future desktop uploader to distinguish uploaded label from canonical API states `finalized` and `ingested_pending_processing`? [Completeness, Spec §FR-015/SC-007]
- [ ] CHK003 Are user-facing truth requirements defined for successful ingest without implying transcription, summary, dashboard readiness, workflow start, or MediaScribe submission? [Clarity, Spec §FR-018/FR-040]
- [ ] CHK004 Are support/operator-facing degraded and failed status requirements defined with concrete unavailable or policy reasons? [Completeness, Spec §US4/FR-016/FR-047]

## Requirement Clarity

- [ ] CHK005 Is the desktop/UI label "uploaded" clearly scoped as presentation copy rather than a canonical API state? [Clarity, Spec §Clarifications/FR-015]
- [ ] CHK006 Are retryable versus terminal status requirements unambiguous for future desktop copy and recovery prompts? [Clarity, Spec §US2/US4]
- [ ] CHK007 Are over-limit user-facing requirements clear about rejected/degraded outcomes and prohibited false success labels? [Clarity, Spec §FR-047/SC-022]
- [ ] CHK008 Are sharing/download unavailable states specified clearly enough for future dashboard/access UI to avoid exposing audio, transcript, summary, or public URLs in 012? [Clarity, Spec §US6/FR-034]

## Requirement Consistency

- [ ] CHK009 Are desktop-facing status names consistent across spec, OpenAPI contract, desktop status contract, and quickstart expectations? [Consistency, Spec §FR-015, Contracts]
- [ ] CHK010 Are user-visible capture truth requirements consistent with the rule that server ingest status is post-capture lifecycle, not recording truth? [Consistency, Spec §FR-025, Constitution §Visible Consent]
- [ ] CHK011 Are future upload queue requirements consistent with 012 explicitly not implementing the production desktop uploader or local retry UI? [Consistency, Spec §FR-029]

## Scenario Coverage

- [ ] CHK012 Are offline-at-recording-finish, app restart, retry, abort, expiry, and stale policy scenarios represented as requirements for future desktop status handling? [Coverage, Spec §Edge Cases]
- [ ] CHK013 Are storage outage and metadata-store failure scenarios represented with desktop-visible blocked or recoverable semantics? [Coverage, Spec §FR-026/Edge Cases]
- [ ] CHK014 Are wrong workspace/device/user status requests covered without requiring the future UI to reveal foreign resource existence? [Coverage, Spec §FR-042/SC-019]

## Acceptance Criteria Quality

- [ ] CHK015 Are status-matrix success criteria measurable enough to drive tasks for contract tests without requiring UI implementation? [Measurability, Spec §SC-007]
- [ ] CHK016 Are not-implemented dashboard/share/download attempts measurable as 012 validation cases without defining actual UI screens? [Measurability, Spec §SC-015]

## Notes

- Use this checklist to keep future user-visible truth aligned with backend lifecycle semantics.
