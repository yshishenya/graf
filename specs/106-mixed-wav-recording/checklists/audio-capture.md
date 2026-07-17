# Audio Capture Requirements Checklist: Чистый единый аудиопоток

**Purpose**: Validate that the capture and audio-quality requirements are complete, measurable and consistent before implementation.

**Created**: 2026-07-17

**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [timeline contract](../contracts/timeline-and-artifact-contract.md)

## Requirement Completeness

- [X] CHK001 Are common-clock and recording-epoch requirements explicitly defined for both microphone and system source batches? [Completeness, Spec §FR-002, Plan §1]
- [X] CHK002 Are source PTS, actual sample rate, channel count, duration, discontinuity and route generation all specified as required timing inputs rather than inferred values? [Completeness, Plan §1, Contract §Required Source Batch Fields]
- [X] CHK003 Are requirements specified for delayed first source, known gap, overlap, route change, source queue overflow and early Stop? [Coverage, Spec §Edge Cases, Contract §Timing Decisions]
- [X] CHK004 Are the required final members and the explicit prohibition of v5 `mic.wav`, `incoming.wav`, raw source copies and partial files consistent across the specification and package contract? [Consistency, Spec §FR-001/FR-010/FR-013, Package Contract §Exact Final Members]
- [X] CHK005 Is the exact relationship between the canonical 48 kHz timeline, 16 kHz WAV and 48 kHz M4A specified without allowing a second independent mix or post-hoc AAC decode? [Completeness, Spec §FR-002–FR-004, Plan §2]
- [X] CHK006 Are source-preserving silence and double-talk requirements explicitly distinguished from quality failures or amplitude presence gates? [Clarity, Spec §FR-002/FR-005, Package Contract §Canonical WAV/§Mixing Contract]

## Clarity And Measurability

- [X] CHK007 Is “one continuous synchronized conversation timeline” quantified by an unambiguous accepted divergence threshold, duration and treatment of AAC priming? [Measurability, Spec §SC-002, Package Contract §Timeline Contract]
- [X] CHK008 Are “gap,” “overlap,” “uncomparable clock,” “unsafe loss” and “integrity outcome” defined with observable, typed outcomes rather than subjective wording? [Clarity, Spec §Edge Cases, Contract §Timing Decisions]
- [X] CHK009 Is the failure boundary between an expected silence interval and an incomplete/invalid audio artifact clear and consistent? [Clarity, Spec §Edge Cases, Package Contract §Canonical WAV]
- [X] CHK010 Are actual WAV and M4A format requirements complete enough to distinguish a valid final artifact from an extension-only, truncated or wrong-codec file? [Completeness, Spec §FR-001/FR-012, Package Contract §Canonical WAV/§Playback M4A]
- [X] CHK011 Are the mix-profile requirements bounded and sufficiently precise to preserve both participants and avoid clipping without reintroducing AEC, VAD or a hidden participant mute? [Clarity, Spec §FR-005, Package Contract §Mixing Contract]
- [X] CHK012 Are success measures for long-run timing, source marker placement and finalization completeness stated independently of the implementation mechanism? [Measurability, Spec §SC-001–SC-003, Quickstart §Focused macOS checks]

## Scenario And Non-Functional Coverage

- [X] CHK013 Are required hardware scenarios defined for local speech, incoming speech, overlap, silence and music, including a safe non-private test signal policy? [Coverage, Spec §SC-003/SC-005, Quickstart §Installed-app hardware acceptance]
- [X] CHK014 Are route and perceived-volume requirements stated separately from recording artifact quality so a good file cannot hide an audible regression? [Consistency, Spec §FR-006/SC-005, Plan §Validation Plan]
- [X] CHK015 Are start, Stop, drain, converter flush and atomic finalization requirements complete enough to preclude partial media being represented as ready? [Coverage, Spec §FR-001/FR-012, Package Contract §Atomic Finalization]
- [X] CHK016 Is the requirement to keep active capture visible and immediately stoppable preserved for every degradation and timing-failure state? [Coverage, Spec §FR-006, Constitution §II]

## Ambiguities And Dependencies

- [X] CHK017 Is the source-timestamp comparability assumption explicitly named as an installed-app acceptance dependency, with a no-fallback outcome if it fails? [Assumption, Research §Research Outcome, Plan §1]
- [X] CHK018 Are historical v3/v4 audio requirements isolated clearly enough that compatibility reading cannot be mistaken for permitted new v5 capture? [Consistency, Spec §FR-010/FR-013, Package Contract §Backward Compatibility]

## Review Result

- Requirements review passed on 2026-07-17 after the exact `canonical-mix.v1` profile and degraded-state control requirement were added.
