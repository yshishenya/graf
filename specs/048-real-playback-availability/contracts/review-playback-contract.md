# Contract: Review Playback

## Review Playback Availability

Meeting detail review includes a `playback` object.

Rules:

- Owner review playback is available for ready or partial meetings with both
  retained microphone and incoming/system audio, even when artifact download
  policy is disabled.
- `available=true` requires a server-owned relative `playback_path`.
- `available=false` requires a safe `unavailable_reason` and no playback path.
- `source_mode=combined_review_stream` means both required sources are
  represented.
- `source_mode=none` means no playable review stream is exposed.
- Review playback availability must not change "Download audio" or export
  artifact states.

## Playback Route

Route:

```text
GET /api/v1/cabinet/meetings/{meeting_id}/playback
Range: bytes=<start>-<end>
```

Available full response:

- status: `200`
- media type: audio review stream media type
- headers:
  - `Accept-Ranges: bytes`
  - `Content-Length`
  - `Content-Disposition: inline; filename="meeting-review.wav"`

Available range response:

- status: `206`
- media type: audio review stream media type
- headers:
  - `Accept-Ranges: bytes`
  - `Content-Range: bytes <start>-<end>/<total>`
  - `Content-Length: <range-length>`
  - `Content-Disposition: inline; filename="meeting-review.wav"`

Denied responses:

- unauthorized or foreign meeting: same no-existence-proof behavior as existing
  cabinet detail access;
- deleted/deleting: safe meeting deletion response;
- processing/failed/not imported: safe playback unavailable response;
- missing one retained source: safe playback unavailable response;
- storage unavailable or unsafe review stream: safe unavailable/retryable
  response.

Forbidden route behavior:

- no signed URLs;
- no object keys;
- no private local paths;
- no transcript text in playback route responses;
- no raw provider payloads;
- no client-side MediaScribe access.

## Web And Embedded Review UI

Available state must render:

- persistent bottom player area;
- hidden or visually integrated browser audio element using the server-owned
  playback route;
- play/pause control;
- skip backward and skip forward controls;
- current time and duration;
- speed control;
- transcript timestamps that seek the player;
- speaker timeline lanes when diarization is available.

Unavailable state must render:

- persistent bottom unavailable area;
- safe reason copy;
- duration if known;
- no playable audio element;
- transcript remains readable.

Responsive rules:

- desktop web, mobile-width web, and macOS embedded review must have no
  horizontal overflow;
- the bottom player must not cover the final transcript rows;
- keyboard activation must work for timestamp and player controls.

## Evidence Contract

Allowed evidence:

- `playback_available`;
- `unavailable_reason`;
- safe response status and header names;
- `source_mode`;
- viewport class;
- safe synthetic segment sequence;
- observed seek seconds;
- pass/fail counts.

Forbidden evidence:

- raw audio;
- transcript text from private meetings;
- private meeting titles;
- signed URLs;
- object keys;
- local paths;
- credentials;
- account identifiers.
