# Contract: WAV Track Format

## Purpose

Define the track-level audio format for new local recordings.

## Required WAV Properties

Each required track file must be:

- Container: WAV / RIFF
- Audio format: PCM signed 16-bit little-endian
- Channels: mono / 1 channel
- Sample rate: 16000 Hz
- Bits per sample: 16
- File role:
  - `mic.wav`: local microphone track
  - `incoming.wav`: incoming/remote speaker mix track

## Timeline Rules

- Both tracks share session `t=0`.
- Silence must be preserved.
- VAD trimming before persistence is forbidden.
- If one source begins later, the corresponding file must contain silence or
  the package must be marked degraded with an alignment failure reason.
- Ready tracks should have aligned duration within the tolerance defined during
  implementation validation.

## Validation Rules

Validation must inspect file headers, not only file extensions.

Minimum checks:

- RIFF/WAVE header exists.
- Format code is PCM, not float.
- Channel count is `1`.
- Sample rate is `16000`.
- Bits per sample is `16`.
- Data chunk is non-empty for saved tracks.
- Manifest metadata matches file header metadata.
