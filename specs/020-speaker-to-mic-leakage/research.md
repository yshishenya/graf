# Research: Speaker-To-Mic Leakage Control

**Date**: 2026-06-04

## Decision: Leakage Truth Runs During Package Finalization

**Rationale**: The user clarified that recording-time behavior should stay
simple: record as-is, do not clean live, do not warn live, and do not ask the
user to change devices. Finalization has the saved tracks, duration metadata,
route facts, and enough time to perform bounded analysis outside realtime audio
callbacks.

**Alternatives considered**:

- Live leakage warning: rejected for this slice because it burdens the user
  during the meeting.
- Live cleanup/AEC: rejected for this slice because the user explicitly said no
  cleaning during the meeting. It remains a future spike if clean built-in
  speakerphone support is required.
- Preflight route readiness: rejected for this slice because route class alone
  cannot prove the saved artifact is clean.

## Decision: Preserve Five Leakage Statuses

**Rationale**: The status set remains `clean`, `leakage_detected`, `unproven`,
`not_measured`, and `not_applicable`. The key planning rule is to keep
`unproven` and `not_measured` separate:

- `clean`: measurement ran, evidence was reliable, and leakage was below the
  accepted threshold.
- `leakage_detected`: measurement ran, evidence was reliable, and leakage was
  above the accepted threshold.
- `unproven`: measurement was attempted but could not prove cleanliness because
  alignment, reference windows, double-talk separation, or confidence was
  insufficient.
- `not_measured`: measurement did not run or cannot apply to this package shape.
- `not_applicable`: the gate does not apply to this package/artifact type.

**Alternatives considered**:

- Merge `unproven` and `not_measured`: rejected because debugging and future
  MediaScribe upload policy need to know whether measurement was attempted.
- Use only pass/fail: rejected because real meeting packages can be ambiguous
  without being proven clean or proven contaminated.

## Decision: Thresholds Are Versioned And Multi-Dimensional

**Rationale**: A single correlation value is not enough to prove speech leakage
truth. The first threshold version, `leakage-threshold.v1`, should define:

- timeline alignment tolerance for whether dual-track measurement is valid;
- far-end-only reference window minimum duration;
- leakage level proxy comparing far-end reference energy with mic energy;
- correlation/lag evidence for likely direct digital loopback;
- acoustic leakage confidence from delayed/blurred reference energy;
- double-talk exclusion or confidence downgrade;
- clipping/dropout exclusions;
- residual leakage gate for derived cleaned tracks.

`leakage-threshold.v1` starts with conservative numeric gates so implementation
does not invent its own definitions:

| Gate | Initial value | Meaning |
| --- | ---: | --- |
| `timelineToleranceMs` | `1000` | Tracks with larger start/end mismatch cannot be clean dual-track evidence. |
| `minimumFarEndOnlyWindowMs` | `15000` | At least 15 seconds of usable far-end-only evidence is required to prove clean. |
| `maximumLeakageLevelDb` | `-45.0` | Far-end leakage proxy in `mic.wav` must stay at least 45 dB below the reference window. |
| `maximumCorrelationPeak` | `0.12` | Stronger correlation requires `leakage_detected` or `unproven`, depending on confidence and lag stability. |
| `minimumConfidence` | `0.80` | Lower confidence cannot produce `clean`; it becomes `unproven` when measurement was attempted. |
| `maximumAlignmentDriftMs` | `250` | Larger drift across the measured overlap blocks clean dual-track evidence. |
| `minimumDerivedConfidence` | `0.85` | Derived cleaned tracks need stronger confidence before transcription eligibility. |
| `maximumDerivedResidualLeakageDb` | `-50.0` | Derived local mic residual leakage must be at least 50 dB below the reference proxy. |

These are acceptance gates for implementation and fixtures, not final DSP tuning
claims. If controlled validation shows the values are too strict or too loose,
the implementation must create a new threshold version such as
`leakage-threshold.v2`; it must not silently reinterpret v1 evidence. Until the
fixture matrix passes, common built-in speakerphone packages must be treated as
`leakage_detected`, `unproven`, or `not_measured`, not clean.

**Alternatives considered**:

- Hard-code one RMS or correlation threshold: rejected because it confuses
  digital loopback, acoustic echo, room noise, and double-talk.
