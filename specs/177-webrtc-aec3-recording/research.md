# Research: WebRTC AEC3 Recording

## Decision 1: Use WebRTC AEC3 from freedesktop v2.1

**Decision**: Pin `webrtc-audio-processing` tag `v2.1`, commit
`846fe90a289f58b7c9303a635142aa2c7caa93e5` (WebRTC M131).

**Rationale**: This is the latest stable freedesktop release as of 2026-08-20.
Its AEC3 is the same open algorithm family exposed by MacWhisper's closed
RecordKit framework. The seven later `master` commits are build/platform
maintenance and do not update AEC3. A pinned release gives reviewable source,
license and reproducible dependency identity.

**Alternatives considered**:

- RecordKit/MacWhisper binaries: rejected because the implementation is closed
  and commercial; copying code or binaries would violate clean-room and license
  boundaries.
- Floating freedesktop `master`: rejected because it adds drift without an AEC3
  benefit.
- Apple Voice Processing I/O: previous Features 038/039 did not prove it for
  GRAF's ScreenCaptureKit + app-owned microphone topology.
- Suppression gates, ANC, text deduplication: rejected because they remove or
  infer speech rather than cancel the known render reference.

## Decision 2: Static XCFramework with a narrow C ABI

**Decision**: Build WAP and pinned Abseil statically for arm64 and x86_64, merge
the archive, and check in `GrafAEC3.xcframework`. Swift imports only fixed-width
C functions and an opaque processor handle.

**Rationale**: A two-architecture prototype built and linked successfully. The
smoke executable loaded CoreFoundation, libc++, libSystem and Swift runtimes but
no WebRTC/Abseil dylib. Static linking preserves the current single-component
signing/notarization model and requires no Homebrew installation at runtime.
The C ABI prevents Swift from depending on unstable WebRTC C++ headers.

**Alternatives considered**:

- Runtime dylib/framework: rejected because it adds nested signing, rpath and
  library-validation risk with no product value.
- Build WAP during every app build: rejected because it adds network and host
  toolchain variability to ordinary Swift builds.
- Reimplement AEC3: rejected as unnecessary and unsafe.

## Decision 3: Reproducible dependency build

**Decision**: The vendor build verifies the exact WAP commit, forces the pinned
Meson wrap for Abseil `20240722.0`, uses static libraries, disables LTO, builds
with a macOS 14.0 minimum, sets `ZERO_AR_DATE=1`, and records tool versions and
artifact hashes.

**Rationale**: Upstream otherwise prefers host pkg-config Abseil, which creates
Homebrew/version/architecture drift. The Swift package declares macOS 14.0 even
though the shipped app currently targets 14.5, so the archive must use the
lower deployment target to avoid unsafe-link warnings.

**Alternatives considered**:

- Host Abseil: rejected because it is not a reproducible or redistributable
  input.
- Bit-for-bit identity across all Xcode releases: not promised; provenance and
  hashes are recorded per approved toolchain build.

## Decision 4: AEC-only configuration

**Decision**: Enable desktop echo cancellation and explicitly disable mobile
mode, AEC high-pass filtering, the general high-pass filter, noise suppression,
gain controllers 1 and 2, transient suppression, VAD and AecDump.

**Rationale**: The user requested echo removal without ANC or other signal
processing. `enforce_high_pass_filtering` defaults to true upstream, but it is
not required to satisfy the functional contract and would alter the microphone
beyond echo removal. Disabling it makes the boundary auditable: the only
enabled processor is desktop AEC3.

**Alternatives considered**:

- Keep AEC3's default enforced high-pass: technically defensible as an AEC
  support filter, but rejected because GRAF's requirement is stricter than the
  upstream default.

## Decision 5: Frame after canonical PTS alignment

**Decision**: `RecordingAudioTimeline` remains the sole alignment owner. It
downmixes/resamples both inputs to 48 kHz mono, emits paired 480-sample frames,
calls `ProcessReverseStream(system)` before `ProcessStream(microphone)`, then
uses cleaned microphone plus unchanged system in the current mix. At final
flush, a partial pair is zero-padded, processed, and trimmed to its original
sample count.

**Rationale**: This is the first existing point where both sources are in the
same rate, channel layout and PTS domain. Callback sizes and callback arrival
times are irrelevant once the timeline produces exact aligned frames. Reusing
it avoids a second queue, clock mapper or audio graph.

**Alternatives considered**:

