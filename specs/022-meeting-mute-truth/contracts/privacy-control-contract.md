# Contract: Product Privacy Control

## Control States

The native desktop capture session exposes these product-owned controls:

- `Record`: starts a visible local recording.
- `Pause`: suppresses/redacts local microphone samples while recording remains
  active.
- `Resume`: returns local microphone samples to ordinary capture.
- `Stop`: ends recording and finalizes the local artifact.

`Pause` is not the same as third-party meeting-app mute. UI, metadata, and
diagnostics must keep those concepts separate.

## State Transitions

```text
idle
  -> detecting
  -> ready
  -> starting
  -> active
  -> paused
  -> active
  -> stopping
  -> stopped
```

Allowed transition requirements:

- `active -> paused` records a `ProductPrivacySegment` start event.
- `paused -> active` records the segment end and resume event.
- `paused -> stopping` records the segment end and stop event.
- Stop remains available while paused.
- Active visible indicator remains visible while paused.

## Local Microphone Treatment

During `paused` intervals:

- live local microphone speech must not be written as ordinary accepted mic
  audio;
- the preferred treatment is silence/redaction to preserve track duration and
  timeline alignment;
- no raw paused audio is retained in diagnostics or evidence;
- `incoming.wav` continues only if the active recording remains otherwise
  valid and user-visible.

## Acceptance Rules

- A pause interval passes only when the final manifest includes a matching
  `ProductPrivacySegment` and local mic audio for that interval is
  silenced/redacted.
- A pause interval fails if the app stores ordinary local mic speech for that
  interval.
- The UI may say product-owned pause was applied; it must not say third-party
  meeting-app mute was respected unless adapter evidence exists.
