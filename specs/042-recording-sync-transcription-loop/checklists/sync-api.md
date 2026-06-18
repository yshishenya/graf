# Sync/API Checklist: Recording Sync And Transcription Loop

**Purpose**: Validate requirement quality for offline queue, upload resume,
server reconciliation, idempotency, and API contracts.
**Created**: 2026-06-18
**Feature**: `specs/042-recording-sync-transcription-loop/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [x] CHK001 Are all local queue states required by offline, retry, blocked,
  failed, uploaded, deleted, and conflict flows explicitly defined?
  [Completeness, Spec US1/US3/US5, Plan "Desktop identity and queue"]
- [x] CHK002 Are server reconciliation requirements defined for app launch,
  reconnect, manual retry, queue view, and embedded review navigation?
  [Completeness, Contract `desktop-sync-contract.md`]
- [x] CHK003 Are idempotency requirements documented for meeting creation,
  media revision creation, upload session creation, part upload, finalization,
  and processing pickup? [Completeness, Spec FR-002/FR-010, Plan Phase 1]
- [x] CHK004 Are requirements defined for migration from
  `desktop-upload-queue.v1` to v2 without losing queued recordings?
  [Gap, Data Model "Desktop Upload Queue Item"]

## Requirement Clarity

- [x] CHK005 Is "server truth is authoritative" defined with concrete fields
  such as accepted bytes, missing ranges, status, access/deletion state, and
  media revision identity? [Clarity, Contract `desktop-sync-contract.md`]
- [x] CHK006 Is the boundary between `localRecordingId`, `directoryId`,
  `localMediaRevisionId`, `mediaRevisionId`, `meetingId`, and `uploadSessionId`
  unambiguous? [Clarity, Data Model]
- [x] CHK007 Are conflict states named with exact reason codes and next-action
  semantics instead of broad terms like "out of sync"? [Clarity, Spec US5,
  Data Model "Sync Conflict State"]

## Requirement Consistency

- [x] CHK008 Do upload retry requirements align with the immutable media
  revision rule and avoid implying checksum refresh or in-place content update?
  [Consistency, Spec Clarifications, Contract `media-revision-contract.md`]
- [x] CHK009 Do API contracts preserve existing server-mediated upload and
  no direct object-storage credential rules? [Consistency, Constitution III,
  Plan Constraints]
- [x] CHK010 Are processing and review status requirements consistent between
  local queue state, server meeting state, media revision state, and cabinet
  review status? [Consistency, Spec US4/US5, Contract `review-surface-contract.md`]

## Acceptance Criteria Quality

- [x] CHK011 Are success criteria measurable enough to prove "exactly one
  meeting" and "exactly one initial media revision" across retries?
  [Measurability, Spec SC-002]
- [x] CHK012 Are upload interruption/retry criteria defined at enough distinct
  points to cover partial part acceptance, missing ranges, and finalization?
  [Coverage, Spec US3]
- [x] CHK013 Are duplicate prevention criteria traceable to both client and
  server requirements? [Traceability, Spec US2/US3, Plan Implementation Approach]

## Edge Case Coverage

- [x] CHK014 Are malformed or stale local queue documents addressed in
  requirements and migration assumptions? [Gap, Data Model]
- [x] CHK015 Are expired upload sessions, mismatched idempotency keys, repeated
  parts with different checksum, and missing server ranges covered as separate
  requirement states? [Coverage, Contract `desktop-sync-contract.md`]
- [x] CHK016 Are server deleted/access-revoked cases clearly separated from
  ordinary network retry cases? [Clarity, Spec US5]
