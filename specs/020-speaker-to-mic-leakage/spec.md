# Feature Specification: Speaker-To-Mic Leakage Control

**Feature Branch**: `020-speaker-to-mic-leakage`

**Created**: 2026-06-04

**Status**: Archived v3 leakage finalization; not used by the v5 path

**Input**: User observed during a live meeting that sound from the speakers gets
captured by the microphone. Evidence recording directory id:
`20260604-091621-C705ED72-E352-4522-93F2-1219953177EE`. The feature must fully
analyze and prevent remote/far-end speaker audio from contaminating the local
microphone path, while preserving 2brain Rec's driver-first dual-track capture,
visible recording control, local-only diagnostics, clean-room Krisp-category
positioning, and future MediaScribe dual-track readiness.

## Problem Evidence And Baseline

- A real 73-minute meeting recording produced `mic.wav`, `incoming.wav`, and
  `manifest.json`.
- The manifest status is `degraded` with `failureReason=timeline_misaligned`.
- `mic.wav` is WAV PCM signed 16-bit little-endian, mono, 16000 Hz, about
  73:13.07 long.
- `incoming.wav` is WAV PCM signed 16-bit little-endian, mono, 16000 Hz, about
  70:40.88 long.
- The microphone track is about 152.19 seconds longer than the incoming track.
- Automated correlation over the shared overlap did not show a persistent
  zero-latency digital copy of `incoming.wav` inside `mic.wav`; the observed
  symptom is therefore treated as an acoustic echo/leakage and recording-truth
  problem unless later evidence proves a direct software loop.
- The current architecture already separates virtual microphone and virtual
  speaker roles, but it does not yet prove that the persisted local mic track is
  a clean near-end track when physical speakers are audible in the room.
- The constitution requires the virtual audio layer to prevent loopback from
  remote audio into `2brain Rec Microphone`; this feature is a capture-integrity
  gate, not a cosmetic transcript-quality improvement.

## Clarifications

### Session 2026-06-04

- Q: What must happen if built-in mic plus built-in speakers cannot pass clean dual-track validation? → A: The plan must propose an alternative recording/transcription architecture instead of shipping unresolved leakage.
- Q: What alternative is acceptable if clean dual-track cannot be proven? → A: Preserve tracks as evidence, but allow transcription readiness to change around leakage labels and post-processing instead of treating `mic.wav` as clean truth.
- Q: Should users be asked to fix risky routes during recording? → A: No. The product must solve leakage on the app side first; if clean separation cannot be achieved, the plan must evaluate non-separated recording such as mixed meeting audio.
- Q: When may the plan use mixed audio instead of clean separated tracks? → A: Only after Apple/WebRTC/app-side clean dual-track spikes fail acceptance.
- Q: When does a recording receive final leakage status? → A: Only after recording stops and package finalization analyzes saved evidence.
- Q: Should this feature clean leakage during the live meeting? → A: No. It must not perform live leakage cleanup; it records evidence as-is and assigns recording truth after finalization.
- Q: May the system create cleaned audio after recording? → A: Yes. Post-recording cleanup may create derived cleaned tracks while preserving original `mic.wav` and `incoming.wav` as evidence.
- Q: Should route readiness remain in this feature? → A: No. Remove route readiness from this feature; analyze finalized recording packages only.
- Q: Should final leakage statuses remain as currently named? → A: Yes. Keep `clean`, `leakage_detected`, `unproven`, `not_measured`, and `not_applicable`; planning may refine rules. `unproven` means measurement was attempted but cleanliness was not proven. `not_measured` means measurement did not run or did not apply.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Remote Audio Out Of The Local Mic Track (Priority: P1)

As a meeting user, I want the saved local microphone evidence to represent my
local speech truthfully, including whether it contains remote speaker leakage,
so that future transcripts do not double-count remote speech as mine.

**Why this priority**: If speaker audio leaks into the saved mic path and the
system later treats that track as clean, diarization can assign remote speech to
the user and MediaScribe dual-track input becomes untrustworthy.

**Independent Test**: Run a controlled meeting or synthetic call with remote
speech playing through the selected physical output while the local user is
silent, then verify the finalized recording package either marks the local mic
track clean below the accepted leakage threshold or truthfully marks it as
contaminated, unproven, or not transcription-ready.

