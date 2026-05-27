# Contract: macOS Audio Driver QA Acceptance

## Supported MVP Matrix

Operating systems:

- macOS 14.5 on Apple Silicon
- latest stable macOS at release-candidate time on Apple Silicon

Meeting targets:

- Chrome browser meetings
- Opera browser meetings
- Yandex Browser meetings
- Yandex Telemost in browser after QA

Physical audio classes:

- built-in microphone/speakers
- wired headsets
- USB microphones
- USB headsets
- Bluetooth headsets
- AirPods-class devices

## Release Candidate Gates

- Both virtual devices appear after install or after a clearly requested restart.
- The app never shows `ready` before both mic and speaker synthetic route tests
  pass.
- At least one approved browser meeting validation path passes for each
  officially supported browser target.
- Remote meeting audio is not present in the virtual microphone path.
- Local mic and remote speaker tracks are captured separately.
- Wired 60-minute calls remain aligned within 100 ms with dropped frames below
  0.1%.
- Bluetooth and AirPods-class 60-minute calls remain usable with dropped frames
  below 0.5%.
- A 5-minute network/server outage does not interrupt live passthrough.
- Capture can be stopped in one interaction from a visible local surface.
- Updates defer or require explicit safe timing during active calls.
- Uninstall removes app-managed artifacts where OS permits and truthfully reports
  manual cleanup.
- Diagnostics contain no raw audio, transcript text, credentials, tokens, or
  signed URLs by default.

## Best-Effort Labeling

Any meeting target, physical device, or OS version outside this matrix must be
labeled best-effort unless a later spec adds it to the official QA matrix.

## Defect Severity Rules

P0:

- invisible or silent active capture
- no one-action stop during active capture
- remote audio loops into virtual microphone
- passthrough fails during normal supported call flow
- virtual devices fail to install or uninstall on supported macOS
- diagnostics expose forbidden content

P1:

- route verification gives false `ready`
- degraded/missing track is not visible before finalization
- update interrupts active call
- local buffer pressure can cause silent data loss

P2:

- confusing recovery copy
- unsupported targets not clearly labeled best-effort
- non-color accessibility cue missing from non-critical state
