# Contract: installer and permission onboarding

## Installer contract

- The staged app has bundle identifier `pro.2brain.graf`, executable `GRAF`,
  and bundle name `GRAF.app`.
- The app metadata contains both `NSMicrophoneUsageDescription` and
  `NSAudioCaptureUsageDescription`/screen-capture explanation required by the
  capture path.
- `codesign --verify --deep --strict` is run before the package is assembled.
- The no-account package may be unsigned at the product-package layer. User
  documentation must describe the single Finder/System Settings Gatekeeper
  confirmation and must not instruct users to disable Gatekeeper globally.
- No installer path installs a driver, changes TCC, or requires a privileged
  audio component.

## Permission contract

- `unknown` microphone state: the primary action calls
  `AVCaptureDevice.requestAccess(for: .audio)`.
- The shared microphone service re-reads its current state before requesting and
  does not call the platform request API for `denied` or `restricted`.
- `denied` microphone state: the primary recovery action opens
  `Privacy_Microphone`; it does not call `requestAccess` again as if a prompt
  were guaranteed.
- `restricted` microphone state: the UI says that a device policy blocks access
  and links to the same settings/policy surface without promising a bypass.
- Screen/System Audio uses its own settings URL and status; it is never inferred
  from microphone state.
- If the Core Graphics preflight is negative or potentially stale, including a
  granted value after a system-audio runtime failure, GRAF verifies the same
  ScreenCaptureKit shareable-content path without starting capture. A successful
  functional probe is sufficient for the current process; a failed probe keeps
  recording blocked and marks the previously granted state stale. It does not
  trigger TCC reset or database edits.
- The normal Screen/System Audio request path MUST run that functional probe
  even when `CGRequestScreenCaptureAccess()` returns `true`; the Core Graphics
  boolean alone is not accepted as a fresh grant.
- A “ready” state is shown only after a fresh read reports both permissions as
  granted.
