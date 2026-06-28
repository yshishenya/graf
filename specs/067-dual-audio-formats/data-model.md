# Data Model: Dual Audio Formats

## Source Recording Package

Local package created by the macOS recorder.

Fields:

- `directory_id`: local package identity.
- `session_id`: recording session identity.
- `manifest.json`: local custody manifest.
- `mic.wav`: required transcription microphone source.
- `incoming.wav`: required transcription incoming/system source.
- `meeting-review.m4a`: optional playback/distribution derivative.
- `started_at`, `stopped_at`, `duration_seconds`: timeline truth.
- `privacy_segments`, `retention_decision`, `transcription_readiness`: existing
  metadata-only lifecycle fields.

Rules:

- `mic.wav` and `incoming.wav` are required for normal transcription upload.
- `meeting-review.m4a` is optional and must not mutate or replace either WAV.
- Invalid playback derivative is ignored and may be removed locally without
  blocking WAV upload.

## Transcription WAV Pair

Two aligned source-role files used by the server-owned MediaScribe path.

Fields:

- `microphone_path`: local `mic.wav`.
- `system_audio_path`: local `incoming.wav`.
- `codec`: `wav-pcm-s16le`.
- `sample_rate_hz`: `16000`.
- `channel_count`: `1`.
- `duration_seconds`, `byte_count`, `sha256`.
- `transport_role`: `microphone` or `system`.

Rules:

- Must remain separate by role.
- Must preserve timeline silence/padding.
- Must remain the normal transcription input.

## Playback/Distribution Audio Asset

Optional compressed review artifact.

Fields:

- `file_name`: `meeting-review.m4a`.
- `transport_role`: `playback`.
- `codec`: `m4a-aac-lc`.
- `container`: M4A/MP4.
- `mime_type`: `audio/mp4`.
- `sample_rate_hz`: `48000`.
- `channel_count`: `1`.
- `bitrate_target_bps`: `64000`.
- `duration_seconds`, `byte_count`, `sha256`.
- `source_roles`: `local_microphone`, `incoming_system`.
- `source_mode`: `stored_review_m4a`.
- `state`: `not_applicable`, `pending`, `available`, `degraded`, `failed`,
  `blocked`, or `purged`.

Rules:

- Must be derived from accepted local capture sources.
- Must be validated before upload.
- Must not become the normal MediaScribe input.
- May be reused for allowed audio download/export, but only after export policy
  allows it.

## Upload Track Completeness

Desktop-side local description of uploadable artifacts.

Fields:

- `transport_role`: `microphone`, `system`, `manifest`, optional `playback`.
- `file_name`, `present`, `byte_count`, `sha256`, `duration_seconds`.
- `uploadable`: derived from presence and positive byte count, plus role-specific
  validation.

Rules:

- Required upload roles are `microphone`, `system`, and `manifest`.
- `playback` is included only when `meeting-review.m4a` passes validation.
- Active server upload session truth is preserved when local optional playback
  appears later; retry/finalize descriptors are filtered to the session's
  expected roles.

## Server Track Artifact

Persisted artifact row for uploaded track content.

Fields:

- `workspace_id`, `meeting_id`, `media_revision_id`.
- `track_role`: includes `playback` in addition to transcription roles.
- `storage_object_key`.
- `status`: stored/deleted lifecycle state.
- `duration_seconds`, `byte_length`, checksum metadata.

Rules:

- `playback` artifacts are content-bearing and must follow the same access,
  retention, deletion, audit, and diagnostics safety rules as audio WAV tracks.
- Missing object reads must fail closed or fall back to reconstructible WAV
  review playback when both WAV sources are available.

## Review Playback State

Server-owned response model for cabinet review playback.

Fields:

- `available`: whether playback route may be used.
- `playback_path`: server route, not storage URL.
- `source_mode`: `stored_review_m4a`, `combined_review_stream`, or `none`.
- `duration_seconds`.
- `policy_label`, `unavailable_reason`.

Rules:

- Playback route may be available even when audio download/export is disabled.
- Access revoked, deleting/deleted meetings, missing audio, or retention purge
  fail closed.

## Audit And Lifecycle Records

Metadata-only records for playback/download requests and denied attempts.

Fields:

- `event_type`: playback/download requested, completed, or denied.
- `artifact_class`: `audio`.
- `source_mode`: `stored_review_m4a` or fallback mode when relevant.
- `policy_reason`, `outcome`, `byte_length`.

Rules:

- Do not record raw audio bytes, transcript text, signed URLs, object keys, local
  paths, credentials, or private meeting content.
- Deletion reports must account for playback artifacts separately from
  transcription WAVs when present.
