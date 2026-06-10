# Feasibility Research: Speaker-To-Mic Leakage Control

**Created**: 2026-06-04

This research estimates how hard it is to implement speaker-to-mic leakage
control at the current project stage. It uses public sources and the current
2brain Rec codebase. It is not an implementation plan yet.

## Executive Summary

The problem is real and category-critical. Remote/far-end audio played through
physical speakers can acoustically enter the physical microphone. If 2brain Rec
then forwards that microphone signal to `2brain Rec Microphone` or saves it as
`mic.wav`, remote speakers can be duplicated into the local mic track.

At the current stage, there are three feasible levels:

1. **Detection and truthful gating**: feasible now, low-to-medium complexity.
   The system measures or classifies leakage, marks routes/packages as clean,
   degraded, blocked, or unproven, and prevents false transcription readiness.
2. **Headset-first clean MVP**: feasible now, medium complexity. Routes with
   headphones/headsets can become the first clean accepted path; built-in
   speakerphone routes remain blocked or pilot-only until proven.
3. **Full active speakerphone AEC**: feasible but high complexity. It requires
   a real-time echo-control pipeline with aligned far-end reference, near-end
   capture, delay estimation, double-talk handling, route-change recovery,
   CPU/latency budgets, and careful integration outside HAL realtime hazards.

Recommended near-term approach: implement **gate + mitigation** in stages. First
make the product truthful and block unsafe routes; then accept headphones/headset
routes; then prototype active AEC for built-in speakerphone routes behind a
validation gate.

## What AEC Requires

Acoustic echo cancellation is not just "remove matching sound from a WAV file".
Production AEC needs:

- **Far-end reference**: the audio sent to the speaker.
- **Near-end capture**: the microphone signal containing local speech plus any
  acoustic echo.
- **Timing alignment**: the reference must arrive at the AEC before or close to
  the echo in the mic signal.
- **Delay estimation**: playback buffers, DAC, room path, ADC, and capture
  buffers all add delay.
- **Double-talk handling**: local and remote people may speak simultaneously.
- **Residual echo suppression**: linear adaptive filtering alone is often not
  enough.
- **Route-change recovery**: moving the laptop, changing volume, switching
  Bluetooth profiles, or restarting Core Audio can invalidate the filter.

This matches public AEC guidance from WebRTC AEC3, SpeexDSP, PJSIP, and Apple
voice-processing APIs.

## Current 2brain Rec Fit

2brain Rec already has several good prerequisites:

- Separate virtual devices: `2brain Rec Microphone` and `2brain Rec Speaker`.
- Driver-side virtual speaker `WriteMix` is mirrored into `capture_buffer`,
  which can serve as a far-end reference/incoming track source.
- App-side passthrough captures physical microphone frames and writes them into
  shared `mic_buffer` for the virtual microphone.
- Local recordings already save `mic.wav`, `incoming.wav`, and a metadata-only
  manifest.
- The constitution already forbids remote audio loopback into
  `2brain Rec Microphone`.

Current blockers:

- `mic.wav` is currently recorded through an app-side `AVAudioRecorder`, while
  `incoming.wav` is written from shared speaker capture. They are not guaranteed
  to share the same clock, frame cadence, or `t=0`.
- The live evidence package is already `timeline_misaligned`; mic is about
  152.19 seconds longer than incoming.
- The current route can be format-correct but semantically contaminated:
  `mic.wav` can contain physical speaker leakage even when `incoming.wav`
  separately contains the same remote audio.
- There is no explicit leakage status in route readiness or recording manifest.
- There is no accepted AEC component, threshold, route matrix, or controlled
  leakage stimulus.

## Implementation Options

### Option 1: Detection And Truthful Gating

Complexity: low-to-medium.

What it does:

- Adds leakage status to route/package evidence.
- Marks `clean`, `leakage_detected`, `unproven`, or `not_measured`.
- Blocks transcription-ready status when leakage or timeline mismatch exists.
- Adds controlled far-end-only test stimuli and metadata-only metrics.

Pros:

- Can be built using existing dual-track artifacts and shared-memory counters.
- Low realtime risk because analysis can run outside HAL callbacks.
- Immediately prevents false "clean recording" claims.

Cons:

- Does not itself clean the live microphone.
- Built-in speaker/mic calls may still echo unless blocked or guided to
  headphones.

Best use:

- Mandatory first layer before any active AEC rollout.

### Option 2: Headset-First Clean MVP

Complexity: medium.

What it does:

- Treats headphones/headsets as the first accepted clean capture route.
- Built-in speakers plus built-in mic remain blocked/degraded unless they pass
  explicit leakage validation.
- UI gives clear recovery actions: use headphones/headset, lower output volume,
  select a different mic/output, rerun route check.