- Process inside native callbacks: rejected because mic/system callbacks have
  different sizes, queues and delivery jitter.
- Add an independent rechunker after mixing: rejected because the microphone
  must be cleaned before mixing and a second timeline owner can drift.

## Decision 6: Delay and clock policy

**Decision**: Set APM stream delay to `0 ms` for the current PTS-aligned path.
Do not feed a correlation-derived acoustic lag into that field. AEC3 estimates
the acoustic echo-path delay internally; the host continues to own PTS,
ordering, gaps, route identity and bounded queues.

**Rationale**: `set_stream_delay_ms` describes known host/HAL buffering between
render/capture delivery and physical devices, not the room echo lag. GRAF does
not currently have a trustworthy HAL delay measurement. Supplying invented
values is worse than the documented zero baseline.

**Alternatives considered**:

- Estimate the value from cross-correlation: rejected because that duplicates
  and misinforms AEC3's internal delay estimator.
- Adaptive host-side delay controller: deferred until a measured HAL signal is
  available and the zero baseline fails controlled hardware tests.

## Decision 7: Fail closed and preserve only a cleaned prefix

**Decision**: Processor creation/configuration failure blocks recording start.
After start, missing reference, process error, route change, source loss,
unbounded gap, overflow or invalid samples produces an explicit degraded
outcome. The writer may finalize only frames already returned successfully by
AEC3; it must not re-drain queued input through the existing salvage path.

**Rationale**: A raw-microphone fallback recreates the exact double-voice defect
while presenting the package as normal. Retaining a proven cleaned prefix is
truthful and preserves user data without weakening the boundary.

**Alternatives considered**:

- Continue with raw mic: rejected by FR-005.
- Hidden reset and resume on the same route generation: rejected for the first
  release because route/reference truth is not currently observable enough.
- Delete the whole partial recording: rejected because a bounded, clearly
  degraded cleaned prefix is recoverable and remains stoppable.

## Decision 8: Route and discontinuity policy

**Decision**: Native mic and system producers must publish real monotonic route
generations and terminal capture failures. Route generation change,
format/timebase change, backward PTS, missing reference and queue loss end the
trusted AEC segment. The existing privacy Pause continues feeding the valid
system reference and PTS-aligned zeroed microphone through the same processor;
Resume restores microphone samples without a raw bypass. The first version
finalizes the cleaned prefix as degraded for actual capture/reference
discontinuities instead of attempting transparent continuation.

**Rationale**: Current producers always emit generation `0`, ScreenCaptureKit
does not surface `didStopWithError`, and microphone disconnect/runtime errors
are not propagated. AEC3 cannot repair a reference from the wrong device or
invent samples. Privacy Pause is not a source discontinuity—the current wrapper
preserves timestamps and emits deliberate zero microphone samples—so degrading
every paused recording would contradict the protected Pause/Resume product
contract. A visible degraded stop remains smaller and safer for real route or
source discontinuities.

**Alternatives considered**:

- Automatic in-place reset: deferred until route generation and synchronized
  restart can be proven without cross-route blocks.

## Decision 9: Optional health metadata, no AecDump

**Decision**: Add a backward-compatible optional echo-processing descriptor to
the v5 manifest. It records dependency identity, state/reason, processed/error
counts, host gap/overflow/saturation/reset counters, stream delay and bounded
AEC3 statistics (delay, ERL, ERLE). Never enable AecDump or persist raw frames.

**Rationale**: Public APM statistics expose delay, echo return loss and echo
return loss enhancement. Drift, gaps, overflow and saturation must be counted
by the host. These values are sufficient to explain integrity without storing
private audio.

**Alternatives considered**:

- New manifest schema: rejected because optional fields decode safely in the
  existing v5 model.
- Raw debug audio or WebRTC dumps: prohibited because they can contain meeting
  audio.

## Decision 10: License and release surface

**Decision**: Bundle a consolidated notice containing WAP/WebRTC BSD licenses,
PATENTS, Abseil Apache-2.0 and notices for statically included third-party DSP
objects. Extend the current third-party notice and installer validators.

**Rationale**: Static linkage removes runtime components but not attribution
obligations. The final app remains subject to the repository's existing
Developer ID, notarization, stapling, Gatekeeper and Sparkle checks.

**Alternatives considered**:

- Mention only WAP: rejected because the static archive includes Abseil and
  bundled DSP objects even when some processing features are disabled at
  runtime.
