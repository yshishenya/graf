# Infra And Processing Checklist: Recording Sync And Transcription Loop

**Purpose**: Validate requirement quality for Postgres schema changes, MinIO
artifact ownership, Temporal workflow idempotency, MediaScribe processing, and
runtime validation gates.
**Created**: 2026-06-18
**Feature**: `specs/042-recording-sync-transcription-loop/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [x] CHK001 Are schema requirements complete for `media_revisions`,
  revision-linked upload sessions, track artifacts, manifest snapshots,
  workflows, jobs, results, and lifecycle/deletion records?
  [Completeness, Data Model]
- [x] CHK002 Are migration/backfill requirements defined for existing meeting,
  upload, artifact, and processing rows that predate media revisions?
  [Gap, Plan Implementation Approach]
- [x] CHK003 Are RLS/tenant isolation requirements defined for new
  `media_revisions` and revision-linked tables? [Gap, Constitution quality
  gates, Plan Source Code]
- [x] CHK004 Are dependency-unavailable states defined separately for Postgres,
  MinIO, Temporal, MediaScribe, and web cabinet availability?
  [Completeness, Spec US5/US6]

## Requirement Clarity

- [x] CHK005 Is the processing workflow identity rule
  `processing/<media_revision_id>` specified clearly enough to avoid duplicate
  MediaScribe submissions? [Clarity, Research, Contract
  `media-revision-contract.md`]
- [x] CHK006 Are retryable and terminal processing failures distinguished with
  safe reason codes and user-visible status implications? [Clarity, Spec US4/US5]
- [x] CHK007 Are artifact storage ownership and object-key visibility
  requirements clear enough to prevent signed URL leakage? [Clarity, Security
  Checklist, Data Model "Track Artifact"]

## Requirement Consistency

- [x] CHK008 Do workflow/job/result uniqueness requirements align with the new
  media revision model rather than preserving meeting-only uniqueness where it
  blocks future revisions? [Consistency, Data Model, Research]
- [x] CHK009 Do cabinet query requirements select the correct current/accepted
  media revision and its latest result consistently? [Consistency, Contract
  `review-surface-contract.md`]
- [x] CHK010 Do local buffer retention requirements align with server lifecycle
  and deletion accounting after upload finalization? [Consistency, Spec US6,
  Data Model "Lifecycle Accounting"]

## Acceptance Criteria Quality

- [x] CHK011 Are infrastructure success criteria measurable without requiring
  real MediaScribe credentials in committed tests? [Measurability, Quickstart]
- [x] CHK012 Are quickstart commands scoped enough to prove the path without
  overclaiming production readiness? [Measurability, Quickstart]
- [x] CHK013 Are production claims limited to evidence boundaries such as
  local gate, infra smoke, or live dependency smoke? [Clarity, Current Status]

## Edge Case Coverage

- [x] CHK014 Are disk-full, object-store write failure, DB transaction failure,
  workflow-start failure, and MediaScribe import failure covered as requirement
  states? [Coverage, Spec US5/US6]
- [x] CHK015 Are cleanup requirements defined for temporary upload objects and
  failed/aborted upload sessions? [Coverage, Data Model]