Pros:

- Physically prevents acoustic leakage for the common clean path.
- Easier to validate quickly.
- Fits privacy/truthfulness: no route is called clean unless proven.

Cons:

- Weaker product promise than full Krisp-like speakerphone support.
- Users may expect laptop speakerphone to work eventually.

Best use:

- Recommended first MVP acceptance path if we need reliable clean recordings
  before active AEC is ready.

### Option 3: Apple Voice Processing / VoiceProcessingIO

Complexity: medium-to-high, uncertain.

What it does:

- Tries to use Apple's built-in voice processing / echo-cancelled input path.
- Candidate APIs include `AVAudioEngine` voice processing,
  `kAudioUnitSubType_VoiceProcessingIO`, and AVFoundation system microphone
  modes such as Voice Isolation.

Pros:

- Uses native Apple primitives.
- Potentially lower integration effort than shipping WebRTC AEC.
- May handle built-in mic/speaker routes well where supported.
- Clean-room friendly: relies on public platform behavior rather than copying a
  commercial product's DSP stack.

Cons:

- macOS behavior can be route-dependent and less controllable than a custom AEC
  graph.
- Voice processing can alter channel count, sample format, AGC/noise behavior,
  and route topology.
- It may not map cleanly onto a custom virtual-device driver plus app bridge.
- Needs proof that processed mic output can feed both `2brain Rec Microphone`
  and the recording writer with stable timing.
- System Mic Modes/Voice Isolation are partly user/system controlled; public
  APIs allow inspection and presenting system UI, but planning must not assume
  the app can silently force Voice Isolation for all routes.

Best use:

- A bounded spike, not assumed acceptance.

## Apple Built-In Voice Processing Research Gate

The project should try Apple built-in processing before building custom DSP.
The reason is simple: if the OS can provide acceptable AEC for the built-in
microphone/speaker route, 2brain Rec avoids shipping, tuning, and maintaining a
large custom echo canceller.

The Apple path is not a free pass. It must be proven against 2brain Rec's
virtual-device architecture.

### Candidate Apple APIs

1. **AVAudioEngine voice processing**

   Apple's WWDC19 AVAudioEngine update describes voice processing mode as aimed
   at echo cancellation and VoIP. The important planning detail is that echo
   cancellation requires both input and output nodes to be in voice processing
   mode. For 2brain Rec, this means the spike must determine whether the app
   audio graph can own both the physical microphone input and the physical
   output path that receives `2brain Rec Speaker` audio.

2. **VoiceProcessingIO Audio Unit**

   `kAudioUnitSubType_VoiceProcessingIO` is the lower-level Audio Unit route for
   Apple's voice-processing path. It may fit better than `AVAudioEngine` because
   the current bridge already uses Core Audio Audio Units. The risk is that it
   can change route topology, channel behavior, and aggregate-device behavior on
   macOS, so it needs a no-hang and route-stability spike.

3. **System microphone modes / Voice Isolation**

   `AVCaptureDevice.MicrophoneMode.voiceIsolation` is a system microphone mode
   that isolates voice and attenuates other signals. Apple exposes inspection
   APIs such as active/preferred microphone mode and a system UI entry point for
   microphone modes. This is useful for guidance and diagnostics, but should be
   treated as user/system-controlled unless planning proves deterministic app
   control for the exact 2brain Rec route.

4. **Echo-cancelled input preference**

   Apple also documents echo-cancelled input preferences on `AVAudioSession`.
   Current public docs describe this as limited to supported hardware/routes and
   newer iPhone models, and voice-processing APIs already apply echo
   cancellation on supported routes. For macOS MVP planning, this is mostly a
   reference point and not the main desktop implementation path.

### What The Apple Spike Must Prove

The spike must answer all of these before Apple processing can be accepted:

- Does the cleaned near-end signal feed `2brain Rec Microphone`, not only an
  internal test recorder?
- Does the same cleaned near-end signal feed `mic.wav` so live route and saved
  artifact truth match?
- Does Apple processing see the same far-end output that 2brain Rec actually
  sends to physical speakers?
- Are `mic.wav` and `incoming.wav` still aligned within the accepted tolerance?
- Are channel count, sample rate, sample format, and channel order stable enough
  for our shared-memory and WAV contracts?
- Does it preserve near-end speech during double-talk?
- Does it avoid half-duplex behavior where local speech is suppressed whenever
  remote audio is active?
- Does it preserve non-recording passthrough and visible recording controls?
- Does it avoid Core Audio hangs, app crashes, route disappearing, or surprise
  default-device changes?
- Does it work on the required MVP route matrix, or only on a narrower route
  such as built-in mic/speaker?

### Apple Spike Acceptance States

The plan should classify Apple processing with one of these outcomes:

