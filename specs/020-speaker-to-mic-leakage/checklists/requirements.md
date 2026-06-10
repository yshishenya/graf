# Specification Quality Checklist: Speaker-To-Mic Leakage Control

**Purpose**: Validate specification completeness and quality before proceeding
to clarification and planning.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details are required to understand user value.
- [x] Focused on user value, capture integrity, recording truth, and privacy.
- [x] Written for product, QA, and engineering stakeholders.
- [x] All mandatory sections completed.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain.
- [x] Requirements are testable and unambiguous enough for clarification.
- [x] Success criteria are measurable.
- [x] Success criteria are technology-agnostic.
- [x] All acceptance scenarios are defined.
- [x] Edge cases are identified.
- [x] Scope is clearly bounded.
- [x] Dependencies and assumptions identified.

## Feature Readiness

- [x] Functional requirements have clear acceptance criteria.
- [x] User scenarios cover live route, recording artifact, UX recovery,
  diagnostics, and clean-room constraints.
- [x] Feature meets measurable outcomes defined in Success Criteria.
- [x] No proprietary Krisp implementation detail is copied or required.

## Notes

- Clarification is mandatory before planning because the feature touches audio
  routing, recording truth, driver readiness, privacy diagnostics, and UX
  recovery states.
- Planning must define the leakage threshold, controlled validation method,
  route matrix, AEC/dependency decision, timeline-alignment strategy, and
  metadata-only evidence contract.

## Post-Clarification Requirement Completeness

- [x] CHK001 Are finalized-package leakage statuses fully specified for `clean`, `leakage_detected`, `unproven`, `not_measured`, and `not_applicable`, including when each status is allowed? [Completeness, Spec §FR-006, Spec §FR-010]
- [x] CHK002 Are transcription-readiness requirements complete for clean original tracks, contaminated original tracks, unproven packages, not-measured packages, and derived cleaned tracks? [Completeness, Spec §FR-003b, Spec §FR-010a.1, Spec §FR-011, Spec §FR-028]
- [x] CHK003 Are requirements explicit that final leakage truth is assigned only after stop/finalization and not from preflight, live UI, or route class? [Clarity, Spec §FR-001, Spec §FR-010a, Spec §SC-019]
- [x] CHK004 Are requirements complete for preserving original `mic.wav` and `incoming.wav` when post-recording cleanup creates derived artifacts? [Completeness, Spec §FR-003b.1, Spec §FR-010a.1, Spec §SC-020]
- [x] CHK005 Are lineage, confidence, residual-leakage, and usability requirements defined for every derived cleaned track before it can affect transcription readiness? [Completeness, Spec §FR-003b.1, Spec §FR-010a.1]

## Requirement Clarity

- [x] CHK006 Is the accepted leakage threshold defined or explicitly deferred to planning with required threshold dimensions such as intelligibility, level, confidence, and threshold version? [Clarity, Spec §FR-014, Spec §SC-001, Spec §SC-004]
- [x] CHK007 Is "clean dual-track acceptance" clarified enough for planning to compare Apple voice processing, WebRTC AEC3, app-side graph changes, post-processing, and mixed-audio fallback? [Clarity, Spec §FR-003a, Spec §FR-003e, Spec §SC-015]
- [x] CHK008 Is "common built-in speakerphone use" specific enough to guide the required built-in Mac microphone plus built-in Mac speakers go/no-go decision? [Clarity, Spec §FR-003a, Spec §SC-015]
- [x] CHK009 Are `unproven` and `not_measured` distinguished clearly enough that finalization cannot choose either label arbitrarily? [Clarity, Spec §FR-010, Spec §SC-005]
- [x] CHK010 Is the boundary between acoustic leakage suspicion and direct software loopback suspicion defined with measurable evidence expectations? [Clarity, Spec §FR-012, Spec §US4]

## Requirement Consistency