**Acceptance Scenarios**:

1. **Given** `2brain Rec Microphone` and `2brain Rec Speaker` are selected in a
   supported meeting target, **When** remote speech plays through built-in or
   wired speakers while the local user is silent, **Then** this feature records
   the evidence as-is and does not claim live echo cleanup.
2. **Given** the local recording is active, **When** remote speech plays and the
   local user is silent, **Then** finalization either proves `mic.wav` is below
   the accepted leakage threshold or marks the package contaminated, unproven,
   or not transcription-ready.
3. **Given** the local user and remote speaker talk at the same time, **When**
   leakage diagnostics evaluate the finalized package, **Then** the system
   distinguishes double-talk from far-end-only leakage as far as evidence allows
   and does not mark uncertain evidence as clean.
4. **Given** the selected output route may cause leakage, **When** the meeting
   is recorded, **Then** this feature does not block or classify live route
   readiness and instead evaluates leakage from the finalized package.
5. **Given** most expected users rely on built-in Mac speakers, built-in
   microphones, or lightweight headphones, **When** planning evaluates MVP
   capture viability, **Then** built-in speakerphone quality is treated as a
   required product problem to solve rather than a permanently optional route.

---

### User Story 2 - Preserve Clean Dual-Track Recording Truth (Priority: P1)

As a user reviewing or uploading a recording later, I want the finalized saved
artifact to truthfully state whether the local mic track is clean,
contaminated, degraded, or unproven, so that transcription, diarization, and
playback do not rely on false dual-track assumptions.

**Why this priority**: The current MediaScribe plan depends on separate
`mic_file` and `incoming_file` tracks with a shared timeline. A contaminated mic
track is not a clean local speaker track even if the file format is correct.

**Independent Test**: Stop a recording after controlled far-end-only,
near-end-only, and double-talk intervals, inspect the manifest/evidence, and
confirm it records track alignment and leakage truth before declaring the
package transcription-ready.

**Acceptance Scenarios**:

1. **Given** both tracks are saved, **When** their timelines differ beyond the
   accepted tolerance, **Then** the package remains degraded and reports
   timeline misalignment.
2. **Given** remote-to-mic leakage exceeds the accepted threshold, **When** the
   package is finalized, **Then** the manifest or associated evidence records a
   concrete leakage failure reason and does not claim clean dual-track
   readiness.
3. **Given** leakage could not be measured because the recording lacks a valid
   reference, route metadata, or aligned test windows, **When** the package is
   finalized, **Then** the system reports leakage status as unproven rather than
   clean.
4. **Given** the local user records with headphones or another output route
   that prevents acoustic leakage, **When** controlled validation passes, **Then**
   the package can be marked clean for this gate.
5. **Given** a recording is still in progress, **When** leakage evidence is
   incomplete, **Then** the system does not assign final `clean`,
   `leakage_detected`, or `unproven` package status until stop/finalization.

---

### User Story 3 - Avoid User-Burden During Recording (Priority: P1)

As a user joining a meeting, I want 2brain Rec to record without asking me to
understand or fix audio routing, so that I can start and stop recording normally
while the product later tells the truth about the saved artifact.

**Why this priority**: Most expected users may rely on built-in speakers,
built-in microphones, or lightweight headphones. The product should not shift
the burden of speaker-to-mic leakage onto the user.

**Independent Test**: Try built-in speakers, wired headphones, USB headsets,
Bluetooth/AirPods-class devices, aggregate outputs, and high-volume speaker
routes; confirm recording is not blocked by leakage route status and each
finalized package gets package-level leakage evidence where measurement is
possible.

**Acceptance Scenarios**:

1. **Given** built-in speakers are selected with a built-in microphone, **When**
   the user records a meeting, **Then** 2brain Rec records without requiring the
   user to change route and later classifies the finalized package.
2. **Given** wired headphones or a validated headset are selected, **When** the
   user records a meeting, **Then** the package can be classified clean only
   after finalization evidence passes.
3. **Given** Bluetooth, AirPods-class, aggregate, multi-output, or unknown
   virtual routes are selected, **When** they lack sufficient leakage evidence
   under the finalization threshold, alignment, and reference-window rules,
   **Then** the finalized package is marked `unproven` or `not_measured` rather
   than clean.
