# Data Model: Meeting Playback Timestamp Seek

## Playback Availability

Represents whether the current viewer can play retained meeting audio.

Fields:

- `available`: true only when retained audio exists, policy allows playback,
  the viewer may access it, and the meeting lifecycle allows it.
- `unavailable_reason`: one of `none`, `no_audio`, `policy_disabled`,
  `access_denied`, `processing`, `failed`, `deleted`, `deleting`,
  `audio_purged`, `transcript_only`, `review_audio_unavailable`, or
  `storage_unavailable`.
- `duration_seconds`: safe non-negative duration shown to the viewer.
- `playback_path`: server-owned playback path when available; absent otherwise.
- `speed_options`: allowed playback speeds for the review UI.
- `policy_label`: short user-facing policy label for the current playback
  state.
- `source_mode`: `combined_review_stream` when dual-track review audio
  represents both retained speech sources, `single_retained_track` only for
  legacy or single-source meetings, or `none` when playback is unavailable.

Validation rules:

- `playback_path` is present only when `available` is true.
- `playback_path` must be a server-owned route, not an object-storage URL.
- `duration_seconds` must never be negative.
- Dual-track meetings must not use `single_retained_track` as the full meeting
  review stream.
- Unavailable states must not expose object keys, signed URLs, provider
  identifiers, private local paths, or private meeting content.

## Review Audio Stream

Represents the server-mediated audio bytes used by the review player.

Fields:

- `source_mode`: `combined_review_stream` or `single_retained_track`.
- `included_sources`: safe source labels, such as `local_microphone` and
  `incoming_system`.
- `duration_seconds`: safe playback duration.
- `media_type`: safe response media type.

Validation rules:

- A normal dual-track meeting requires both `local_microphone` and
  `incoming_system` in the review stream.
- If the required source tracks cannot be safely combined or retrieved,
  playback availability becomes false with `review_audio_unavailable` or
  `storage_unavailable`.
- The review stream must not expose storage object keys, signed URLs, private
  paths, or provider identifiers.

## Transcript Seek Target

Represents a transcript segment that can move playback to a start time.

Fields:

- `segment_id`: existing transcript segment identifier.
- `sequence`: existing display order.
- `start_seconds`: non-negative seek position.
- `end_seconds`: segment end position when available.
- `timestamp_label`: user-facing timestamp label.
- `seekable`: true when playback is available and the timestamp is valid.
- `seek_seconds`: the playback time used when the target is activated.

Validation rules:

- `seekable` is false when playback is unavailable.
- `seek_seconds` is present only when the timestamp is valid and in range.
- malformed, missing, duplicated, or out-of-range timestamps must not break the
  review page.

## Playback Policy State

Represents policy and lifecycle inputs that determine playback availability.

Inputs:

- viewer access decision;
- artifact audio policy;
- stored audio artifact presence;
- meeting deletion state;
- processing/review status;
- transcript-only or audio-purged lifecycle state;
- storage availability.

State transitions:

```text
processing/failed/no_audio/policy_disabled/access_denied/deleted/deleting/audio_purged/transcript_only/review_audio_unavailable
  -> available only after retained audio exists, policy allows playback, viewer is authorized, and lifecycle state permits playback

available
  -> unavailable immediately when access, deletion, retention, purge, or artifact policy changes
```

## Playback Evidence

Metadata-only release evidence for this feature.

Allowed fields:

- feature id;
- route class;
- availability state;
- unavailable reason;
- duration bucket or numeric duration;
- segment count;
- selected segment index;
- target seek seconds;
- observed current-time bucket;
- viewport class;
- pass/fail result.

Forbidden fields:

- raw audio;
- transcript text;
- object storage keys;
- signed URLs;
- credentials or tokens;
- private local paths;
- live account identifiers;
- private meeting titles or content.
