# Research: Apple Voice Processing Spike

## Decision: Treat Apple Processing As A Bounded Candidate, Not A Claim

`038` will evaluate Apple native voice processing as a candidate path for
reducing speaker-to-mic leakage. The presence of an API, an enabled state, or a
system Mic Mode is not enough to mark a route clean. Clean built-in speakerphone
acceptance requires lineage, leakage, double-talk, alignment, no-hang, CPU, and
metadata-only evidence.

**Rationale**: Apple documents voice processing support for voice-chat use cases
and echo cancellation, but 2brain Rec must prove the processed signal is the
same signal used by the product's live and persisted recording paths. The
product promise is package truth, not generic platform capability.

**Alternatives considered**:

- Enable Apple processing and immediately mark built-in speakerphone clean:
  rejected because it would bypass 2brain Rec's leakage and package gates.
- Skip Apple and go straight to WebRTC AEC3: rejected because Apple processing
  may be lower-maintenance if it proves the route and quality.

## Decision: Evaluate The App-Owned Audio Graph Path First

The first candidate should use the app-owned microphone graph from `037` and
determine whether Apple voice processing can be inserted while preserving the
recording package contract. Lower-level voice-processing I/O is a second
candidate only if the app-owned graph path cannot prove needed route ownership.

**Rationale**: `037` already gives 2brain Rec a controlled microphone frame path
before `mic.wav`. Evaluating Apple processing inside or adjacent to that path
minimizes package churn and directly answers whether processed near-end evidence
can feed the product.

**Alternatives considered**:

- Start with a separate internal test recorder: rejected because it would not
  prove product lineage.
- Start by replacing the entire recording graph: rejected because it increases
  risk before the spike establishes feasibility.

## Decision: Treat Mic Modes As Guidance Unless Ownership Is Proven

System microphone modes, including Voice Isolation, can be observed or surfaced
as user guidance only when the evidence clearly labels them as user/system
controlled. They cannot be used as clean acceptance unless the spike proves
deterministic app ownership for the exact recording route.

**Rationale**: User/system-controlled modes can improve practical audio quality,
but they are not a stable product-owned cleanup contract by themselves. A user
may change modes, unsupported routes may differ, and mode state may not map to
the persisted `mic.wav` path.

**Alternatives considered**:

- Require Voice Isolation as the accepted product path: rejected until app-owned
  control and package lineage are proven.
- Ignore Mic Modes entirely: rejected because guidance-only evidence may still
  be useful for product copy or `040` fallback decisions.

## Decision: Preserve Original Package Truth And Existing Leakage Authority

Original `mic.wav`, `incoming.wav`, and `manifest.json` remain the local package
source of truth. Apple candidate evidence may add metadata or explicit
candidate/derived lineage, but it must not silently overwrite original evidence
or bypass `020` finalization.

**Rationale**: Existing upload, leakage, deletion, diagnostics, and review
surfaces already understand the accepted local package. A spike should answer
whether Apple processing is trustworthy without redefining the entire recording
contract.

**Alternatives considered**:

- Write only a processed microphone artifact and discard original evidence:
  rejected because failed or uncertain processing would leave no reliable
  baseline.
- Mark a package clean from pre-stop processing metadata alone: rejected because
  `020` finalization is the current authority for clean package status.

## Decision: Use A Required Route And Scenario Matrix

The initial required matrix includes built-in mic/speakers, built-in mic/wired
headphones, USB headset, at least one browser meeting target, far-end-only,
near-end-only, double-talk, loud speaker/clipping, and route-change scenarios.
Bluetooth/AirPods-class evidence is useful when available but not required for
the initial built-in speakerphone decision.

**Rationale**: Built-in speakerphone is the decision target. Wired/headset rows
separate "speaker leakage" from "normal clean route" behavior. Browser meeting
rows protect against validating only synthetic local playback that does not
match real capture conditions.

**Alternatives considered**:

- Require broad hardware coverage immediately: rejected because unavailable
  hardware should not block the initial built-in speakerphone go/no-go.
- Validate only synthetic fixtures: rejected because route topology and physical
  leakage are central to this spike.

## Decision: Defer To WebRTC AEC3 When Lineage Or Quality Fails

If Apple processing cannot prove route ownership, far-end reference access,
processed-signal lineage, double-talk preservation, stability, or residual
leakage quality, the primary outcome should be a blocked/guidance-only state or
`defer_to_webrtc_aec3`.

**Rationale**: WebRTC AEC3 is higher-complexity but gives 2brain Rec explicit
render/capture reference processing. It should be justified by concrete Apple
limitations rather than by intuition.

**Alternatives considered**:

- Loosen acceptance thresholds for Apple: rejected because false clean recording
  is worse than a truthful unsupported route.
- Jump to `040` fallback without trying WebRTC: rejected unless Apple evidence
  also shows the target route is not strategically worth a custom AEC attempt.

## Primary Sources And Local Evidence

- `docs/audio-capture-backlog.md`, Feature 038 scope and validation matrix.
- `specs/020-speaker-to-mic-leakage/feasibility-research.md`, Apple processing
  and WebRTC AEC3 backlog rationale.
- `specs/037-microphone-sample-graph-foundation/spec.md`, merged app-owned
  microphone graph foundation.
- Apple Developer Documentation: `AVAudioIONode.setVoiceProcessingEnabled(_:)`
  <https://developer.apple.com/documentation/avfaudio/avaudioionode/setvoiceprocessingenabled%28_%3A%29>
- Apple Developer Documentation: `kAudioUnitSubType_VoiceProcessingIO`
  <https://developer.apple.com/documentation/audiotoolbox/kaudiounitsubtype_voiceprocessingio>
- Apple Developer Documentation:
  `AVCaptureDevice.MicrophoneMode.voiceIsolation`
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/microphonemode/voiceisolation>
- Apple WWDC19 "What's New in AVAudioEngine"
  <https://developer.apple.com/videos/play/wwdc2019/510/>
- Apple WWDC23 "What's new in voice processing"
  <https://developer.apple.com/videos/play/wwdc2023/10235/>
