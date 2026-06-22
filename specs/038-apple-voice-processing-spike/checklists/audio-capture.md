# Audio Capture Requirements Checklist: Apple Voice Processing Spike

**Purpose**: Validate audio-capture requirement completeness before tasks and implementation
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are built-in speakerphone acceptance requirements defined separately from guidance-only or blocked outcomes? [Completeness, Spec §FR-002]
- [x] CHK002 Are processed-signal lineage requirements complete for live microphone behavior, persisted microphone artifact, incoming reference, and manifest truth? [Completeness, Spec §FR-004, Contract §Recording Package Lineage]
- [x] CHK003 Are baseline comparison requirements defined for the same route class and scenario before candidate processing is trusted? [Completeness, Spec §FR-003]
- [x] CHK004 Are original `mic.wav`, `incoming.wav`, and `manifest.json` preservation requirements explicit? [Completeness, Spec §FR-005]
- [x] CHK005 Are `020` leakage finalization authority requirements preserved without contradiction? [Consistency, Spec §FR-006]

## Requirement Clarity

- [x] CHK006 Are Apple processing outcome states named and mutually exclusive enough for task and evidence mapping? [Clarity, Spec §FR-002, Data Model §AppleProcessingOutcome]
- [x] CHK007 Is the distinction between app-owned processing, lower-level voice-processing I/O, and system Mic Mode guidance clear enough to avoid false acceptance? [Clarity, Research §Decision: Treat Mic Modes As Guidance]
- [x] CHK008 Are route/scenario validation rows specific enough to prevent synthetic-only acceptance? [Clarity, Spec §FR-007]
- [x] CHK009 Is missing Bluetooth/AirPods evidence explicitly scoped so it does not block the built-in speakerphone decision? [Clarity, Spec §FR-008]

## Acceptance Criteria Quality

- [x] CHK010 Are built-in speakerphone success criteria measurable across leakage, speech preservation, alignment, Stop/quit, route change, and redaction gates? [Acceptance Criteria, Spec §SC-002]
- [x] CHK011 Are failure and unproven outcomes required to include bounded reason codes and next-step recommendations? [Acceptance Criteria, Spec §SC-005]
- [x] CHK012 Are no-clean-claim requirements objectively enforceable in release-facing and user-facing wording? [Measurability, Spec §SC-006]

## Scenario Coverage

- [x] CHK013 Are far-end-only, near-end-only, double-talk, loud speaker/clipping, route change, browser meeting, Stop/quit, and diagnostic scenarios all represented? [Coverage, Quickstart §Manual Runtime Matrix]
- [x] CHK014 Are route topology failures addressed when Apple processing cannot see the same output that reaches physical speakers? [Edge Case, Spec §Edge Cases]
- [x] CHK015 Are sample format, channel count, timing, and route topology changes covered as failure or unproven conditions? [Coverage, Spec §FR-011, Edge Cases]

## Dependencies & Assumptions

- [x] CHK016 Is the dependency on merged `037` app-owned microphone graph explicit? [Dependency, Spec §FR-001]
- [x] CHK017 Are follow-up boundaries for `039`, `040`, and `041` explicit enough to avoid scope creep? [Scope, Spec §Program Context]
- [x] CHK018 Are accepted CPU/no-hang and alignment gates referenced as preserved constraints rather than relaxed by the spike? [Consistency, Plan §Performance Goals]

## Notes

- Checklist is complete after reviewing `spec.md`, `plan.md`, `research.md`,
  `data-model.md`, `contracts/`, and `quickstart.md`.
