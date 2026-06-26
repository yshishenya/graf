# UX Custody Checklist: Local Upload Custody

**Purpose**: Validate requirement quality for native custody status, user
actions, server-list authority, accessibility, localization, and compact
right/control surface behavior.
**Created**: 2026-06-26
**Feature**: `specs/057-local-upload-custody/spec.md`

**Note**: This checklist tests whether requirements are complete, clear,
consistent, and measurable. It does not test implementation behavior.

## Requirement Completeness

- [x] CHK001 Are requirements defined for zero, one, and many local custody
  items across all-synced, uploading, offline, auth-required, admin-blocked,
  cannot-send, retention-warning, and terminal states? [Completeness, Spec US4,
  FR-020-FR-022]
- [x] CHK002 Are normal user actions fully enumerated and limited to meaningful
  actions the meeting owner can perform? [Completeness, Spec FR-010-FR-012,
  Action Policy]
- [x] CHK003 Are server-known and server-unknown presentation requirements
  complete enough to prevent duplicate native/WebView meeting rows?
  [Completeness, Spec US2, Authority Model, FR-006-FR-009]
- [x] CHK004 Are expanded local details requirements defined without turning
  the UI into a task queue or exposing transport internals? [Completeness, Spec
  US4, FR-021-FR-022]

## Requirement Clarity

- [x] CHK005 Is "local upload is not a user task" translated into concrete UI
  requirements for copy, actions, and default surfaces? [Clarity, Spec Product
  Thesis, US3, User-Facing State Model]
- [x] CHK006 Are warning states separated from calm automatic states with clear
  criteria for when warning styling or notification is allowed? [Clarity, Spec
  State Priority And Notification Policy]
- [x] CHK007 Is review-route availability defined so local-only custody cannot
  create or imply a server review route? [Clarity, Spec Authority Model,
  FR-045]
- [x] CHK008 Are Russian-ready copy requirements concrete enough to avoid
  blaming the user for transport, server, policy, or product failures?
  [Clarity, Spec FR-032, User-Facing State Model]

## Requirement Consistency

- [x] CHK009 Do native shell requirements align with the server-owned WebView
  authority model and feature `058` presentation ownership? [Consistency, Spec
  Server Web Refactor Boundary, Plan Structure Decision]
- [x] CHK010 Are normal UI forbidden actions consistent across user stories,
  functional requirements, action policy, and contracts? [Consistency, Spec
  US3, FR-010, Action Policy, Contract `desktop-custody-contract.md`]
- [x] CHK011 Are accessibility requirements consistent between collapsed
  inspector, narrow window, and increased text-size/zoom states? [Consistency,
  Spec SC-017, Notification Policy]

## Acceptance Criteria Quality

- [x] CHK012 Are UX success criteria measurable enough to validate user
  comprehension within 10 seconds and no duplicate list rows? [Measurability,
  Spec SC-002, SC-003, SC-011]
- [x] CHK013 Are foreground, background, hidden, and WebView-not-open cases
  represented in requirements without depending on route navigation?
  [Coverage, Spec Edge Cases, FR-039]

## Edge Case Coverage

- [x] CHK014 Are requirements defined for retention deadline, disk pressure,
  terminal undelivered, and cannot-send states without promising recovery?
  [Coverage, Spec US1, User-Facing State Model]
- [x] CHK015 Are requirements defined for safe incident/report actions when the
  normal user cannot fix the blocker? [Coverage, Spec US5, FR-023-FR-024]

## Implementation Evidence

- US4 custody status now uses `DesktopUploadCustodySummary` copy keys instead
  of transport queue labels; automatic upload states do not expose Retry or
  Stop retry controls to normal users.
- The collapsed shell counts only real meeting-owner actions, while automatic
  saved/uploading custody is shown as neutral local-safekeeping status.
- Secondary custody details are rendered in the native inspector disclosure
  outside the server-owned WebView and include explicit local-delete
  confirmation copy without exposing file paths, audio, transcripts, tokens, or
  signed URLs.
