# UX Checklist: Local Recording Persistence

**Purpose**: Validate visible user control and truthfulness of the local
recording experience before implementation.

- [x] User can discover the recording location from the app after `Stop`.
- [x] UI must not show complete/saved acceptance for missing or failed required
  tracks.
- [x] UI must preserve visible active recording indicator and one-action stop.
- [x] UI must distinguish saved, degraded, failed, and blocked local recording
  outcomes.
- [x] UI must avoid retention, deletion, upload, transcription, and dashboard
  claims in this slice.
- [x] UI copy must answer "where is the recording?" without requiring logs or
  developer tools.
- [x] Manual smoke requires opening the local artifact location and inspecting
  manifest/track presence.
- [x] Accessibility remains covered by visible status and stop control inherited
  from feature `007`.

## Notes

- No UX requirement gaps before task generation.
