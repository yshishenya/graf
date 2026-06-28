# Pre-Implementation Readiness Checklist: Calendar Context Ingestion

**Purpose**: Validate that the post-`origin/master` 060 requirements and planning artifacts are complete, clear, bounded, and ready for implementation.
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and planning quality, not application behavior.

## Requirement Completeness

- [x] CHK001 Are the read-only calendar boundaries still complete after the latest master merge, including no calendar mutation, no sending, no auto-join, no auto-record, and no retrospective matching? [Completeness, Spec §FR-002, Spec §FR-025, Spec §FR-026]
- [x] CHK003 Are recording-time context, safe title fallback, participant roster, privacy lifecycle, and desktop prompt scenarios all represented in tasks with exact file paths? [Completeness, Tasks §Phases 3-8]

## Requirement Clarity

- [x] CHK004 Is the "whole calendar" scope still clarified as forward-only future sync rather than past-event import or retrospective matching? [Clarity, Spec §Clarifications, Spec §FR-022]
- [x] CHK005 Are one-minute join/open prompts and event-start record prompts specified without implying automatic recording in 060? [Clarity, Spec §FR-023, Spec §SC-011]
- [x] CHK006 Is the server-owned credential boundary clear enough to keep provider app passwords, OAuth refresh tokens, and service-app keys out of the desktop client? [Clarity, Plan §Constraints, Spec §Assumptions]

## Requirement Consistency

- [x] CHK007 Do calendar attendee, future-recipient candidate, meeting access, share grant, and speaker identity requirements remain separate and non-conflicting? [Consistency, Spec §FR-009, Spec §FR-010, Spec §User Story 7]
- [x] CHK008 Are disconnect, deletion, retention, backup expiry, diagnostics, and evidence requirements consistent with treating stored calendar context as meeting content under 2brain Rec control? [Consistency, Spec §FR-016, Spec §FR-018]
- [x] CHK009 Are tasks aligned with the current master touchpoints for ingest, cabinet, access/share, meeting lifecycle, desktop upload, capture UI, app wiring, and shared models? [Consistency, Tasks §Phase 5-9]

## Acceptance Criteria Quality

- [x] CHK010 Can provider coverage and field-preservation criteria be measured with synthetic fixtures without committing live calendar data or private screenshots? [Measurability, Spec §SC-002, Spec §SC-003, Spec §SC-007]
- [x] CHK011 Can no-egress criteria be objectively assessed for attendee emails, messages, share links, calendar updates, bot joins, hidden capture, auto-record, and retrospective matches? [Measurability, Spec §SC-010]
- [x] CHK012 Can desktop prompt timing criteria be objectively assessed for the one-minute join/open prompt and at-start record prompt while preserving visible Record/Stop control? [Measurability, Spec §SC-011]

## Dependencies & Assumptions

- [x] CHK013 Are external provider capability assumptions documented with enough specificity to avoid treating unavailable, unsupported, private, free-busy-only, or admin-policy-dependent fields as real data? [Assumption, Spec §FR-019, Provider Deep Dive]
- [x] CHK014 Are existing product dependencies documented for workspace identity, auth/session access, meeting access, deletion, upload, processing, review, and desktop capture controls? [Dependency, Spec §Assumptions, Tasks §Phase 2-10]
- [x] CHK015 Is the high-risk validation lane and release/deploy boundary explicit enough for implementation and later closeout? [Traceability, Plan §Risk / Validation Lane, Plan §Release Gate]

## Notes

- Reviewed after merging `origin/master` into `codex/060-calendar-context-ingestion`.
- No spec or plan changes were required by this checklist pass.