- Tune thresholds from real meeting content: rejected for privacy and
  repeatability reasons.

## Decision: Built-In Speakerphone Go/No-Go For This Slice

**Rationale**: Built-in Mac microphone plus built-in Mac speakers is a required
product problem, but this slice explicitly does not perform live cleanup. The
go/no-go decision for this slice is therefore:

- `no_go_for_clean_builtin_speakerphone_mvp`: 020 must not claim built-in
  speakerphone clean dual-track MVP readiness unless the finalized package
  passes `leakage-threshold.v1` through persisted evidence.
- `go_for_truthful_finalization`: 020 may ship package-level leakage truth,
  fail-closed transcription readiness, route metadata, and optional derived
  artifacts.
- `future_gate_required_for_live_clean_dual_track`: accepting built-in
  speakerphone as a clean live dual-track route requires a later Spec Kit slice
  proving Apple/WebRTC/app-side processing or an explicit alternative
  architecture.

This satisfies the constitution by preventing false clean claims now while
keeping live loopback prevention as a visible, unresolved MVP gate rather than a
hidden assumption.

**Alternatives considered**:

- Treat built-in speakerphone as clean after finalization-only analysis:
  rejected unless the package actually passes the threshold matrix.
- Block built-in speakerphone during recording: rejected because this feature
  must not burden the user during the meeting.
- Claim live cleanup through Apple/WebRTC without a spike: rejected because this
  slice performs no live cleanup.

## Decision: Original Tracks Are Immutable Evidence

**Rationale**: `mic.wav` and `incoming.wav` are the recording truth. If
post-recording cleanup is added, it creates a derived artifact with source
lineage, processor/version, confidence, residual leakage status, and separate
transcription eligibility. It never overwrites the original tracks.

**Alternatives considered**:

- Rewrite `mic.wav` after cleanup: rejected because it destroys evidence and
  makes later debugging/deletion/accounting ambiguous.
- Use derived output automatically for transcription: rejected unless residual
  leakage evidence passes the same finalization gate.

## Decision: Transcription Readiness Fails Closed

**Rationale**: A package must not be transcription-ready when required tracks
are missing, empty, timeline-misaligned, contaminated above threshold, or only
ambiguous. Future MediaScribe dual-track upload must read package leakage truth
before treating `mic.wav` as `mic_file`.

**Alternatives considered**:

- Upload degraded packages and let diarization handle it: rejected because the
  product would knowingly pass false local-speaker evidence downstream.
- Treat `unproven` as ready with warning: rejected for MVP because it blurs
  evidence truth.

## Decision: Route Facts Are Metadata, Not Live Readiness

**Rationale**: Device class, output volume, mute, browser target, `coreaudiod`,
sleep/wake, and route changes are useful evidence. They cannot prove final
cleanliness on their own and must not block normal recording in this feature.

**Alternatives considered**:

- Block risky routes such as built-in speakers at start: rejected because the
  user asked not to shift the problem to the user during recording.
- Ignore route facts entirely: rejected because QA/debug needs to understand
  which routes produce clean, contaminated, or unmeasurable packages.

## Decision: Apple Voice Processing Is A Spike Gate, Not This Slice's Runtime

**Rationale**: Apple APIs such as `AVAudioEngine` voice processing,
`VoiceProcessingIO`, and system Mic Modes/Voice Isolation may help future
built-in speakerphone support. For this slice they are not selected as runtime
cleanup because the feature explicitly avoids live cleanup. Planning still
records the spike gates required before Apple processing can be promoted:

- cleaned near-end signal must feed both `2brain Rec Microphone` and `mic.wav`;
- the processor must see the same far-end signal sent to physical speakers;
- `mic.wav` and `incoming.wav` must remain aligned;
- double-talk must preserve local speech;
- channel count, sample rate, format, AGC/noise behavior, and route topology
  must stay stable or be normalized;
- route changes must not hang Core Audio or hide capture state.