- `accepted_for_builtin_speakerphone`: built-in mic/speaker route passes leakage,
  double-talk, latency, alignment, and stability gates.
- `accepted_for_guidance_only`: Mic Modes/Voice Isolation can be observed or
  opened for the user, but cannot be relied on for clean acceptance.
- `accepted_for_headset_routes_only`: Apple processing is not needed or not
  useful for headphones/headsets, but route classification remains clean.
- `blocked_route_topology`: Apple processing cannot be inserted into the
  virtual-device bridge without breaking route ownership or timing.
- `blocked_quality`: Apple processing runs but fails leakage/double-talk quality
  gates.
- `blocked_stability`: Apple processing runs but causes Core Audio, channel,
  crash, latency, or route-change instability.
- `defer_to_webrtc_aec3`: Apple processing is insufficient; continue with
  WebRTC AEC3 or another approved processing component.

### Why This Matters For Planning

Planning must not collapse "Voice Isolation exists" into "speaker-to-mic leakage
is solved." The product needs a cleaned signal in two places: the virtual
microphone used by the meeting app, and the local `mic.wav` track used for
future MediaScribe. If Apple processing only affects a user-selected system mic
mode, or only affects another capture path, it does not solve 2brain Rec's
driver-first route.

Conversely, if Apple processing works in the app bridge, it should be preferred
over custom AEC for the first built-in-speaker route because it reduces custom
DSP scope and keeps the macOS MVP platform-native.

### Option 4: WebRTC AEC3 In The App Audio Graph

Complexity: high.

What it does:

- Adds WebRTC's audio processing/AEC3 or a wrapper as a native processing
  component.
- Feeds speaker reference into render analysis and mic frames into capture
  processing.
- Writes the cleaned mic signal into `mic_buffer` and recording artifacts.

Pros:

- Mature, widely used AEC family.
- Designed around render/capture reference processing, delay estimation, and
  double-talk handling.
- More controllable than opaque system voice processing.

Cons:

- Integration work is significant in Swift/C++ app code.
- Requires frame-size, sample-rate, channel, delay, and threading discipline.
- Must not add allocation/logging/blocking work to HAL callbacks.
- Needs packaging/licensing review, CPU tests, crash tests, and route-change
  recovery.

Best use:

- Likely long-term path for real speakerphone support, after detection and route
  truth are implemented.

### Option 5: SpeexDSP AEC

Complexity: medium, quality risk.

What it does:

- Uses SpeexDSP echo cancellation with microphone and playback frames.

Pros:

- Simpler API and easier to prototype.
- Explicitly documents rec/play/out semantics and timing constraints.
- Useful as a learning/prototype baseline.

Cons:

- Older technology and likely weaker than WebRTC AEC3 for modern laptop
  speakerphone cases.
- More sensitive to timing, clock mismatch, nonlinear distortion, and
  double-talk.

Best use:

- Diagnostic/prototype baseline, not first choice for production quality.

## Difficulty By Goal

| Goal | Difficulty | Why |
| --- | --- | --- |
| Mark contaminated recordings as degraded | Low | Can extend manifest/evidence outside realtime paths. |
| Detect timeline mismatch | Low | Already present; needs stronger readiness semantics. |
| Controlled leakage test with synthetic stimulus | Medium | Needs safe test harness, route setup, and metrics. |
| Headset-first clean gate | Medium | Needs route classification, UX, and QA matrix. |
| Apple AVAudioEngine voice-processing spike | Medium-high | Needs app graph proof that input and output can both be in voice-processing mode and still feed virtual mic plus recording. |
| Apple VoiceProcessingIO spike | Medium-high | Native but route-dependent and can disturb Core Audio topology. |
| System Mic Modes/Voice Isolation guidance | Low-medium | Useful for user guidance and diagnostics, but not deterministic clean acceptance unless proven. |
| WebRTC AEC3 live mic processing | High | Needs real-time app graph, aligned reference/capture, delay, double-talk, packaging, CPU/latency gates. |
| Krisp-like all-route speakerphone quality | Very high | Requires robust model/algorithm tuning across rooms, devices, volume, Bluetooth, and route changes. |

## Best-Practice Implications

- Do not run AEC or file writing inside HAL callbacks unless it is proven
  realtime-safe; prefer app-owned processing with bounded buffers.
- Use the exact far-end signal that is sent to the physical output as the AEC
  reference.
- Keep the reference and capture clocks/timelines aligned; otherwise AEC and
  leakage measurement become unreliable.
- Treat double-talk as a first-class scenario. A bad canceller can suppress the
  local speaker whenever remote audio is active.
- Treat clipping and loud speaker distortion as route failures; nonlinear
  distortion is hard for classical AEC to cancel.
