# Research: единый аудиопоток v5

## Evidence Reviewed

- Current `origin/master` capture and upload implementation, including its local tests, contract validator and server processing path.
- The completed but unmerged feature-103 capture worktree as a read-only reference; it is not an implementation baseline and is not merged here.
- The existing GRAF single-track MediaScribe client and playback normalization lifecycle.
- The companion MediaScribe source tree's public single-WAV contract, without inspecting or copying its uncommitted echo-classifier work.
- Apple public documentation for `SCStreamOutput`, `AVAudioFile` and `AVAudioConverter`, plus OpenAI Whisper's public audio loader. Links are listed under the decisions they support.

## Existing Failure Analysis

### Finding: current audio is aligned by availability, not time

The active macOS path receives two independent sample sources, strips their `CMSampleBuffer` presentation timestamps, polls them every 50 ms and mixes whatever counts are currently available. System capture starts before the microphone and stops before it. The M4A writer then pads and drains based on array lengths and wall-clock time.

This cannot establish a common epoch, preserve the location of a gap, or bound long-run drift. It explains the observed desynchronization. A 1–3 second duration tolerance only hides this defect; it does not prove synchronized conversation time.

### Finding: dual transcription magnifies acoustic leakage into duplicate text

The old package uploads separate `mic.wav` and `incoming.wav`, calls a dual MediaScribe endpoint and merges two independent ASR/diarization results. If a speaker's audio is acoustically present in the microphone, the same speech can appear in both recognition streams and merge as duplicate/mis-attributed text. The user's controlled comparison found the combined recording materially more coherent than the separate-track result.

The new design removes the second ASR source. It does not make an unproven claim that physical speaker leakage is magically absent: no AEC is used and the v5 validation gate tests the actual transcript outcome on a controlled recording.

### Finding: legacy leakage/AEC gates actively conflict with the chosen path

`LeakageFinalizationService` reads both old WAVs and can block package eligibility. Apple voice-processing and WebRTC evaluation surfaces also remain in the current tree. They are incompatible with a one-WAV v5 package and have previously changed audible incoming playback volume. They must be removed from the active v5 capture/eligibility path, not retained as a hidden fallback.

### Finding: the server has a usable single-track seam with two missing guards

GRAF already has `submit_single_track`, but a first-party mixed recording needs its own immutable source kind instead of pretending to be a manual upload. The current role-set validator does not combine roles with source kind, which could accept an impossible package and only fail later in processing. The single-track staging path also needs an explicit internal-codec → HTTP content type mapping so `wav-pcm-s16le` is actually sent as a `.wav` with `audio/wav`.

## Decisions

### Decision: canonical input is a one-timeline PCM mix, not a post-hoc AAC decode

**Chosen**: Mix aligned 48 kHz mono PCM once during capture and fan it out to a 16 kHz PCM WAV and 48 kHz AAC M4A. The WAV is submitted directly.

**Why**: It preserves one source timeline, avoids lossy AAC → WAV decoding, eliminates dual source/ASR merge, and lets M4A remain optimized for listening. OpenAI Whisper's audio loader itself downmixes and resamples source content to mono PCM s16le at 16 kHz, so providing this format directly is an appropriate interoperable ASR contract.

**Rejected alternatives**:

- Send M4A to ASR: adds a second decoder/timing surface and violates the explicit WAV requirement.
- Capture two WAVs then mix after Stop: preserves the independent-clock defect and increases retained raw audio/deletion work.
- Keep two ASR jobs and improve merge/dedupe: cannot make source identity truthful and keeps the duplicate failure mode.
- Server-side mix: moves the highest-rate capture alignment out of the native client, adds storage/egress work and creates a second audio transformation.

**Sources**:

