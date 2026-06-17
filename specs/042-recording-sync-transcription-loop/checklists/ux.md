# UX Review Checklist: Recording Sync And Transcription Loop

**Purpose**: Validate requirement quality for desktop queue visibility, browser
review, embedded desktop review, out-of-sync states, accessibility, and copy.
**Created**: 2026-06-18
**Feature**: `specs/042-recording-sync-transcription-loop/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [ ] CHK001 Are user-visible labels required for every queue/review state:
  local-only, queued, uploading, retrying, uploaded, submitted, processing,
  ready, partial, blocked, failed, deleted, and conflict? [Completeness, Spec
  US5, Contract `review-surface-contract.md`]
- [ ] CHK002 Are next-action requirements defined for automatic retry, manual
  retry, stop retry, open review, wait, contact operator, auth required, and
  deletion/access blocked states? [Completeness, Spec US5]
- [ ] CHK003 Are requirements defined for both web browser review and embedded
  desktop review, including what is shared and what remains native-only?
  [Completeness, Spec US4, Contract `review-surface-contract.md`]
- [ ] CHK004 Are empty, partial, processing, failed, and unavailable transcript
  states described without fake transcript/notes content? [Completeness, Spec
  US4/US6]

## Requirement Clarity

- [ ] CHK005 Is the desktop/web authority boundary clear: native controls own
  capture/upload truth, server web owns transcript/review/governance truth?
  [Clarity, Plan Implementation Approach]
- [ ] CHK006 Are copy requirements clear enough to avoid overpromising offline
  upload success when local package quality/privacy gates block upload?
  [Clarity, Spec US1/US5]
- [ ] CHK007 Are notes/action requirements explicitly deferred or made
  available based on stored generated outcomes, not implied by transcript
  readiness? [Clarity, Contract `review-surface-contract.md`]

## Requirement Consistency

- [ ] CHK008 Do web and embedded desktop review requirements use the same status
  taxonomy and media revision provenance? [Consistency, Contract
  `review-surface-contract.md`]
- [ ] CHK009 Do future editing/video affordances remain out of scope in visible
  copy and requirements while preserving revision provenance? [Consistency,
  Spec Clarifications, Post-MVP backlog]
- [ ] CHK010 Are desktop review links consistent with server meeting identity,
  avoiding local-only review claims? [Consistency, Contract
  `desktop-sync-contract.md`]

## Accessibility & Localization Requirements

- [ ] CHK011 Are accessibility requirements defined for queue rows, retry
  controls, review links, processing states, transcript sections, and conflict
  notices? [Gap, UX Non-Functional]
- [ ] CHK012 Are localization-safe labels and reason-code mapping requirements
  defined for Russian MVP copy and future English/admin surfaces?
  [Gap, UX Non-Functional]
- [ ] CHK013 Are responsive requirements defined for browser and desktop
  embedded review surfaces at compact widths? [Gap, Contract
  `review-surface-contract.md`]

## Edge Case Coverage

- [ ] CHK014 Are requirements defined for offline embedded review, not
  configured server URL, expired session, denied meeting, deleted meeting, and
  server timeout states? [Coverage, Spec US5]
- [ ] CHK015 Are status/progress requirements defined for large uploads without
  exposing private filenames or local paths? [Coverage, Spec US3/US6]
