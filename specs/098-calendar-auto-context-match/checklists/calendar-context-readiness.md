# Requirements Readiness Checklist: Calendar Auto Context Match

**Purpose**: Formal PR/release-review checklist for the completeness, clarity, consistency and measurability of 098 requirements across matching, privacy, lifecycle, API/UI, macOS and production closeout.
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Note**: This checklist evaluates the quality of the written requirements. It is not an implementation test plan.

## Requirement Completeness

- [x] CHK001 Are requirements defined for the complete live flow from non-blocking recording-start resolution through atomic meeting consumption and final context projection? [Completeness, Spec §FR-001–FR-005, Plan §Summary]
- [x] CHK002 Are durable requirements specified for every current state: automatic match, user-selected match, ambiguity, no context, private/all-day/stale/manual/offline skip, user clear and deletion? [Completeness, Spec §FR-014–FR-016, §FR-027–FR-033, Data Model §RecordingCalendarContextLink]
- [x] CHK003 Are title-provenance requirements complete for user-confirmed, calendar, app-context, generic, upload-provided, filename-derived and legacy titles? [Completeness, Spec §FR-017–FR-019, §FR-035–FR-036, Data Model §Meeting]
- [x] CHK004 Are match-time snapshot requirements complete for safe title, roster, event time, source evidence and recurring-series continuity after provider edits? [Completeness, Spec §FR-016, §FR-019–FR-020, §FR-024–FR-026]
- [x] CHK005 Are requirements defined for owner correction, ambiguity resolution, explicit continue-without-context and later clear/reselect behavior? [Completeness, Spec §FR-014–FR-015, §FR-038–FR-039]
- [x] CHK006 Are lifecycle requirements complete for unconsumed attempts, matched context, source disconnect, meeting deletion, retention reports and backup expiry? [Completeness, Spec §FR-019, §FR-041, Data Model §Lifecycle And Retention]

## Requirement Clarity

- [x] CHK007 Is the five-minute pre-start candidate window expressed with an exact inclusive/exclusive boundary and an explicit no-post-end rule? [Clarity, Research §Deterministic Matcher]
- [x] CHK008 Is a recently ended event's role clarified as an ambiguity blocker rather than a selectable sole candidate, including exact back-to-back boundaries? [Clarity, Spec §FR-014, Research §Deterministic Matcher]
- [x] CHK009 Is the provisional pre-start requirement clear about the final recording overlap needed before the calendar context becomes authoritative? [Clarity, API Contract §Meeting Creation Delta]
- [x] CHK010 Is “fresh calendar” quantified through the 24-hour threshold, latest-sync-failed rule and sync-horizon coverage? [Clarity, Spec §FR-028, Research §Freshness Contract]
- [x] CHK011 Is “relevant selected source” defined precisely enough to decide when one stale source vetoes an otherwise clear candidate? [Ambiguity, Research §Freshness Contract]
- [x] CHK012 Are strong duplicate identities defined without relying on title, organizer or time similarity, including cross-source provider-ID behavior? [Clarity, Spec §FR-047, Research §Strong Stable Evidence]

## Requirement Consistency

- [x] CHK013 Are 098's strict private/all-day auto-match exclusions explicitly consistent with 063 settings that may opt those categories into preview/prompts? [Consistency, Spec §FR-009–FR-010, UI Contract §Settings Boundary]
- [x] CHK014 Are single-event prompt requirements consistent with automatic provenance, while overlap choice remains user-selected provenance? [Consistency, Spec §FR-014–FR-015, UI Contract §macOS Prompt Semantics]
- [x] CHK015 Is the stable-title-on-clear decision consistent with the no-active-context label and title-source explanation across list/review surfaces? [Consistency, Spec §FR-018–FR-019, §FR-035, UI Contract §Clear Context]
- [x] CHK016 Are manual upload and offline recovery exclusions consistent across the spec, resolve/create contract, title precedence and user-facing reason copy? [Consistency, Spec §FR-011–FR-012, §FR-036, API Contract §Meeting Creation Delta]
- [x] CHK017 Are participant requirements consistent across roster display, access control, sharing, delivery, recurring context and speaker-label deferral? [Consistency, Spec §FR-020–FR-026, §FR-040, §FR-044–FR-045]
- [x] CHK018 Are automatic retries, user terminal states and explicit re-selection requirements mutually consistent and free of an automatic reattachment path? [Consistency, Spec §FR-027, §FR-038–FR-039, Data Model §State transitions]

