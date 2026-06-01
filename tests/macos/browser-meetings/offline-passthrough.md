# Offline Passthrough Acceptance Scenario

## Scope

Validate that live mic/speaker passthrough remains usable during backend,
network, MediaScribe, or upload outages. This is a US2 acceptance scenario and
does not require audio to leave the desktop during the outage.

For the 005 pre-recording hardening slice, this file also records the
no-recording/no-upload policy boundary: short smoke evidence may state whether
local speech, remote audio, and no-loopback were observed, but it must not
create raw audio, recording snippets, transcript text, upload payloads, or
external egress.

## 005 No-Recording/No-Upload Policy Scan

- [ ] Short smoke evidence records selected input/output and user-observed audio
  usability only.
- [ ] Short smoke evidence records `recordingStarted: false`.
- [ ] Recording, transcription, upload, MediaScribe, Langfuse, and server
  workflows remain inactive during pre-recording hardening.
- [ ] Raw audio, audio snippets, transcript text, credentials, tokens, signed
  URLs, and meeting content are absent from evidence and diagnostics.
- [ ] Long-duration replay is not accepted from this checklist until local
  recording support exists.

## Preconditions

- US1 route verification passes.
- Capture can start manually with a visible local indicator.
- Local encrypted buffer policy is configured.
- The selected browser target is in the supported QA matrix.

## Scenario

- [ ] Join a supported browser meeting.
- [ ] Select `2brain Rec Microphone` and `2brain Rec Speaker` in the meeting.
- [ ] Start capture manually.
- [ ] Confirm local mic passthrough and physical speaker output are usable.
- [ ] Simulate network/backend outage for 5 minutes.
- [ ] Continue speaking and receiving remote audio during the outage.
- [ ] Confirm the driver/app reports degraded upload/backend state without
      reporting a false driver failure.
- [ ] Confirm local capture buffering continues or degrades truthfully before
      silent loss.
- [ ] Restore network/backend.
- [ ] Confirm passthrough never required the backend to recover.
- [ ] Stop capture using one local action.

## Pass Criteria

- Live call passthrough is not interrupted by the 5-minute outage.
- Local capture state is visible and never silently drops required tracks.
- Server/network failure is not mislabeled as driver failure.
- Buffered artifacts remain desktop-owned and diagnostics do not expose raw
  audio, transcript text, credentials, tokens, or signed URLs.