4. **Given** the user changes microphone, output, volume, mute, browser target,
   sleep/wake state, or `coreaudiod` state, **When** 2brain Rec detects the
   change, **Then** the change is captured as metadata when available for
   finalization evidence without requiring immediate user remediation.

---

### User Story 4 - Detect And Diagnose Leakage Without Leaking Content (Priority: P2)

As QA or support, I want metadata-only leakage evidence that identifies whether
speaker audio is contaminating the mic path, so that the team can debug route
quality without storing or exporting raw meeting content.

**Why this priority**: The problem was found in a real meeting. Future evidence
must be strong enough to reproduce and fix it, but diagnostics must preserve the
project's no-content, no-secret boundary.

**Independent Test**: Run the leakage diagnostics on controlled stimuli and a
saved artifact package, then confirm outputs include safe metrics, thresholds,
route facts, and failure reasons without raw audio samples, transcript text,
participant speech, credentials, tokens, signed URLs, or live secret paths.

**Acceptance Scenarios**:

1. **Given** a controlled far-end reference stimulus is used, **When** leakage
   diagnostics run, **Then** evidence includes measured leakage classification,
   route metadata, timing/alignment status, and threshold outcome only.
2. **Given** a real meeting recording is analyzed, **When** evidence is saved,
   **Then** it excludes transcript text, raw audio, participant names, and full
   local user paths.
3. **Given** evidence detects possible software loopback, **When** diagnostics
   are produced, **Then** it distinguishes direct digital loop suspicion from
   acoustic leakage suspicion.

---

### User Story 5 - Keep Clean-Room Krisp-Category Behavior (Priority: P2)

As the product owner, I want 2brain Rec to solve this as a clean-room
Krisp-category audio routing and echo-control problem, so that the product
matches the category expectation without copying Krisp assets, copy,
proprietary behavior, binaries, or protected implementation details.

**Why this priority**: The PRD positions 2brain Rec in the same category while
requiring brand and implementation distance. Echo control is category-critical,
but it must be based on public OS APIs, original code, licensed SDKs, or
approved open-source/commercial models.

**Independent Test**: Review the design artifacts and implementation plan to
confirm they rely only on public documentation, behavior-level observations,
original implementation, and approved dependencies.

**Acceptance Scenarios**:

1. **Given** the team studies Krisp behavior, **When** requirements are written,
   **Then** they describe product outcomes and public architecture patterns
   rather than copying proprietary implementation details.
2. **Given** an echo-cancellation component is selected later, **When** it is
   evaluated, **Then** licensing, offline/local processing, CPU, latency,
   privacy, and clean-room suitability are documented before implementation.

### Edge Cases

- Remote audio plays through laptop speakers while the local user is silent.
- Remote audio plays loudly enough to distort speakers or clip the microphone.
- The local user and remote participant speak simultaneously.
- The local user is naturally quiet or pauses for long intervals.
- Browser/WebRTC echo cancellation is disabled, bypassed, unavailable, or
  ineffective because 2brain Rec virtual routing changes the browser's normal
  reference path.
- The meeting app applies its own AEC/noise suppression before or after the
  virtual device layer.
- The recording starts before the incoming track has frames or stops after the
  incoming track stops.
- `mic.wav` and `incoming.wav` have different lengths, missing silence padding,
  clock drift, or unknown `t=0`.
- The physical output is built-in speakers, wired headphones, USB headset,
  Bluetooth/AirPods-class, aggregate, multi-output, HDMI, AirPlay, or another
  virtual device.
- The physical microphone is built-in, USB, Bluetooth, headset boom, monitor
  mic, or another virtual device.
- The user changes output volume, mute state, mic gain, selected devices,
  browser target, or system route during a meeting.
- The room changes during a call: laptop moved, lid angle changed, external
  speaker moved, or another device in the room joins the same call.
- The physical route allowed the meeting to be recorded, but the finalized
  package does not meet the clean or transcription-ready dual-track gate.
- A leakage measurement uses a real meeting artifact and must not preserve
  content-bearing evidence in repository files.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define and enforce a speaker-to-mic leakage gate
  only at finalized recording package level before a package can be accepted as
  clean or transcription-ready.