## Acceptance Criteria Quality

- [x] CHK019 Can each functional requirement be traced to at least one measurable scenario or quickstart receipt, especially FR-028–FR-050? [Traceability, Spec §Functional Requirements, Quickstart §Server Integration Matrix]
- [x] CHK020 Are the performance requirements objectively measurable with stated p95 boundaries, sample conditions and a definition of MVP scale? [Measurability, Plan §Performance Goals]
- [x] CHK021 Are zero-side-effect criteria measurable for access grants, shares, recipients, delivery, calendar writes, auto-join and speaker renames? [Measurability, Spec §SC-008, API Contract §Side-Effect Prohibitions]
- [x] CHK022 Are web/browser and embedded-macOS parity criteria defined against one authoritative state and refresh point rather than only visual similarity? [Acceptance Criteria, Spec §SC-012, UI Contract §Embedded macOS Parity]
- [x] CHK023 Are migration, RLS, rollback, local CI, release, deploy and runtime-smoke success conditions stated separately so one narrow green check cannot prove full closeout? [Acceptance Criteria, Plan §Validation Plan, Quickstart §Migration and §Release]

## Scenario Coverage

- [x] CHK024 Are primary scenarios complete for clear current match, valid pre-start match, title application and roster availability variants? [Coverage, Spec §User Story 1, Quickstart §Server Integration Matrix]
- [x] CHK025 Are alternate scenarios complete for no calendar, no selected calendar, ad-hoc meeting, weak event signal and title that is unsafe to apply? [Coverage, Spec §User Story 2, §Edge Cases]
- [x] CHK026 Are exception scenarios complete for stale/latest-failed sync, provider unavailable, missing attempt, foreign/expired/consumed attempt and partial candidate loss? [Coverage, Exception Flow, Spec §FR-028, §FR-032]
- [x] CHK027 Are recovery scenarios complete for upload retry, app crash, queue rescan, source reconnect, user correction, user clear and meeting deletion? [Coverage, Recovery Flow, Spec §FR-027, §FR-038–FR-041]
- [x] CHK028 Are concurrency requirements defined for duplicate resolve keys, simultaneous meeting creates, simultaneous selections and one authoritative context row? [Coverage, Edge Case, Spec §FR-027, API Contract §Recording-Start Resolve]
- [x] CHK029 Are recurring scenarios complete for first occurrence, missing series metadata, authorized predecessor, deleted/inaccessible/cross-space predecessor and current-context stability? [Coverage, Spec §User Story 5, §FR-024–FR-026, §FR-045]

## Edge Case Coverage

- [x] CHK030 Are exact timing edges specified for event start, event end, five-minute grace, five-minute recent-end guard, zero-duration overlap and long recordings spanning later events? [Edge Case, Spec §Edge Cases, Research §Deterministic Matcher]
- [x] CHK031 Are duplicate/recurrence edges addressed for provider copies, conference-link hashes, recurrence instances, missing series IDs and iCalendar UID fallback? [Edge Case, Spec §FR-024, §FR-047, Data Model §Matching Invariants]
- [x] CHK032 Are candidate/roster truncation and disappearing/deleted candidate requirements defined without exposing hidden counts or stale details? [Edge Case, Data Model §CalendarRosterSnapshotItem, API Contract §Read Meeting Calendar Context]
- [x] CHK033 Are legacy migration edges documented for multiple historical links, active-link selection, absent safe snapshots and non-overwritable legacy titles? [Edge Case, Data Model §Migration reconciliation]

