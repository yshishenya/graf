# Data Model And State Invariants

## Capture

- `MacOSMeetingActivityDetector` tracks one `TrackedAudioOwnership` per bundle:
  first observation, latest event, inactive time and stable count.
- A tracked bundle may emit one eligible start output until it becomes inactive
  for the existing grace period; it then emits one `.ended` and is removed.
- `MeetingDetectionRecordingTarget` carries target/bundle identity, start reason,
  policy and acknowledgement evidence. Automatic reasons require active matching
  policy/ack; `prompt_button` records explicit user confirmation.
- `CaptureSession` remains the lifecycle source of truth. `stopManualRecording`
  transitions active/starting sessions through the existing stop/finalize path and
  ignores duplicate requests while a stop is in progress.

## Email auth

- `AuthCallbackState` is one-time, provider-bound, workspace-bound and stores a
  hashed normalized email/code plus expiry and requested safe redirect.
- Verification may issue exactly one authenticated session and sets the cookie
  selected from the request origin.
- Production cookie: `__Host-twobrain_rec_owner_session`, Secure, HttpOnly,
  SameSite=Lax. Local explicit loopback HTTP cookie:
  `graf_dev_owner_session`, non-Secure, HttpOnly, SameSite=Lax.
- Cookie values are transferred through the existing WebKit cookie store and
  native `HTTPCookieStorage`; no document JavaScript or bypass header is added.
