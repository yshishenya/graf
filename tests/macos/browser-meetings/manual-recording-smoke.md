# Manual Recording Smoke Matrix

Feature: `007-capture-session-indicator`

## Scope

This matrix records metadata-only manual recording smoke evidence. It is not
long-duration recording acceptance and does not validate upload, MediaScribe,
Langfuse, dashboard notes, retention, or deletion.

## Required Setup

- `2brain Rec Microphone` selected as the meeting microphone.
- `2brain Rec Speaker` selected as the meeting speaker.
- Low-resource non-recording passthrough route is valid.
- User presses Record manually.
- Active recording has a visible local indicator and one-action Stop.
- User presses Stop manually.

## Target Matrix

| Target | Current 007 Status | Required Evidence |
|---|---|---|
| Yandex Telemost | Manual smoke pending | Manual start, visible indicator, one-action stop, no upload/transcription/external egress |
| Chrome | Manual smoke pending | Manual start, visible indicator, one-action stop, no upload/transcription/external egress |
| Opera | Manual smoke pending | Manual start, visible indicator, one-action stop, no upload/transcription/external egress |
| Zoom | Manual smoke pending | Manual start, visible indicator, one-action stop, no upload/transcription/external egress |
| Yandex Browser | Not accepted in current cycle | Run only if explicitly added back to smoke scope |

## Evidence Fields

- target name and version if available;
- selected microphone and speaker;
- route state before Record;
- recording start result;
- visible indicator surface;
- stop action availability;
- stop result and elapsed time;
- no upload/transcription/MediaScribe/Langfuse/dashboard activity;
- pass, blocked, or not accepted status;
- concrete blocked/not accepted reason.

Evidence must remain metadata-only and must not include raw audio, transcript
text, meeting content, credentials, tokens, signed URLs, passwords, or live
secret paths.
