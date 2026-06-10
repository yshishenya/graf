# UX Checklist: Live Route Stability

**Purpose**: Validate user-facing route-status, passive-history, recording-control, and accessibility requirements before task generation.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the quality of requirements and planning artifacts. It does not test implementation behavior.

## Successful Autorepair UX

- [x] CHK001 Are successful-autorepair requirements clear that no required user action, disruptive modal, meeting settings reopen, app relaunch, or `Run Check` is part of clean acceptance? [Clarity, Spec §FR-032, Spec §FR-044, Spec §SC-022]
- [x] CHK002 Are passive status/history requirements complete enough to make successful autorepair visible to QA/history without interrupting the meeting user? [Completeness, Spec §FR-044, Spec §FR-045, Contract §Route Evidence Events]
- [x] CHK003 Are requirements consistent between quiet recovery for the meeting user and truthful passive status/history evidence for later review? [Consistency, Spec §Autorepair Product Rule, Plan §Summary]

## Failed And Blocked State UX

- [x] CHK004 Are non-recoverable state requirements clear enough to avoid false healthy UI while also avoiding infinite user prompts or retry churn? [Clarity, Spec §FR-029, Spec §FR-038, Contract §Autorepair State Machine]
- [x] CHK005 Are blocked/degraded user-facing copy requirements complete enough to explain artifact or route truth without making the user responsible for audio-engineering decisions? [Completeness, Spec §FR-018, Spec §FR-044]
- [x] CHK006 Are requirements clear that Bluetooth and AirPods-class default routes are deferred or not accepted for `019`, rather than silently claimed as working? [Clarity, Spec §FR-042, Spec §SC-020]

## Recording Visibility And Control

- [x] CHK007 Are requirements complete for preserving the visible recording indicator and one-action stop when autorepair runs while recording is active? [Completeness, Spec §FR-017, Spec §FR-030]
- [x] CHK008 Are requirements clear enough to distinguish routing-only live passthrough from active recording and assisted recording? [Clarity, Spec §FR-018]
- [x] CHK009 Are requirements consistent that live route stability work must not start hidden recording, stop recording invisibly, or dilute consent and control requirements? [Consistency, Constitution §II, Spec §FR-014, Spec §FR-017]

## Accessibility And Localization

- [x] CHK010 Are user-facing route-status requirements specified for localization-ready simple language rather than internal engineering terms? [UX, Spec §Constitutional Requirements, Plan §Constitution Check]
- [x] CHK011 Are accessibility requirements complete for passive status/history surfaces, including keyboard reachability and non-color-only communication? [Coverage, Spec §Constitutional Requirements]
- [x] CHK012 Are requirements clear that successful repair does not require a modal, while blocked or failure states remain accessible without hiding active capture state? [Clarity, Spec §FR-044, Constitution §II]

## User Action Audit

- [x] CHK013 Are requirements complete for recording user actions that invalidate clean acceptance, including `Run Check`, meeting device reselect, app relaunch, and settings reopen? [Completeness, Spec §Logging And Evidence Contract, Contract §Route Evidence Events]
- [x] CHK014 Are acceptance criteria measurable enough to prove no normal user action was required in accepted autorepair runs? [Measurability, Spec §SC-007b, Spec §SC-022]
- [x] CHK015 Are user-action audit requirements consistent with keeping `Run Check` as a diagnostic and development fallback only? [Consistency, Spec §FR-002, Spec §FR-003, Spec §SC-007]

## Scope And Brand Boundary

- [x] CHK016 Are UI/UX requirements scoped to route status/history and recording control without introducing dashboards, onboarding, landing pages, or `020` leakage UI? [Scope, Spec §Scope Boundary]
- [x] CHK017 Are clean-room and brand-distance requirements sufficient for any user-facing copy related to route stability and recovery? [UX, Constitution §Product And Platform Constraints, Spec §Constitutional Requirements]
