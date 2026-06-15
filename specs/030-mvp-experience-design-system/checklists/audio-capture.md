# Audio Capture Requirements Checklist: MVP Product Experience And Design System

**Purpose**: Validate that requirements protect macOS capture truth, local recording authority, permission clarity, and track-status expectations in the design/prototype artifacts. This checklist tests the written requirements, not the implementation.
**Created**: 2026-06-11
**Feature**: 030-mvp-experience-design-system

## Requirement Completeness

- [x] CHK001 Are requirements complete for every desktop capture-critical state: idle, permission-blocked, ready, active, stopping, saved-local, degraded, failed, local-only, queued, and offline/server-stale? [Completeness, Data Model §Desktop Trust Shell, Spec §FR-002-FR-003]
- [x] CHK002 Are requirements complete for preserving visible active recording truth and one-action Stop across native home, live recording, embedded cabinet, meeting review, and degraded states? [Completeness, Spec §US2, Spec §FR-003, Spec §FR-007]
- [x] CHK003 Are requirements complete for microphone, system-audio, screen/system capture, and permission recovery states without authorizing production capture implementation in this slice? [Completeness, Constitution §I, Spec §FR-031]
- [x] CHK004 Are requirements complete for distinguishing local artifact truth from upload queue truth and server processing truth after Stop? [Completeness, Spec §FR-003, Spec §FR-029, Contract cross-surface-status]
- [x] CHK005 Are requirements complete for system-audio-first MVP positioning while keeping virtual-driver routing outside MVP acceptance and outside this design slice? [Completeness, Constitution §I, Plan §Constitution Check]
- [x] CHK006 Are requirements complete for manual recording availability, assisted auto-start boundaries, and policy-gated recording states in user-facing design artifacts? [Completeness, Constitution §II, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK007 Is "native local authority" defined clearly enough to prevent server-loaded UI from owning, delaying, restyling, or contradicting recording truth? [Clarity, Spec §FR-003, Spec §FR-007, Data Model §Desktop Trust Shell]
- [x] CHK008 Is "visible recording indicator" specified with enough artifact-level detail to make all desktop states reviewable without copying OS or Krisp-specific indicator patterns? [Clarity, Spec §FR-016, Quickstart §8]
- [x] CHK009 Are permission-blocked and recovery states described clearly enough for designers to know the difference between microphone permission, system-audio/screen permission, server auth, and workspace policy? [Clarity, Constitution §I-II, Data Model §Desktop Trust Shell]
- [x] CHK010 Are "local only", "queued", "uploading", "uploaded", and "transcription" defined clearly enough to prevent users from reading upload as capture success or transcript readiness? [Clarity, Contract cross-surface-status]
- [x] CHK011 Is the boundary between recording controls, upload controls, and meeting review controls clear across desktop, embedded cabinet, and browser cabinet surfaces? [Clarity, Spec §FR-004-FR-008, Contract route-visibility]
- [x] CHK012 Are audio-first manual upload requirements clear about usable audio extraction from common video/meeting files without promising video-native review? [Clarity, Spec §FR-011-FR-013]

## Requirement Consistency

- [x] CHK013 Are capture-truth requirements consistent between the constitution, spec, plan, data model, route contract, status contract, and quickstart? [Consistency, Constitution §I-II, Spec §FR-003, Plan §Post-Design Constitution Check]
- [x] CHK014 Are embedded cabinet rules consistent with the requirement that server-rendered content cannot obscure Stop, active recording state, permissions, local queue truth, or recovery actions? [Consistency, Spec §FR-007, Contract route-visibility]
- [x] CHK015 Are manual upload and desktop-recorded meeting states consistent about track truth when uploaded media lacks separate microphone/system tracks? [Consistency, Spec §Edge Cases, Data Model §Media Upload Flow]
- [x] CHK016 Are future multiplatform contracts consistent with keeping each platform's capture trust shell native rather than forcing macOS capture UI onto other platforms? [Consistency, Spec §US4, Spec §FR-010]
- [x] CHK017 Are clean-room visual requirements consistent with capture UI needs so the product does not copy Krisp or OS-specific recording affordances while still communicating recording state clearly? [Consistency, Spec §FR-016-FR-017, Quickstart §8]
- [x] CHK018 Are active recording and server/account/auth states consistently separated so sign-out or server outage cannot imply local capture has stopped or local files are deleted? [Consistency, Spec §US2, Spec §Edge Cases]

## Acceptance Criteria Quality

- [x] CHK019 Can reviewers objectively determine whether 100% of desktop capture-critical states preserve visible local recording truth and one-action Stop? [Measurability, Spec §SC-002]
- [x] CHK020 Can reviewers objectively determine whether 100% of embedded desktop cabinet screens preserve the native capture boundary? [Measurability, Spec §SC-008]
- [x] CHK021 Are acceptance criteria defined for status disagreements between desktop and web without requiring implementation behavior to be tested in this slice? [Acceptance Criteria, Spec §SC-013, Contract cross-surface-status]
- [x] CHK022 Are capture-related success criteria written so reviewers can distinguish missing requirements from visual preference disagreements? [Acceptance Criteria, Spec §SC-002, Spec §SC-008, Spec §SC-015]
- [x] CHK023 Are measurable criteria defined for text overflow and compact-control clarity where capture status and Stop must remain visible? [Measurability, Spec §FR-018, Quickstart §8]

## Scenario Coverage

- [x] CHK024 Are primary recording scenarios represented for idle, ready, active recording, Stop, local saved, queued, uploading, and completed review? [Coverage, Spec §US2, Data Model §Owner Value Loop]
- [x] CHK025 Are alternate scenarios represented for signed-out local recording, server-offline recording, stale policy, and embedded cabinet unavailability? [Coverage, Spec §Edge Cases]
- [x] CHK026 Are exception scenarios represented for permission denied, capture degraded, recording failed, local package damaged, upload blocked, and server status unavailable? [Coverage, Constitution §I, Spec §US2]
- [x] CHK027 Are recovery scenarios represented for permission recovery, retry upload, handoff to browser, and returning from browser-only route while recording truth stays local? [Coverage, Contract route-visibility, Spec §Edge Cases]
- [x] CHK028 Are non-functional capture UX scenarios represented for accessibility, localization, light/dark themes, non-color status, and compact desktop surfaces? [Coverage, Spec §FR-018-FR-019]

## Edge Case Coverage

- [x] CHK029 Are requirements defined for user-owned uploads that have mixed, missing, or non-separated microphone/system audio tracks? [Coverage, Spec §Edge Cases, Data Model §Media Upload Flow]
- [x] CHK030 Are requirements defined for active recording while browser-only cabinet routes are hidden, disabled, or handed off? [Coverage, Contract route-visibility]
- [x] CHK031 Are requirements defined for transcription-in-progress and partial/degraded meeting review without making capture, upload, or processing truth ambiguous? [Coverage, Spec §US3, Contract cross-surface-status]
- [x] CHK032 Are requirements defined for local file existence disagreements, such as meeting exists locally but not on server or exists on server but not locally? [Coverage, Spec §Edge Cases]

## Dependencies & Assumptions

- [x] CHK033 Are assumptions about implemented `014` desktop upload and `015` processing documented as context for capture-status design rather than new capture implementation scope? [Dependency, Plan §Technical Context, Research §Owner Value Loop]
- [x] CHK034 Are dependencies on future native capture/UI implementation slices traceable without allowing this design checklist to approve capture code, drivers, installers, or production rollout? [Scope, Spec §FR-031]
- [x] CHK035 Is there any ambiguity about whether audio-capture requirements in this checklist are design-readiness gates rather than runtime QA tests? [Ambiguity, Plan §Summary, Quickstart §Purpose]