- **FR-002**: The leakage gate MUST evaluate remote/far-end speaker audio
  contamination separately from ordinary microphone noise, room echo, silence,
  clipping, dropout, and timeline alignment.
- **FR-003**: The system MUST prevent intelligible remote speaker audio from
  being treated as clean local speech in finalized recording and transcription
  readiness decisions. This feature MUST NOT perform live leakage cleanup
  during the active meeting.
- **FR-003a**: The implementation plan MUST treat built-in Mac microphone plus
  built-in Mac speakers as a required target route for this problem. If this
  route cannot meet clean dual-track acceptance through Apple voice processing,
  WebRTC AEC3, route control, or another approved local method, the plan MUST
  propose an alternative product architecture instead of accepting unresolved
  speaker-to-mic leakage as MVP behavior.
- **FR-003b**: If clean dual-track cannot be proven for a required route, an
  alternative architecture MAY preserve `mic.wav` and `incoming.wav` as evidence
  tracks, but MUST NOT treat the local mic track as clean local-speaker truth.
  The alternative MUST define leakage labels, post-processing or diarization
  assumptions, and revised transcription-readiness semantics before upload or
  transcription can depend on the package.
- **FR-003b.1**: After recording stops, the system MAY create derived cleaned
  audio tracks through post-recording processing. Derived tracks MUST be clearly
  labeled as derived artifacts, MUST preserve lineage to the original evidence
  tracks, and MUST NOT replace or overwrite original `mic.wav` or `incoming.wav`.
- **FR-003c**: The product MUST NOT make leakage truth depend on the user
  switching devices, lowering volume, rerunning route checks, accepting risk, or
  understanding audio-routing concepts during normal recording. User guidance MAY
  explain degraded truth after the fact, but the primary mitigation MUST be
  recording semantics, post-finalization evidence, or an alternative capture
  strategy.
- **FR-003d**: If separated local-mic and incoming-speaker tracks cannot be made
  truthful for common built-in speakerphone use, the plan MUST evaluate a
  non-separated recording option, including a single mixed meeting audio track
  with explicit diarization and confidence semantics, before rejecting the
  feature as infeasible.
- **FR-003e**: A non-separated or mixed-audio fallback MUST NOT be selected as
  the first implementation path. It is allowed only after Apple built-in voice
  processing, WebRTC AEC3 or an approved equivalent, and app-side recording
  graph changes fail the accepted clean dual-track gates for required built-in
  speakerphone routes.
- **FR-004**: The original `local_mic` evidence track MUST remain labeled as
  original evidence and MUST NOT be labeled clean or transcription-ready unless
  the package finalization gate proves it clean. If post-recording cleanup
  creates a derived track, the derived artifact MUST carry separate lineage,
  confidence, residual-leakage status, and transcription eligibility.
- **FR-005**: The system MUST preserve local near-end speech during double-talk
  and MUST NOT solve leakage by muting the microphone whenever remote audio is
  active.
- **FR-006**: The system MUST NOT expose or enforce leakage route readiness in
  this feature. Leakage outcomes are package-level finalization results:
  `clean`, `leakage_detected`, `unproven`, `not_measured`, or `not_applicable`.
- **FR-007**: The system SHOULD capture microphone route, output route, output
  volume, mute, browser target, app bridge health, `coreaudiod`, sleep/wake, or
  selected-device changes as metadata for finalization evidence when available,
  but MUST NOT use them as live leakage blockers in this feature.
- **FR-008**: The system MUST reject self-routing where any 2brain Rec virtual
  device is selected as a physical working microphone or output.
- **FR-009**: Aggregate, multi-output, Bluetooth/AirPods, HDMI/AirPlay, and
  unknown virtual audio routes MUST be represented in package evidence when
  available, but MUST NOT create user-facing route-readiness blocks in this
  feature.
- **FR-010**: The system MUST classify saved recording packages with a leakage
  status: `clean`, `leakage_detected`, `unproven`, `not_measured`, or
  `not_applicable`.