## Non-Functional Requirements

- [x] CHK034 Are authorization requirements specified for resolve, consume, read, choose, clear and recurring predecessor access, including not-found semantics across user/workspace boundaries? [Coverage, Spec §FR-003–FR-004, API Contract §Common Rules]
- [x] CHK035 Are tenant-isolation/RLS requirements documented for every new workspace-scoped entity and for SQLite/PostgreSQL validation parity? [Completeness, Data Model §RLS And Portability]
- [x] CHK036 Are sensitive-data requirements explicit for persisted attempts, context snapshots, roster JSON, API projections, audit metadata, diagnostics and evidence? [Completeness, Spec §FR-029–FR-030, Data Model §Audit Model]
- [x] CHK037 Are accessibility requirements defined for keyboard flow, radio grouping, focus restoration, live announcements, target size, status semantics and private accessible labels? [Coverage, UI Contract §Accessibility]
- [x] CHK038 Are localization requirements complete for all states/actions, recording-time timezone formatting and Russian/English message pairs without internal reason codes? [Coverage, UI Contract §Localization]
- [x] CHK039 Are fail-soft requirements quantified so resolve/provider/calendar failure cannot block capture, meeting creation, upload, processing, playback or review? [Clarity, Spec §FR-032, Plan §Performance Goals]
- [x] CHK040 Is the standalone security-audit deferral written consistently so acceptance privacy tests remain mandatory but are not misreported as the deferred Codex Security scan? [Consistency, Spec §SC-011, Research §Validation Boundary]

## Dependencies And Release Boundaries

- [x] CHK041 Are reused 059/060/063 contracts identified precisely, including which existing behavior is preserved versus superseded by 098? [Dependency, Spec §Dependencies, Plan §Structure Decision]
- [x] CHK042 Are 098 owner/workspace boundaries specified independently enough that skipped feature 097 is not an implementation prerequisite? [Dependency, Spec §Session 2026-07-13, §Dependencies]
- [x] CHK043 Are canonical OpenAPI, feature-local contracts, macOS payload compatibility and old-client safe defaults all included in requirements traceability? [Dependency, API Contract §Purpose and §Meeting Creation Delta]
- [x] CHK044 Are release requirements complete for changelog, product-status truth, task/issue reconciliation, PR/merge SHA, CalVer tag, Russian release notes, migration, deploy, smoke and cleanup? [Completeness, Quickstart §Release And Production Closeout]
- [x] CHK045 Are out-of-scope boundaries explicit enough to prevent auto-record, provider writes, auto-share/delivery, speaker identity, retrospective scanning, multi-event timelines or a duplicate native review UI from entering implementation? [Boundary, Spec §Out of Scope, UI Contract §Forbidden UI Side Effects]
- [x] CHK046 Are start-time decline and later clear specified as distinct durable states with separate semantics and evidence? [Consistency, Spec §FR-051, Data Model §RecordingCalendarMatchAttempt, UI Contract §Correction And Clear Contract]
- [x] CHK047 Is attempt lifetime normative and measurable as exactly 24 hours after server evaluation, including boundary rejection and purge eligibility? [Clarity, Spec §FR-052, API Contract §Recording-Start Resolve, Data Model §Lifecycle And Retention]

## Notes

- Check items off only after reading the final spec, plan, research, data model, contracts and quickstart together.
- Record any unresolved wording gap inline and update the authoritative requirement before implementation tasks are accepted.
- This checklist does not execute tests or validate implementation behavior.
- Final reconciliation on 2026-07-13 reread all authoritative requirement and
  validation artifacts. The 47 items remain complete as requirement-quality
  questions. Local CI, commit/PR, browser visual QA, release/deploy/runtime
  proof and the deferred standalone security scan remain separate execution
  gates and are not claimed by the checkmarks above.
