# Research: Microphone Sample Graph Foundation

## Decision: Feed An App-Owned Microphone Sample Source Into The Existing Writer

Accepted `037` recordings must use an app-owned microphone sample source that
feeds `LocalRecordingWriter` through `microphoneSampleSourceFactory`. The source
captures microphone frames before they are written to `mic.wav`, exposes bounded
metadata-only health counters, and keeps the writer responsible for the existing
PCM package format.

**Rationale**: The current writer already has a `LocalRecordingSampleSource`
protocol, a microphone source factory, PCM writer support, bounded drain logic,
and tests for injected sample sources. Using this seam gives future cleanup/AEC
work access to microphone frames without changing the package contract or
duplicating file-finalization logic.

**Alternatives considered**:

- Continue using `AVAudioRecorder` as the accepted microphone path: rejected for
  `037` acceptance because it does not give the app frame-level control before
  persistence.
- Build a new recording package writer: rejected because it would churn the
  accepted `025` package and `020` leakage gates.
- Mix microphone and incoming audio into one file first: rejected because
  dual-track truth is a core product and MediaScribe readiness requirement.

## Decision: Use Native Recording Input Selection With Default Fallback

The recording flow must resolve a microphone input before starting capture. If
the user selected a native recording microphone, use that input. If no selection
exists, use the current macOS default input and record that fallback truth in
metadata.

**Rationale**: The user clarified that `037` should include native recording
microphone selection. Using the current default only as fallback keeps the app
usable without setup while making explicit selection possible for clean-room
recording experiments and future AEC comparisons.

**Alternatives considered**:

- Use only the macOS default input: rejected by clarification.
- Defer selection to `041`: rejected because the app-owned stream must know
  which input it owns and must fail closed if the wrong selected input is used.
- Change the global macOS default input to satisfy selection: rejected because
  recording selection must not silently mutate system routing.

## Decision: Reject Virtual And Unsupported Self-Routing Inputs

Recording microphone selection must reject `2brain Rec Microphone`,
`2brain Rec Speaker`, aggregate/multi-output/other virtual devices, and
unsupported self-routing inputs before capture starts.

**Rationale**: The current product baseline parks virtual-driver routing as
future advanced work. A recording input that loops app output back into the mic
path can make speaker leakage worse and would produce misleading `037`
evidence. Existing `SelfRoutingGuard` and physical-device classification provide
the local policy shape to reuse or narrow.

**Alternatives considered**:

- Allow all devices and mark them after recording: rejected because the feature
  must fail closed on unsupported selection and avoid misleading clean evidence.
- Require the user to select the old 2brain virtual microphone: rejected because
  the MVP recording path is system-audio-first and must not depend on virtual
  devices.

## Decision: Preserve The Current Local Package Contract

`037` keeps `mic.wav`, `incoming.wav`, and `manifest.json`. The microphone track
remains `wav-pcm-s16le`, 16 kHz, mono, timeline-aligned when accepted. New stream
truth belongs in manifest metadata and diagnostics, not in extra raw sample
files.

**Rationale**: Existing accepted behavior, tests, upload readiness, leakage
finalization, and deletion accounting already expect the local dual-track
package. The feature should prepare for cleanup while minimizing downstream
churn.

**Alternatives considered**:

- Add a raw microphone capture dump: rejected because diagnostics must remain
  metadata-only and raw audio evidence is not safe to commit/export.
- Write a new cleaned or processed microphone track: rejected because cleanup
  and derived-track deletion accounting are future slices.

## Decision: Treat Legacy Recorder Fallback As Compatibility, Not Proof

The old `AVAudioRecorder` path may remain temporarily as a bounded fallback
while the app-owned graph is introduced, but an accepted `037` success must prove
the app-owned sample source path was used. If capture falls back to legacy
recording, the manifest or evidence must mark the package degraded, unproven, or
legacy-not-ready for the `037` graph readiness claim.

**Rationale**: The backlog explicitly allows keeping the current recorder path
until the graph is validated or later removed. That is useful for product
continuity, but it cannot be used as evidence that future cleanup/AEC has a
controllable frame source.

**Alternatives considered**:

- Remove `AVAudioRecorder` immediately: rejected because it increases blast
  radius before runtime evidence exists.
- Silently fall back and still mark the recording accepted for `037`: rejected
  because it would create false readiness.

## Decision: Fail Closed On Stream Identity, Availability, And Health Problems

The microphone stream must record blocked, degraded, failed, or unproven truth
for permission denial, selected input disappearance, unsupported selection,
route change, no frames, silence, write failure, Stop/quit interruption, and
resource cleanup failures.

**Rationale**: A controllable mic stream is only useful if failures do not look
like clean recordings. Existing failure reasons such as `permission_denied`,
`device_unavailable`, `silent_input`, `no_frames`, `write_failed`,
`capture_failed`, `timeline_misaligned`, `legacy_not_ready`, and `app_closed`
are close to the needed state model.

**Alternatives considered**:

- Trust final WAV existence alone: rejected because empty/silent/wrong-device
  tracks can still produce files.
- Add raw samples to diagnostics for debugging: rejected by privacy and
  evidence-safety requirements.

## Decision: Defer Cleanup And AEC Claims To Follow-Up Features

`037` provides selected/default microphone frames, timing, and health metadata.
It does not enable Apple voice processing, WebRTC AEC3, fallback decisions, or
permission-readiness onboarding claims.

**Rationale**: Features `038`-`041` answer separate questions: Apple
voice-processing behavior, WebRTC AEC feasibility, speakerphone fallback
product decision, and onboarding readiness. Mixing them into `037` would make
acceptance ambiguous and harder to verify.

**Alternatives considered**:

- Enable voice processing in the first sample graph: rejected because it changes
  audio behavior and requires separate CPU/latency/leakage proof.
- Ship WebRTC AEC in the foundation slice: rejected because dependency,
  licensing, packaging, and double-talk validation are separate gates.

## Primary Sources And Local Evidence

- `docs/audio-capture-backlog.md`, Feature 037 scope and acceptance gates.
- `specs/025-system-audio-capture-pivot/plan.md`, accepted package, CPU, and
  system-audio-first constraints.
- `specs/020-speaker-to-mic-leakage/spec.md`, leakage-finalization truth model.
- Apple AVAudioEngine documentation:
  <https://developer.apple.com/documentation/avfaudio/avaudioengine>
- Apple AVAudioInputNode documentation:
  <https://developer.apple.com/documentation/avfaudio/avaudioinputnode>
- Apple microphone authorization guidance:
  <https://developer.apple.com/documentation/avfoundation/requesting-authorization-to-capture-and-save-media>