- [x] CHK011 Are requirements consistent between "no live leakage cleanup" and allowing post-recording cleanup as a derived artifact? [Consistency, Spec §FR-003, Spec §FR-003b.1, Spec §FR-010b]
- [x] CHK012 Are requirements consistent between preserving dual-track semantics and permitting a later mixed-audio fallback only after clean dual-track spikes fail? [Consistency, Spec §FR-003d, Spec §FR-003e, Spec §FR-027, Spec §SC-018]
- [x] CHK013 Are requirements consistent between not blocking live route readiness and collecting route metadata for finalization evidence? [Consistency, Spec §FR-006, Spec §FR-007, Spec §SC-006]
- [x] CHK014 Are requirements consistent between driver-first separate-track constitution obligations and the alternative architecture paths allowed by the feature? [Consistency, Constitution §I, Spec §FR-003b, Spec §FR-003d]
- [x] CHK015 Are requirements consistent between metadata-only diagnostics and using real meeting artifacts as leakage evidence? [Consistency, Spec §FR-014, Spec Edge Cases, Constitution §III]

## Acceptance Criteria Quality

- [x] CHK016 Are leakage success criteria measurable without relying on subjective terms such as "usable", "intelligible", or "clean" without thresholds? [Measurability, Spec §SC-001, Spec §SC-002]
- [x] CHK017 Are matrix acceptance requirements precise about which target/browser and device-route combinations must pass versus merely receive evidence or an explicit unproven/not-measured status? [Acceptance Criteria, Spec §FR-026, Spec §SC-007]
- [x] CHK018 Are timeline-alignment tolerances defined or explicitly required from planning before a package can be considered transcription-ready? [Measurability, Spec §FR-011, Spec §SC-003]
- [x] CHK019 Are Apple voice-processing decision criteria objectively measurable across leakage, double-talk, latency, channel/format stability, route-change, crash/no-hang, and alignment outcomes? [Acceptance Criteria, Spec §FR-022, Spec §SC-013, Spec §SC-014]
- [x] CHK020 Is the user-burden criterion objectively measurable for normal recording flow without device switching, volume lowering, rerun checks, or technical risk acceptance? [Acceptance Criteria, Spec §FR-003c, Spec §SC-017]

## Scenario And Edge Case Coverage

- [x] CHK021 Are far-end-only, near-end-only, silence, double-talk, clipping, dropout, and misalignment scenarios all covered by requirements rather than only by edge-case notes? [Coverage, Spec §US1, Spec §US2, Spec Edge Cases]
- [x] CHK022 Are route-change scenarios during recording covered for metadata capture without accidentally becoming live remediation requirements? [Coverage, Spec §US3, Spec §FR-007]
- [x] CHK023 Are Bluetooth/AirPods-class, aggregate, multi-output, HDMI/AirPlay, and unknown virtual routes covered with explicit finalization truth outcomes? [Coverage, Spec §FR-009, Spec §FR-026, Spec §SC-007]
- [x] CHK024 Are browser/WebRTC AEC-disabled, meeting-app AEC, and virtual-device reference-path scenarios covered enough for planning to avoid false assumptions about available far-end reference audio? [Coverage, Spec Edge Cases, Spec §FR-021, Spec §FR-025]
- [x] CHK025 Are infeasible clean-dual-track outcomes covered with required alternative architecture semantics rather than an unresolved product gap? [Recovery, Spec §FR-003a, Spec §FR-003d, Spec §SC-015, Spec §SC-016]

## Privacy, Security, And Clean-Room Requirements