- Do not rely on browser WebRTC AEC alone. 2brain Rec's virtual-device routing
  can change what the browser sees as the capture/playback relationship.
- Do not rely on system Mic Modes alone unless validation proves they clean the
  exact virtual-microphone output and recording path.
- Prefer Apple voice-processing primitives before custom DSP, but only behind
  explicit spike evidence.
- Make headphones/headsets a first-class recovery path, not a hidden support
  suggestion.
- Preserve clean-room boundaries: study public behavior and APIs only; do not
  copy Krisp implementation, strings, assets, or private behavior.

## Recommended Next Clarification Answer

For the current `020` spec, the best answer to the minimal acceptance question
is:

**Gate + active mitigation, staged.**

Meaning:

- A route may be marked clean only when leakage is prevented, suppressed, or
  physically avoided.
- Detection-only is not enough for final acceptance.
- Headphones/headsets can be accepted first.
- Built-in speakerphone routes can remain blocked or pilot-only until Apple
  voice processing or WebRTC AEC3 proves clean.

## Recommended Plan Shape

During `$speckit-plan`, split the work into phases:

1. **Phase 0 research**: choose thresholds, route matrix, and AEC spike path.
2. **Phase 1 contracts**: leakage status model, route evidence, manifest fields,
   diagnostic redaction, controlled stimulus contract.
3. **Phase 2 detection gate**: timeline alignment, leakage measurement,
   metadata-only evidence, transcription-ready blocking.
4. **Phase 3 headset-first acceptance**: route classification, UX recovery,
   validation matrix.
5. **Phase 4 active AEC spike**: Apple VoiceProcessingIO and/or WebRTC AEC3
   behind flags, with CPU/latency/crash gates.
6. **Phase 5 promotion decision**: built-in speakerphone route accepted only
   after controlled and live meeting evidence passes.

## Sources

- Apple Developer Documentation: `AVAudioIONode.voiceProcessingEnabled`
  <https://developer.apple.com/documentation/avfaudio/avaudioionode/isvoiceprocessingenabled>
- Apple Developer Documentation: echo-cancelled input availability and
  preference APIs
  <https://developer.apple.com/documentation/avfaudio/avaudiosession/isechocancelledinputenabled>
- Apple Developer Documentation: `kAudioUnitSubType_VoiceProcessingIO`
  <https://developer.apple.com/documentation/audiotoolbox/kaudiounitsubtype_voiceprocessingio>
- Apple WWDC19: `AVAudioEngine` voice processing mode for echo cancellation and
  VoIP; both input and output nodes need voice-processing mode
  <https://developer.apple.com/videos/play/wwdc2019/510>
- Apple Developer Documentation: `AVCaptureDevice.MicrophoneMode.voiceIsolation`
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/microphonemode/voiceisolation>
- Apple Developer Documentation: system video effects and microphone modes
  <https://developer.apple.com/documentation/avfoundation/system-video-effects-and-microphone-modes>
- Apple Developer Documentation: show the system UI for microphone modes
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/showsystemuserinterface%28_%3A%29>
- Apple Developer Documentation: inspect the user's preferred microphone mode
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/preferredmicrophonemode>
- Apple Support: user-facing Mic Modes on Mac, including Voice Isolation
  <https://support.apple.com/en-ie/guide/mac-help/mchle82b42f0/mac>
- WebRTC source: `EchoCanceller3` receives render/capture frames and handles
  jitter around API call sequence
  <https://webrtc.googlesource.com/src/+/38fd1758e90bcdc7690a552e7ef0ec0d143d2f30/webrtc/modules/audio_processing/aec3/echo_canceller3.h>
- WebRTC source: AEC3 configuration and suppressor/delay tuning
  <https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/aec3/echo_canceller3.cc>
- PJSIP AEC docs: multiple AEC options including hardware AEC, WebRTC AEC3, and
  Speex AEC
  <https://docs.pjsip.org/en/2.16/specific-guides/audio/aec.html>
- Speex manual: echo cancellation timing requirements and troubleshooting
  <https://speex.org/docs/manual/speex-manual/node7.html>
- Speex API reference: microphone rec, speaker play, cleaned output semantics
  <https://www.speex.org/docs/api/speex-api-reference.pdf>
- Switchboard AEC3 explainer: delay estimation, double-talk, and AEC3 pipeline
  <https://switchboard.audio/hub/how-webrtc-aec3-works/>
- rtcStats AEC note: browsers can disable AEC and then speaker audio captured
  by mic can be sent back
  <https://www.rtcstats.com/kb/observation-aecdisabled>
- Microsoft echo troubleshooting: headphones, volume, and speaker placement as
  mitigations
  <https://learn.microsoft.com/en-us/azure/communication-services/resources/troubleshooting/voice-video-calling/audio-issues/echo-issue>
