# Audio Capture Checklist: Dual Audio Formats

**Purpose**: Validate requirement quality for capture, local recording truth,
and audio artifact integrity.

## Capture And Track Truth

- [x] Requirements preserve separate microphone and incoming/system WAV files for
  transcription.
- [x] Requirements state that playback/distribution audio must not replace the
  MediaScribe dual-track input.
- [x] Requirements describe how timeline silence, padding, duration, and source
  role truth remain authoritative.
- [x] Requirements cover the case where playback generation fails but
  transcription remains valid.

## Playback Derivative

- [x] Requirements define one logical playback/distribution asset and its
  relation to the same meeting/media revision.
- [x] Requirements distinguish true source-fidelity improvement from size/seek
  improvement when only 16 kHz WAV sources are available.
- [x] Requirements cover invalid, missing, partial, and wrong-container playback
  files.
- [x] Requirements define compatibility expectations for web and embedded macOS
  review.

## Quality And Performance

- [x] Requirements include measurable size reduction, seek, playback startup,
  and listening-comfort criteria.
- [x] Requirements avoid promising noise suppression, echo cancellation, or
  quality that was not captured.
- [x] Requirements require validation before claiming any bitrate/quality tier
  change beyond the MVP default.

## Evidence Safety

- [x] Requirements keep audio QA evidence metadata-only unless a future approved
  spec explicitly allows content-bearing evidence.
