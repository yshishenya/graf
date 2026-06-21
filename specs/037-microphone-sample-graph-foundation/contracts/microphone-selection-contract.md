# Contract: Recording Microphone Selection

## Purpose

Define how the macOS app chooses the input for the app-owned microphone stream.

## Preconditions

- The user starts a local recording through the native Record action.
- Microphone permission is requested or already granted.
- The app can enumerate or resolve native input metadata.

## Accepted Path

1. If the user has selected a recording microphone, resolve that device by
   native identifier.
2. If no explicit selection exists, resolve the current macOS default input.
3. Classify the resolved input with existing physical/virtual/self-routing
   policy.
4. Reject unsupported selections before capture starts.
5. Store selected/default truth as metadata in the recording session and local
   package manifest.

## Success Response

- `selectionResult = accepted`
- `mode = userSelected` or `macOSDefaultFallback`
- `inputDeviceId` and `inputDisplayName` are present when the OS exposes them.
- `diagnosticSafe = true`

## Failure Responses

- Permission denied or restricted: block start with `permission_denied`.
- Selected device unavailable: block or fail closed with `device_unavailable`.
- Unsupported 2brain virtual/self-routing input: reject selection with a
  metadata-safe rejection reason.
- Input identity cannot be proven: fail closed or mark graph readiness
  `unproven`; do not silently claim the selected/default input was used.

## Forbidden

- Do not require selecting `2brain Rec Microphone` or `2brain Rec Speaker` in
  the meeting app.
- Do not change the global macOS default input as a side effect of choosing the
  recording input.
- Do not store raw audio, private paths, participant identifiers, credentials,
  tokens, signed URLs, or transcript text in selection metadata.
