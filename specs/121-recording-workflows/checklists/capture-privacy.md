# Capture And Privacy Requirements Checklist: Complete Recording Workflows

**Purpose**: Validate capture, custody, privacy, and recovery requirement quality before implementation
**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are pre-start microphone and system-audio readiness requirements defined independently? [Completeness, Spec §FR-001]
- [x] CHK002 Are manual Start and detect-and-ask requirements both documented without implying hidden auto-start? [Completeness, Spec §FR-002–FR-003]
- [x] CHK003 Are starting, active, paused, stopping, finalizing, local-custody, upload, processing, and deletion states all covered? [Coverage, Spec §FR-004–FR-018]
- [x] CHK004 Are source-loss and degraded-capture requirements defined separately from ordinary silence? [Completeness, Spec §FR-009–FR-010, Edge Cases]
- [x] CHK005 Are offline capture, crash recovery, retry, and last-usable-copy requirements documented? [Coverage, Spec §FR-011–FR-018]

## Requirement Clarity

- [x] CHK006 Is one-action Stop defined across main, titlebar, menu-bar, active, paused, and embedded-route states? [Clarity, Spec §US2, FR-005–FR-008]
- [x] CHK007 Is Pause clearly defined as suppressing both product-owned sources rather than a second microphone-only mute? [Clarity, Spec §FR-006, Out of Scope]
- [x] CHK008 Is recovery behavior explicit about preservation/finalization rather than promising seamless repair? [Clarity, Spec §FR-015–FR-018]
- [x] CHK009 Are local custody and server acceptance described as different states with measurable consequences? [Clarity, Spec §US3, FR-011–FR-016]

## Consistency And Trust Boundaries

- [x] CHK010 Do capture requirements remain consistent with the system-audio-first v5 package dependency and removed legacy routing boundary? [Consistency, Spec §Product Scope, Assumptions]
- [x] CHK011 Do browser/embedded requirements preserve native capture authority and persistent Stop? [Consistency, Spec §FR-023–FR-024]
- [x] CHK012 Do MediaScribe and credential requirements keep all dependency calls server-side? [Consistency, Spec §FR-055]
- [x] CHK013 Are meeting-app mute claims excluded while product Pause remains explicit? [Consistency, Spec §Out of Scope]

## Scenario And Edge-Case Coverage

- [x] CHK014 Are duplicate Start and rapid Pause/Resume/Stop ordering requirements addressed? [Coverage, Spec §Edge Cases, SC-003]
- [x] CHK015 Are permission revocation, device removal, sleep/wake, disk limits, and maximum duration addressed? [Coverage, Spec §Edge Cases]
- [x] CHK016 Are upload authentication expiry, network flapping, duplicate finalize, and relaunch addressed? [Coverage, Spec §US3, Edge Cases]
- [x] CHK017 Are failure requirements artifact-specific so playback/transcript/summary availability does not collapse into one state? [Coverage, Spec §FR-017–FR-018, FR-025]

## Measurability And Evidence Safety

- [x] CHK018 Can stop reachability, duplicate prevention, crash recovery, and timeline alignment be objectively measured? [Measurability, Spec §SC-002–SC-005]
- [x] CHK019 Are full-content Langfuse AI observations, plaintext Temporal History, and retained Generation Call storage separated from ordinary metadata-only logs, screenshots, audit, diagnostics, and committed evidence, with raw audio/runtime credentials never deliberately attached? [Observability, Spec §FR-056, FR-071, FR-088, SC-011]
- [x] CHK020 Are local, repository, installed-app, production, and release evidence boundaries distinguished? [Completeness, Spec §SC-012, Dependencies/Out of Scope]

## Notes

- 20/20 requirement-quality checks re-pass on 2026-07-22 against constitution
  v4.0.0 and the plaintext observability boundary.
- Implementation evidence belongs in `quickstart.md`; these checks validate the
  written contract, not runtime behavior.
