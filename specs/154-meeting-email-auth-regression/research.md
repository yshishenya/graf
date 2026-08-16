# Research: Feature 154

## Findings

1. `MacOSMeetingActivityDetector` already emits prompt, saved-target and ended
   outputs and already owns debounce/end-grace state. The app's
   `meetingDetectionPrerequisites()` currently passes a prerequisite with
   `requiresAssistedAuthorization = true`, so the detector suppresses the first
   prompt when policy/acknowledgement is absent.
2. Feature 145 requires assisted authorization for timeout and saved-target
   starts, but also explicitly preserves manual start without acknowledgement.
   Therefore detector preflight must be capture-ready-only for prompt display;
   `currentMeetingDetectionStartDecision` and the start path must require policy
   only for automatic reasons. A prompt button is explicit user confirmation.
3. The existing prompt view already has an 8-second `MeetingDetectionCountdown`
   and cancellation task. Its late callback is safe only if the app's start
   decision re-check remains authoritative.
4. Target end already routes to `stopManualRecording` and the capture stop guard
   makes the operation idempotent. Tests must cover a second end while stop is
   in progress so a future refactor cannot remove this property.
5. Server email start/verify tests pass and use request-scoped
   `auth_session_cookie_name(request)`. In local HTTP mode that name is
   `graf_dev_owner_session`; the macOS bridge and upload token helper currently
   recognize only the production `__Host-` name. Cookie selection must be based
   on the actual loopback HTTP origin, not on a copied header or a second login
   protocol.

## Decisions

- Preserve Feature 145 fail-closed policy checks for automatic starts.
- Treat prompt button as user-confirmed capture, while preserving meeting target
  metadata and the existing visible capture route.
- Share one origin-aware cookie-name helper between WebKit sync and desktop
  requests; production remains `__Host-twobrain_rec_owner_session`, local
  loopback HTTP remains `graf_dev_owner_session`.
- Add behavioral tests at the smallest existing test seams; no new dependency.

## Deferred / Not Needed

- No server auth protocol change is needed because focused integration tests
  already pass.
- No real meeting audio, transcript, external email delivery, deployment or
  notarization is required for this regression slice.
