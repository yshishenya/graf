# UX Requirements Checklist: MVP Product Experience And Design System

**Purpose**: Validate that UX, interaction, accessibility, localization, and owner-value-loop requirements are complete, clear, measurable, and consistent before task generation.
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirement quality only. It does not verify UI implementation.

## Requirement Completeness

- [x] CHK001 Are requirements defined for every step in the owner value loop: sign-in/local policy, desktop idle, active recording, stop, local saved/queued, upload/transcription status, manual upload, complete review, degraded/failure, browser-only handoff, and deletion/access entry? [Completeness, Spec §FR-027, Quickstart §6]
- [x] CHK002 Are native desktop trust-shell requirements complete for readiness, recording, Stop, local artifact truth, upload queue truth, server/account status, and degraded/offline states? [Completeness, Spec §US2, Spec §FR-002, Spec §FR-003]
- [x] CHK003 Are embedded desktop cabinet subset requirements complete for account, workspace, recent meetings, upload, processing, meeting review, session recovery, and basic settings entry points? [Completeness, Spec §FR-004-FR-006, Contract route-visibility]
- [x] CHK004 Are browser web cabinet requirements complete enough to distinguish full browser product surfaces from desktop-embedded subset surfaces? [Completeness, Spec §FR-008, Data Model §Server Web Cabinet]
- [x] CHK005 Are meeting review requirements complete for transcript, playback context, summary, decisions, action items, source/status provenance, clear next actions, and unavailable states? [Completeness, Spec §FR-028, Contract cross-surface-status]
- [x] CHK006 Are manual media upload UX requirements complete for audio files, common video/meeting files, unsupported media, no-audio media, duplicate media, and audio-first copy boundaries? [Completeness, Spec §FR-011-FR-013]

## Requirement Clarity

- [x] CHK007 Is "allowlisted desktop-relevant subset" clarified with explicit route classifications and default behavior for unknown routes? [Clarity, Spec §FR-009, Contract route-visibility]
- [x] CHK008 Is "current status everywhere" defined through named statuses rather than vague status copy? [Clarity, Spec §FR-029, Contract cross-surface-status]
- [x] CHK009 Are requirements clear about what "complete meeting review" includes and what remains unavailable or degraded? [Clarity, Spec §FR-028, Spec §SC-014]
- [x] CHK010 Is "modern 2026 minimal UX" translated into concrete design-system requirements such as density, typography roles, color roles, component families, icon rules, and light/dark behavior? [Clarity, Spec §FR-015, Data Model §Design System Contract]
- [x] CHK011 Are browser-only handoff requirements clear enough to avoid users interpreting hidden/disabled routes as app failure? [Clarity, Contract route-visibility]
- [x] CHK012 Are visual artifact requirements clear about the difference between static visual pack, clickable prototype, route matrix, state matrix, component inventory, and QA checklist? [Clarity, Spec §FR-026]

## Requirement Consistency

- [x] CHK013 Are desktop and web requirements consistent about upload success not implying transcript readiness or notes readiness? [Consistency, Spec §SC-005, Contract cross-surface-status]
- [x] CHK014 Are native capture boundary requirements consistent across spec, route visibility contract, prototype handoff contract, and quickstart? [Consistency, Spec §FR-007, Contract route-visibility, Quickstart §4]
- [x] CHK015 Are manual upload requirements consistent with the audio-first MVP promise and the deferred full-video UX boundary? [Consistency, Spec §FR-011-FR-013, Research §Manual Upload]
- [x] CHK016 Are desktop embedded cabinet requirements consistent with the ADR rule that server-rendered UI must not own capture-critical truth? [Consistency, Spec §FR-004-FR-007, Plan §Constitution Check]
- [x] CHK017 Are design-system requirements consistent across macOS native desktop, embedded cabinet, and browser cabinet surfaces without forcing macOS capture UI onto future platforms? [Consistency, Spec §US4, Spec §FR-010]

## Acceptance Criteria Quality

- [x] CHK018 Can the 95% primary-journey coverage criterion be objectively evaluated from the written artifacts and prototype? [Measurability, Spec §SC-003, Quickstart §6]
- [x] CHK019 Can the route visibility requirement be objectively evaluated for 100% of cabinet routes and navigation elements? [Measurability, Spec §SC-007, Contract route-visibility]
- [x] CHK020 Can the embedded cabinet native-boundary review be objectively evaluated for every embedded screen? [Measurability, Spec §SC-008]
- [x] CHK021 Are criteria defined for deciding whether a meeting review screen is "complete", "partial", "degraded", or "failed"? [Acceptance Criteria, Spec §FR-014, Spec §SC-014]
- [x] CHK022 Are success criteria written so reviewers can distinguish missing requirements from design preference disagreements? [Acceptance Criteria, Spec §SC-001-SC-015]

## Scenario Coverage

- [x] CHK023 Are primary, alternate, exception, recovery, and non-functional UX scenarios represented in the requirements? [Coverage, Spec §User Scenarios, Spec §Edge Cases]
- [x] CHK024 Are requirements defined for signed-out-but-local-recording-allowed states without implying upload or server access? [Coverage, Spec §Edge Cases]
- [x] CHK025 Are requirements defined for transcription-in-progress states in both app and web without showing an empty or misleading transcript page? [Coverage, Spec §US3 Scenario 6]
- [x] CHK026 Are requirements defined for app/web temporary status disagreement, including which source of truth wins and how the user-facing copy stays truthful? [Coverage, Spec §Edge Cases, Contract cross-surface-status]
- [x] CHK027 Are requirements defined for browser-only handoff from desktop, including the user goal, route class, and next action? [Coverage, Contract route-visibility]
- [x] CHK028 Are requirements defined for no-meetings empty state, upload empty state, processing empty state, and review unavailable state? [Coverage, Spec §US3]

## Accessibility And Localization Requirements

- [x] CHK029 Are keyboard navigation, focus, screen reader labels, contrast, text overflow, and non-color status requirements specified for all interactive desktop and web surfaces? [Coverage, Spec §FR-018]
- [x] CHK030 Are light and dark theme requirements complete for status badges, warnings, transcript/review reading, embedded cabinet, and native desktop controls? [Completeness, Spec §FR-015, Spec §SC-006]
- [x] CHK031 Are localization requirements defined for Russian and English status/copy categories across recording, upload, transcription, review, auth, deletion, and policy states? [Coverage, Spec §FR-019]
- [x] CHK032 Is long technical status text constrained with requirements for compact desktop surfaces and responsive web layouts? [Clarity, Spec §Edge Cases, Spec §FR-018]

## Ambiguities And Conflicts

- [x] CHK033 Are any terms such as "dashboard", "cabinet", "meeting review", "notes ready", or "degraded" used with conflicting meanings across artifacts? [Ambiguity, Spec §Key Entities, Contract cross-surface-status]
- [x] CHK034 Are deferred UX surfaces clearly identified so tasks do not accidentally include broad admin, billing, team management, sharing, downloads, detailed audit, help/legal, or full video UX? [Scope, Spec §FR-030]
- [x] CHK035 Are requirements clear about which visuals are product commitments versus prototype examples that may change during implementation? [Ambiguity, Contract prototype-handoff]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline.
- These items validate requirements quality, not implementation behavior.