- **FR-010.1**: The final leakage status meanings MUST be:
  - `clean`: leakage measurement ran and found remote speaker leakage below the
    accepted threshold.
  - `leakage_detected`: leakage measurement ran and found remote speaker
    leakage above the accepted threshold.
  - `unproven`: leakage measurement was attempted, but the package did not
    contain enough reliable evidence to prove cleanliness, such as alignment
    within tolerance, sufficient reference windows, or separable far-end-only
    evidence.
  - `not_measured`: leakage measurement did not run or could not apply to this
    package, such as unsupported package shape, missing reference signal, or
    skipped measurement.
  - `not_applicable`: the leakage gate does not apply to this package or
    artifact type.
- **FR-010.2**: Planning MAY refine the decision rules, thresholds, and exact
  evidence requirements for these statuses, but MUST preserve the distinction
  between `unproven` as "attempted but not proven" and `not_measured` as "not
  measured or not applicable to measurement."
- **FR-010a**: Final leakage status MUST be assigned only during package
  finalization after recording stops, using saved track evidence, timeline
  alignment, route metadata, and leakage diagnostics. Preflight, route class,
  and in-progress processing MUST NOT assign final package cleanliness.
- **FR-010a.1**: If post-recording cleanup creates a derived cleaned track, the
  package MUST retain separate statuses for original evidence cleanliness and
  derived artifact usability. A derived track may be eligible for transcription
  only when its lineage, confidence, and residual-leakage evidence pass the
  accepted finalization gate.
- **FR-010b**: During normal recording, the app MUST NOT show user-facing live
  leakage status, ask the user to act on it, or apply live leakage cleanup in
  this feature. Recording-time behavior is limited to capture and evidence
  collection; leakage decisions are made after stop/finalization.
- **FR-011**: A package MUST NOT be marked transcription-ready when required
  tracks are timeline-misaligned beyond tolerance, missing, empty, failed, or
  contaminated by leakage above threshold.
- **FR-012**: Leakage diagnostics MUST distinguish likely acoustic leakage from
  likely direct software loopback using available timing, correlation, route,
  and track evidence.
- **FR-013**: Leakage diagnostics MUST support controlled validation stimuli
  that are explicit, local, non-secret, non-meeting-content, and excluded from
  production diagnostics by default.
- **FR-014**: Diagnostics and evidence MUST include route class, selected device
  classes when available, package leakage status, threshold version, alignment
  status, measurement confidence, failure reason, and derived-artifact lineage
  without raw audio, transcript
  text, participant speech, meeting content, credentials, tokens, signed URLs,
  passwords, or live absolute user paths.
- **FR-015**: The app MAY expose concise recording-truth status for failed or
  risky leakage states, but MUST NOT require the user to change devices, reduce
  output volume, rerun validation, or accept technical risk as the normal path
  to record. Any user-facing copy MUST describe the artifact truth in simple
  language rather than making the user responsible for audio engineering.
- **FR-016**: The system MUST preserve visible manual `Record`/`Stop`, active
  recording indicator, and one-action stop while adding finalized recording
  truth.
- **FR-017**: The system MUST NOT add hidden recording, no-driver fallback,
  direct desktop-to-MediaScribe upload, MediaScribe credentials on desktop,
  Langfuse content traces, or external network egress in this feature.
- **FR-018**: The solution MUST preserve realtime safety: no file IO, logging,
  allocation, locks, network calls, process launches, UI work, or unbounded waits
  may be added to HAL/Core Audio realtime callbacks.
- **FR-019**: The system MUST maintain clean-room separation from Krisp and other
  commercial products by relying only on public documentation, behavior-level
  observations, original code, and approved dependencies.
- **FR-020**: The plan for any AEC/noise/voice-processing, post-processing, or
  mixed-audio fallback dependency MUST record licensing, offline/local
  processing behavior, CPU budget, latency budget, privacy boundary, route
  topology, test coverage, fallback behavior, and clean-room basis before
  coding.
- **FR-021**: Planning MUST evaluate Apple/macOS built-in voice-processing
  options before selecting a custom AEC implementation. The evaluation MUST
  include `AVAudioEngine` voice processing, `VoiceProcessingIO`, and system
  microphone modes, and MUST document whether each option can clean the exact
  signal delivered to `2brain Rec Microphone` and persisted as `mic.wav`.
