# Audio Capture Requirements Checklist: WebRTC AEC3 Speakerphone Spike

**Purpose**: Validate capture, echo-cancellation, corpus, rollback, and package-truth requirements before task generation.
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the written requirements and plan artifacts, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are the source-of-truth prerequisites from `037`, `038`, and `020` explicitly identified before AEC3 can affect recording truth? [Completeness, Spec §FR-001, Spec §FR-009]
- [x] CHK002 Are all possible 039 outcome states enumerated with a single immediate-promotion state limited to built-in Mac microphone plus built-in Mac speakers? [Completeness, Spec §FR-002]
- [x] CHK003 Are baseline microphone, incoming reference, candidate evidence, and package truth represented as separate concepts before promotion? [Completeness, Spec §FR-003, Spec §FR-008]
- [x] CHK004 Are render/reference failure classes complete enough to cover missing, late, protected, silent, clipped, and non-representative reference audio? [Completeness, Spec §FR-004]
- [x] CHK005 Are timing-risk classes complete enough to cover delay, jitter, unsafe call ordering, and drift? [Completeness, Spec §FR-005, Spec §FR-007]
- [x] CHK006 Are required quality dimensions for far-end-only, near-end-only, and double-talk scenarios documented before immediate promotion? [Completeness, Spec §FR-006]
- [x] CHK007 Are lab-grade corpus requirements complete across file count, slices, full-file runs, long-form runs, room conditions, device profiles, and speaker-volume levels? [Completeness, Spec §FR-006a, Spec §FR-006c, Spec §SC-008, Spec §SC-009]
- [x] CHK008 Are controlled real-hardware scenarios explicitly enumerated rather than described only as "critical scenarios"? [Completeness, Spec §FR-006d, Spec §FR-006g, Spec §SC-010]
- [x] CHK009 Are acceptance-threshold requirements declared before validation begins, including the rule that threshold changes invalidate affected evidence? [Completeness, Spec §FR-006f, Spec §FR-012a]
- [x] CHK010 Are rollback trigger requirements complete across route, reference, quality, timing, lineage, diagnostics, and Stop/quit uncertainty? [Completeness, Spec §FR-006e, Spec §FR-014, Spec §SC-012]

## Requirement Clarity

- [x] CHK011 Is the promotion scope stated in route language that cannot be confused with Bluetooth, AirPods, USB, wired, browser, or external output routes? [Clarity, Spec §FR-011, Spec §FR-018]
- [x] CHK012 Is "accepted for immediate promotion" distinguishable from derived-candidate, guidance-only, blocked, and deferred outcomes? [Clarity, Spec §FR-002, Spec §FR-017]
- [x] CHK013 Is "fail closed" tied to specific blocked, unproven, rollback, or defer outcomes instead of left as an informal phrase? [Clarity, Spec §FR-004, Spec §FR-014]
- [x] CHK014 Are residual leakage, speech preservation, double-talk, timing, clipping/dropout, CPU/no-hang, Stop/quit, app-status, diagnostics, and rollback gates linked to the threshold profile? [Clarity, Spec §FR-006f, Spec §FR-012a]
- [x] CHK015 Is the difference between offline corpus evidence and real app recording evidence clear enough to prevent offline-only promotion? [Clarity, Spec §FR-006d, Spec §SC-010]
- [x] CHK016 Are long-form full-file requirements quantified with duration and count rather than described as "large" or "realistic"? [Clarity, Spec §SC-008]

## Requirement Consistency

- [x] CHK017 Do corpus requirements in the spec, data model, contract, and quickstart use the same scenario families and minimum counts? [Consistency, Spec §FR-006a, Data Model §WebRTCAEC3ValidationCorpus, Contract §Immediate Promotion Rules]
- [x] CHK018 Do rollback requirements align between user stories, functional requirements, data model, lineage contract, and quickstart? [Consistency, Spec §User Story 2, Spec §FR-006e, Data Model §AEC3RollbackEvent, Contract §Recording Package Lineage]
- [x] CHK019 Do package-truth requirements consistently preserve original `mic.wav`, `incoming.wav`, and `manifest.json` until immediate-promotion gates pass? [Consistency, Spec §FR-008, Plan §Storage, Contract §Recording Package Lineage]
- [x] CHK020 Are non-built-in supporting-route requirements consistent with the no-broadened-claim success criterion? [Consistency, Spec §FR-011, Spec §SC-011, Quickstart §Supporting Route Evidence]
- [x] CHK021 Are Stop/quit and active-capture requirements consistent with the constitution's visible user-control principle? [Consistency, Constitution §II, Spec §FR-013, Plan §Constitution Check]

## Acceptance Criteria Quality

- [x] CHK022 Are success criteria measurable for required row completeness, lineage contradictions, diagnostic privacy, blocked reasons, and copy claims? [Measurability, Spec §SC-001 through Spec §SC-006]
- [x] CHK023 Is immediate-promotion acceptance measurable across corpus, full-file, real-hardware, threshold-profile, app-status, rollback, licensing, and package-readiness gates? [Measurability, Spec §SC-002, Spec §SC-008, Spec §SC-010]
- [x] CHK024 Are blocked or unproven outcomes required to include both a safe reason code and a next-step recommendation? [Measurability, Spec §SC-005]
- [x] CHK025 Is the AEC3-to-040 fallback decision measurable enough to prevent relaxing clean-recording gates when AEC3 fails? [Measurability, Spec §SC-007]

## Edge Case Coverage

- [x] CHK026 Are unsafe reference, double-talk, clipping, route change, timing drift, speech suppression, offline-only, stale status, CPU/no-hang, licensing, and diagnostics edge cases all represented? [Coverage, Spec §Edge Cases]
- [x] CHK027 Are scenario classes covered for primary, alternate, exception, recovery, and non-functional audio paths? [Coverage, Spec §User Scenarios, Spec §Edge Cases]
- [x] CHK028 Are route-change and rollback recovery requirements present after a candidate has already been promoted? [Coverage, Recovery Flow, Spec §FR-006e, Spec §SC-012]
- [x] CHK029 Are full-file and sliced-window validation requirements both present so the plan cannot pass on small excerpts alone? [Coverage, Spec §FR-006a, Spec §SC-008]
- [x] CHK030 Are real-hardware app recording requirements bounded to consented test content and metadata-only committed evidence? [Coverage, Spec §FR-006d, Spec §Assumptions]

## Dependencies & Assumptions

- [x] CHK031 Are WebRTC dependency readiness, license, patent grant, packaging, signing, notarization, and release readiness represented as blockers rather than assumptions? [Dependency, Spec §FR-016, Plan §Primary Dependencies]
- [x] CHK032 Are sample-rate/channel conversions and unsupported frame assumptions required to become blocked or unproven instead of silently accepted? [Dependency, Plan §Performance Goals]
- [x] CHK033 Are local app package-readiness dependencies connected to recording/transcription truth before candidate promotion? [Dependency, Spec §FR-008, Spec §FR-009, Contract §Recording Package Lineage]
- [x] CHK034 Are private corpus/audio assets explicitly excluded from committed evidence while allowing metadata-only evidence rows? [Assumption, Spec §FR-015, Quickstart §Out Of Scope]

## Notes

- 2026-06-22: Passed after adding explicit acceptance-threshold profile, controlled real-hardware scenario enumeration, and app rollback/status requirements.
