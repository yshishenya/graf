# Post-Master Refresh Requirements Checklist: Calendar Context Ingestion

**Purpose**: Validate requirement quality after refreshing feature 060 from `origin/master` that includes feature 059 recording date/title metadata.
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)
**Master Baseline**: `origin/master` `94ffcb6` (`v2026.06.27.1`)

## Requirement Consistency After 059

- [x] PMR001 Are calendar title rules still explicit that `calendar` title source is allowed only from current or explicitly selected future event context at recording time, not from retrospective matching? [Consistency, Spec §FR-011, Spec §FR-012, Spec §FR-022, Spec §FR-026]
- [x] PMR002 Are 059 safe recording title/date fields compatible with 060 calendar context so generic/user/app-context titles remain valid when no calendar context is linked? [Consistency, Spec §User Story 3, Spec §FR-012, Spec §FR-013]
- [x] PMR003 Are manually supplied or user-renamed meeting titles still higher priority than later calendar title changes? [Consistency, Spec §FR-013]
- [x] PMR004 Is the future-only rule still clear after 059 introduced persisted `started_at` and `ended_at`, so existing/past recordings are not scanned for calendar matches? [Clarity, Spec §Clarifications, Spec §FR-022, Spec §SC-010]

## Scope Boundary After 059

- [x] PMR005 Are auto-record, "do not ask again", always-record automation, bot auto-join, and hidden capture still excluded from 060 despite desktop event-start prompts? [Scope, Spec §Clarifications, Spec §FR-023, Spec §FR-026]
- [x] PMR006 Are message sending, summary/transcript/report delivery, share grants, calendar invite updates, and calendar mutation still excluded even though attendee/recipient-candidate data is ingested? [Scope, Spec §FR-010, Spec §FR-025]
- [x] PMR007 Are participant roster requirements still separated from diarized speakers, access control, recipient authorization, and future speaker mapping? [Boundary, Spec §FR-009, Spec §FR-010, Spec §User Story 4]

## Validation And Evidence Readiness

- [x] PMR008 Are validation expectations still mapped to tests that cover the 059/060 interaction: create-meeting metadata, calendar context link, cabinet list/review, desktop queue/client, and no-egress boundaries? [Traceability, Tasks §T075, §T079-T082, §T085, §T123-T133]
- [x] PMR009 Are provider research and fixture requirements unaffected by 059, with Yandex/Mail.ru, Russian/on-prem CalDAV, Google, Microsoft Graph, Exchange EWS, and Bitrix24 still in scope? [Traceability, Spec §SC-002, Tasks §T014, §T023, §T031-T035, §T051-T057]
- [x] PMR010 Is evidence wording required to be refreshed after the new master baseline so old local CI results are not presented as post-refresh proof? [Evidence, Tasks §T001, §T127-T136]

## Notes

- This checklist validates written requirements and closeout readiness after the master refresh. It does not replace focused implementation tests or `infra/scripts/ci-local.sh`.
- One implementation risk was identified while applying this checklist: desktop queue refresh must preserve an already selected `calendarContextEventId` alongside 059 `recordingMetadata`. The requirement boundary is satisfied after preserving both fields and adding a regression test.
