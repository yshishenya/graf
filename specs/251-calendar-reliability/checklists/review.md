# Requirements review: calendar reliability
**Created**: 2026-09-06
**Ownership**: reviewer-owned; checked means requirement quality, not implementation completion. Implementation must not edit markers.
## Access and data
- [x] CHK001 Are owner access, full provider content, encryption/escaping and separate auto-context permissions consistent? [FR-001,009]
- [x] CHK002 Are recurrence, timezone, cancellation and duplicate identity outcomes explicit? [FR-002,003,008]
## Recovery and UX
- [x] CHK003 Are sync schedule, claim fencing, selection/disconnect races and catalog changes testable? [FR-004,005]
- [x] CHK004 Are empty/live/error/dirty/focus and per-source UX states fully specified? [FR-006,007]
## Acceptance
- [x] CHK005 Are full journey, source-content roundtrip, negative access and release boundaries explicit? [FR-009,010; SC-001..004]

## Independent requirements review — 2026-09-06
Reviewer: calendar_research, separate from implementation owner.
- CHK002: PASS. FR-002/003/008, research and data model specify occurrence identity, TZID, exclusions, moved/cancelled events, id-only deletion and distinct meetings using one call URL. Design clarification explicitly preserves floating-time limitation when the timezone is unknown.
- CHK004: PASS. FR-006/007, contract and quickstart specify empty/list/error states, 30-second refresh, visibility/online recovery, dirty form/dialog/focus retention, and independent source errors.
- CHK005: PASS. Quickstart contains connect/cancel/select/sync/change/delete/disconnect/reconnect, protected content roundtrip, negative owner access, scoped server/native/browser evidence and explicit separate production acceptance.
- CHK001: PASS after Design clarification. Full title/description/location/participants/attachments roundtrip through protected owner content; texts with URLs/passcodes remain encrypted at rest, owner rendering does not flush plaintext to ORM, HTTPS opening and independent auto-context permissions remain.
- CHK003: PASS after Design clarification. The source claim and original selection are checked under row lock before every catalog/result/cursor/error write; the running claim is immutable, disconnect/reclaim defeats old publication.
- All five markers certify requirement quality only. No implementation completion or production acceptance is implied.