- **FR-022**: Apple built-in voice processing MUST NOT be accepted based on API
  availability alone. It MUST pass controlled leakage, double-talk, latency,
  channel/format stability, route-change, crash/no-hang, and local recording
  alignment validation before any original or derived package artifact is marked
  clean.
- **FR-023**: System Mic Modes and Voice Isolation MUST be treated as
  user/system-controlled assistance unless planning proves an app-owned,
  deterministic integration. The app MAY guide the user to the system
  microphone-mode UI and MAY observe active/preferred microphone mode when
  available, but MUST NOT claim it can force or guarantee Voice Isolation unless
  the platform API and validation evidence prove that behavior.
- **FR-024**: If Apple voice processing changes channel count, sample format,
  sample rate, route topology, AGC/noise behavior, or output loudness, the
  feature MUST either normalize and validate those changes or reject the
  resulting original/derived artifact as clean evidence.
- **FR-025**: If Apple built-in processing cannot access the same far-end
  reference that 2brain Rec sends to the physical output, or if it cannot feed
  the cleaned near-end signal into both the virtual microphone and recording
  writer with stable timing, the feature MUST treat Apple processing as
  insufficient for clean package acceptance and continue to WebRTC AEC3,
  post-recording cleanup, or mixed-audio fallback evaluation.
- **FR-026**: The package finalization validation matrix MUST include recordings
  made with built-in mic/speakers, wired headphones, USB headset,
  Bluetooth/AirPods-class device, aggregate or multi-output route, and at least
  one supported browser/meeting target.
- **FR-027**: The system MUST preserve dual-track semantics: remote speaker audio
  remains available in the incoming track while the local mic track represents
  the local user as cleanly as the accepted route permits.
- **FR-028**: The system MUST expose enough metadata for future MediaScribe
  submission logic to refuse contaminated or unproven packages before upload or
  transcription starts.
- **FR-029**: If leakage classification or cleanup cannot be implemented
  acceptably for a finalized package, the product MUST fail truthfully with a
  clear package-level reason instead of silently shipping degraded audio.

### Key Entities *(include if feature involves data)*

- **Leakage Evaluation**: A metadata-only assessment of whether far-end speaker
  audio is present in the local microphone path above the accepted threshold.
- **Far-End Reference**: The incoming/remote audio signal used to determine
  whether speaker output is leaking into the mic path. It must be aligned enough
  for measurement and must not be stored in diagnostics as raw content.
- **Near-End Capture**: The local microphone path expected to represent the
  recording owner or local participant.
- **Leakage Status**: Package or route state: `clean`, `leakage_detected`,
  `unproven`, `not_measured`, or `not_applicable`. `unproven` means the system
  tried to measure leakage but could not prove cleanliness; `not_measured` means
  measurement did not run or was not applicable.
- **Leakage Threshold Version**: The named acceptance threshold set used for a
  measurement, so future tuning does not make old evidence ambiguous.
- **Recording Route Metadata**: Metadata about physical input/output class and
  route changes captured for finalization evidence, without creating
  user-facing leakage readiness.
- **Recording Cleanliness Evidence**: Metadata-only proof attached to a
  recording package or QA run, excluding raw audio and meeting content.
- **Derived Cleaned Track**: A post-recording audio artifact produced from
  original evidence tracks to reduce leakage or improve transcription. It must
  be labeled as derived and traceable to source evidence.
- **Timeline Alignment State**: Whether local mic and incoming tracks share a
  sufficiently aligned timeline for leakage measurement and dual-track
  transcription readiness.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly affects macOS virtual audio
  capture integrity. It must preserve driver-first MVP behavior, separate mic
  and speaker tracks, fail-closed readiness, self-routing rejection, and no
  remote-to-mic loopback acceptance.
- **Visible Control Impact**: The feature must preserve manual start/stop,
  visible active recording indicator, and one-action stop. Leakage warnings or
  blocks must not hide active capture state.
- **Data Boundary Impact**: This feature is local-only unless a later plan
  explicitly scopes server-side metadata ingestion. It must not call
  MediaScribe, Langfuse, LLM services, analytics, or any external network
  dependency.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, API keys,
  or live credential paths may be stored in specs, diagnostics, evidence,
  screenshots, logs, or fixtures.