- [x] CHK026 Are metadata-only evidence requirements complete enough to exclude raw audio, transcript text, participant speech, credentials, tokens, signed URLs, passwords, API keys, and live absolute user paths? [Security, Spec §FR-014, Spec §SC-008, Constitution §III]
- [x] CHK027 Are requirements explicit that this feature introduces no direct MediaScribe upload, Langfuse content tracing, analytics, or external network egress? [Security, Spec §FR-017, Spec §SC-010, Constitution §III]
- [x] CHK028 Are clean-room requirements defined for Apple/WebRTC/commercial dependency evaluation without copying Krisp proprietary implementation details? [Clean-Room, Spec §FR-019, Spec §FR-020, Spec §US5]
- [x] CHK029 Are retention/deletion implications of new recording-quality metadata defined consistently with project lifecycle accounting? [Lifecycle, Spec Constitutional Requirements, Constitution §IV]
- [x] CHK030 Are user-facing recording-truth copy requirements specified for localization, keyboard reachability, color-independent communication, and brand distance? [UX, Spec Constitutional Requirements, Spec §FR-015]

## Realtime And Platform Requirement Quality

- [x] CHK031 Are realtime-safety requirements complete for every Core Audio/HAL callback path touched by leakage evidence, post-processing, route metadata, or recording writers? [Realtime Safety, Spec §FR-018, Constitution §I]
- [x] CHK032 Are macOS-native platform constraints reflected in requirements that affect driver, virtual device, voice-processing, and recording-writer behavior? [Platform, Constitution Product And Platform Constraints, Spec §FR-021]
- [x] CHK033 Are requirements clear that Apple system Mic Modes and Voice Isolation are user/system-controlled unless planning proves deterministic app ownership? [Platform Clarity, Spec §FR-023]
- [x] CHK034 Are channel count, sample format, sample rate, route topology, AGC/noise behavior, and output loudness changes covered as acceptance blockers for clean evidence? [Coverage, Spec §FR-024]
- [x] CHK035 Are dependency evaluation requirements complete for licensing, offline/local processing, CPU budget, latency budget, privacy boundary, test coverage, and fallback behavior before coding? [Dependencies, Spec §FR-020]

## Planning Readiness

- [x] CHK036 Are all plan-required decision records listed in the spec: Apple voice processing, WebRTC/custom AEC, app-side graph changes, post-recording cleanup, and mixed-audio fallback? [Planning Readiness, Spec §FR-003a, Spec §FR-003e, Spec §SC-013, Spec §SC-018]
- [x] CHK037 Are plan inputs sufficient to define `research.md`, `data-model.md`, contracts, and `quickstart.md` for finalization evidence and package truth states? [Planning Readiness, Spec Key Entities, Spec §FR-014, Spec §FR-028]
- [x] CHK038 Are out-of-scope boundaries complete for backend upload, MediaScribe processing, dashboard review, retention jobs, deletion workflows, assisted auto-recording, and live leakage cleanup? [Scope, Spec §FR-017, Spec Assumptions]
- [x] CHK039 Are requirement IDs granular and stable enough for tasks and future analyze findings to trace implementation work without bundling unrelated decisions? [Traceability, Spec §FR-001..FR-029, Spec §SC-001..SC-020]
- [x] CHK040 Are all clarified decisions reflected in functional requirements and success criteria rather than only in the Clarifications section? [Traceability, Spec Clarifications, Spec §FR-003a..FR-010b, Spec §SC-015..SC-020]

## Post-Plan Resolution Notes

- CHK002, CHK006, CHK016, and CHK018 are resolved by
  `plan.md`, `research.md`, `data-model.md`, and the package leakage contract:
  transcription readiness now fails closed unless original or derived leakage
  evidence passes a named threshold version.
- CHK007, CHK008, CHK017, CHK019, and CHK021 are resolved by the plan's route
  matrix, Apple/WebRTC decision gates, and quickstart validation scenarios.
- CHK010 is resolved by metadata fields for correlation lag, direct loopback
  suspicion, acoustic leakage suspicion, clipping, dropout, confidence, and
  alignment evidence.
- CHK014 is resolved by the plan's scoped constitution tension note: this slice
  does not claim live cleanup, and future live/AEC or alternative architecture
  work remains a separate go/no-go gate.
- CHK029 and CHK031 are resolved by modeling derived artifacts as package
  lifecycle artifacts and keeping leakage work outside HAL/Core Audio realtime
  callbacks.
