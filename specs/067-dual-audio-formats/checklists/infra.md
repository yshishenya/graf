# Infra Checklist: Dual Audio Formats

**Purpose**: Validate requirement quality for storage, upload retry, fallback,
and operational gates.

## Upload And Storage

- [x] Requirements define optional playback upload separately from required WAV
  upload.
- [x] Requirements cover interrupted upload after required WAV tracks succeed
  but playback upload is pending or failed.
- [x] Requirements require stable meeting/media revision identity across retry.
- [x] Requirements require duplicate-prevention for meetings, media revisions,
  playback assets, and transcription submissions.

## Fallback And Failure States

- [x] Requirements cover missing stored playback object and safe WAV fallback.
- [x] Requirements cover storage unavailable, partial, failed, transcript-only,
  export-disabled, deleted, and policy-blocked states.
- [x] Requirements define user-safe lifecycle states instead of hidden media
  copies.

## Validation And Release

- [x] Requirements and plan name focused macOS and server tests for the feature.
- [x] Requirements and plan name `infra/scripts/ci-local.sh` as the repository
  closeout gate.
- [x] Release/deploy is scoped out of this turn and remains a separate gate.
