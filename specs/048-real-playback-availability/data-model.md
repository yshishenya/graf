# Data Model: Real Playback Availability

## Review Playback Availability

Represents whether the current viewer may listen to meeting audio inside the
review page.

Fields:

- `available`: true only when the viewer can view the meeting, the meeting is
  ready or partial, retained microphone and incoming/system audio are present,
  and lifecycle state allows playback.
- `duration_seconds`: non-negative review audio duration.
- `unavailable_reason`: safe reason for unavailable playback.
- `playback_path`: server-owned relative route when `available` is true.
- `policy_label`: short Russian copy for available/unavailable state.
- `source_mode`: `combined_review_stream` when both required sources are
  represented; `none` when unavailable.
- `included_sources`: safe labels for sources represented by playback.

Validation rules:

- `playback_path` is present only when `available` is true.
- `playback_path` is a relative path under 2brain Rec, never a storage URL.
- `available` does not depend on `audio_download`.
- Download/export controls remain governed by artifact egress policy.

## Playback Range Response

Represents a server-mediated browser playback response.

Fields:

- `media_type`: audio media type.
- `body`: full body or range body.
- `status_code`: 200 for full response, 206 for satisfiable byte range, 416 for
  unsatisfiable range.
- `headers`: safe playback headers such as `Accept-Ranges`, `Content-Length`,
  `Content-Range`, and `Content-Disposition: inline`.

Validation rules:

- Range responses must not include object keys, signed URLs, local paths, or
  credentials.
- Denied responses must not leak whether a foreign/private meeting exists.
- Audit metadata records outcome and source mode only.

## Speaker Timeline Lane

Represents one diarized speaker row in the playback timeline.

Fields:

- `speaker_key`: stable safe key.
- `label`: user-facing speaker label.
- `talk_time_percent`: 0-100 summary share.
- `segments`: start/end time ranges for visible lane marks.
- `source_roles`: safe source roles represented by the speaker.

Validation rules:

- Segment start/end times are clamped to the meeting duration for rendering.
- Missing diarization shows a reserved/unavailable state, not empty broken UI.
- Speaker lanes must fit desktop, embedded desktop, and mobile widths.

## Playback Evidence

Metadata-only proof that 048 behavior was validated.

Allowed fields:

- command name and pass/fail result;
- route status code and safe response header names;
- playback available/unavailable boolean;
- unavailable reason;
- duration;
- viewport class;
- selected synthetic segment sequence;
- observed seek seconds.

Forbidden fields:

- raw audio;
- transcript text from private meetings;
- meeting title from private meetings;
- object key;
- signed URL;
- credentials or tokens;
- private local path;
- account identifier.