- **Retention/Deletion Impact**: This feature adds recording-quality metadata,
  not new retention/deletion promises. Any future upload or dashboard surface
  must use leakage status to avoid false transcription readiness.
- **Audit Impact**: Recording package leakage outcomes and route metadata used
  during finalization must be auditable as metadata-only events.
- **UX/Brand/Accessibility Impact**: User-facing states must use original
  2brain Rec language, be localizable, keyboard reachable, not rely on color
  alone, and remain brand-distinct from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In controlled far-end-only validation, a finalized package marked
  clean keeps remote speaker leakage in the local mic path below the accepted
  intelligibility and level thresholds for 100% of required device/browser
  matrix runs.
- **SC-002**: During double-talk validation, original local mic samples remain
  unchanged, double-talk windows do not cause mic muting or suppression by the
  leakage finalization logic, and uncertain overlapping evidence is downgraded
  to `unproven` rather than marked `clean`.
- **SC-003**: A recording package with track duration mismatch beyond tolerance
  is marked degraded or unproven 100% of the time and is not marked
  transcription-ready.
- **SC-004**: A recording package with measured leakage above threshold is
  marked `leakage_detected` 100% of the time and is not marked clean.
- **SC-005**: A finalized package without enough aligned reference evidence is
  marked `unproven` or `not_measured`, never clean.
- **SC-005a**: No in-progress recording is marked final `clean`,
  `leakage_detected`, or `unproven`; those package-level statuses appear only
  after stop/finalization.
- **SC-006**: Leakage route readiness is not exposed or enforced in this
  feature; selected input/output, volume/mute, browser target, app bridge,
  `coreaudiod`, and sleep/wake changes are used only as finalization metadata
  when available.
- **SC-007**: Recordings made with built-in mic/speaker, wired headphones, USB
  headset, Bluetooth/AirPods-class, aggregate/multi-output, and supported
  browser meeting targets all receive package-level finalization evidence or an
  explicit `unproven`/`not_measured` status.
- **SC-008**: Diagnostics and evidence scans find no raw audio, transcript text,
  meeting content, participant speech, credentials, tokens, signed URLs,
  passwords, API keys, or live absolute user paths.
- **SC-009**: Realtime-safety validation finds no new blocking operations,
  logging, allocation, file IO, wall-clock, IPC wait, process launch, network
  call, or UI dependency in HAL/Core Audio callback paths.
- **SC-010**: The feature does not start upload, MediaScribe transcription,
  Langfuse content tracing, dashboard publication, retention jobs, deletion
  workflows, or external egress.
- **SC-011**: User-facing recording-truth status is shown only after package
  finalization for degraded, contaminated, unproven, not-measured, or derived
  cleaned outcomes without requiring the user to perform technical remediation.
- **SC-012**: Existing visible capture indicator, manual `Record`/`Stop`, local
  artifact format, and non-recording passthrough regression gates remain
  passing.
- **SC-013**: The plan contains an Apple built-in voice-processing decision
  record covering `AVAudioEngine` voice processing, `VoiceProcessingIO`, and
  system Mic Modes/Voice Isolation with pass/fail/spike outcomes and cited
  Apple sources.
- **SC-014**: Any Apple voice-processing path promoted beyond spike passes the
  same controlled leakage and double-talk gates as any custom AEC path and
  preserves aligned `mic.wav`/`incoming.wav` recording truth.
- **SC-015**: The plan contains a go/no-go decision for built-in Mac
  microphone plus built-in Mac speakers. For this finalization-only slice, the
  decision MUST be no-go for claiming clean built-in speakerphone dual-track
  MVP behavior by default, while allowing truthful package finalization and
  clean status only for packages that pass the accepted threshold matrix. The
  no-go decision MUST include at least one alternative architecture for meeting
  capture or transcription readiness, such as changing dual-track assumptions,
  using post-processing with explicit truth labels, or adopting a different
  local capture strategy.
- **SC-016**: If the plan selects an alternative to clean dual-track, it defines
  how leakage labels and post-processing affect transcript confidence,
  diarization, speaker attribution, upload eligibility, and user-facing
  recording truth.
