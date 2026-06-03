# Research: Recording Artifact Format

## Decision: Use Two Separate WAV Track Files

**Decision**: New local recording packages use two files: `mic.wav` and
`incoming.wav`, rather than one mixed file or one multi-channel file.

**Rationale**: The MediaScribe dual-track endpoint expects `mic_file` and
`incoming_file`. Separate files avoid role ambiguity, preserve the local
speaker as `MIC`, and let MediaScribe diarize only the incoming remote speaker
mix. A single mixed file would lose the product's local/remote separation and
would require weaker diarization later.

**Alternatives considered**:

- **Single mixed mono file**: Smaller and simpler, but loses local/remote role
  separation and contradicts the dual-track contract.
- **Single stereo file with channel mapping**: Convenient as one artifact, but
  Whisper-style tooling may downmix channels and MediaScribe's current
  contract expects two multipart files.
- **Compressed files (`m4a`/`opus`)**: Smaller, but MediaScribe's current
  preferred contract is WAV PCM 16k mono to avoid extra conversion.

## Decision: WAV PCM Signed 16-bit Little-Endian, Mono, 16000 Hz

**Decision**: Each track file must be WAV, `pcm_s16le`, mono, 16000 Hz.

**Rationale**: This matches the MediaScribe integration contract and minimizes
server-side conversion before transcription/diarization. Although WAV is larger
than compressed speech codecs, this format is predictable, easy to validate,
and preserves quality for STT.

**Alternatives considered**:

- **Current 48k stereo LPCM/float files**: Already exists but creates larger and
  less directly usable files; MediaScribe would need conversion and channel
  normalization.
- **AAC/M4A**: Better size and macOS compatibility, but adds lossy encoding and
  does not match the preferred MediaScribe path.
- **Opus/WebM**: Excellent size for speech, but less aligned with the current
  MediaScribe contract and some desktop transcription workflows.

## Decision: Preserve Silence And Shared `t=0`

**Decision**: Local writer must not remove silence before persistence. Both
tracks should represent the same session timeline; late-starting sources are
padded with silence or marked degraded if alignment cannot be represented.

**Rationale**: MediaScribe result timestamps are only useful if both source
tracks share a truthful timeline. VAD trimming before submission would shift
segments and break transcript, diarization, and playback alignment.

**Alternatives considered**:

- **Trim silence for smaller files**: Saves storage but breaks timestamp truth.
- **Store per-track offset only**: Possible, but the MediaScribe endpoint takes
  files, not a timeline manifest, so silence padding is safer for MVP.

## Decision: Treat Old Local Recording Manifests As Legacy

**Decision**: Existing `local-recording-manifest.v1` artifacts remain local
recording evidence but are not automatically accepted as MediaScribe-ready.
New artifacts should use updated readiness metadata.

**Rationale**: Feature `008` validated local persistence, not transcription
readiness. Silently upgrading acceptance would hide format and timeline risks.

**Alternatives considered**:

- **Backfill/migrate old files**: Useful later, but unnecessary before upload
  and potentially expensive or lossy.
- **Break old manifest reads**: Avoids ambiguity but harms diagnostics and QA
  history.

## Decision: Keep Desktop Completely Offline For MediaScribe

**Decision**: The macOS app must not read `.env`, `MEDIASCRIBE_API_KEY`, or call
MediaScribe in this feature.

**Rationale**: The constitution requires desktop clients to never store or send
MediaScribe credentials. This slice prepares local artifacts only; backend
upload/ingest and server-side MediaScribe submission are separate.

**Alternatives considered**:

- **Developer-only direct MediaScribe test in app**: Faster manual validation,
  but violates the product boundary and risks credential leakage.
