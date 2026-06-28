# Contract: Playback, Download, And Egress

## Review Playback Route

Route:

```text
GET /api/v1/cabinet/meetings/{meeting_id}/playback
```

Access:

- Uses existing cabinet meeting access checks.
- Playback may remain allowed when audio download/export policy is disabled.
- Foreign workspace, revoked access, deleting/deleted meeting, unavailable
  processing state, missing audio, and storage unavailable states fail closed.

Preferred success response when stored M4A exists:

```text
Status: 200 OK or 206 Partial Content
Content-Type: audio/mp4
Accept-Ranges: bytes
Content-Disposition: inline; filename="meeting-review.m4a"
```

Fallback success response when stored M4A is absent but both WAV sources exist:

```text
Status: 200 OK or 206 Partial Content
Content-Type: audio/wav
Accept-Ranges: bytes
Content-Disposition: inline; filename="meeting-review.wav"
```

Range requests:

- Valid `Range: bytes=start-end` returns `206` with `Content-Range`.
- Malformed or unsatisfiable ranges return a safe problem response and record a
  metadata-only denied playback event.

## Meeting Review State

`playback.source_mode` values:

- `stored_review_m4a`: stored M4A artifact will be used.
- `combined_review_stream`: server will synthesize WAV review audio from stored
  microphone and system WAV artifacts.
- `none`: no playable review audio is currently available.

The UI must receive a server route path only, never object-storage URLs, signed
URLs, object keys, or local file paths.

## Audio Download/Export

Audio download/export is separate from review playback.

When audio download/export is disabled:

- review playback may still succeed through the playback route;
- artifact download must fail closed according to existing policy.

When audio download/export is allowed:

- server returns the stored `meeting-review.m4a` when available;
- server may fall back to generated `meeting-review.wav` only when stored M4A is
  unavailable and both WAV sources are retained;
- response metadata and audit events must report source mode without exposing
  storage details.

## Audit And Diagnostics

Allowed metadata:

- artifact class;
- request class;
- source mode;
- byte length;
- outcome;
- policy reason.

Forbidden in logs, diagnostics, committed evidence, and audit metadata:

- raw audio bytes;
- transcript text;
- private meeting content;
- credentials or tokens;
- signed URLs;
- storage object keys;
- local file paths.