- [Whisper audio loader](https://github.com/openai/whisper/blob/main/whisper/audio.py) uses `pcm_s16le`, one channel and the 16 kHz sample rate.
- [Apple AVAudioConverter TN3136](https://developer.apple.com/documentation/technotes/tn3136-avaudioconverter-performing-sample-rate-conversions) describes correct sample-rate conversion use.

### Decision: timestamps and explicit gaps are required; sample counts are not a fallback

**Chosen**: Capture batch PTS, true input rate, duration and discontinuity in the callback. Normalize to a common 48 kHz timebase, write silence for a known gap, deterministically trim overlap, and fail integrity on unsafe overflow or unreconcilable timing.

**Why**: Equal sample counts cannot establish a common start time or preserve the placement of a dropout. The output frame index is the v5 source of timeline truth; both final artifacts derive from it.

**Rejected alternatives**:

- Current 50 ms polling/FIFO pairing: has no PTS relation.
- Independent stop-tail padding against wall clock: masks rather than resolves a source gap.
- Silent dropping at bounded queue capacity: destroys the only timing truth.
- A raw retained reference track for later repair: increases private media retention and still does not repair capture-time user result.

**Sources**:

- [Apple SCStreamOutput](https://developer.apple.com/documentation/screencapturekit/scstreamoutput) supplies `CMSampleBuffer` output suitable for timestamp-aware handling.
- [Apple AVAudioConverter](https://developer.apple.com/documentation/avfaudio/avaudioconverter) is the native conversion primitive used in the target client.

### Decision: no AEC/voice processing and no hidden transcript cleanup

**Chosen**: Remove AEC, Apple voice processing, WebRTC AEC, echo-cleanup, amplitude gates and hidden text de-duplication from the new path. Use one truthful capture/mix and one ASR job. Quality is proven against controlled real-result criteria rather than asserted by a processing label.

**Why**: The user explicitly rejected AEC after it changed audible incoming audio and failed to eliminate the observed issue. A second independent ASR is the structural cause of many duplicates; a reversible, visible future editing tool is separate scope and cannot substitute for sound capture quality.

**Rejected alternatives**:

- Apple/VoiceProcessingIO fallback: can influence other audio and creates a second capture graph.
- WebRTC AEC behind a flag: retains build/runtime/validation debt and violates the no-hidden-fallback decision.
- Offline AEC after Stop: creates another private representation and needs delay estimation; it is still a non-truthful audio rewrite.
- LLM or text dedupe: hides a recording defect and cannot safely preserve overlapping turns without an explicit product contract.

### Decision: v5 uses a new first-party source kind, plus existing playback lifecycle

**Chosen**: `initial_mixed_recording` owns `{manifest,media,playback}`; `media` alone is authoritative and `playback` remains a candidate for existing normalization/reuse. Source kind and role/descriptors are validated together at session creation and finalization.

**Why**: Reusing `manual_upload` would lie about provenance and calendar flow. Existing immutable revision/fingerprint fields already encode the needed identity, and existing playback normalization/deletion already owns M4A.

**Rejected alternatives**:

- Database package-version column: duplicates immutable manifest/source-kind truth and requires a migration without solving a user need.
- New playback worker/table: duplicates a proven lifecycle.
- Role-set-only acceptance: can make an accepted v5-like package unprocessable under an old source kind.

### Decision: rollback is a release boundary, not a live user setting

**Chosen**: Record a known-good pre-v5 release/commit before canary. Deploy additive server reading support first; rollback only future capture by returning to that desktop baseline. Keep server v5 readers while v5 data exists.

**Why**: A live feature flag or quiet dual fallback would keep two active recorders and make a recording's real source ambiguous. Accepted data must not be silently reprocessed or rewritten.

**Rejected alternatives**:

- Per-user audio mode setting: exposes internal quality machinery and doubles test surface.
- Automatic dual fallback after a v5 error: creates unannounced extra audio, ASR and external jobs.
- Server rollback below a v5 reader: makes accepted records unreadable.

## Research Outcome

All material implementation choices are resolved. The only runtime fact that cannot be established by static research is real device timestamp comparability and route/volume behavior; the quickstart makes those installed-app gates mandatory before feature closeout.
