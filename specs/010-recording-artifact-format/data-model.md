# Data Model: Recording Artifact Format

## Recording Artifact Package

Represents one local saved manual recording.

Fields:

- `schemaVersion`: updated local recording manifest schema for artifact-format
  readiness.
- `sessionId`: generated capture session id.
- `directoryId`: safe generated directory id.
- `startedAt`, `stoppedAt`, `createdAt`: lifecycle timestamps.
- `status`: `saved`, `degraded`, or `failed`.
- `transcriptionReadiness`: `ready`, `degraded`, `failed`, or `legacy_not_ready`.
- `mediaScribeSourceMode`: `dual`.
- `externalEgressStarted`: always `false` in this slice.
- `transcriptionStarted`: always `false` in this slice.
- `diagnosticSafe`: `true` when metadata contains no forbidden content.
- `tracks`: exactly one mic track and one incoming track for a ready package.
- `failureReason`: concrete reason when not ready.

Validation rules:

- Ready package requires both required track roles.
- Ready package requires every track to be WAV `pcm_s16le`, mono, 16000 Hz.
- Ready package requires aligned timeline evidence.
- Ready package requires no upload/transcription egress.
- Manifest must not include live absolute user paths or full API keys.

## Artifact Track

Represents one role-specific audio file.

Fields:

- `trackId`: generated stable id within the package.
- `role`: `local_mic` or `remote_speaker`.
- `mediaScribeField`: `mic_file` for `local_mic`, `incoming_file` for
  `remote_speaker`.
- `status`: `saved`, `missing`, `degraded`, or `failed`.
- `fileName`: safe basename, `mic.wav` or `incoming.wav`.
- `format`: `wav-pcm-s16le`.
- `sampleRate`: `16000`.
- `channelCount`: `1`.
- `bitsPerSample`: `16`.
- `durationMs`: track duration.
- `byteCount`: file byte count.
- `frameCount`: audio frame count at 16000 Hz.
- `timelineStartMs`: `0` for ready tracks.
- `timelineAligned`: true when the track shares package `t=0`.
- `checksum`: integrity marker if available.
- `failureReason`: concrete reason when not saved/ready.

Validation rules:

- A saved track must have `byteCount > 44`, `frameCount > 0`, and
  `durationMs > 0`.
- A saved track must use the required format values.
- Required tracks must not be VAD-trimmed before persistence.
- If a source has no speech but was captured, silence still counts as timeline
  content; empty physical files remain degraded/missing.

## Transcription Readiness State

Package-level readiness for future backend MediaScribe submission.

States:

- `ready`: both tracks are present, aligned, and in the required format.
- `degraded`: package has enough local evidence but one or more requirements
  are incomplete; future backend must not submit without remediation.
- `failed`: package cannot be used as a recording artifact.
- `legacy_not_ready`: package predates the `010` artifact contract.

Transitions:

- `recording` -> `ready`: stop/finalization succeeds for both tracks.
- `recording` -> `degraded`: missing/empty/misaligned/unconverted track.
- `recording` -> `failed`: directory/write/finalization failure.
- `legacy` -> `legacy_not_ready`: old manifest loaded or inspected by tooling.

## Forbidden Metadata

The following must not appear in manifest, diagnostics, fixtures with live
values, or QA evidence:

- raw audio bytes;
- transcript text;
- meeting content;
- participant names inferred from content;
- credentials;
- tokens;
- signed URLs;
- passwords;
- API keys;
- full MediaScribe keys;
- live absolute user paths.