- **SC-017**: The plan includes a user-burden check proving that the normal
  recording flow does not require the user to fix leakage by switching routes,
  lowering volume, rerunning checks, or accepting technical risk. If clean
  separation is infeasible, the plan compares separated-track and mixed-audio
  alternatives with explicit transcription and diarization tradeoffs.
- **SC-018**: Any decision to use mixed audio includes failed-spike evidence for
  clean dual-track on required built-in speakerphone routes and explains why the
  fallback is more truthful than continuing to label separated tracks as clean.
- **SC-019**: Finalization produces the first authoritative leakage status for a
  package, and the status is derived from persisted evidence rather than a
  preflight or live UI state.
- **SC-020**: Any derived cleaned track keeps original `mic.wav` and
  `incoming.wav` unchanged, records source lineage and confidence, and is not
  submitted for transcription unless residual leakage evidence passes the
  accepted finalization gate.

## Assumptions

- The live observation is treated as a real capture-integrity issue even though
  the initial numerical analysis does not prove a persistent direct software
  loop.
- The current local architecture uses separate virtual microphone and speaker
  devices and persists `mic.wav` plus `incoming.wav`; this feature strengthens
  cleanliness and truth gates around those tracks.
- Controlled validation may use synthetic reference audio or test meetings, but
  repository artifacts must remain metadata-only.
- Headphones/headsets may produce cleaner evidence, but the product cannot rely
  on user route changes as the normal MVP answer because many expected users use
  built-in Mac speakers, built-in microphones, or lightweight headphones.
- Any production-quality echo cancellation or voice-processing component will be
  selected during planning, after licensing, privacy, latency, CPU, platform
  behavior, route-topology, and clean-room review.
- Apple/macOS built-in voice processing is the preferred first spike because it
  may avoid custom DSP, but it is not assumed to satisfy 2brain Rec acceptance
  until it proves clean output for the virtual microphone and recording writer.
- Backend upload, MediaScribe processing, dashboard review, retention, deletion,
  and assisted auto-recording are out of scope for this feature unless a later
  Spec Kit plan explicitly supersedes this scope.

## External Research Sources

- Krisp Help: "How Krisp Microphone and Krisp Speaker work?"
  <https://help.krisp.ai/hc/en-us/articles/4402174576402-How-Krisp-Microphone-and-Krisp-Speaker-work>
- Krisp blog: "What is Acoustic Echo Cancellation?"
  <https://krisp.ai/blog/acoustic-echo-cancellation/>
- rtcStats: "AEC intentionally disabled"
  <https://www.rtcstats.com/kb/observation-aecdisabled>
- Microsoft Learn: "The user experiences echo during the call"
  <https://learn.microsoft.com/en-us/azure/communication-services/resources/troubleshooting/voice-video-calling/audio-issues/echo-issue>
- Switchboard: "Acoustic Echo Cancellation: How WebRTC AEC3 Works"
  <https://switchboard.audio/hub/how-webrtc-aec3-works/>
- Apple WWDC19: "What's New in AVAudioEngine"
  <https://developer.apple.com/videos/play/wwdc2019/510>
- Apple Developer Documentation: `AVAudioIONode.voiceProcessingEnabled`
  <https://developer.apple.com/documentation/avfaudio/avaudioionode/isvoiceprocessingenabled>
- Apple Developer Documentation: `kAudioUnitSubType_VoiceProcessingIO`
  <https://developer.apple.com/documentation/audiotoolbox/kaudiounitsubtype_voiceprocessingio>
- Apple Developer Documentation: `AVCaptureDevice.MicrophoneMode.voiceIsolation`
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/microphonemode/voiceisolation>
- Apple Developer Documentation: system video effects and microphone modes
  <https://developer.apple.com/documentation/avfoundation/system-video-effects-and-microphone-modes>
- Apple Developer Documentation: `AVCaptureDevice.showSystemUserInterface(_:)`
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/showsystemuserinterface%28_%3A%29>
- Apple Developer Documentation: `AVCaptureDevice.preferredMicrophoneMode`
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/preferredmicrophonemode>
- Apple Support: "Use Mic Modes on your Mac"
  <https://support.apple.com/en-ie/guide/mac-help/mchle82b42f0/mac>
