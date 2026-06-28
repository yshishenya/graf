# Security And Privacy Checklist: Dual Audio Formats

**Purpose**: Validate requirement quality for access control, egress,
diagnostics, retention, and deletion.

## Access And Egress

- [x] Requirements keep playback route access server-owned and authorized.
- [x] Requirements state that playback availability does not automatically allow
  audio download/export.
- [x] Requirements make revoked access, deletion, retention purge, and missing
  audio fail closed.
- [x] Requirements prohibit exposing object-storage URLs, signed URLs, object
  keys, and local paths.

## External Dependencies And Secrets

- [x] Requirements preserve the server-owned MediaScribe boundary.
- [x] Requirements state that desktop clients never store MediaScribe
  credentials or send audio directly to MediaScribe.
- [x] Requirements introduce no new external codec/transcoding dependency for
  the MVP slice.

## Diagnostics And Evidence

- [x] Requirements prohibit raw audio, transcript text, credentials, tokens,
  signed URLs, object keys, private paths, and private meeting content in
  diagnostics, logs, screenshots, and committed evidence.
- [x] Requirements require metadata-only audit and support evidence for playback
  and download events.

## Retention And Deletion

- [x] Requirements account for source, transcription, playback, distribution,
  temporary, and purged artifact states.
- [x] Requirements avoid universal deletion claims outside 2brain Rec control.
