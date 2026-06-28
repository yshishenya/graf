# Contract: Audio Artifacts And Upload

## Local Recording Package

Required files after accepted stop:

```text
manifest.json
mic.wav
incoming.wav
```

Optional file:

```text
meeting-review.m4a
```

`meeting-review.m4a` contract:

- Container: MP4/M4A.
- Codec: AAC-LC.
- MIME type after server egress: `audio/mp4`.
- Sample rate: 48 kHz.
- Channels: mono.
- Target bitrate: 64 kbps.
- Source roles: microphone plus incoming/system audio.
- Purpose: playback and approved distribution only.

## Desktop Validation

The desktop upload scanner may include `meeting-review.m4a` only when all are
true:

- file exists and has positive byte count;
- AVFoundation can open it as an audio file;
- `AVFormatIDKey` is `kAudioFormatMPEG4AAC`;
- sample rate is 48 kHz;
- channel count is 1;
- frame length is greater than zero.

If validation fails, the scanner must ignore the optional playback file and keep
the package uploadable when the required WAV pair and manifest are valid.

## Upload Session

Default expected roles:

```json
["microphone", "system", "manifest"]
```

Expected roles when validated playback M4A exists:

```json
["microphone", "system", "manifest", "playback"]
```

`expected_track_sizes` must include exactly the roles expected by the upload
session. If local playback appears after a session already exists, the desktop
queue preserves that server session truth and filters retry/finalize descriptors
to the session's expected roles.

## Upload File Descriptor

Playback descriptor:

```json
{
  "transportRole": "playback",
  "fileName": "meeting-review.m4a",
  "codec": "m4a-aac-lc",
  "sampleRateHz": 48000,
  "channelCount": 1
}
```

The playback descriptor is optional and must not change required descriptor
order for `microphone`, `system`, and `manifest`.

## Server Artifact Role

Server ingest accepts `track_role=playback` as an uploaded track role. A stored
playback artifact is a content-bearing audio artifact and inherits normal access,
retention, deletion, and audit requirements.

MediaScribe submission remains restricted to the accepted microphone and system
WAV artifacts. The `playback` artifact must not be submitted as the normal
dual-track transcription input.
