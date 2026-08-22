# Audio Capture Requirements Checklist: WebRTC AEC3 Recording

**Purpose**: Formal pre-implementation review of capture, AEC, integrity, packaging and evidence requirements
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md)

**Audience/timing**: Author and peer reviewer before tasks, analysis and implementation

## Requirement Completeness

- [x] CHK001 Are requirements defined for the complete signal path from native mic/system inputs through PTS alignment, echo processing and canonical mixing? [Completeness, Spec §FR-001–FR-003, Plan §Summary]
- [x] CHK002 Are the exact enabled and disabled signal-processing categories documented, including the AEC support high-pass decision? [Completeness, Spec §FR-004, Research §Decision 4]
- [x] CHK003 Are requirements defined for processor readiness before start and failures after start without a raw-microphone fallback? [Completeness, Spec §FR-005–FR-007]
- [x] CHK004 Are artifact count, names, roles and upload/transcription eligibility defined for both normal and degraded outcomes? [Completeness, Spec §FR-008, Contract §Recording Integrity]
- [x] CHK005 Are route generation, producer stop, device disconnect, format/timebase change, pause/resume and clock-drift requirements all documented? [Completeness, Spec §FR-007, Research §Decision 8]
- [x] CHK006 Are required manifest identity, health, counters, statistics and safe reason codes specified? [Completeness, Spec §FR-011, Data Model §EchoProcessingHealth]
- [x] CHK007 Are historical package compatibility and prohibited legacy-runtime boundaries both specified? [Completeness, Spec §FR-009–FR-010, Contract §Compatibility]
- [x] CHK008 Are license, notices, architecture slices, linkage and release-signing boundaries documented for the new dependency? [Completeness, Spec §FR-014, Research §Decisions 2/3/10]

## Requirement Clarity

- [x] CHK009 Is “AEC only” unambiguous about mobile mode, HPF, NS/ANC, AGC, transient suppression, VAD, gates and AecDump? [Clarity, Contract §Disabled processing]
- [x] CHK010 Is the processor input contract quantified as finite mono float at 48 kHz with exactly 480 matched samples per side? [Clarity, Contract §Input]
- [x] CHK011 Is processing order explicit about render-before-capture and the meaning/value of stream delay? [Clarity, Contract §Processing order, Research §Decision 6]
- [x] CHK012 Is valid system silence distinguished from missing render reference so silence filling cannot hide loss? [Clarity, Data Model §Canonical frame pair]
- [x] CHK013 Is “preserve a cleaned prefix” bounded to frames already returned successfully rather than queued raw inputs? [Clarity, Contract §Failure package]
- [x] CHK014 Are normal, degraded and failed states defined with terminal transitions and eligibility consequences? [Clarity, Data Model §State transitions]
- [x] CHK015 Is privacy Pause/Resume clearly distinguished from terminal route/reference discontinuities, with no raw bypass in either case? [Clarity, Research §Decision 8, Contract §Discontinuity]

## Requirement Consistency

- [x] CHK016 Does the unchanged `canonical-mix.v1` claim align with cleaning only the microphone before retaining the existing mix equation? [Consistency, Spec §FR-003/FR-008, Data Model §Relationships]
- [x] CHK017 Do fail-closed requirements consistently prohibit both a normal raw-mic package and salvage re-drain after an AEC failure? [Consistency, Spec §FR-005–FR-006, Contract §Failure package]
- [x] CHK018 Do diagnostics requirements consistently permit only bounded metadata while prohibiting raw audio in manifests, logs, dumps and evidence? [Consistency, Spec §FR-011, Contract §Diagnostics]
- [x] CHK019 Do visible-control requirements preserve Record, countdown, Pause/Resume and one-action Stop even when audio integrity degrades? [Consistency, Spec §FR-012, Plan §Constitution Check]
- [x] CHK020 Does dependency packaging preserve the existing single signed app component and universal distribution contract? [Consistency, Plan §Project Structure, Contract §Distribution]

## Acceptance Criteria Quality

- [x] CHK021 Are echo reduction, convergence, near-end preservation, double-talk, system-level and alignment outcomes numerically measurable? [Measurability, Spec §SC-001–SC-006, Quickstart §4]
- [x] CHK022 Are callback partition and final-tail requirements precise enough to prove exact frame count independently of callback size? [Measurability, Quickstart §3]
- [x] CHK023 Is the maximum permitted per-frame processing latency quantified for the supported path? [Measurability, Plan §Performance Goals]
- [x] CHK024 Are saturation and invalid measurement conditions defined as non-passing evidence rather than successful quality rows? [Acceptance Criteria, Quickstart §4]
- [x] CHK025 Are package-surface outcomes objectively countable as one manifest, one WAV, one M4A and no raw/reference artifact? [Acceptance Criteria, Contract §Normal package]

## Scenario And Edge-Case Coverage

- [x] CHK026 Are primary far-end-only, alternate headphone/near-end-only and simultaneous double-talk scenarios all represented? [Coverage, Spec §User Story 1, Quickstart §4/§6]
- [x] CHK027 Are exception flows defined for processor startup/configuration failure, per-call errors, missing reference, non-finite samples and source termination? [Coverage, Data Model §EchoProcessingFailureReason]
- [x] CHK028 Are boundary cases defined for arbitrary callback partitions, final partial frames, jitter, overlap, backward PTS, bounded gaps and overflows? [Coverage, Spec §Edge Cases, Quickstart §3]
- [x] CHK029 Are recovery requirements explicit that v1 ends the trusted segment and preserves truthful degradation instead of silently resetting? [Recovery, Research §Decision 8]
- [x] CHK030 Are hardware scenarios defined across built-in speakers, headphones, wired/Bluetooth route changes, volume levels, rooms and long duration? [Coverage, Quickstart §6]

## Non-Functional Requirements

- [x] CHK031 Are bounded memory, serial processing, exact duration and 60-minute drift requirements documented? [Non-Functional, Plan §Performance Goals/Constraints, Quickstart §4]
- [x] CHK032 Are local-only processing, no new egress/credentials and metadata-only evidence requirements explicit? [Privacy, Plan §Constitution Check]
- [x] CHK033 Are reproducibility requirements explicit about exact source commit, pinned Abseil fallback, deployment target, tool provenance and hashes? [Dependency, Research §Decisions 1–3]
- [x] CHK034 Are public release requirements distinguished from local ad-hoc evidence, with Developer ID/notarization gates left mandatory? [Distribution, Quickstart §5/§7]

## Dependencies And Assumptions

- [x] CHK035 Is reliance on AEC3's internal acoustic-delay estimator distinguished from host-owned PTS, route, gap and queue responsibilities? [Assumption, Research §Decision 6]
- [x] CHK036 Is the lack of trustworthy HAL delay measurement documented together with the bounded zero-delay policy and upgrade trigger? [Assumption, Research §Decision 6]
- [x] CHK037 Is the clean-room relationship to MacWhisper limited to observed architecture while excluding its closed code and binaries? [Dependency, Spec §FR-014, Research §Decision 1]
- [x] CHK038 Is the hardware acceptance scope explicit enough to prevent synthetic tests alone from authorizing a release? [Dependency, Quickstart §6]

## Notes

- All 38 requirement-quality checks pass in the plan/design set dated 2026-08-20.
- This checklist reviews the written contract. Runnable implementation evidence is defined separately in `quickstart.md`.