| Option | 020 outcome | Reason | Source basis |
| --- | --- | --- | --- |
| `AVAudioEngine` voice processing / `AVAudioIONode.isVoiceProcessingEnabled` | spike_only | Public API can enable voice processing on an audio I/O node, but 020 has not proven that the cleaned near-end signal feeds both `2brain Rec Microphone` and persisted `mic.wav` with the same far-end reference and stable timing. | Apple Developer Documentation for `AVAudioIONode.isVoiceProcessingEnabled` and WWDC19 "What's New in AVAudioEngine". |
| `kAudioUnitSubType_VoiceProcessingIO` | spike_only | Public Audio Unit exists for voice processing, but 020 does not validate route topology, double-talk behavior, channel/format changes, or driver/recording-writer integration. | Apple Developer Documentation for `kAudioUnitSubType_VoiceProcessingIO`. |
| System Mic Modes / Voice Isolation | user_system_assistance_only | Mic Modes are user/system-controlled unless a later plan proves deterministic app ownership. 020 may observe or guide only in a future UX slice and must not claim it can force clean capture. | Apple Developer Documentation for system microphone modes, `AVCaptureDevice.MicrophoneMode.voiceIsolation`, `preferredMicrophoneMode`, `showSystemUserInterface(_:)`, and Apple Support Mic Modes guide. |

None of these Apple options is accepted for runtime cleanup or clean package
claims in 020. Promotion requires a later Spec Kit slice with controlled
leakage, double-talk, latency, route-change, crash/no-hang, channel/format, and
alignment validation.

**Alternatives considered**:

- Accept Voice Isolation because it exists in macOS: rejected because API
  availability does not prove the exact virtual-microphone and recording path is
  clean.
- Ignore Apple processing and jump to custom AEC: rejected because the macOS MVP
  should evaluate native public APIs first.

## Decision: WebRTC AEC3 And Custom AEC Are Deferred

**Rationale**: WebRTC AEC3 is a plausible future path for active speakerphone
support, but it is high complexity and has packaging, licensing, CPU, latency,
delay, double-talk, route-change, and realtime-safety risk. It should not be
mixed into this finalization-only slice.

**Alternatives considered**:

- Implement AEC3 immediately: rejected because the clarified scope excludes
  live cleanup and implementation needs a separate plan.
- Use SpeexDSP as production AEC: rejected for now because quality risk is high
  for modern laptop speakerphone and double-talk cases.

## Decision: Mixed Audio Is A Fallback After Failed Clean Dual-Track Gates

**Rationale**: If built-in speakerphone cannot produce truthful separated
tracks through Apple/WebRTC/app-side clean dual-track work, a mixed or
non-separated recording architecture may be more honest. It must define
diarization confidence, leakage labels, upload eligibility, and user-facing
truth before use.

For 020, mixed audio is evaluated as a decision record only and is not selected
as the implementation path. The decision record must capture:

- which clean dual-track gates were attempted or deferred;
- why finalization-only truth is safer than labeling separated tracks clean;
- what a future mixed mode would mean for diarization confidence, speaker
  attribution, upload eligibility, user-facing truth, and MediaScribe input
  shape;
- the explicit condition that mixed audio can become implementation scope only
  after a later plan records failed clean dual-track evidence or amends the
  architecture.

**Alternatives considered**:

- Choose mixed audio now: rejected because the spec requires clean dual-track
  options to fail first.
- Continue separated tracks and label them clean anyway: rejected as false
  evidence.

## Decision: Dependency Decision Records Are Required Before Promotion

**Rationale**: Apple voice processing, WebRTC AEC3, custom AEC, post-recording
cleanup processors, and mixed-audio capture each change product truth. Before
any of them is promoted beyond a metadata-only decision, the repository must
record licensing, offline/local processing behavior, CPU and latency budget,
privacy boundary, route topology assumptions, test coverage, fallback behavior,
and clean-room source basis.

**Alternatives considered**:

- Put dependency notes only in code comments: rejected because tasks and future
  reviews need a durable, reviewable decision artifact.
- Treat public Apple API availability as the decision record: rejected because
  public API availability does not prove the exact 2brain Rec route is clean.

## Decision: Diagnostics Stay Metadata-Only

**Rationale**: Leakage evidence must include safe metrics, threshold version,
alignment status, route class, confidence, failure reason, original/derived
artifact lineage, and egress flags. It must exclude raw audio snippets,
transcript text, participant speech, meeting content, credentials, tokens,
signed URLs, passwords, API keys, and live absolute user paths.

**Alternatives considered**:

- Store short raw clips for debugging: rejected for production diagnostics.
  Controlled local test stimuli may exist as explicit fixtures, but meeting
  content must not be preserved in diagnostics.
